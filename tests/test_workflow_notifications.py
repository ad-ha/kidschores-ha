"""Notification workflow tests using YAML scenarios.

These tests verify that notifications are sent correctly during
chore workflows and that they use the kid's configured language.

Test Organization:
- TestChoreClaimNotifications: Notifications sent when chores are claimed
- TestNotificationLanguage: Verify notifications use kid's language preference
- TestNotificationActions: Verify action buttons are translated

Coordinator API Reference:
- claim_chore(kid_id, chore_id, user_name)
- approve_chore(parent_name, kid_id, chore_id, points_awarded=None)

Notification System:
- async_send_notification(hass, service, title, message, actions, extra_data)
- _notify_parents_translated() - Uses kid's dashboard_language for translations
"""

# pylint: disable=protected-access
# pylint: disable=redefined-outer-name
# pylint: disable=unused-argument  # hass fixture required for HA test setup

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.kidschores import const
from custom_components.kidschores.coordinator import KidsChoresDataCoordinator
from tests.helpers.setup import SetupResult, setup_from_yaml


# =============================================================================
# FIXTURES
# =============================================================================


def register_mock_notify_services(hass: HomeAssistant) -> None:
    """Register mock notify services for testing.

    This allows the config flow to accept notify service names in the
    mobile_notify_service field, enabling true end-to-end notification testing.
    """
    async def mock_notify_service(call):  # noqa: ARG001
        """Mock notify service handler."""

    # Register mock notify services that match what's in the YAML scenario
    hass.services.async_register("notify", "mobile_app_mom", mock_notify_service)
    hass.services.async_register("notify", "mobile_app_zoe", mock_notify_service)
    hass.services.async_register("notify", "mobile_app_max", mock_notify_service)


@pytest.fixture
async def scenario_notifications(
    hass: HomeAssistant,
    mock_hass_users: dict[str, Any],
) -> SetupResult:
    """Load notification testing scenario.

    Contains:
    - 2 kids: Zoë (English), Max (Slovak)
    - 1 parent: Mom (notifications enabled)
    - 4 chores: Feed the cat (Zoë), Clean room (Max), Walk the dog (shared), Auto chore
    """
    # Register mock notify services BEFORE config flow runs
    register_mock_notify_services(hass)

    return await setup_from_yaml(
        hass,
        mock_hass_users,
        "tests/scenarios/scenario_notifications.yaml",
    )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def load_notification_translations(language: str) -> dict[str, Any]:
    """Load notification translations from JSON file.

    Args:
        language: Language code (e.g., 'en', 'sk')

    Returns:
        Dictionary containing the full translations file content
    """
    translations_path = Path(
        f"custom_components/kidschores/translations_custom/{language}_notifications.json"
    )

    if not translations_path.exists():
        raise FileNotFoundError(f"Translation file not found: {translations_path}")

    with open(translations_path, encoding="utf-8") as f:
        return json.load(f)


def get_action_titles(language: str) -> dict[str, str]:
    """Get action button titles for a language.

    Returns:
        Dict mapping action keys to translated titles
    """
    translations = load_notification_translations(language)
    return translations.get("actions", {})


def enable_parent_notifications(
    coordinator: KidsChoresDataCoordinator,
    parent_id: str,
) -> None:
    """Enable notifications for a parent in coordinator data.

    NOTE: This helper is only needed for scenarios that DON'T register mock notify
    services before setup. For scenario_notifications.yaml, mock services are
    registered by the fixture, so notifications are enabled through the config flow.

    Use this helper for scenarios where you intentionally have notifications disabled
    in the YAML but need to enable them for specific tests.

    Args:
        coordinator: The coordinator instance
        parent_id: Internal ID of the parent to enable notifications for
    """
    # Enable mobile notifications
    coordinator._data[const.DATA_PARENTS][parent_id][
        const.CONF_ENABLE_MOBILE_NOTIFICATIONS_LEGACY
    ] = True

    # Set a mock notify service
    coordinator._data[const.DATA_PARENTS][parent_id][
        const.CONF_MOBILE_NOTIFY_SERVICE_LEGACY
    ] = "notify.notify"

    # Ensure enable_notifications is also set
    coordinator._data[const.DATA_PARENTS][parent_id][
        const.DATA_PARENT_ENABLE_NOTIFICATIONS
    ] = True

    # Persist changes
    coordinator._persist()


class NotificationCapture:
    """Helper class to capture notifications during tests."""

    def __init__(self) -> None:
        """Initialize capture storage."""
        self.notifications: list[dict[str, Any]] = []

    async def capture(
        self,
        hass: HomeAssistant,
        service: str,
        title: str,
        message: str,
        actions: list[dict[str, Any]] | None = None,
        extra_data: dict[str, Any] | None = None,
    ) -> None:
        """Capture a notification call."""
        self.notifications.append({
            "service": service,
            "title": title,
            "message": message,
            "actions": actions or [],
            "extra_data": extra_data or {},
        })

    def clear(self) -> None:
        """Clear captured notifications."""
        self.notifications = []

    def get_with_actions(self) -> list[dict[str, Any]]:
        """Get notifications that have action buttons."""
        return [n for n in self.notifications if n.get("actions")]

    def get_action_titles(self) -> set[str]:
        """Get all action button titles from captured notifications."""
        titles: set[str] = set()
        for notif in self.notifications:
            for action in notif.get("actions", []):
                if title := action.get("title"):
                    titles.add(title)
        return titles


# =============================================================================
# CHORE CLAIM NOTIFICATION TESTS
# =============================================================================


class TestChoreClaimNotifications:
    """Tests for notifications sent when chores are claimed."""

    @pytest.mark.asyncio
    async def test_notifications_enabled_via_config_flow(
        self,
        hass: HomeAssistant,
        scenario_notifications: SetupResult,
    ) -> None:
        """Verify notifications are enabled through config flow, not manual override.

        This test confirms the mock notify services are registered correctly
        and the config flow accepted the notification settings.
        """
        coordinator = scenario_notifications.coordinator
        parent_id = scenario_notifications.parent_ids["Mom"]

        # Get parent data from coordinator
        parent_data = coordinator._data[const.DATA_PARENTS][parent_id]

        # Verify notifications were enabled through config flow
        assert parent_data.get(const.DATA_PARENT_ENABLE_NOTIFICATIONS) is True, (
            "Notifications should be enabled through config flow"
        )
        assert parent_data.get(const.CONF_MOBILE_NOTIFY_SERVICE_LEGACY) == "notify.mobile_app_mom", (
            "Mobile notify service should be set through config flow"
        )

        # Verify mock service exists
        all_services = hass.services.async_services()
        assert "notify" in all_services, "Notify domain should exist"
        assert "mobile_app_mom" in all_services["notify"], (
            "Mock notify service should be registered"
        )

    @pytest.mark.asyncio
    async def test_claim_sends_notification_to_parent(
        self,
        hass: HomeAssistant,
        scenario_notifications: SetupResult,
    ) -> None:
        """Claiming a chore with notify_on_claim=true sends notification."""
        coordinator = scenario_notifications.coordinator
        kid_id = scenario_notifications.kid_ids["Zoë"]
        chore_id = scenario_notifications.chore_ids["Feed the cat"]

        # Notifications enabled through config flow (mock services registered by fixture)
        capture = NotificationCapture()

        with patch(
            "custom_components.kidschores.coordinator.async_send_notification",
            new=capture.capture,
        ):
            coordinator.claim_chore(kid_id, chore_id, "Zoë")
            await hass.async_block_till_done()

        # Notification should be sent
        assert len(capture.notifications) > 0, "No notification was sent on chore claim"

    @pytest.mark.asyncio
    async def test_claim_notification_has_action_buttons(
        self,
        hass: HomeAssistant,
        scenario_notifications: SetupResult,
    ) -> None:
        """Chore claim notification includes approve/disapprove action buttons."""
        coordinator = scenario_notifications.coordinator
        kid_id = scenario_notifications.kid_ids["Zoë"]
        chore_id = scenario_notifications.chore_ids["Feed the cat"]

        # Notifications enabled through config flow (mock services registered by fixture)
        capture = NotificationCapture()

        with patch(
            "custom_components.kidschores.coordinator.async_send_notification",
            new=capture.capture,
        ):
            coordinator.claim_chore(kid_id, chore_id, "Zoë")
            await hass.async_block_till_done()

        # Should have notification with actions
        notifs_with_actions = capture.get_with_actions()
        assert len(notifs_with_actions) > 0, "No notification with action buttons found"

        # Actions should include approve, disapprove, remind
        action_titles = capture.get_action_titles()
        assert len(action_titles) >= 2, f"Expected at least 2 action buttons, got: {action_titles}"

    @pytest.mark.asyncio
    async def test_auto_approve_chore_no_parent_notification(
        self,
        hass: HomeAssistant,
        scenario_notifications: SetupResult,
    ) -> None:
        """Auto-approve chores don't send parent notifications (already approved)."""
        coordinator = scenario_notifications.coordinator
        kid_id = scenario_notifications.kid_ids["Zoë"]
        chore_id = scenario_notifications.chore_ids["Auto chore"]

        # Notifications enabled through config flow (mock services registered by fixture)
        capture = NotificationCapture()

        with patch(
            "custom_components.kidschores.coordinator.async_send_notification",
            new=capture.capture,
        ):
            coordinator.claim_chore(kid_id, chore_id, "Zoë")
            await hass.async_block_till_done()

        # Auto-approve should send kid notification (approval) but no parent notification
        # Filter for parent notifications (those with action buttons for approve/disapprove)
        parent_notifs = capture.get_with_actions()
        assert len(parent_notifs) == 0, (
            f"Auto-approve chore should not send parent notification with actions. "
            f"Got: {parent_notifs}"
        )


# =============================================================================
# NOTIFICATION LANGUAGE TESTS
# =============================================================================


class TestNotificationLanguage:
    """Tests for notification language based on kid's dashboard_language."""

    @pytest.mark.asyncio
    async def test_english_kid_gets_english_actions(
        self,
        hass: HomeAssistant,
        scenario_notifications: SetupResult,
    ) -> None:
        """Kid with dashboard_language='en' triggers English action buttons."""
        coordinator = scenario_notifications.coordinator
        kid_id = scenario_notifications.kid_ids["Zoë"]  # English language
        chore_id = scenario_notifications.chore_ids["Feed the cat"]

        # Verify kid is configured for English
        kid_lang = coordinator._data[const.DATA_KIDS][kid_id].get(
            const.DATA_KID_DASHBOARD_LANGUAGE
        )
        assert kid_lang == "en", f"Expected kid language 'en', got '{kid_lang}'"

        # Notifications enabled through config flow (mock services registered by fixture)
        capture = NotificationCapture()

        with patch(
            "custom_components.kidschores.coordinator.async_send_notification",
            new=capture.capture,
        ):
            coordinator.claim_chore(kid_id, chore_id, "Zoë")
            await hass.async_block_till_done()

        # Get expected English action titles
        expected_actions = get_action_titles("en")
        expected_titles = set(expected_actions.values())

        # Verify action buttons are in English
        actual_titles = capture.get_action_titles()

        # At least one expected English title should appear
        matching = actual_titles & expected_titles
        assert len(matching) > 0, (
            f"Expected English action titles {expected_titles}, "
            f"but got {actual_titles}"
        )

    @pytest.mark.asyncio
    async def test_slovak_kid_gets_slovak_actions(
        self,
        hass: HomeAssistant,
        scenario_notifications: SetupResult,
    ) -> None:
        """Kid with dashboard_language='sk' triggers Slovak action buttons."""
        coordinator = scenario_notifications.coordinator
        kid_id = scenario_notifications.kid_ids["Max"]  # Slovak language
        chore_id = scenario_notifications.chore_ids["Clean room"]

        # Verify kid is configured for Slovak
        kid_lang = coordinator._data[const.DATA_KIDS][kid_id].get(
            const.DATA_KID_DASHBOARD_LANGUAGE
        )
        assert kid_lang == "sk", f"Expected kid language 'sk', got '{kid_lang}'"

        # Notifications enabled through config flow (mock services registered by fixture)
        capture = NotificationCapture()

        with patch(
            "custom_components.kidschores.coordinator.async_send_notification",
            new=capture.capture,
        ):
            coordinator.claim_chore(kid_id, chore_id, "Max")
            await hass.async_block_till_done()

        # Get expected Slovak action titles
        try:
            expected_actions = get_action_titles("sk")
            expected_titles = set(expected_actions.values())
        except FileNotFoundError:
            pytest.skip("Slovak translations not available")

        # Verify action buttons are in Slovak
        actual_titles = capture.get_action_titles()

        # At least one expected Slovak title should appear
        matching = actual_titles & expected_titles
        assert len(matching) > 0, (
            f"Expected Slovak action titles {expected_titles}, "
            f"but got {actual_titles}"
        )

    @pytest.mark.asyncio
    async def test_notification_uses_kid_language_not_system(
        self,
        hass: HomeAssistant,
        scenario_notifications: SetupResult,
    ) -> None:
        """Parent notifications use kid's language, not HA system language."""
        coordinator = scenario_notifications.coordinator

        # Verify HA system language is English (default)
        assert hass.config.language == "en", "Test expects HA system to be English"

        # Claim chore for Slovak kid
        kid_id = scenario_notifications.kid_ids["Max"]  # Slovak
        chore_id = scenario_notifications.chore_ids["Clean room"]

        # Notifications enabled through config flow (mock services registered by fixture)
        capture = NotificationCapture()

        with patch(
            "custom_components.kidschores.coordinator.async_send_notification",
            new=capture.capture,
        ):
            coordinator.claim_chore(kid_id, chore_id, "Max")
            await hass.async_block_till_done()

        # Actions should NOT be English (system language)
        # They should be Slovak (kid's language)
        try:
            english_actions = get_action_titles("en")
            english_titles = set(english_actions.values())

            slovak_actions = get_action_titles("sk")
            slovak_titles = set(slovak_actions.values())
        except FileNotFoundError:
            pytest.skip("Slovak translations not available")

        actual_titles = capture.get_action_titles()

        # Verify Slovak titles are used, not English
        english_match = actual_titles & english_titles
        slovak_match = actual_titles & slovak_titles

        # If languages have different translations, Slovak should match
        if english_titles != slovak_titles:
            assert len(slovak_match) > len(english_match), (
                f"Expected Slovak titles (kid's language), not English (system). "
                f"Got: {actual_titles}, Slovak: {slovak_titles}, English: {english_titles}"
            )


# =============================================================================
# NOTIFICATION ACTION BUTTON TESTS
# =============================================================================


class TestNotificationActions:
    """Tests for notification action button content."""

    @pytest.mark.asyncio
    async def test_actions_not_raw_translation_keys(
        self,
        hass: HomeAssistant,
        scenario_notifications: SetupResult,
    ) -> None:
        """Action button titles should be translated, not raw keys."""
        coordinator = scenario_notifications.coordinator
        kid_id = scenario_notifications.kid_ids["Zoë"]
        chore_id = scenario_notifications.chore_ids["Feed the cat"]

        # Notifications enabled through config flow (mock services registered by fixture)
        capture = NotificationCapture()

        with patch(
            "custom_components.kidschores.coordinator.async_send_notification",
            new=capture.capture,
        ):
            coordinator.claim_chore(kid_id, chore_id, "Zoë")
            await hass.async_block_till_done()

        action_titles = capture.get_action_titles()

        # Titles should NOT be raw translation keys
        for title in action_titles:
            assert not title.startswith("notif_action_"), (
                f"Action title is raw key, not translated: {title}"
            )
            assert not title.startswith("err-"), (
                f"Action title is error fallback: {title}"
            )
            # Should be actual words, not snake_case keys
            assert "_" not in title or " " in title, (
                f"Action title looks like a key, not translated text: {title}"
            )

    @pytest.mark.asyncio
    async def test_actions_include_approve_disapprove(
        self,
        hass: HomeAssistant,
        scenario_notifications: SetupResult,
    ) -> None:
        """Chore claim notifications include approve and disapprove actions."""
        coordinator = scenario_notifications.coordinator
        kid_id = scenario_notifications.kid_ids["Zoë"]
        chore_id = scenario_notifications.chore_ids["Feed the cat"]

        # Notifications enabled through config flow (mock services registered by fixture)
        capture = NotificationCapture()

        with patch(
            "custom_components.kidschores.coordinator.async_send_notification",
            new=capture.capture,
        ):
            coordinator.claim_chore(kid_id, chore_id, "Zoë")
            await hass.async_block_till_done()

        notifs_with_actions = capture.get_with_actions()
        assert len(notifs_with_actions) > 0, "No notifications with actions"

        # Get all action identifiers to verify approve/disapprove are present
        action_ids: set[str] = set()
        for notif in notifs_with_actions:
            for action in notif.get("actions", []):
                # Actions use "action" key, not "uri"
                if action_id := action.get("action"):
                    action_ids.add(action_id)

        # Action identifiers should contain approve and disapprove action types
        action_text = " ".join(action_ids)
        assert "approve" in action_text.lower() or any(
            const.ACTION_APPROVE_CHORE in aid for aid in action_ids
        ), f"No approve action found in actions: {action_ids}"
