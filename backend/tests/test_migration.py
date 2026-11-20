from pathlib import Path

MIGRATION = Path(__file__).parents[1] / "migrations" / "versions" / "20261103_0001_initial_schema.py"


def test_initial_migration_has_expected_revision():
    source = MIGRATION.read_text()
    assert "revision" in source and "20261103_0001" in source
    assert "down_revision: Union[str, None] = None" in source


def test_migration_defines_both_telemetry_functions_and_triggers():
    source = MIGRATION.read_text()
    assert "CREATE OR REPLACE FUNCTION enforce_telemetry_reading_value_type()" in source
    assert "CREATE OR REPLACE FUNCTION prevent_telemetry_metric_type_change()" in source
    assert "CREATE TRIGGER trg_telemetry_readings_value_type" in source
    assert "CREATE TRIGGER trg_telemetry_metrics_type_immutable" in source


def test_reading_trigger_checks_metric_type_and_locks_metric_row():
    source = MIGRATION.read_text()
    assert "FOR SHARE" in source
    assert "IF NOT FOUND THEN" in source
    assert "specified device type" in source
    assert "Telemetry value column does not match metric data_type" in source


def test_metric_type_change_is_prevented_after_readings_exist():
    source = MIGRATION.read_text()
    assert "Cannot change telemetry metric data_type after readings exist" in source
    assert "BEFORE UPDATE OF data_type ON telemetry_metrics" in source


def test_downgrade_removes_triggers_and_functions():
    source = MIGRATION.read_text()
    assert "DROP TRIGGER IF EXISTS trg_telemetry_metrics_type_immutable" in source
    assert "DROP TRIGGER IF EXISTS trg_telemetry_readings_value_type" in source
    assert "DROP FUNCTION IF EXISTS prevent_telemetry_metric_type_change" in source
    assert "DROP FUNCTION IF EXISTS enforce_telemetry_reading_value_type" in source


USER_SESSION_MIGRATION = (
    Path(__file__).parents[1]
    / "migrations"
    / "versions"
    / "20261103_0002_user_sessions.py"
)


def test_user_session_migration_has_correct_revision_chain():
    source = USER_SESSION_MIGRATION.read_text()

    assert 'revision: str = "20261103_0002"' in source
    assert 'down_revision: Union[str, None] = "20261103_0001"' in source


def test_user_session_migration_creates_required_schema():
    source = USER_SESSION_MIGRATION.read_text()

    assert 'op.create_table(\n        "user_sessions"' in source
    assert '"token_hash"' in source
    assert '"expires_at"' in source
    assert '"last_seen_at"' in source
    assert '"revoked_at"' in source
    assert "uq_user_sessions_token_hash" in source
    assert "ck_user_sessions_expiry_after_creation" in source
    assert "ix_user_sessions_user_expires" in source
    assert '["users.id"]' in source
    assert 'ondelete="CASCADE"' in source


def test_user_session_migration_has_downgrade():
    source = USER_SESSION_MIGRATION.read_text()

    assert "def downgrade() -> None:" in source
    assert '"ix_user_sessions_user_expires"' in source
    assert 'op.drop_table("user_sessions")' in source


PERMANENT_HISTORY_MIGRATION = (
    Path(__file__).parents[1]
    / "migrations"
    / "versions"
    / "20261104_0004_permanent_membership_history.py"
)


def test_permanent_history_migration_has_correct_revision_chain():
    source = PERMANENT_HISTORY_MIGRATION.read_text()
    assert 'revision: str = "20261104_0004"' in source
    assert 'down_revision: Union[str, None] = "20261103_0003"' in source


def test_permanent_history_migration_creates_history_and_indexes():
    source = PERMANENT_HISTORY_MIGRATION.read_text()
    assert '"membership_history"' in source
    assert "ix_membership_history_workspace_created" in source
    assert "ix_membership_history_membership_created" in source
    assert "ix_membership_history_membership_sequence" in source
    assert '"event_sequence"' in source
    assert "sa.BigInteger()" in source
    assert "sa.Identity(always=True)" in source
    assert "ix_membership_history_actor_created" in source
    assert "ix_membership_history_subject_created" in source


def test_permanent_history_migration_removes_audit_workspace_fk():
    source = PERMANENT_HISTORY_MIGRATION.read_text()
    assert '"audit_logs_workspace_id_fkey"' in source
    assert 'type_="foreignkey"' in source


def test_permanent_history_migration_protects_audit_tables():
    source = PERMANENT_HISTORY_MIGRATION.read_text()
    assert "CREATE OR REPLACE FUNCTION prevent_permanent_audit_mutation()" in source
    assert "BEFORE UPDATE OR DELETE" in source
    assert "BEFORE TRUNCATE" in source
    assert "CREATE TRIGGER trg_{table_name}_prevent_mutation" in source
    assert "CREATE TRIGGER trg_{table_name}_prevent_truncate" in source
    assert '("membership_history", "audit_logs")' in source


def test_permanent_history_migration_blocks_downgrade():
    source = PERMANENT_HISTORY_MIGRATION.read_text()
    assert "def downgrade() -> None:" in source
    assert "Migration 20261104_0004 is irreversible" in source
    assert "Downgrade would violate the permanent-retention policy." in source
    assert 'op.drop_table("membership_history")' not in source
    assert "op.create_foreign_key(" not in source


OWNER_INVARIANT_MIGRATION = (
    Path(__file__).parents[1]
    / "migrations"
    / "versions"
    / "20261104_0005_workspace_owner_invariant.py"
)


def test_owner_invariant_migration_has_correct_revision_chain():
    source = OWNER_INVARIANT_MIGRATION.read_text()

    assert 'revision: str = "20261104_0005"' in source
    assert 'down_revision: Union[str, None] = "20261104_0004"' in source


def test_owner_invariant_migration_creates_partial_unique_index():
    source = OWNER_INVARIANT_MIGRATION.read_text()

    assert '"uq_workspace_members_active_owner"' in source
    assert '"workspace_members"' in source
    assert 'unique=True' in source
    assert "role = 'owner' AND is_active IS TRUE" in source


def test_owner_invariant_migration_creates_deferred_constraint_trigger():
    source = OWNER_INVARIANT_MIGRATION.read_text()

    assert "CREATE CONSTRAINT TRIGGER trg_workspace_members_active_owner" in source
    assert "AFTER INSERT OR UPDATE OR DELETE" in source
    assert "DEFERRABLE INITIALLY DEFERRED" in source
    assert "FOR EACH ROW" in source
    assert "EXECUTE FUNCTION enforce_workspace_active_owner()" in source


def test_owner_invariant_function_checks_active_owner_with_advisory_lock():
    source = OWNER_INVARIANT_MIGRATION.read_text()

    assert "CREATE OR REPLACE FUNCTION enforce_workspace_active_owner()" in source
    assert "pg_advisory_xact_lock" in source
    assert "hashtextextended(target_workspace_id::text, 0)" in source
    assert "FROM workspaces" in source
    assert "FOR UPDATE" not in source
    assert source.index("PERFORM pg_advisory_xact_lock") < source.index(
        "PERFORM id"
    )
    assert "role = 'owner'" in source
    assert "is_active IS TRUE" in source
    assert "Workspace % must have at least one active owner" in source
    assert "ERRCODE = '23514'" in source


def test_owner_invariant_downgrade_removes_only_invariant_objects():
    source = OWNER_INVARIANT_MIGRATION.read_text()
    downgrade = source.split("def downgrade() -> None:", 1)[1]

    assert "DROP TRIGGER IF EXISTS trg_workspace_members_active_owner" in downgrade
    assert "DROP FUNCTION IF EXISTS enforce_workspace_active_owner()" in downgrade
    assert '"uq_workspace_members_active_owner"' in downgrade
    assert "DROP TABLE" not in downgrade
    assert "membership_history" not in downgrade
    assert "audit_logs" not in downgrade


MQTT_TOPIC_ROUTE_MIGRATION = (
    Path(__file__).parents[1]
    / "migrations"
    / "versions"
    / "20261112_0011_mqtt_topic_routes.py"
)


def test_mqtt_topic_route_migration_has_correct_revision_chain():
    source = MQTT_TOPIC_ROUTE_MIGRATION.read_text()

    assert 'revision: str = "20261112_0011"' in source
    assert 'down_revision: Union[str, None] = "20261105_0010"' in source


def test_mqtt_topic_route_migration_creates_expected_columns():
    source = MQTT_TOPIC_ROUTE_MIGRATION.read_text()

    assert 'op.create_table(\n        "mqtt_topic_routes"' in source
    for column in (
        '"id"',
        '"workspace_id"',
        '"device_id"',
        '"broker_key"',
        '"topic"',
        '"direction"',
        '"qos"',
        '"is_enabled"',
        '"created_at"',
        '"updated_at"',
    ):
        assert column in source

    assert "sa.String(80)" in source
    assert "sa.String(512)" in source
    assert "server_default=sa.text(\"true\")" in source
    assert "server_default=sa.func.now()" in source


def test_mqtt_topic_route_migration_creates_required_constraints():
    source = MQTT_TOPIC_ROUTE_MIGRATION.read_text()

    assert "fk_mqtt_topic_routes_workspace_device" in source
    assert '"devices.workspace_id", "devices.id"' in source
    assert 'ondelete="RESTRICT"' in source

    assert "uq_mqtt_topic_routes_broker_topic_direction" in source
    assert "ck_mqtt_topic_routes_direction" in source
    assert "ck_mqtt_topic_routes_qos" in source
    assert "ck_mqtt_topic_routes_broker_key_nonempty" in source
    assert "ck_mqtt_topic_routes_exact_topic" in source

    assert "position('+' in topic) = 0" in source
    assert "position('#' in topic) = 0" in source


def test_mqtt_topic_route_migration_creates_workspace_device_index():
    source = MQTT_TOPIC_ROUTE_MIGRATION.read_text()

    assert "ix_mqtt_topic_routes_workspace_device" in source
    assert '["workspace_id", "device_id", "is_enabled"]' in source


def test_mqtt_topic_route_downgrade_protects_existing_routes():
    source = MQTT_TOPIC_ROUTE_MIGRATION.read_text()
    downgrade = source.split("def downgrade() -> None:", 1)[1]

    assert "LOCK TABLE mqtt_topic_routes IN ACCESS EXCLUSIVE MODE" in downgrade
    assert "IF EXISTS (SELECT 1 FROM mqtt_topic_routes)" in downgrade
    assert "Cannot downgrade: MQTT topic routes exist" in downgrade

    assert downgrade.index("ACCESS EXCLUSIVE") < downgrade.index("IF EXISTS")
    assert downgrade.index("IF EXISTS") < downgrade.index("op.drop_index")
    assert downgrade.index("op.drop_index") < downgrade.index(
        'op.drop_table("mqtt_topic_routes")'
    )
