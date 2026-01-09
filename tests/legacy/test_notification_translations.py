"""Test notification action button translations.

Tests that action buttons in notifications (Approve, Disapprove, Remind)
are properly translated based on the kid's language preference.

These tests verify:
1. Notification system prerequisites (ha_user_id, notify_service, associated_kids)
2. Action buttons are translated to English when kid's language is "en"
3. Action buttons are translated to Slovak when kid's language is "sk"
4. Parent notifications use kid's language, not system language

Translation verification strategy: Tests load the actual translation files
dynamically rather than hardcoding expected text. This ensures tests only
fail if translations are missing or the notification system is broken,
not if translation content changes over time.

SKIPPED: Functionality now covered by modern tests in test_workflow_notifications.py:
- TestNotificationLanguage::test_english_kid_gets_english_actions
- TestNotificationLanguage::test_slovak_kid_gets_slovak_actions
- TestNotificationLanguage::test_notification_uses_kid_language_not_system
"""

# pylint: disable=protected-access,redefined-outer-name,unused-argument

import json
from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.skip(
    reason="Functionality covered by modern tests in test_workflow_notifications.py"
)

from custom_components.kidschores import const


def load_notification_translations(language: str) -> dict:
    """Load notification translations from JSON file for given language.

    Args:
        language: Language code (e.g., 'en', 'sk')

    Returns:
        Dictionary with translation keys and values, or empty dict if file not found
    """
    # Navigate from tests/legacy/ -> tests/ -> repo root -> custom_components/
    translations_dir = (
        Path(__file__).parent.parent.parent
        / "custom_components"
        / "kidschores"
        / "translations_custom"
    )
    translation_file = translations_dir / f"{language}_notifications.json"

    if not translation_file.exists():
        raise FileNotFoundError(f"Translation file not found: {translation_file}")

    with open(translation_file, "r", encoding="utf-8") as f:
        return json.load(f)


def get_expected_action_titles(language: str) -> dict[str, str]:
    """Get expected action button titles for a language.

    Loads from translation JSON and extracts action titles.

    Args:
        language: Language code (e.g., 'en', 'sk')

    Returns:
        Dict mapping action keys to translated titles:
        {
            'approve': 'Approve',      # or translated equivalent
            'disapprove': 'Disapprove', # or translated equivalent
            'remind_30': 'Remind in 30 min'  # or translated equivalent
        }
    """
    translations = load_notification_translations(language)
    actions = translations.get("actions", {})

    if not actions:
        raise ValueError(f"No 'actions' section found in {language}_notifications.json")

    return actions


@pytest.mark.asyncio
async def test_notification_action_translations_english(
    hass,
    scenario_full,
    mock_hass_users,
):
    """Test that action buttons are translated to English.

    Setup:
    - Use scenario_full (has multiple kids, parents, chores)
    - Configure parent with: associated_kids, enable_notifications, mobile_notify_service
    - Set kid's dashboard_language to "en"
    - Claim a chore (triggers parent notification with action buttons)

    Verify:
    - async_send_notification is called
    - Action buttons contain "Approve", "Disapprove", "Remind in 30 min"
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[const.DOMAIN][config_entry.entry_id][const.COORDINATOR]

    # Get IDs
    kid_id = name_to_id_map["kid:Zoë"]
    parent_id = name_to_id_map["parent:Môm Astrid Stârblüm"]
    # Use "Garage Cleanup" - assigned to Zoë, NOT auto-approve, NOT in chores_completed
    chore_id = name_to_id_map["chore:Garage Cleanup"]

    # === CRITICAL SETUP: Configure notification prerequisites ===

    # 1. Set kid's HA user ID (links HA user to kidschores kid profile)
    coordinator._data[const.DATA_KIDS][kid_id][const.DATA_KID_HA_USER_ID] = (
        mock_hass_users["kid1"].id
    )

    # 2. Set kid's language to English
    coordinator._data[const.DATA_KIDS][kid_id][const.DATA_KID_DASHBOARD_LANGUAGE] = "en"

    # 3. Configure parent with associated kid
    coordinator._data[const.DATA_PARENTS][parent_id][
        const.DATA_PARENT_ASSOCIATED_KIDS
    ] = [kid_id]

    # 4. Enable notifications for parent
    coordinator._data[const.DATA_PARENTS][parent_id][
        const.DATA_PARENT_ENABLE_NOTIFICATIONS
    ] = True

    # 5. Set mobile notification service for parent
    coordinator._data[const.DATA_PARENTS][parent_id][
        const.CONF_ENABLE_MOBILE_NOTIFICATIONS_LEGACY
    ] = True
    coordinator._data[const.DATA_PARENTS][parent_id][
        const.CONF_MOBILE_NOTIFY_SERVICE_LEGACY
    ] = "notify.notify"

    # 6. Ensure chore is NOT auto-approve and has notify_on_claim enabled
    coordinator._data[const.DATA_CHORES][chore_id][const.DATA_CHORE_AUTO_APPROVE] = (
        False
    )
    coordinator._data[const.DATA_CHORES][chore_id][const.DATA_CHORE_NOTIFY_ON_CLAIM] = (
        True
    )

    # Persist all changes
    coordinator._persist()

    # Track notifications sent
    notifications_sent = []

    async def capture_notification(
        hass_arg, service, title, message, actions=None, extra_data=None
    ):
        """Capture notification calls for verification."""
        notifications_sent.append(
            {
                "service": service,
                "title": title,
                "message": message,
                "actions": actions,
                "extra_data": extra_data,
            }
        )

    with patch(
        "custom_components.kidschores.coordinator.async_send_notification",
        new=capture_notification,
    ):
        # Claim chore - this triggers _notify_parents_translated with action buttons
        coordinator.claim_chore(
            kid_id=kid_id,
            chore_id=chore_id,
            user_name="Zoë",
        )
        await hass.async_block_till_done()

    # === VERIFICATION ===

    # 1. Verify notification was sent
    assert len(notifications_sent) > 0, (
        f"No notifications were captured. "
        f"Parent associated_kids: {coordinator._data[const.DATA_PARENTS][parent_id].get(const.DATA_PARENT_ASSOCIATED_KIDS)}, "
        f"Parent enable_notifications: {coordinator._data[const.DATA_PARENTS][parent_id].get(const.DATA_PARENT_ENABLE_NOTIFICATIONS)}, "
        f"Parent mobile_notify_service: {coordinator._data[const.DATA_PARENTS][parent_id].get(const.CONF_MOBILE_NOTIFY_SERVICE_LEGACY)}"
    )

    # 2. Find notification with actions
    notif_with_actions = None
    for notif in notifications_sent:
        if notif.get("actions"):
            notif_with_actions = notif
            break

    assert notif_with_actions is not None, (
        f"No notification with actions found. Captured notifications: {notifications_sent}"
    )

    # 3. Verify action buttons are translated to English
    # Load expected translations dynamically from en_notifications.json
    expected_actions = get_expected_action_titles("en")
    expected_titles = set(expected_actions.values())

    actions = notif_with_actions["actions"]
    actual_titles = {a.get("title", "") for a in actions if a.get("title")}

    # Verify all expected English translations appear in actions
    for expected_title in expected_titles:
        assert expected_title in actual_titles, (
            f"Expected action title '{expected_title}' not found in actual titles: {actual_titles}. "
            f"This indicates either the notification system didn't translate actions, "
            f"or the en_notifications.json 'actions' section was modified."
        )


@pytest.mark.asyncio
async def test_notification_action_translations_slovak(
    hass,
    scenario_full,
    mock_hass_users,
):
    """Test that action buttons are translated to Slovak.

    Same setup as English test, but with kid's language set to "sk".
    Verifies Slovak translations appear in action buttons.
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[const.DOMAIN][config_entry.entry_id][const.COORDINATOR]

    # Get IDs
    kid_id = name_to_id_map["kid:Zoë"]
    parent_id = name_to_id_map["parent:Môm Astrid Stârblüm"]
    # Use "Garage Cleanup" - assigned to Zoë, NOT auto-approve, NOT in chores_completed
    chore_id = name_to_id_map["chore:Garage Cleanup"]

    # === CRITICAL SETUP ===

    # 1. Set kid's HA user ID
    coordinator._data[const.DATA_KIDS][kid_id][const.DATA_KID_HA_USER_ID] = (
        mock_hass_users["kid1"].id
    )

    # 2. Set kid's language to SLOVAK
    coordinator._data[const.DATA_KIDS][kid_id][const.DATA_KID_DASHBOARD_LANGUAGE] = "sk"

    # 3. Configure parent with associated kid
    coordinator._data[const.DATA_PARENTS][parent_id][
        const.DATA_PARENT_ASSOCIATED_KIDS
    ] = [kid_id]

    # 4. Enable notifications for parent
    coordinator._data[const.DATA_PARENTS][parent_id][
        const.DATA_PARENT_ENABLE_NOTIFICATIONS
    ] = True

    # 5. Set mobile notification service for parent
    coordinator._data[const.DATA_PARENTS][parent_id][
        const.CONF_ENABLE_MOBILE_NOTIFICATIONS_LEGACY
    ] = True
    coordinator._data[const.DATA_PARENTS][parent_id][
        const.CONF_MOBILE_NOTIFY_SERVICE_LEGACY
    ] = "notify.notify"

    # 6. Ensure chore is NOT auto-approve and has notify_on_claim enabled
    coordinator._data[const.DATA_CHORES][chore_id][const.DATA_CHORE_AUTO_APPROVE] = (
        False
    )
    coordinator._data[const.DATA_CHORES][chore_id][const.DATA_CHORE_NOTIFY_ON_CLAIM] = (
        True
    )

    # Persist all changes
    coordinator._persist()

    # Track notifications sent
    notifications_sent = []

    async def capture_notification(
        hass_arg, service, title, message, actions=None, extra_data=None
    ):
        """Capture notification calls for verification."""
        notifications_sent.append(
            {
                "service": service,
                "title": title,
                "message": message,
                "actions": actions,
                "extra_data": extra_data,
            }
        )

    with patch(
        "custom_components.kidschores.coordinator.async_send_notification",
        new=capture_notification,
    ):
        # Claim chore - triggers parent notification
        coordinator.claim_chore(
            kid_id=kid_id,
            chore_id=chore_id,
            user_name="Zoë",
        )
        await hass.async_block_till_done()

    # === VERIFICATION ===

    assert len(notifications_sent) > 0, "No notifications were captured"

    notif_with_actions = None
    for notif in notifications_sent:
        if notif.get("actions"):
            notif_with_actions = notif
            break

    assert notif_with_actions is not None, (
        f"No notification with actions found. Captured: {notifications_sent}"
    )

    # Verify action buttons are translated to Slovak
    # Load expected translations dynamically from sk_notifications.json
    expected_actions = get_expected_action_titles("sk")
    expected_titles = set(expected_actions.values())

    actions = notif_with_actions["actions"]
    actual_titles = {a.get("title", "") for a in actions if a.get("title")}

    # Verify all expected Slovak translations appear in actions
    for expected_title in expected_titles:
        assert expected_title in actual_titles, (
            f"Expected Slovak action title '{expected_title}' not found in actual titles: {actual_titles}. "
            f"This indicates either the notification system didn't translate actions to Slovak, "
            f"or the sk_notifications.json 'actions' section was modified."
        )


@pytest.mark.asyncio
async def test_notification_uses_kid_language_not_system_language(
    hass,
    scenario_full,
    mock_hass_users,
):
    """Test that parent notifications use kid's language, not system language.

    This is the key behavior: even if HA system language is English,
    parent notifications should be in the kid's configured language.
    """
    config_entry, name_to_id_map = scenario_full
    coordinator = hass.data[const.DOMAIN][config_entry.entry_id][const.COORDINATOR]

    # Verify HA system language is English (default in tests)
    assert hass.config.language == "en", "Test expects HA system language to be English"

    # Get IDs
    kid_id = name_to_id_map["kid:Zoë"]
    parent_id = name_to_id_map["parent:Môm Astrid Stârblüm"]
    # Use "Garage Cleanup" - assigned to Zoë, NOT auto-approve, NOT in chores_completed
    chore_id = name_to_id_map["chore:Garage Cleanup"]

    # Configure kid with SLOVAK language (different from system)
    coordinator._data[const.DATA_KIDS][kid_id][const.DATA_KID_HA_USER_ID] = (
        mock_hass_users["kid1"].id
    )
    coordinator._data[const.DATA_KIDS][kid_id][const.DATA_KID_DASHBOARD_LANGUAGE] = "sk"

    # Configure parent
    coordinator._data[const.DATA_PARENTS][parent_id][
        const.DATA_PARENT_ASSOCIATED_KIDS
    ] = [kid_id]
    coordinator._data[const.DATA_PARENTS][parent_id][
        const.DATA_PARENT_ENABLE_NOTIFICATIONS
    ] = True
    coordinator._data[const.DATA_PARENTS][parent_id][
        const.CONF_ENABLE_MOBILE_NOTIFICATIONS_LEGACY
    ] = True
    coordinator._data[const.DATA_PARENTS][parent_id][
        const.CONF_MOBILE_NOTIFY_SERVICE_LEGACY
    ] = "notify.notify"

    # Configure chore
    coordinator._data[const.DATA_CHORES][chore_id][const.DATA_CHORE_AUTO_APPROVE] = (
        False
    )
    coordinator._data[const.DATA_CHORES][chore_id][const.DATA_CHORE_NOTIFY_ON_CLAIM] = (
        True
    )

    coordinator._persist()

    notifications_sent = []

    async def capture_notification(
        hass_arg, service, title, message, actions=None, extra_data=None
    ):
        notifications_sent.append(
            {
                "title": title,
                "message": message,
                "actions": actions,
            }
        )

    with patch(
        "custom_components.kidschores.coordinator.async_send_notification",
        new=capture_notification,
    ):
        coordinator.claim_chore(kid_id=kid_id, chore_id=chore_id, user_name="Zoë")
        await hass.async_block_till_done()

    assert len(notifications_sent) > 0, "No notifications captured"

    # The notification should be in Slovak (kid's language), NOT English (system language)
    notif = notifications_sent[0]

    # Check that Slovak text appears (not English)
    # Load expected Slovak translations dynamically
    expected_slovak_actions = get_expected_action_titles("sk")
    expected_slovak_titles = set(expected_slovak_actions.values())

    # Load English translations to ensure we DON'T see them
    expected_english_actions = get_expected_action_titles("en")
    english_titles = set(expected_english_actions.values())

    actions = notif.get("actions", [])
    if actions:
        actual_titles = {a.get("title", "") for a in actions if a.get("title")}

        # Should have Slovak titles, not English
        for slovak_title in expected_slovak_titles:
            assert slovak_title in actual_titles, (
                f"Expected Slovak '{slovak_title}', but got {actual_titles}. "
                f"System language is {hass.config.language}, kid language is 'sk'. "
                f"Parent notifications should use KID's language, not system language."
            )

        # Should NOT have English titles
        for english_title in english_titles:
            assert english_title not in actual_titles, (
                f"Should NOT have English '{english_title}' when kid's language is Slovak. "
                f"Got: {actual_titles}. Parent notifications must use kid's language, not system language."
            )
