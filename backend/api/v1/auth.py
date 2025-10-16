"""
Authentication API endpoints
用户认证和授权
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError, jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional
import logging

from database import get_db
from models.user import User
from config import settings
from schemas.user import UserCreate, UserResponse, PasswordChange, Token
from services.token_cache import get_token_cache

router = APIRouter()
logger = logging.getLogger(__name__)

# Password hashing functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码 - 使用bcrypt直接验证"""
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """生成密码哈希 - 使用bcrypt直接hash"""
    return bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRE_HOURS)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """获取当前用户 - 使用Redis缓存优化"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Step 1: 检查Redis缓存 (优先级最高)
        token_cache = get_token_cache()
        if token_cache:
            cached_user = await token_cache.get_cached_user(token)
            if cached_user:
                # 从缓存获取用户数据，避免数据库查询
                result = await db.execute(
                    select(User).where(User.id == cached_user["user_id"])
                )
                user = result.scalar_one_or_none()
                if user and user.is_active:
                    logger.debug(f"✅ Cache hit for user {user.username}")
                    return user
                else:
                    # 缓存的用户已被禁用或删除，失效缓存
                    await token_cache.invalidate_token(token)

        # Step 2: 缓存未命中，解析JWT token
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    # Step 3: 从数据库查询用户
    result = await db.execute(
        select(User).where(User.username == username)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    # Step 4: 查询成功后，缓存用户数据
    if token_cache and user:
        await token_cache.cache_token(
            token,
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_active": user.is_active
            }
        )
        logger.debug(f"📦 Cached user data for {user.username}")

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """用户注册"""
    try:
        # 检查用户名是否已存在
        result = await db.execute(
            select(User).where(User.username == user_data.username)
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Username already registered")

        # 检查邮箱是否已存在
        result = await db.execute(
            select(User).where(User.email == user_data.email)
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already registered")

        # 创建用户
        user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=get_password_hash(user_data.password),
            is_active=True,
            is_superuser=False
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        logger.info(f"New user registered: {user_data.username}")

        return user

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to register user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """用户登录 - 支持Token缓存"""
    try:
        # 查找用户
        result = await db.execute(
            select(User).where(User.username == form_data.username)
        )
        user = result.scalar_one_or_none()

        # 验证用户和密码
        if not user or not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(status_code=400, detail="Inactive user")

        # 更新最后登录时间
        user.last_login = datetime.now()
        await db.commit()

        # 创建访问令牌
        access_token = create_access_token(data={"sub": user.username})

        # 缓存token到Redis
        token_cache = get_token_cache()
        if token_cache:
            await token_cache.cache_token(
                access_token,
                {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "is_active": user.is_active
                }
            )
            logger.info(f"User logged in with token cache: {user.username}")
        else:
            logger.info(f"User logged in (no cache): {user.username}")

        return Token(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.model_validate(user)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to login: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """获取当前用户信息"""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "is_active": current_user.is_active,
        "is_superuser": current_user.is_superuser,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None
    }


@router.post("/logout")
async def logout(
    token: str = Depends(oauth2_scheme)
):
    """用户登出 - 使token失效"""
    token_cache = get_token_cache()
    if token_cache:
        await token_cache.invalidate_token(token)
        logger.info("User logged out, token invalidated")
        return {"message": "Logged out successfully"}
    else:
        # 如果Redis不可用，仍然返回成功（前端会删除token）
        logger.warning("Logout: Redis not available, token not cached")
        return {"message": "Logged out (Redis unavailable)"}


@router.put("/me/password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """修改密码 - 失效所有现有token"""
    try:
        # 验证旧密码
        if not verify_password(password_data.old_password, current_user.hashed_password):
            raise HTTPException(status_code=400, detail="Incorrect password")

        # 更新密码
        current_user.hashed_password = get_password_hash(password_data.new_password)
        await db.commit()

        # 失效该用户的所有token
        token_cache = get_token_cache()
        if token_cache:
            await token_cache.invalidate_user_tokens(current_user.id)
            logger.info(f"User {current_user.username} changed password, all tokens invalidated")
        else:
            logger.info(f"User {current_user.username} changed password")

        return {"message": "Password updated successfully. Please login again."}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to change password: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
