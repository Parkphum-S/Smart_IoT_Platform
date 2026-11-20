from pathlib import Path

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

from app.modules.devices.models import DeviceCredential


TABLE = DeviceCredential.__table__


def test_device_credential_has_expected_columns():
    expected = {
        "id",
        "workspace_id",
        "device_id",
        "broker_key",
        "credential_identifier",
        "credential_type",
        "secret_hash",
        "secret_reference",
        "created_at",
        "expires_at",
        "revoked_at",
        "credential_status",
        "rotated_at",
        "last_used_at",
    }

    assert set(TABLE.columns.keys()) == expected


def test_device_credential_has_named_primary_key():
    assert TABLE.primary_key.name == "pk_device_credentials"
    assert list(TABLE.primary_key.columns.keys()) == ["id"]


def test_device_credential_has_workspace_scoped_foreign_key():
    foreign_keys = [
        constraint
        for constraint in TABLE.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    ]

    assert len(foreign_keys) == 1

    fk = foreign_keys[0]
    assert fk.name == "fk_device_credentials_workspace_device"
    assert [element.parent.name for element in fk.elements] == [
        "workspace_id",
        "device_id",
    ]
    assert [element.target_fullname for element in fk.elements] == [
        "devices.workspace_id",
        "devices.id",
    ]
    assert fk.ondelete == "RESTRICT"


def test_device_credential_has_broker_scoped_unique_constraint():
    unique_constraints = [
        constraint
        for constraint in TABLE.constraints
        if isinstance(constraint, UniqueConstraint)
    ]

    assert len(unique_constraints) == 1

    unique = unique_constraints[0]
    assert unique.name == "uq_device_credentials_broker_identifier"
    assert list(unique.columns.keys()) == [
        "broker_key",
        "credential_identifier",
    ]


def test_device_credential_has_all_integrity_checks():
    expected = {
        "ck_device_credentials_broker_key_nonempty",
        "ck_device_credentials_identifier_nonempty",
        "ck_device_credentials_type_nonempty",
        "ck_device_credentials_exactly_one_secret",
        "ck_device_credentials_status",
        "ck_device_credentials_expiry_after_creation",
        "ck_device_credentials_revocation_consistency",
    }

    actual = {
        constraint.name
        for constraint in TABLE.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert actual == expected


def test_device_credential_has_expected_indexes():
    expected = {
        "ix_device_credentials_device_id",
        "ix_device_credentials_workspace_device_status",
    }

    actual = {index.name for index in TABLE.indexes}

    assert actual == expected

    composite_index = next(
        index
        for index in TABLE.indexes
        if index.name == "ix_device_credentials_workspace_device_status"
    )

    assert list(composite_index.columns.keys()) == [
        "workspace_id",
        "device_id",
        "credential_status",
    ]


def test_device_credential_has_expected_nullability_and_defaults():
    assert not TABLE.c.workspace_id.nullable
    assert not TABLE.c.device_id.nullable
    assert not TABLE.c.broker_key.nullable
    assert not TABLE.c.credential_identifier.nullable
    assert not TABLE.c.credential_type.nullable

    assert TABLE.c.secret_hash.nullable
    assert TABLE.c.secret_reference.nullable
    assert TABLE.c.expires_at.nullable
    assert TABLE.c.revoked_at.nullable
    assert TABLE.c.rotated_at.nullable
    assert TABLE.c.last_used_at.nullable

    status = TABLE.c.credential_status

    assert not status.nullable
    assert status.default.arg == "pending"
    assert status.server_default.arg == "pending"

    assert TABLE.c.created_at.server_default is not None


def test_device_credential_column_types():
    assert TABLE.c.broker_key.type.length == 80
    assert TABLE.c.credential_identifier.type.length == 160
    assert TABLE.c.credential_type.type.length == 40
    assert TABLE.c.secret_hash.type.length == 255
    assert TABLE.c.secret_reference.type.length == 512
    assert TABLE.c.credential_status.type.length == 20


def test_device_credential_migration_revision_and_safety_guard():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "20261112_0012_device_credential_schema.py"
    )

    source = migration_path.read_text()

    assert 'revision = "20261112_0012"' in source
    assert 'down_revision = "20261112_0011"' in source

    assert "LOCK TABLE device_credentials IN ACCESS EXCLUSIVE MODE" in source

    assert (
        "Cannot migrate device_credentials: existing rows require "
        "explicit broker identity mapping"
    ) in source

    assert (
        "Cannot downgrade device_credentials: rows contain broker identity data"
    ) in source

    assert "uq_device_credentials_broker_identifier" in source
    assert "fk_device_credentials_workspace_device" in source
