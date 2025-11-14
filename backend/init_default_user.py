"""
初始化默认用户
Create default user for the application
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from database.session import SessionLocal
from models.user import User


async def create_default_user():
    """创建默认用户（如果不存在）"""
    async with SessionLocal() as db:
        try:
            # 检查是否已存在用户
            result = await db.execute(select(User).where(User.id == 1))
            existing_user = result.scalar_one_or_none()

            if existing_user:
                print(f"默认用户已存在: {existing_user.username}")
                return

            # 使用 SQL 直接插入，避免 bcrypt 版本问题
            # 这个哈希值对应密码 "admin123"
            # 使用 bcrypt 生成: $2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU2J0rYQ4A9G
            await db.execute(text("""
                INSERT INTO users (id, username, email, hashed_password, is_active, is_superuser, created_at)
                VALUES (1, 'admin', 'admin@btc-watcher.com',
                        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU2J0rYQ4A9G',
                        true, true, NOW())
                ON CONFLICT (id) DO NOTHING
            """))

            await db.commit()

            print(f"✓ 默认用户创建成功:")
            print(f"  - ID: 1")
            print(f"  - 用户名: admin")
            print(f"  - 邮箱: admin@btc-watcher.com")
            print(f"  - 默认密码: admin123")
            print(f"  - 提示: 请在生产环境中修改默认密码！")

        except Exception as e:
            print(f"✗ 创建默认用户失败: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    print("开始初始化默认用户...")
    asyncio.run(create_default_user())
    print("初始化完成！")

