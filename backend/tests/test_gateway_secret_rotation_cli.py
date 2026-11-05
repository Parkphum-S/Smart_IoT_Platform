"""Unit tests for the internal gateway-secret rotation CLI."""

from contextlib import asynccontextmanager
import sys
from types import SimpleNamespace
from uuid import uuid4

import pytest

from scripts.gateway_secret_rotation import (
    check_key_retirement,
    main,
    rotate_workspace,
)


class FakeSession:
    def __init__(self, tracker):
        self.tracker = tracker

    async def __aenter__(self):
        self.tracker["sessions"] += 1
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def begin(self):
        tracker = self.tracker

        @asynccontextmanager
        async def transaction():
            tracker["transactions"] += 1
            try:
                yield
            except Exception:
                tracker["rollbacks"] += 1
                raise
            else:
                tracker["commits"] += 1

        return transaction()


class FakeSessionFactory:
    def __init__(self, tracker):
        self.tracker = tracker

    def __call__(self):
        return FakeSession(self.tracker)


class FakeRotationService:
    def __init__(self, counts):
        self.counts = iter(counts)
        self.calls = 0

    async def rotate_workspace_batch(
        self, session, *, workspace_id, batch_size
    ):
        self.calls += 1
        return SimpleNamespace(rotated_count=next(self.counts))


@pytest.mark.asyncio
async def test_each_batch_uses_its_own_committed_transaction():
    tracker = {
        "sessions": 0,
        "transactions": 0,
        "commits": 0,
        "rollbacks": 0,
    }
    service = FakeRotationService([2, 1, 0])

    total = await rotate_workspace(
        FakeSessionFactory(tracker),
        service,
        uuid4(),
        2,
        emit=lambda message: None,
    )

    assert total == 3
    assert service.calls == 3
    assert tracker == {
        "sessions": 3,
        "transactions": 3,
        "commits": 3,
        "rollbacks": 0,
    }


@pytest.mark.asyncio
async def test_failed_batch_rolls_back_and_stops_immediately():
    tracker = {
        "sessions": 0,
        "transactions": 0,
        "commits": 0,
        "rollbacks": 0,
    }

    class FailingService:
        def __init__(self):
            self.calls = 0

        async def rotate_workspace_batch(
            self, session, *, workspace_id, batch_size
        ):
            self.calls += 1
            if self.calls == 2:
                raise RuntimeError("simulated decryption failure")
            return SimpleNamespace(rotated_count=1)

    service = FailingService()

    with pytest.raises(RuntimeError, match="decryption failure"):
        await rotate_workspace(
            FakeSessionFactory(tracker),
            service,
            uuid4(),
            1,
            emit=lambda message: None,
        )

    assert service.calls == 2
    assert tracker == {
        "sessions": 2,
        "transactions": 2,
        "commits": 1,
        "rollbacks": 1,
    }



@pytest.mark.asyncio
async def test_retirement_check_rejects_unconfigured_version():
    tracker = {"sessions": 0, "transactions": 0, "commits": 0, "rollbacks": 0}

    class FakeRepository:
        async def get_key_version_counts(self, session):
            return {}

    with pytest.raises(ValueError, match="must remain configured"):
        await check_key_retirement(
            FakeSessionFactory(tracker),
            retire_version="old-key",
            active_version="new-key",
            configured_versions={"new-key"},
            repository=FakeRepository(),
        )

    assert tracker["sessions"] == 1


def test_main_does_not_print_internal_exception_details(monkeypatch, capsys):
    async def fail(_):
        raise RuntimeError("sensitive-marker-do-not-display")

    monkeypatch.setattr("scripts.gateway_secret_rotation.run", fail)
    monkeypatch.setattr(
        sys,
        "argv",
        ["gateway_secret_rotation", "check-key-usage", "--retire-version", "old-key"],
    )

    assert main() == 1

    captured = capsys.readouterr()
    assert "Gateway secret maintenance failed" in captured.err
    assert "sensitive-marker-do-not-display" not in captured.err
    assert "restricted application logs" not in captured.err


def test_main_interrupt_message_preserves_batch_commit_context(monkeypatch, capsys):
    async def interrupt(_):
        raise KeyboardInterrupt

    monkeypatch.setattr("scripts.gateway_secret_rotation.run", interrupt)
    monkeypatch.setattr(
        sys,
        "argv",
        ["gateway_secret_rotation", "check-key-usage", "--retire-version", "old-key"],
    )

    assert main() == 130

    captured = capsys.readouterr()
    assert "in-progress batch was rolled back" in captured.err
    assert "previously committed batches remain committed" in captured.err
