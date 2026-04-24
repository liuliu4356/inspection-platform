"""
Usage:
    python scripts/promote_user.py <username> [role]

Promote a user to the specified role (default: admin).
Requires a running database with the inspection_platform schema.

Examples:
    python scripts/promote_user.py alice admin
    python scripts/promote_user.py bob operator
"""
import argparse
import asyncio
import sys
from uuid import UUID

sys.path.insert(0, "backend")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings


async def promote( username: str, role_code: str) -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession)

    async with SessionLocal() as session:
        from app.models.user import Role, User, UserRole

        user_result = await session.execute(select(User).where(User.username == username))
        user = user_result.scalar_one_or_none()
        if user is None:
            print(f"Error: User '{username}' not found.")
            sys.exit(1)

        role_result = await session.execute(select(Role).where(Role.code == role_code))
        role = role_result.scalar_one_or_none()
        if role is None:
            print(f"Error: Role '{role_code}' not found. Available roles: admin, operator, viewer")
            sys.exit(1)

        # Check if already has this role
        existing = await session.execute(
            select(UserRole).where(
                UserRole.user_id == user.id, UserRole.role_id == role.id
            )
        )
        if existing.scalar_one_or_none() is not None:
            print(f"User '{username}' already has the '{role_code}' role.")
            return

        session.add(UserRole(user_id=user.id, role_id=role.id))
        await session.commit()

        # Show current roles
        role_result = await session.execute(
            select(Role)
            .join(UserRole, Role.id == UserRole.role_id)
            .where(UserRole.user_id == user.id)
        )
        roles = role_result.scalars().all()
        role_names = [r.name for r in roles]
        print(f"User '{username}' promoted to '{role_code}'.")
        print(f"Current roles: {', '.join(role_names)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Promote a user to a role")
    parser.add_argument("username", help="Username to promote")
    parser.add_argument(
        "role",
        nargs="?",
        default="admin",
        choices=["admin", "operator", "viewer"],
        help="Target role (default: admin)",
    )
    args = parser.parse_args()
    asyncio.run(promote(args.username, args.role))


if __name__ == "__main__":
    main()
