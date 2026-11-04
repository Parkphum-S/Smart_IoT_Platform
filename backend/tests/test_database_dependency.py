"""Tests for the database session and transaction dependency."""

from types import SimpleNamespace

import pytest

from app.api.deps import get_db_session


class FakeTransaction:
    def __init__(self):
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.committed = True
        else:
            self.rolled_back = True


class FakeSession:
    def __init__(self):
        self.transaction = FakeTransaction()

    def begin(self):
        return self.transaction


class FakeSessionContext:
    def __init__(self):
        self.session = FakeSession()
        self.closed = False

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc_value, traceback):
        self.closed = True


class FakeSessionFactory:
    def __init__(self):
        self.context = FakeSessionContext()

    def __call__(self):
        return self.context


@pytest.fixture
def fake_request():
    factory = FakeSessionFactory()
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(db_session_factory=factory)
        )
    )
    return request, factory


@pytest.mark.asyncio
async def test_database_session_is_injected(fake_request):
    request, factory = fake_request

    dependency = get_db_session(request)
    session = await anext(dependency)

    assert session is factory.context.session
    assert factory.context.session.transaction.committed is False

    with pytest.raises(StopAsyncIteration):
        await dependency.asend(None)

    assert factory.context.session.transaction.committed is True
    assert factory.context.session.transaction.rolled_back is False


@pytest.mark.asyncio
async def test_database_session_is_closed_after_request(fake_request):
    request, factory = fake_request

    dependency = get_db_session(request)
    await anext(dependency)

    assert factory.context.closed is False

    with pytest.raises(StopAsyncIteration):
        await dependency.asend(None)

    assert factory.context.closed is True


@pytest.mark.asyncio
async def test_database_transaction_rolls_back_on_exception(fake_request):
    request, factory = fake_request

    dependency = get_db_session(request)
    await anext(dependency)

    with pytest.raises(RuntimeError, match="operation failed"):
        await dependency.athrow(RuntimeError("operation failed"))

    transaction = factory.context.session.transaction
    assert transaction.committed is False
    assert transaction.rolled_back is True
    assert factory.context.closed is True
