#!/usr/bin/env python3
"""
Create a test user for E2E tests
"""
import asyncio
import bcrypt
from database.session import SessionLocal
from models.user import User
from sqlalchemy import select


def get_password_hash(password: str) -> str:
    """Generate password hash using bcrypt"""
    return bcrypt.hashpw(
        password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')


async def create_test_user():
    """Create or verify test user"""
    async with SessionLocal() as db:
        try:
            # Check if test_user exists
            result = await db.execute(
                select(User).where(User.username == 'test_user')
            )
            existing = result.scalar_one_or_none()

            if existing:
                print('✅ test_user already exists')
                print(f'   Username: {existing.username}')
                print(f'   Email: {existing.email}')
                return

            # Create test_user
            test_user = User(
                username='test_user',
                email='test_user_e2e@example.com',
                hashed_password=get_password_hash('test_password'),
                is_active=True,
                is_superuser=False
            )

            db.add(test_user)
            await db.commit()

            print('✅ Test user created successfully!')
            print('   Username: test_user')
            print('   Password: test_password')
            print('   Email: test_user_e2e@example.com')

        except Exception as e:
            print(f'❌ Error: {e}')
            await db.rollback()


if __name__ == '__main__':
    asyncio.run(create_test_user())
