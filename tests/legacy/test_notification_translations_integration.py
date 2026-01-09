"""Integration tests for notification action button translations.

This module tests that notification action buttons show translated text
instead of raw translation keys like 'notif_action_approve'.

Tests use the dynamic translation loading system to verify:
1. Action buttons have proper translation constants
2. Translations are loaded correctly from JSON files
3. Action titles resolve to human-readable text (not raw keys)

Focuses specifically on notification translation integration,
not config flow setup (see test_config_flow_fresh_start.py for that).
"""

import json
from pathlib import Path
from typing import Any, Dict

import pytest

from custom_components.kidschores import const


def load_notification_translations() -> Dict[str, Any]:
    """Load notification translations from JSON file dynamically.

    Returns:
        Dictionary containing the actions section from translations_custom/en_notifications.json

    Raises:
        FileNotFoundError: If en_notifications.json doesn't exist
        KeyError: If actions section is missing
    """
    translations_path = Path(
        "custom_components/kidschores/translations_custom/en_notifications.json"
    )

    if not translations_path.exists():
        raise FileNotFoundError(f"Translation file not found: {translations_path}")

    with open(translations_path, "r", encoding="utf-8") as f:
        translations = json.load(f)

    if "actions" not in translations:
        raise KeyError("Missing 'actions' section in en_notifications.json")

    return translations["actions"]


def get_expected_action_titles() -> Dict[str, str]:
    """Get expected action button titles from translation file.

    Returns:
        Mapping of action constants to expected translated titles
    """
    actions = load_notification_translations()

    return {
        const.TRANS_KEY_NOTIF_ACTION_APPROVE: actions.get("approve", "err-approve"),
        const.TRANS_KEY_NOTIF_ACTION_DISAPPROVE: actions.get(
            "disapprove", "err-disapprove"
        ),
        const.TRANS_KEY_NOTIF_ACTION_REMIND_30: actions.get(
            "remind_30", "err-remind_30"
        ),
    }


@pytest.mark.asyncio
async def test_action_approve_translation_loaded() -> None:
    """Test that 'approve' action has proper translation key and loads correctly."""

    # Test that constant exists and has expected value
    assert hasattr(const, "TRANS_KEY_NOTIF_ACTION_APPROVE")
    assert const.TRANS_KEY_NOTIF_ACTION_APPROVE == "notif_action_approve"

    # Test that translation loads from JSON
    expected_titles = get_expected_action_titles()
    assert const.TRANS_KEY_NOTIF_ACTION_APPROVE in expected_titles

    approve_title = expected_titles[const.TRANS_KEY_NOTIF_ACTION_APPROVE]
    assert approve_title != "err-approve", "Translation missing for 'approve' action"
    assert len(approve_title) > 0, "Empty translation for 'approve' action"
    assert approve_title != "approve", "Translation should be more than just the key"


@pytest.mark.asyncio
async def test_action_disapprove_translation_loaded() -> None:
    """Test that 'disapprove' action has proper translation key and loads correctly."""

    # Test that constant exists and has expected value
    assert hasattr(const, "TRANS_KEY_NOTIF_ACTION_DISAPPROVE")
    assert const.TRANS_KEY_NOTIF_ACTION_DISAPPROVE == "notif_action_disapprove"

    # Test that translation loads from JSON
    expected_titles = get_expected_action_titles()
    assert const.TRANS_KEY_NOTIF_ACTION_DISAPPROVE in expected_titles

    disapprove_title = expected_titles[const.TRANS_KEY_NOTIF_ACTION_DISAPPROVE]
    assert disapprove_title != "err-disapprove", (
        "Translation missing for 'disapprove' action"
    )
    assert len(disapprove_title) > 0, "Empty translation for 'disapprove' action"
    assert disapprove_title != "disapprove", (
        "Translation should be more than just the key"
    )


@pytest.mark.asyncio
async def test_action_remind_translation_loaded() -> None:
    """Test that 'remind_30' action has proper translation key and loads correctly."""

    # Test that constant exists and has expected value
    assert hasattr(const, "TRANS_KEY_NOTIF_ACTION_REMIND_30")
    assert const.TRANS_KEY_NOTIF_ACTION_REMIND_30 == "notif_action_remind_30"

    # Test that translation loads from JSON
    expected_titles = get_expected_action_titles()
    assert const.TRANS_KEY_NOTIF_ACTION_REMIND_30 in expected_titles

    remind_title = expected_titles[const.TRANS_KEY_NOTIF_ACTION_REMIND_30]
    assert remind_title != "err-remind_30", "Translation missing for 'remind_30' action"
    assert len(remind_title) > 0, "Empty translation for 'remind_30' action"
    assert remind_title != "remind_30", "Translation should be more than just the key"


# TODO: Add integration tests for actual notification sending with translated actions:
# - test_chore_approval_notification_with_translated_actions()
# - test_reward_claim_notification_with_translated_actions()
# - test_notification_action_buttons_in_real_scenarios()
