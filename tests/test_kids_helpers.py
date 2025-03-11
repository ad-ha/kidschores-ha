"""Test kids configuration helper functions.

Tests validate that config flow and options flow use the same centralized
helper functions for kids configuration, ensuring consistency.
"""

from custom_components.kidschores import const, flow_helpers as fh


def test_build_kids_data_with_all_values() -> None:
    """Test build_kids_data extracts all values correctly."""
    user_input = {
        const.CFOF_KIDS_INPUT_KID_NAME: "Sarah",
        const.CFOF_KIDS_INPUT_HA_USER: "user_123",
        const.CFOF_KIDS_INPUT_ENABLE_MOBILE_NOTIFICATIONS: True,
        const.CFOF_KIDS_INPUT_MOBILE_NOTIFY_SERVICE: "mobile_app_phone",
        const.CFOF_KIDS_INPUT_ENABLE_PERSISTENT_NOTIFICATIONS: True,
        const.CFOF_GLOBAL_INPUT_INTERNAL_ID: "test-kid-id-123",
    }

    result = fh.build_kids_data(user_input)

    assert "test-kid-id-123" in result
    kid_data = result["test-kid-id-123"]
    assert kid_data[const.DATA_KID_NAME] == "Sarah"
    assert kid_data[const.DATA_KID_HA_USER_ID] == "user_123"
    assert kid_data[const.DATA_KID_ENABLE_NOTIFICATIONS] is True
    assert kid_data[const.DATA_KID_MOBILE_NOTIFY_SERVICE] == "mobile_app_phone"
    assert kid_data[const.DATA_KID_USE_PERSISTENT_NOTIFICATIONS] is True
    assert kid_data[const.DATA_KID_INTERNAL_ID] == "test-kid-id-123"


def test_build_kids_data_generates_uuid_if_missing() -> None:
    """Test build_kids_data generates UUID when internal_id not provided."""
    user_input = {
        const.CFOF_KIDS_INPUT_KID_NAME: "Tommy",
    }

    result = fh.build_kids_data(user_input)

    # Should have one entry with a generated UUID
    assert len(result) == 1
    internal_id = list(result.keys())[0]
    assert len(internal_id) == 36  # UUID format
    assert result[internal_id][const.DATA_KID_NAME] == "Tommy"


def test_build_kids_data_with_defaults() -> None:
    """Test build_kids_data uses defaults for optional fields."""
    user_input = {
        const.CFOF_KIDS_INPUT_KID_NAME: "Alex",
        const.CFOF_GLOBAL_INPUT_INTERNAL_ID: "alex-id",
    }

    result = fh.build_kids_data(user_input)

    kid_data = result["alex-id"]
    assert kid_data[const.DATA_KID_NAME] == "Alex"
    assert kid_data[const.DATA_KID_HA_USER_ID] == const.SENTINEL_EMPTY
    assert kid_data[const.DATA_KID_ENABLE_NOTIFICATIONS] is True  # Default
    assert kid_data[const.DATA_KID_MOBILE_NOTIFY_SERVICE] == const.SENTINEL_EMPTY
    assert kid_data[const.DATA_KID_USE_PERSISTENT_NOTIFICATIONS] is True  # Default


def test_build_kids_data_strips_whitespace_from_name() -> None:
    """Test build_kids_data strips leading/trailing whitespace from name."""
    user_input = {
        const.CFOF_KIDS_INPUT_KID_NAME: "  Jordan  ",
        const.CFOF_GLOBAL_INPUT_INTERNAL_ID: "jordan-id",
    }

    result = fh.build_kids_data(user_input)

    assert result["jordan-id"][const.DATA_KID_NAME] == "Jordan"


def test_validate_kids_inputs_success() -> None:
    """Test validate_kids_inputs with valid input."""
    user_input = {
        const.CFOF_KIDS_INPUT_KID_NAME: "Emma",
    }

    errors = fh.validate_kids_inputs(user_input)

    assert errors == {}


def test_validate_kids_inputs_empty_name() -> None:
    """Test validate_kids_inputs rejects empty name."""
    user_input = {
        const.CFOF_KIDS_INPUT_KID_NAME: "",
    }

    errors = fh.validate_kids_inputs(user_input)

    assert const.CFOP_ERROR_KID_NAME in errors
    assert errors[const.CFOP_ERROR_KID_NAME] == const.TRANS_KEY_CFOF_INVALID_KID_NAME


def test_validate_kids_inputs_whitespace_only_name() -> None:
    """Test validate_kids_inputs rejects whitespace-only name."""
    user_input = {
        const.CFOF_KIDS_INPUT_KID_NAME: "   ",
    }

    errors = fh.validate_kids_inputs(user_input)

    assert const.CFOP_ERROR_KID_NAME in errors
    assert errors[const.CFOP_ERROR_KID_NAME] == const.TRANS_KEY_CFOF_INVALID_KID_NAME


def test_validate_kids_inputs_missing_name() -> None:
    """Test validate_kids_inputs handles missing name key."""
    user_input = {}

    errors = fh.validate_kids_inputs(user_input)

    assert const.CFOP_ERROR_KID_NAME in errors
    assert errors[const.CFOP_ERROR_KID_NAME] == const.TRANS_KEY_CFOF_INVALID_KID_NAME


def test_validate_kids_inputs_duplicate_name() -> None:
    """Test validate_kids_inputs detects duplicate names."""
    existing_kids = {
        "kid-1": {const.DATA_KID_NAME: "Sarah"},
        "kid-2": {const.DATA_KID_NAME: "Tommy"},
    }

    user_input = {
        const.CFOF_KIDS_INPUT_KID_NAME: "Sarah",  # Duplicate
    }

    errors = fh.validate_kids_inputs(user_input, existing_kids)

    assert const.CFOP_ERROR_KID_NAME in errors
    assert errors[const.CFOP_ERROR_KID_NAME] == const.TRANS_KEY_CFOF_DUPLICATE_KID


def test_validate_kids_inputs_allows_same_name_when_no_existing() -> None:
    """Test validate_kids_inputs allows name when no existing kids to check."""
    user_input = {
        const.CFOF_KIDS_INPUT_KID_NAME: "Sarah",
    }

    # No existing_kids parameter - should pass
    errors = fh.validate_kids_inputs(user_input)

    assert errors == {}


def test_validate_kids_inputs_allows_unique_name() -> None:
    """Test validate_kids_inputs allows unique name when checking existing kids."""
    existing_kids = {
        "kid-1": {const.DATA_KID_NAME: "Sarah"},
        "kid-2": {const.DATA_KID_NAME: "Tommy"},
    }

    user_input = {
        const.CFOF_KIDS_INPUT_KID_NAME: "Emma",  # Unique
    }

    errors = fh.validate_kids_inputs(user_input, existing_kids)

    assert errors == {}
