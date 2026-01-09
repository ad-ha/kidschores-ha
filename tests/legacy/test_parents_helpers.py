"""Test parents configuration helper functions.

Tests validate that config flow and options flow use the same centralized
helper functions for parents configuration, ensuring consistency.
"""

from custom_components.kidschores import const
from custom_components.kidschores import flow_helpers as fh


def test_build_parents_data_with_all_values() -> None:
    """Test build_parents_data extracts all values correctly."""
    user_input = {
        const.CFOF_PARENTS_INPUT_NAME: "Mom",
        const.CFOF_PARENTS_INPUT_HA_USER: "user_456",
        const.CFOF_PARENTS_INPUT_ASSOCIATED_KIDS: ["kid-1", "kid-2"],
        const.CFOF_PARENTS_INPUT_ENABLE_MOBILE_NOTIFICATIONS: True,
        const.CFOF_PARENTS_INPUT_MOBILE_NOTIFY_SERVICE: "mobile_app_iphone",
        const.CFOF_PARENTS_INPUT_ENABLE_PERSISTENT_NOTIFICATIONS: True,
        const.CFOF_GLOBAL_INPUT_INTERNAL_ID: "test-parent-id-456",
    }

    result = fh.build_parents_data(user_input)

    assert "test-parent-id-456" in result
    parent_data = result["test-parent-id-456"]
    assert parent_data[const.DATA_PARENT_NAME] == "Mom"
    assert parent_data[const.DATA_PARENT_HA_USER_ID] == "user_456"
    assert parent_data[const.DATA_PARENT_ASSOCIATED_KIDS] == ["kid-1", "kid-2"]
    assert parent_data[const.DATA_PARENT_ENABLE_NOTIFICATIONS] is True
    assert parent_data[const.DATA_PARENT_MOBILE_NOTIFY_SERVICE] == "mobile_app_iphone"
    assert parent_data[const.DATA_PARENT_USE_PERSISTENT_NOTIFICATIONS] is True
    assert parent_data[const.DATA_PARENT_INTERNAL_ID] == "test-parent-id-456"


def test_build_parents_data_generates_uuid_if_missing() -> None:
    """Test build_parents_data generates UUID when internal_id not provided."""
    user_input = {
        const.CFOF_PARENTS_INPUT_NAME: "Dad",
    }

    result = fh.build_parents_data(user_input)

    # Should have one entry with a generated UUID
    assert len(result) == 1
    internal_id = list(result.keys())[0]
    assert len(internal_id) == 36  # UUID format
    assert result[internal_id][const.DATA_PARENT_NAME] == "Dad"


def test_build_parents_data_with_defaults() -> None:
    """Test build_parents_data uses defaults for optional fields."""
    user_input = {
        const.CFOF_PARENTS_INPUT_NAME: "Grandma",
        const.CFOF_GLOBAL_INPUT_INTERNAL_ID: "grandma-id",
    }

    result = fh.build_parents_data(user_input)

    parent_data = result["grandma-id"]
    assert parent_data[const.DATA_PARENT_NAME] == "Grandma"
    assert parent_data[const.DATA_PARENT_HA_USER_ID] == const.SENTINEL_EMPTY
    assert parent_data[const.DATA_PARENT_ASSOCIATED_KIDS] == []
    assert parent_data[const.DATA_PARENT_ENABLE_NOTIFICATIONS] is True  # Default
    assert parent_data[const.DATA_PARENT_MOBILE_NOTIFY_SERVICE] == const.SENTINEL_EMPTY
    assert (
        parent_data[const.DATA_PARENT_USE_PERSISTENT_NOTIFICATIONS] is True
    )  # Default


def test_build_parents_data_strips_whitespace_from_name() -> None:
    """Test build_parents_data strips leading/trailing whitespace from name."""
    user_input = {
        const.CFOF_PARENTS_INPUT_NAME: "  Uncle Bob  ",
        const.CFOF_GLOBAL_INPUT_INTERNAL_ID: "bob-id",
    }

    result = fh.build_parents_data(user_input)

    assert result["bob-id"][const.DATA_PARENT_NAME] == "Uncle Bob"


def test_build_parents_data_with_empty_associated_kids() -> None:
    """Test build_parents_data handles empty associated kids list."""
    user_input = {
        const.CFOF_PARENTS_INPUT_NAME: "Aunt Sue",
        const.CFOF_PARENTS_INPUT_ASSOCIATED_KIDS: [],
        const.CFOF_GLOBAL_INPUT_INTERNAL_ID: "sue-id",
    }

    result = fh.build_parents_data(user_input)

    assert result["sue-id"][const.DATA_PARENT_ASSOCIATED_KIDS] == []


def test_validate_parents_inputs_success() -> None:
    """Test validate_parents_inputs with valid input."""
    user_input = {
        const.CFOF_PARENTS_INPUT_NAME: "Mom",
    }

    errors = fh.validate_parents_inputs(user_input)

    assert errors == {}


def test_validate_parents_inputs_empty_name() -> None:
    """Test validate_parents_inputs rejects empty name."""
    user_input = {
        const.CFOF_PARENTS_INPUT_NAME: "",
    }

    errors = fh.validate_parents_inputs(user_input)

    assert const.CFOP_ERROR_PARENT_NAME in errors
    assert (
        errors[const.CFOP_ERROR_PARENT_NAME] == const.TRANS_KEY_CFOF_INVALID_PARENT_NAME
    )


def test_validate_parents_inputs_whitespace_only_name() -> None:
    """Test validate_parents_inputs rejects whitespace-only name."""
    user_input = {
        const.CFOF_PARENTS_INPUT_NAME: "   ",
    }

    errors = fh.validate_parents_inputs(user_input)

    assert const.CFOP_ERROR_PARENT_NAME in errors
    assert (
        errors[const.CFOP_ERROR_PARENT_NAME] == const.TRANS_KEY_CFOF_INVALID_PARENT_NAME
    )


def test_validate_parents_inputs_missing_name() -> None:
    """Test validate_parents_inputs handles missing name key."""
    user_input = {}

    errors = fh.validate_parents_inputs(user_input)

    assert const.CFOP_ERROR_PARENT_NAME in errors
    assert (
        errors[const.CFOP_ERROR_PARENT_NAME] == const.TRANS_KEY_CFOF_INVALID_PARENT_NAME
    )


def test_validate_parents_inputs_duplicate_name() -> None:
    """Test validate_parents_inputs detects duplicate names."""
    existing_parents = {
        "parent-1": {const.DATA_PARENT_NAME: "Mom"},
        "parent-2": {const.DATA_PARENT_NAME: "Dad"},
    }

    user_input = {
        const.CFOF_PARENTS_INPUT_NAME: "Mom",  # Duplicate
    }

    errors = fh.validate_parents_inputs(user_input, existing_parents)

    assert const.CFOP_ERROR_PARENT_NAME in errors
    assert errors[const.CFOP_ERROR_PARENT_NAME] == const.TRANS_KEY_CFOF_DUPLICATE_PARENT


def test_validate_parents_inputs_allows_same_name_when_no_existing() -> None:
    """Test validate_parents_inputs allows name when no existing parents to check."""
    user_input = {
        const.CFOF_PARENTS_INPUT_NAME: "Mom",
    }

    # No existing_parents parameter - should pass
    errors = fh.validate_parents_inputs(user_input)

    assert errors == {}


def test_validate_parents_inputs_allows_unique_name() -> None:
    """Test validate_parents_inputs allows unique name when checking existing parents."""
    existing_parents = {
        "parent-1": {const.DATA_PARENT_NAME: "Mom"},
        "parent-2": {const.DATA_PARENT_NAME: "Dad"},
    }

    user_input = {
        const.CFOF_PARENTS_INPUT_NAME: "Grandpa",  # Unique
    }

    errors = fh.validate_parents_inputs(user_input, existing_parents)

    assert errors == {}
