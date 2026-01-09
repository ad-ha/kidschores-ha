"""Tests for flow_helpers.py backup functionality."""

# pylint: disable=redefined-outer-name  # Pytest fixtures
# pylint: disable=unused-argument  # Mock fixtures in test signatures

import datetime
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.kidschores.flow_helpers import (
    cleanup_old_backups,
    create_timestamped_backup,
    format_backup_age,
    validate_backup_json,
)

# ----------------------------------------------------------------------------------
# FIXTURES
# ----------------------------------------------------------------------------------


@pytest.fixture
def mock_storage_manager():
    """Create mock storage manager."""
    manager = MagicMock()
    manager.data = {
        "schema_version": 42,
        "kids": {"kid1": {"name": "Alice", "points": 100}},
        "chores": {"chore1": {"name": "Dishes", "points": 10}},
        "rewards": {},
    }
    manager.get_all_data.return_value = manager.data
    return manager


@pytest.fixture
def mock_hass():
    """Create mock Home Assistant instance."""
    hass = MagicMock()
    hass.config.path.side_effect = lambda *args: os.path.join(
        "/mock/.storage", *args[1:]
    )
    # Mock async_add_executor_job to return the result directly (simulating async execution)
    hass.async_add_executor_job = AsyncMock(side_effect=lambda func, *args: func(*args))
    return hass


# ----------------------------------------------------------------------------------
# TEST: create_timestamped_backup
# ----------------------------------------------------------------------------------


@patch("custom_components.kidschores.flow_helpers.dt_util.utcnow")
@patch("custom_components.kidschores.flow_helpers.shutil.copy2")
@patch("os.path.exists", return_value=True)
@patch("os.makedirs")
async def test_create_timestamped_backup_success(
    mock_makedirs, mock_exists, mock_copy, mock_utcnow, mock_hass, mock_storage_manager
):
    """Test successful backup creation."""
    # Setup
    mock_utcnow.return_value = datetime.datetime(
        2024, 12, 18, 15, 30, 45, tzinfo=datetime.timezone.utc
    )

    # Execute - create_timestamped_backup is now async
    filename = await create_timestamped_backup(
        mock_hass, mock_storage_manager, "recovery"
    )

    # Verify
    assert filename == "kidschores_data_2024-12-18_15-30-45_recovery"
    # Verify shutil.copy2 was called with the storage manager's path
    assert mock_copy.call_count == 1
    call_args = mock_copy.call_args[0]
    assert call_args[1] == "/mock/.storage/kidschores_data_2024-12-18_15-30-45_recovery"


@patch("custom_components.kidschores.flow_helpers.dt_util.utcnow")
@patch("custom_components.kidschores.flow_helpers.shutil.copy2")
@patch("os.path.exists", return_value=True)
@patch("os.makedirs")
async def test_create_timestamped_backup_all_tags(
    mock_makedirs, mock_exists, mock_copy, mock_utcnow, mock_hass, mock_storage_manager
):
    """Test backup creation with all tag types."""
    mock_utcnow.return_value = datetime.datetime(
        2024, 12, 18, 10, 0, 0, tzinfo=datetime.timezone.utc
    )

    tags = ["recovery", "removal", "reset", "pre-migration", "manual"]

    for tag in tags:
        filename = await create_timestamped_backup(mock_hass, mock_storage_manager, tag)
        assert filename == f"kidschores_data_2024-12-18_10-00-00_{tag}"
        assert mock_copy.call_count >= 1


@patch("builtins.open", side_effect=OSError("Disk full"))
async def test_create_timestamped_backup_write_failure(
    mock_file, mock_hass, mock_storage_manager
):
    """Test backup creation handles write failures gracefully."""
    filename = await create_timestamped_backup(
        mock_hass, mock_storage_manager, "recovery"
    )

    assert filename is None


async def test_create_timestamped_backup_no_data(mock_hass):
    """Test backup creation when no data available."""
    manager = MagicMock()
    manager.get_all_data.return_value = None

    filename = await create_timestamped_backup(mock_hass, manager, "recovery")

    assert filename is None


# ----------------------------------------------------------------------------------
# TEST: cleanup_old_backups
# ----------------------------------------------------------------------------------


@patch("custom_components.kidschores.flow_helpers.discover_backups")
@patch("os.remove")
async def test_cleanup_old_backups_respects_max_limit(
    mock_remove, mock_discover, mock_hass, mock_storage_manager
):
    """Test cleanup keeps newest N backups per tag."""
    # Setup: 5 recovery backups (keep newest 3)
    mock_discover.return_value = [
        {
            "filename": "kidschores_data_2024-12-18_15-00-00_recovery",
            "tag": "recovery",
            "timestamp": datetime.datetime(
                2024, 12, 18, 15, 0, 0, tzinfo=datetime.timezone.utc
            ),
            "age_hours": 1,
            "size_bytes": 1000,
        },
        {
            "filename": "kidschores_data_2024-12-18_14-00-00_recovery",
            "tag": "recovery",
            "timestamp": datetime.datetime(
                2024, 12, 18, 14, 0, 0, tzinfo=datetime.timezone.utc
            ),
            "age_hours": 2,
            "size_bytes": 1000,
        },
        {
            "filename": "kidschores_data_2024-12-18_13-00-00_recovery",
            "tag": "recovery",
            "timestamp": datetime.datetime(
                2024, 12, 18, 13, 0, 0, tzinfo=datetime.timezone.utc
            ),
            "age_hours": 3,
            "size_bytes": 1000,
        },
        {
            "filename": "kidschores_data_2024-12-18_12-00-00_recovery",
            "tag": "recovery",
            "timestamp": datetime.datetime(
                2024, 12, 18, 12, 0, 0, tzinfo=datetime.timezone.utc
            ),
            "age_hours": 4,
            "size_bytes": 1000,
        },
        {
            "filename": "kidschores_data_2024-12-18_11-00-00_recovery",
            "tag": "recovery",
            "timestamp": datetime.datetime(
                2024, 12, 18, 11, 0, 0, tzinfo=datetime.timezone.utc
            ),
            "age_hours": 5,
            "size_bytes": 1000,
        },
    ]

    # Execute: Keep newest 3
    await cleanup_old_backups(mock_hass, mock_storage_manager, max_backups=3)

    # Verify: Deleted oldest 2
    assert mock_remove.call_count == 2
    deleted_files = [call.args[0] for call in mock_remove.call_args_list]
    assert (
        "/mock/.storage/kidschores_data_2024-12-18_12-00-00_recovery" in deleted_files
    )
    assert (
        "/mock/.storage/kidschores_data_2024-12-18_11-00-00_recovery" in deleted_files
    )


@patch("custom_components.kidschores.flow_helpers.discover_backups")
@patch("os.remove")
async def test_cleanup_old_backups_never_deletes_permanent_tags(
    mock_remove, mock_discover, mock_hass, mock_storage_manager
):
    """Test cleanup never deletes pre-migration or manual backups."""
    # Setup: Mix of tags
    mock_discover.return_value = [
        {
            "filename": "kidschores_data_2024-12-18_15-00-00_recovery",
            "tag": "recovery",
            "timestamp": datetime.datetime(
                2024, 12, 18, 15, 0, 0, tzinfo=datetime.timezone.utc
            ),
            "age_hours": 1,
            "size_bytes": 1000,
        },
        {
            "filename": "kidschores_data_2024-12-18_10-00-00_pre-migration",
            "tag": "pre-migration",
            "timestamp": datetime.datetime(
                2024, 12, 18, 10, 0, 0, tzinfo=datetime.timezone.utc
            ),
            "age_hours": 6,
            "size_bytes": 1000,
        },
        {
            "filename": "kidschores_data_2024-12-18_09-00-00_manual",
            "tag": "manual",
            "timestamp": datetime.datetime(
                2024, 12, 18, 9, 0, 0, tzinfo=datetime.timezone.utc
            ),
            "age_hours": 7,
            "size_bytes": 1000,
        },
        {
            "filename": "kidschores_data_2024-12-18_08-00-00_recovery",
            "tag": "recovery",
            "timestamp": datetime.datetime(
                2024, 12, 18, 8, 0, 0, tzinfo=datetime.timezone.utc
            ),
            "age_hours": 8,
            "size_bytes": 1000,
        },
    ]

    # Execute: Keep only 1 per tag
    await cleanup_old_backups(mock_hass, mock_storage_manager, max_backups=1)

    # Verify: Only deleted old recovery backup
    assert mock_remove.call_count == 1
    deleted_file = mock_remove.call_args_list[0].args[0]
    assert "kidschores_data_2024-12-18_08-00-00_recovery" in deleted_file


@patch("custom_components.kidschores.flow_helpers.discover_backups")
@patch("os.remove")
async def test_cleanup_old_backups_disabled_when_zero(
    mock_remove, mock_discover, mock_hass, mock_storage_manager
):
    """Test cleanup is disabled when max_backups is 0."""
    mock_discover.return_value = [
        {
            "filename": "kidschores_data_2024-12-18_15-00-00_recovery",
            "tag": "recovery",
            "timestamp": datetime.datetime(
                2024, 12, 18, 15, 0, 0, tzinfo=datetime.timezone.utc
            ),
            "age_hours": 1,
            "size_bytes": 1000,
        }
    ]

    # Execute
    await cleanup_old_backups(mock_hass, mock_storage_manager, max_backups=0)

    # Verify: No deletions
    mock_remove.assert_not_called()


@patch("custom_components.kidschores.flow_helpers.discover_backups")
@patch("os.remove", side_effect=OSError("Permission denied"))
async def test_cleanup_old_backups_continues_on_error(
    mock_remove, mock_discover, mock_hass, mock_storage_manager
):
    """Test cleanup continues even if individual deletion fails."""
    # Setup: 3 old backups
    mock_discover.return_value = [
        {
            "filename": "kidschores_data_2024-12-18_15-00-00_recovery",
            "tag": "recovery",
            "timestamp": datetime.datetime(
                2024, 12, 18, 15, 0, 0, tzinfo=datetime.timezone.utc
            ),
            "age_hours": 1,
            "size_bytes": 1000,
        },
        {
            "filename": "kidschores_data_2024-12-18_14-00-00_recovery",
            "tag": "recovery",
            "timestamp": datetime.datetime(
                2024, 12, 18, 14, 0, 0, tzinfo=datetime.timezone.utc
            ),
            "age_hours": 2,
            "size_bytes": 1000,
        },
        {
            "filename": "kidschores_data_2024-12-18_13-00-00_recovery",
            "tag": "recovery",
            "timestamp": datetime.datetime(
                2024, 12, 18, 13, 0, 0, tzinfo=datetime.timezone.utc
            ),
            "age_hours": 3,
            "size_bytes": 1000,
        },
    ]

    # Execute: Keep only 1 (should try to delete 2, both fail)
    await cleanup_old_backups(mock_hass, mock_storage_manager, max_backups=1)

    # Verify: Attempted to delete both old backups despite failures
    assert mock_remove.call_count == 2


@patch("custom_components.kidschores.flow_helpers.discover_backups")
@patch("os.remove")
async def test_cleanup_old_backups_handles_non_integer_max_backups(
    mock_remove, mock_discover, mock_hass, mock_storage_manager
):
    """Test cleanup handles string/float max_backups values (defensive type coercion).

    Verifies fix for TypeError: slice indices must be integers or None.
    Bug occurred when config entry options stored max_backups as string.
    Function now coerces to int defensively before slice operations.
    """
    # Setup: 5 recovery backups
    mock_discover.return_value = [
        {
            "filename": "kidschores_data_2024-12-18_15-00-00_recovery",
            "tag": "recovery",
            "timestamp": datetime.datetime(
                2024, 12, 18, 15, 0, 0, tzinfo=datetime.timezone.utc
            ),
            "age_hours": 1,
            "size_bytes": 1000,
        },
        {
            "filename": "kidschores_data_2024-12-18_14-00-00_recovery",
            "tag": "recovery",
            "timestamp": datetime.datetime(
                2024, 12, 18, 14, 0, 0, tzinfo=datetime.timezone.utc
            ),
            "age_hours": 2,
            "size_bytes": 1000,
        },
        {
            "filename": "kidschores_data_2024-12-18_13-00-00_recovery",
            "tag": "recovery",
            "timestamp": datetime.datetime(
                2024, 12, 18, 13, 0, 0, tzinfo=datetime.timezone.utc
            ),
            "age_hours": 3,
            "size_bytes": 1000,
        },
        {
            "filename": "kidschores_data_2024-12-18_12-00-00_recovery",
            "tag": "recovery",
            "timestamp": datetime.datetime(
                2024, 12, 18, 12, 0, 0, tzinfo=datetime.timezone.utc
            ),
            "age_hours": 4,
            "size_bytes": 1000,
        },
        {
            "filename": "kidschores_data_2024-12-18_11-00-00_recovery",
            "tag": "recovery",
            "timestamp": datetime.datetime(
                2024, 12, 18, 11, 0, 0, tzinfo=datetime.timezone.utc
            ),
            "age_hours": 5,
            "size_bytes": 1000,
        },
    ]

    # Test with string value (as might come from options flow)
    # This previously caused: TypeError: slice indices must be integers or None
    await cleanup_old_backups(mock_hass, mock_storage_manager, max_backups="3")

    # Verify: Correctly interpreted "3" as integer and deleted oldest 2
    assert mock_remove.call_count == 2
    deleted_files = [call.args[0] for call in mock_remove.call_args_list]
    assert (
        "/mock/.storage/kidschores_data_2024-12-18_12-00-00_recovery" in deleted_files
    )
    assert (
        "/mock/.storage/kidschores_data_2024-12-18_11-00-00_recovery" in deleted_files
    )

    # Reset mock for second test with float
    mock_remove.reset_mock()

    # Test with float value (edge case)
    await cleanup_old_backups(mock_hass, mock_storage_manager, max_backups=2.0)

    # Verify: Correctly interpreted 2.0 as integer and deleted oldest 3
    assert mock_remove.call_count == 3


# ----------------------------------------------------------------------------------
# TEST: discover_backups
# ----------------------------------------------------------------------------------


# ----------------------------------------------------------------------------------
# TEST: format_backup_age
# ----------------------------------------------------------------------------------


def test_format_backup_age_minutes():
    """Test formatting for ages less than 1 hour."""
    assert format_backup_age(0.5) == "30 minutes ago"
    assert format_backup_age(0.016666) == "1 minute ago"
    assert format_backup_age(0.1) == "6 minutes ago"


def test_format_backup_age_hours():
    """Test formatting for ages between 1 and 24 hours."""
    assert format_backup_age(1) == "1 hour ago"
    assert format_backup_age(5) == "5 hours ago"
    assert format_backup_age(23.5) == "23 hours ago"


def test_format_backup_age_days():
    """Test formatting for ages between 1 day and 1 week."""
    assert format_backup_age(24) == "1 day ago"
    assert format_backup_age(48) == "2 days ago"
    assert format_backup_age(72) == "3 days ago"
    assert format_backup_age(167) == "6 days ago"


def test_format_backup_age_weeks():
    """Test formatting for ages greater than 1 week."""
    assert format_backup_age(168) == "1 week ago"
    assert format_backup_age(336) == "2 weeks ago"
    assert format_backup_age(720) == "4 weeks ago"


# ----------------------------------------------------------------------------------
# TEST: validate_backup_json
# ----------------------------------------------------------------------------------


def test_validate_backup_json_valid_minimal():
    """Test validation accepts minimal valid backup."""
    json_str = json.dumps(
        {
            "schema_version": 42,
            "kids": {"kid1": {"name": "Alice"}},
        }
    )

    assert validate_backup_json(json_str) is True


def test_validate_backup_json_valid_complete():
    """Test validation accepts complete backup with all entity types."""
    json_str = json.dumps(
        {
            "schema_version": 42,
            "kids": {},
            "parents": {},
            "chores": {},
            "rewards": {},
            "bonuses": {},
            "penalties": {},
            "achievements": {},
            "challenges": {},
            "badges": {},
        }
    )

    assert validate_backup_json(json_str) is True


def test_validate_backup_json_missing_version():
    """Test validation accepts JSON missing schema_version key (legacy format)."""
    json_str = json.dumps({"kids": {"kid1": {"name": "Alice"}}})

    # Old backups without schema_version are accepted - they will be migrated
    assert validate_backup_json(json_str) is True


def test_validate_backup_json_missing_entity_types():
    """Test validation rejects JSON with schema_version but no entity types."""
    json_str = json.dumps({"schema_version": 42})

    assert validate_backup_json(json_str) is False


def test_validate_backup_json_legacy_v3_format():
    """Test validation accepts legacy KC 3.0 format without schema_version."""
    # Simulates old KC 3.0 backup with badges as list, no schema_version
    json_str = json.dumps(
        {
            "kids": [{"name": "Alice", "points": 100, "badges": []}],
            "chores": [{"name": "Dishes", "points": 10}],
            "rewards": [],
        }
    )

    # Should accept - migration will handle conversion
    assert validate_backup_json(json_str) is True


def test_validate_backup_json_not_dict():
    """Test validation rejects JSON that is not a dictionary."""
    json_str = json.dumps(["not", "a", "dict"])

    assert validate_backup_json(json_str) is False


def test_validate_backup_json_invalid_syntax():
    """Test validation rejects malformed JSON."""
    json_str = '{"schema_version": 42, "kids": {'  # Missing closing braces

    assert validate_backup_json(json_str) is False


def test_validate_backup_json_empty_string():
    """Test validation rejects empty string."""
    assert validate_backup_json("") is False


def test_validate_backup_json_null_string():
    """Test validation rejects null JSON."""
    assert validate_backup_json("null") is False


def test_validate_backup_json_store_v1_format():
    """Test validation accepts Store version 1 format (KC 3.0/3.1/4.0beta1)."""
    # Simulates Home Assistant Store format with version 1 wrapper
    json_str = json.dumps(
        {
            "version": 1,
            "minor_version": 1,
            "key": "kidschores_data",
            "data": {
                "kids": {"kid1": {"name": "Alice", "points": 100}},
                "chores": {"chore1": {"name": "Dishes", "points": 10}},
                "rewards": {},
            },
        }
    )

    # Should accept - Store version 1 is supported
    assert validate_backup_json(json_str) is True


def test_validate_backup_json_store_v2_rejected():
    """Test validation rejects Store version 2 (unsupported future format)."""
    # Simulates hypothetical Store version 2
    json_str = json.dumps(
        {
            "version": 2,
            "minor_version": 0,
            "key": "kidschores_data",
            "data": {
                "kids": {"kid1": {"name": "Alice", "points": 100}},
                "chores": {},
            },
        }
    )

    # Should reject - only version 1 is supported
    assert validate_backup_json(json_str) is False


def test_validate_backup_json_store_missing_data_wrapper():
    """Test validation rejects Store format without data wrapper."""
    json_str = json.dumps(
        {
            "version": 1,
            "minor_version": 1,
            "key": "kidschores_data",
            # Missing "data" key
            "kids": {"kid1": {"name": "Alice"}},
        }
    )

    # Should reject - Store format must have "data" wrapper
    assert validate_backup_json(json_str) is False
