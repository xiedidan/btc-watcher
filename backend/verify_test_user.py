#!/usr/bin/env python3
"""
Verify test user credentials
"""
import asyncio
import bcrypt
from database.session import SessionLocal
from models.user import User
from sqlalchemy import select


async def verify_user():
    async with SessionLocal() as db:
        # Check for test_user
        result = await db.execute(
            select(User).where(User.username == 'test_user')
        )
        test_user = result.scalar_one_or_none()

        if test_user:
            print(f'✅ test_user exists:')
            print(f'   Username: {test_user.username}')
            print(f'   Email: {test_user.email}')

            # Try to verify password
            try:
                is_valid = bcrypt.checkpw(
                    'test_password'.encode('utf-8'),
                    test_user.hashed_password.encode('utf-8')
                )
                print(f'   Password "test_password" valid: {is_valid}')
            except Exception as e:
                print(f'   Error checking password: {e}')
        else:
            print('❌ test_user does not exist')

            # Check for test_alpha_user
            result = await db.execute(
                select(User).where(User.username == 'test_alpha_user')
            )
            alpha_user = result.scalar_one_or_none()

            if alpha_user:
                print(f'\n✅ test_alpha_user exists:')
                print(f'   Username: {alpha_user.username}')
                print(f'   Email: {alpha_user.email}')

                # Try password
                try:
                    is_valid = bcrypt.checkpw(
                        'test_password'.encode('utf-8'),
                        alpha_user.hashed_password.encode('utf-8')
                    )
                    print(f'   Password "test_password" valid: {is_valid}')

                    # Try alpha123
                    is_valid2 = bcrypt.checkpw(
                        'alpha123'.encode('utf-8'),
                        alpha_user.hashed_password.encode('utf-8')
                    )
                    print(f'   Password "alpha123" valid: {is_valid2}')
                except Exception as e:
                    print(f'   Error checking password: {e}')

                print('\n💡 You can update the E2E tests to use test_alpha_user')
                print('   Or create a new test_user account')

if __name__ == '__main__':
    asyncio.run(verify_user())
