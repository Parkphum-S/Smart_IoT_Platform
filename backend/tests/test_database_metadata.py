from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

from app.infrastructure.database.base import Base
from app.modules.users import models as users
from app.modules.devices import models as devices
from app.modules.telemetry import models as telemetry
from app.modules.monitoring import models as monitoring
from app.modules.automation import models as automation

EXPECTED_TABLES = {
    "users", "workspaces", "workspace_members", "user_sessions",
    "device_types", "devices", "device_credentials", "device_status",
    "rooms", "device_rooms", "device_groups", "device_group_members",
    "telemetry_metrics", "telemetry_readings",
    "device_events", "alert_rules", "alerts", "notifications", "audit_logs",
    "membership_history",
    "device_gateways", "device_gateway_members", "device_gateway_secrets",
    "automation_rules", "automation_conditions", "automation_actions",
    "automation_executions",
}


def test_all_expected_tables_are_registered():
    assert set(Base.metadata.tables) == EXPECTED_TABLES
    assert len(Base.metadata.tables) == 27


def test_every_table_has_a_primary_key():
    for table in Base.metadata.tables.values():
        assert len(table.primary_key.columns) >= 1, table.name


def test_all_foreign_keys_reference_registered_tables():
    for table in Base.metadata.tables.values():
        for constraint in table.foreign_key_constraints:
            for element in constraint.elements:
                assert element.column.table.name in Base.metadata.tables


def test_device_group_members_has_composite_primary_key():
    table = Base.metadata.tables["device_group_members"]
    assert set(table.primary_key.columns.keys()) == {"device_group_id", "device_id"}


def test_telemetry_readings_enforces_exactly_one_value():
    table = Base.metadata.tables["telemetry_readings"]
    checks = [c for c in table.constraints if isinstance(c, CheckConstraint)]
    assert any("num_nonnulls" in str(c.sqltext).lower() for c in checks)


def test_telemetry_readings_has_workspace_scoped_foreign_keys():
    table = Base.metadata.tables["telemetry_readings"]
    targets = {tuple(element.target_fullname for element in fk.elements) for fk in table.foreign_key_constraints}
    assert ("devices.workspace_id", "devices.id") in targets
    assert ("devices.id", "devices.device_type_id") in targets
    assert ("telemetry_metrics.device_type_id", "telemetry_metrics.id") in targets


def test_user_sessions_has_required_constraints_and_index():
    table = Base.metadata.tables["user_sessions"]

    unique_constraints = [
        constraint
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    ]
    assert any(
        constraint.name == "uq_user_sessions_token_hash"
        for constraint in unique_constraints
    )

    checks = [
        constraint
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    ]
    assert any(
        constraint.name == "ck_user_sessions_expiry_after_creation"
        for constraint in checks
    )

    assert "ix_user_sessions_user_expires" in {
        index.name for index in table.indexes
    }

    assert any(
        fk.target_fullname == "users.id"
        for fk in table.foreign_keys
    )


def test_membership_history_has_no_foreign_keys():
    table = Base.metadata.tables["membership_history"]
    assert not table.foreign_keys
    assert not table.foreign_key_constraints


def test_membership_history_has_permanent_record_fields():
    table = Base.metadata.tables["membership_history"]
    expected_columns = {
        "id", "workspace_id", "membership_id", "actor_id",
        "event_sequence", "subject_user_id", "event_type",
        "previous_role", "new_role", "details", "created_at",
    }
    assert set(table.columns.keys()) == expected_columns
    assert table.c.event_sequence.type.python_type is int
    assert table.c.event_sequence.identity is not None
    assert table.c.event_sequence.identity.always is True


def test_membership_history_has_expected_indexes():
    table = Base.metadata.tables["membership_history"]
    expected = {
        "ix_membership_history_workspace_created",
        "ix_membership_history_membership_created",
        "ix_membership_history_membership_sequence",
        "ix_membership_history_actor_created",
        "ix_membership_history_subject_created",
    }
    assert {index.name for index in table.indexes} == expected


def test_membership_history_has_role_and_event_constraints():
    table = Base.metadata.tables["membership_history"]
    checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert "ck_membership_history_event_type" in checks
    assert "ck_membership_history_previous_role" in checks
    assert "ck_membership_history_new_role" in checks


def test_audit_log_workspace_id_has_no_foreign_key():
    table = Base.metadata.tables["audit_logs"]
    assert not table.c.workspace_id.foreign_keys
