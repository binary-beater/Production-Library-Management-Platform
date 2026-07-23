from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import BookCondition, UserRole, UserStatus
from app.models.book import Book
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.book_repository import BookRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository


@pytest.mark.asyncio
async def test_base_repository_crud(db_session: AsyncSession) -> None:
    # 1. Create Repository
    user_repo = UserRepository(db_session)

    # 2. Verify Create
    new_user = User(
        name="Test Dev",
        email="test_dev@example.com",
        password_hash="argon2hashpattern123",
        role=UserRole.MEMBER,
        status=UserStatus.ACTIVE,
    )
    saved_user = await user_repo.create(new_user)
    await db_session.flush()
    assert saved_user.id is not None
    assert saved_user.email == "test_dev@example.com"

    # 3. Verify Get By ID
    retrieved_user = await user_repo.get_by_id(saved_user.id)
    assert retrieved_user is not None
    assert retrieved_user.name == "Test Dev"

    # 4. Verify Update
    await user_repo.update(retrieved_user, update_data={"name": "Updated Dev"})
    await db_session.flush()

    updated_user = await user_repo.get_by_id(saved_user.id)
    assert updated_user is not None
    assert updated_user.name == "Updated Dev"

    # 5. Verify Get All
    all_users = await user_repo.get_all()
    assert len(all_users) >= 1

    # 6. Verify Delete
    delete_result = await user_repo.delete(saved_user.id)
    await db_session.flush()
    assert delete_result is True

    deleted_user = await user_repo.get_by_id(saved_user.id)
    assert deleted_user is None


@pytest.mark.asyncio
async def test_unique_constraint_email(db_session: AsyncSession) -> None:
    user_repo = UserRepository(db_session)

    user1 = User(
        name="Dev One",
        email="duplicate@example.com",
        password_hash="hash1",
    )
    await user_repo.create(user1)
    await db_session.flush()

    user2 = User(
        name="Dev Two",
        email="duplicate@example.com",
        password_hash="hash2",
    )
    await user_repo.create(user2)

    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_book_soft_delete(db_session: AsyncSession) -> None:
    book_repo = BookRepository(db_session)

    book = Book(
        isbn="123-456-789",
        title="Production Design",
        author="Architect",
        total_copies=5,
        available_copies=5,
        condition=BookCondition.NEW,
    )
    saved_book = await book_repo.create(book)
    await db_session.flush()

    # Check delete changes is_deleted to True
    delete_result = await book_repo.delete(saved_book.id)
    await db_session.flush()
    assert delete_result is True

    # Verify not queryable by standard repository methods
    retrieved = await book_repo.get_by_id(saved_book.id)
    assert retrieved is None

    # Verify it still physically exists in database by querying base metadata
    from sqlalchemy import select

    raw_result = await db_session.execute(select(Book).where(Book.id == str(saved_book.id)))
    phys_book = raw_result.scalar_one_or_none()
    assert phys_book is not None
    assert phys_book.is_deleted is True
    assert phys_book.deleted_at is not None


@pytest.mark.asyncio
async def test_refresh_token_cascade_on_user_delete(db_session: AsyncSession) -> None:
    user_repo = UserRepository(db_session)
    token_repo = RefreshTokenRepository(db_session)

    user = User(
        name="Token Owner",
        email="owner@example.com",
        password_hash="hash",
    )
    saved_user = await user_repo.create(user)
    await db_session.flush()

    token = RefreshToken(
        user_id=str(saved_user.id),
        token_hash="hashed_token_string",
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    saved_token = await token_repo.create(token)
    await db_session.flush()

    # Verify token exists
    assert await token_repo.get_by_id(saved_token.id) is not None

    # Delete user
    await user_repo.delete(saved_user.id)
    await db_session.flush()

    # Verify token is deleted via CASCADE
    deleted_token = await token_repo.get_by_id(saved_token.id)
    assert deleted_token is None
