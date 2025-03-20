# File: sensor.py
"""Sensors for the KidsChores integration.

This file defines all sensor entities for each Kid, Chore, Reward, and Badge.

Available Sensors:
01. ChoreStatusSensor
02. KidPointsSensor
03. KidMaxPointsEverSensor
04. CompletedChoresTotalSensor
05. CompletedChoresDailySensor
06. CompletedChoresWeeklySensor
07. CompletedChoresMonthlySensor
08. KidHighestBadgeSensor
09. BadgeSensor
10. PendingChoreApprovalsSensor
11. PendingRewardApprovalsSensor
12. SharedChoreGlobalStateSensor
13. RewardStatusSensor
14. PenaltyAppliesSensor
15. KidPointsEarnedDailySensor
16. KidPointsEarnedWeeklySensor
17. KidPointsEarnedMonthlySensor
18. AchievementSensor
19. ChallengeSensor
20. AchievementProgressSensor
21. ChallengeProgressSensor
22. KidHighestStreakSensor
23. BonusAppliesSensor
"""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util
from . import const
from .coordinator import KidsChoresDataCoordinator
from .kc_helpers import get_friendly_label


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    """Set up sensors for KidsChores integration."""
    data = hass.data[const.DOMAIN][entry.entry_id]
    coordinator: KidsChoresDataCoordinator = data[const.DATA_COORDINATOR]

    points_label = entry.options.get(
        const.CONF_POINTS_LABEL, const.DEFAULT_POINTS_LABEL
    )
    points_icon = entry.options.get(const.CONF_POINTS_ICON, const.DEFAULT_POINTS_ICON)
    entities = []

    # Sensor to detail number of Chores pending approval
    entities.append(PendingChoreApprovalsSensor(coordinator, entry))

    # Sensor to detail number of Rewards pending approval
    entities.append(PendingRewardApprovalsSensor(coordinator, entry))

    # For each kid, add standard sensors
    for kid_id, kid_info in coordinator.kids_data.items():
        kid_name = kid_info.get(const.DATA_KID_NAME, f"Kid {kid_id}")

        # Points counter sensor
        entities.append(
            KidPointsSensor(
                coordinator, entry, kid_id, kid_name, points_label, points_icon
            )
        )
        entities.append(
            CompletedChoresTotalSensor(coordinator, entry, kid_id, kid_name)
        )

        # Chores completed by each Kid during the day
        entities.append(
            CompletedChoresDailySensor(coordinator, entry, kid_id, kid_name)
        )

        # Chores completed by each Kid during the week
        entities.append(
            CompletedChoresWeeklySensor(coordinator, entry, kid_id, kid_name)
        )

        # Chores completed by each Kid during the month
        entities.append(
            CompletedChoresMonthlySensor(coordinator, entry, kid_id, kid_name)
        )

        # Kid Highest Badge
        entities.append(KidHighestBadgeSensor(coordinator, entry, kid_id, kid_name))

        # Poimts obtained per Kid during the day
        entities.append(
            KidPointsEarnedDailySensor(
                coordinator, entry, kid_id, kid_name, points_label, points_icon
            )
        )

        # Poimts obtained per Kid during the week
        entities.append(
            KidPointsEarnedWeeklySensor(
                coordinator, entry, kid_id, kid_name, points_label, points_icon
            )
        )

        # Poimts obtained per Kid during the month
        entities.append(
            KidPointsEarnedMonthlySensor(
                coordinator, entry, kid_id, kid_name, points_label, points_icon
            )
        )

        # Maximum Points ever obtained ny a kid
        entities.append(
            KidMaxPointsEverSensor(
                coordinator, entry, kid_id, kid_name, points_label, points_icon
            )
        )

        # Chore Claims and Approvals
        for chore_id, chore_info in coordinator.chores_data.items():
            if kid_id not in chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, []):
                continue
            chore_name = chore_info.get(const.DATA_CHORE_NAME, f"Chore {chore_id}")

        # Penalty Applies
        for penalty_id, penalty_info in coordinator.penalties_data.items():
            penalty_name = penalty_info.get(
                const.DATA_PENALTY_NAME, f"Penalty {penalty_id}"
            )
            entities.append(
                PenaltyAppliesSensor(
                    coordinator, entry, kid_id, kid_name, penalty_id, penalty_name
                )
            )

        # Bonus Applies
        for bonus_id, bonus_info in coordinator.bonuses_data.items():
            bonus_name = bonus_info.get(const.DATA_BONUS_NAME, f"Bonus {bonus_id}")
            entities.append(
                BonusAppliesSensor(
                    coordinator, entry, kid_id, kid_name, bonus_id, bonus_name
                )
            )

        # Achivement Progress per Kid
        for achievement_id, achievement in coordinator.achievements_data.items():
            if kid_id in achievement.get(const.DATA_ACHIEVEMENT_ASSIGNED_KIDS, []):
                achievement_name = achievement.get(
                    const.DATA_ACHIEVEMENT_NAME, f"Achievement {achievement_id}"
                )
                entities.append(
                    AchievementProgressSensor(
                        coordinator,
                        entry,
                        kid_id,
                        kid_name,
                        achievement_id,
                        achievement_name,
                    )
                )

        # Challenge Progress per Kid
        for challenge_id, challenge in coordinator.challenges_data.items():
            if kid_id in challenge.get(const.DATA_CHALLENGE_ASSIGNED_KIDS, []):
                challenge_name = challenge.get(
                    const.DATA_CHALLENGE_NAME, f"Challenge {challenge_id}"
                )
                entities.append(
                    ChallengeProgressSensor(
                        coordinator,
                        entry,
                        kid_id,
                        kid_name,
                        challenge_id,
                        challenge_name,
                    )
                )

        # Highest Streak Sensor per Kid
        entities.append(KidHighestStreakSensor(coordinator, entry, kid_id, kid_name))

    # For each chore assigned to each kid, add a ChoreStatusSensor
    for chore_id, chore_info in coordinator.chores_data.items():
        chore_name = chore_info.get(const.DATA_CHORE_NAME, f"Chore {chore_id}")
        assigned_kids_ids = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
        for kid_id in assigned_kids_ids:
            kid_name = coordinator._get_kid_name_by_id(kid_id) or f"Kid {kid_id}"
            entities.append(
                ChoreStatusSensor(
                    coordinator, entry, kid_id, kid_name, chore_id, chore_name
                )
            )

    # For each shared chore, add a global state sensor
    for chore_id, chore_info in coordinator.chores_data.items():
        if chore_info.get(const.DATA_CHORE_SHARED_CHORE, False):
            chore_name = chore_info.get(const.DATA_CHORE_NAME, f"Chore {chore_id}")
            entities.append(
                SharedChoreGlobalStateSensor(coordinator, entry, chore_id, chore_name)
            )

    # For each Reward, add a RewardStatusSensor
    for reward_id, reward_info in coordinator.rewards_data.items():
        reward_name = reward_info.get(const.DATA_REWARD_NAME, f"Reward {reward_id}")

        # For each kid, create the reward status sensor
        for kid_id, kid_info in coordinator.kids_data.items():
            kid_name = kid_info.get(const.DATA_KID_NAME, f"Kid {kid_id}")
            entities.append(
                RewardStatusSensor(
                    coordinator, entry, kid_id, kid_name, reward_id, reward_name
                )
            )

    # For each Badge, add a BadgeSensor
    for badge_id, badge_info in coordinator.badges_data.items():
        badge_name = badge_info.get(const.DATA_BADGE_NAME, f"Badge {badge_id}")
        entities.append(BadgeSensor(coordinator, entry, badge_id, badge_name))

    # For each Achievement, add an AchievementSensor
    for achievement_id, achievement in coordinator.achievements_data.items():
        achievement_name = achievement.get(
            const.DATA_ACHIEVEMENT_NAME, f"Achievement {achievement_id}"
        )
        entities.append(
            AchievementSensor(coordinator, entry, achievement_id, achievement_name)
        )

    # For each Challenge, add a ChallengeSensor
    for challenge_id, challenge in coordinator.challenges_data.items():
        challenge_name = challenge.get(
            const.DATA_CHALLENGE_NAME, f"Challenge {challenge_id}"
        )
        entities.append(
            ChallengeSensor(coordinator, entry, challenge_id, challenge_name)
        )

    async_add_entities(entities)


# ------------------------------------------------------------------------------------------
class ChoreStatusSensor(CoordinatorEntity, SensorEntity):
    """Sensor for chore status: pending/claimed/approved/etc."""

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_SENSOR_CHORE_STATUS_SENSOR

    def __init__(self, coordinator, entry, kid_id, kid_name, chore_id, chore_name):
        """Initialize the sensor."""

        super().__init__(coordinator)
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._chore_id = chore_id
        self._chore_name = chore_name
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_{chore_id}{const.SENSOR_KC_UID_SUFFIX_CHORE_STATUS_SENSOR}"
        self.entity_id = f"{const.SENSOR_KC_PREFIX}{kid_name}{const.SENSOR_KC_EID_MIDFIX_CHORE_STATUS_SENSOR}{chore_name}"
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_KID_NAME: kid_name,
            const.TRANS_KEY_SENSOR_ATTR_CHORE_NAME: chore_name,
        }

    @property
    def native_value(self):
        """Return the chore's state based on shared or individual tracking."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})

        # The status of the kids chore should always be their own status.
        # It's only global status that would show independent or in-part
        if self._chore_id in kid_info.get(const.DATA_KID_APPROVED_CHORES, []):
            return const.CHORE_STATE_APPROVED
        elif self._chore_id in kid_info.get(const.DATA_KID_CLAIMED_CHORES, []):
            return const.CHORE_STATE_CLAIMED
        elif self._chore_id in kid_info.get(const.DATA_KID_OVERDUE_CHORES, []):
            return const.CHORE_STATE_OVERDUE
        else:
            return const.CHORE_STATE_PENDING

    @property
    def extra_state_attributes(self):
        """Include points, description, etc."""
        chore_info = self.coordinator.chores_data.get(self._chore_id, {})
        shared = chore_info.get(const.DATA_CHORE_SHARED_CHORE, False)
        global_state = chore_info.get(const.DATA_CHORE_STATE, const.CHORE_STATE_UNKNOWN)

        assigned_kids_ids = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
        assigned_kids_names = [
            self.coordinator._get_kid_name_by_id(k_id) or f"Kid {k_id}"
            for k_id in assigned_kids_ids
        ]

        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        chore_streak_data = kid_info.get(const.DATA_KID_CHORE_STREAKS, {}).get(
            self._chore_id, {}
        )
        current_streak = chore_streak_data.get(
            const.DATA_KID_CURRENT_STREAK, const.DEFAULT_ZERO
        )
        highest_streak = chore_streak_data.get(
            const.DATA_KID_MAX_STREAK, const.DEFAULT_ZERO
        )

        stored_labels = chore_info.get(const.DATA_CHORE_LABELS, [])
        friendly_labels = [
            get_friendly_label(self.hass, label) for label in stored_labels
        ]

        attributes = {
            const.ATTR_KID_NAME: self._kid_name,
            const.ATTR_CHORE_NAME: self._chore_name,
            const.ATTR_DESCRIPTION: chore_info.get(
                const.DATA_CHORE_DESCRIPTION, const.CONF_EMPTY
            ),
            const.ATTR_CHORE_CLAIMS_COUNT: kid_info.get(
                const.DATA_KID_CHORE_CLAIMS, {}
            ).get(self._chore_id, const.DEFAULT_ZERO),
            const.ATTR_CHORE_APPROVALS_COUNT: kid_info.get(
                const.DATA_KID_CHORE_APPROVALS, {}
            ).get(self._chore_id, const.DEFAULT_ZERO),
            const.ATTR_CHORE_CURRENT_STREAK: current_streak,
            const.ATTR_CHORE_HIGHEST_STREAK: highest_streak,
            const.ATTR_SHARED_CHORE: shared,
            const.ATTR_GLOBAL_STATE: global_state,
            const.ATTR_RECURRING_FREQUENCY: chore_info.get(
                const.DATA_CHORE_RECURRING_FREQUENCY, const.CONF_NONE_TEXT
            ),
            const.ATTR_APPLICABLE_DAYS: chore_info.get(
                const.DATA_CHORE_APPLICABLE_DAYS, []
            ),
            const.ATTR_DUE_DATE: chore_info.get(
                const.DATA_CHORE_DUE_DATE, const.DUE_DATE_NOT_SET
            ),
            const.ATTR_DEFAULT_POINTS: chore_info.get(
                const.DATA_CHORE_DEFAULT_POINTS, const.DEFAULT_ZERO
            ),
            const.ATTR_PARTIAL_ALLOWED: chore_info.get(
                const.DATA_CHORE_PARTIAL_ALLOWED, False
            ),
            const.ATTR_ALLOW_MULTIPLE_CLAIMS_PER_DAY: chore_info.get(
                const.DATA_CHORE_ALLOW_MULTIPLE_CLAIMS_PER_DAY, False
            ),
            const.ATTR_ASSIGNED_KIDS: assigned_kids_names,
            const.ATTR_LABELS: friendly_labels,
        }

        if chore_info.get(const.DATA_CHORE_ALLOW_MULTIPLE_CLAIMS_PER_DAY, False):
            today_approvals = kid_info.get(
                const.DATA_KID_TODAY_CHORE_APPROVALS, {}
            ).get(self._chore_id, const.DEFAULT_ZERO)
            attributes[const.ATTR_CHORE_APPROVALS_TODAY] = today_approvals

        if (
            chore_info.get(const.DATA_CHORE_RECURRING_FREQUENCY)
            == const.FREQUENCY_CUSTOM
        ):
            attributes[const.ATTR_CUSTOM_FREQUENCY_INTERVAL] = chore_info.get(
                const.DATA_CHORE_CUSTOM_INTERVAL
            )
            attributes[const.ATTR_CUSTOM_FREQUENCY_UNIT] = chore_info.get(
                const.DATA_CHORE_CUSTOM_INTERVAL_UNIT
            )

        return attributes

    @property
    def icon(self):
        """Use the chore's custom icon if set, else fallback."""
        chore_info = self.coordinator.chores_data.get(self._chore_id, {})
        return chore_info.get(const.DATA_CHORE_ICON, const.DEFAULT_CHORE_SENSOR_ICON)


# ------------------------------------------------------------------------------------------
class KidPointsSensor(CoordinatorEntity, SensorEntity):
    """Sensor for a kid's total points balance."""

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_SENSOR_KID_POINTS_SENSOR

    def __init__(self, coordinator, entry, kid_id, kid_name, points_label, points_icon):
        """Initialize the sensor."""

        super().__init__(coordinator)
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._points_label = points_label
        self._points_icon = points_icon
        self._attr_unique_id = (
            f"{entry.entry_id}_{kid_id}{const.SENSOR_KC_UID_SUFFIX_KID_POINTS_SENSOR}"
        )
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_KID_NAME: kid_name,
            const.TRANS_KEY_SENSOR_ATTR_POINTS: self._points_label,
        }
        self.entity_id = f"{const.SENSOR_KC_PREFIX}{kid_name}{const.SENSOR_KC_EID_SUFFIX_KID_POINTS_SENSOR}"

    @property
    def native_value(self):
        """Return the kid's total points."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        return kid_info.get(const.DATA_KID_POINTS, const.DEFAULT_ZERO)

    @property
    def native_unit_of_measurement(self):
        """Return the points label."""
        return self._points_label or const.LABEL_POINTS

    @property
    def icon(self):
        """Use the points' custom icon if set, else fallback."""
        return self._points_icon or const.DEFAULT_POINTS_ICON


# ------------------------------------------------------------------------------------------
class KidMaxPointsEverSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing the maximum points a kid has ever reached."""

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_SENSOR_KID_MAX_POINTS_EVER_SENSOR

    def __init__(self, coordinator, entry, kid_id, kid_name, points_label, points_icon):
        """Initialize the sensor."""

        super().__init__(coordinator)
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._points_label = points_label
        self._points_icon = points_icon
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_max_points_ever"
        self._entry = entry
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_KID_NAME: kid_name
        }
        self.entity_id = f"{const.SENSOR_KC_PREFIX}{kid_name}_points_max_ever"

    @property
    def native_value(self):
        """Return the highest points total the kid has ever reached."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        return kid_info.get(const.DATA_KID_MAX_POINTS_EVER, const.DEFAULT_ZERO)

    @property
    def icon(self):
        """Use the same icon as points or any custom icon you prefer."""
        return self._points_icon or const.DEFAULT_POINTS_ICON

    @property
    def native_unit_of_measurement(self):
        """Optionally display the same points label for consistency."""
        return self._points_label or const.LABEL_POINTS


# ------------------------------------------------------------------------------------------
class CompletedChoresTotalSensor(CoordinatorEntity, SensorEntity):
    """Sensor tracking the total number of chores a kid has completed since integration start."""

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_SENSOR_CHORES_COMPLETED_TOTAL_SENSOR

    def __init__(self, coordinator, entry, kid_id, kid_name):
        """Initialize the sensor."""

        super().__init__(coordinator)
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_completed_total"
        self._attr_native_unit_of_measurement = "chores"
        self._attr_icon = "mdi:clipboard-check-outline"
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_KID_NAME: kid_name
        }
        self.entity_id = f"{const.SENSOR_KC_PREFIX}{kid_name}_chores_completed_total"

    @property
    def native_value(self):
        """Return the total number of chores completed by the kid."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        return kid_info.get(const.DATA_KID_COMPLETED_CHORES_TOTAL, const.DEFAULT_ZERO)


# ------------------------------------------------------------------------------------------
class CompletedChoresDailySensor(CoordinatorEntity, SensorEntity):
    """How many chores kid completed today."""

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_SENSOR_CHORES_COMPLETED_DAILY_SENSOR

    def __init__(self, coordinator, entry, kid_id, kid_name):
        """Initialize the sensor."""

        super().__init__(coordinator)
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_completed_daily"
        self._attr_native_unit_of_measurement = "chores"
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_KID_NAME: kid_name
        }
        self.entity_id = f"{const.SENSOR_KC_PREFIX}{kid_name}_chores_completed_daily"

    @property
    def native_value(self):
        """Return the number of chores completed today."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        return kid_info.get(const.DATA_KID_COMPLETED_CHORES_TOTAL, const.DEFAULT_ZERO)


# ------------------------------------------------------------------------------------------
class CompletedChoresWeeklySensor(CoordinatorEntity, SensorEntity):
    """How many chores kid completed this week."""

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_SENSOR_CHORES_COMPLETED_WEEKLY_SENSOR

    def __init__(self, coordinator, entry, kid_id, kid_name):
        """Initialize the sensor."""

        super().__init__(coordinator)
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_completed_weekly"
        self._attr_native_unit_of_measurement = "chores"
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_KID_NAME: kid_name
        }
        self.entity_id = f"{const.SENSOR_KC_PREFIX}{kid_name}_chores_completed_weekly"

    @property
    def native_value(self):
        """Return the number of chores completed this week."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        return kid_info.get(const.DATA_KID_COMPLETED_CHORES_WEEKLY, const.DEFAULT_ZERO)


# ------------------------------------------------------------------------------------------
class CompletedChoresMonthlySensor(CoordinatorEntity, SensorEntity):
    """How many chores kid completed this month."""

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_SENSOR_CHORES_COMPLETED_MONTHLY_SENSOR

    def __init__(self, coordinator, entry, kid_id, kid_name):
        """Initialize the sensor."""

        super().__init__(coordinator)
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_completed_monthly"
        self._attr_native_unit_of_measurement = "chores"
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_KID_NAME: kid_name
        }
        self.entity_id = f"{const.SENSOR_KC_PREFIX}{kid_name}_chores_completed_monthly"

    @property
    def native_value(self):
        """Return the number of chores completed this month."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        return kid_info.get(const.DATA_KID_COMPLETED_CHORES_MONTHLY, const.DEFAULT_ZERO)


# ------------------------------------------------------------------------------------------
class KidHighestBadgeSensor(CoordinatorEntity, SensorEntity):
    """Sensor that returns the "highest" badge the kid currently has."""

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_SENSOR_KIDS_HIGHEST_BADGE_SENSOR

    def __init__(self, coordinator, entry, kid_id, kid_name):
        """Initialize the sensor."""

        super().__init__(coordinator)
        self._entry = entry
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_highest_badge"
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_KID_NAME: kid_name
        }
        self.entity_id = f"{const.SENSOR_KC_PREFIX}{kid_name}_highest_badge"

    def _find_highest_badge(self):
        """Determine which badge has the highest ranking."""

        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        earned_badge_names = kid_info.get(const.DATA_KID_BADGES, [])

        highest_badge = None
        highest_value = -1

        for badge_name in earned_badge_names:
            # Find badge by name
            badge_data = next(
                (
                    info
                    for bid, info in self.coordinator.badges_data.items()
                    if info.get("name") == badge_name
                ),
                None,
            )
            if not badge_data:
                continue  # skip if not found or invalid

            threshold_val = badge_data.get("threshold_value", const.DEFAULT_ZERO)
            if threshold_val > highest_value:
                highest_value = threshold_val
                highest_badge = badge_name

        return highest_badge, highest_value

    @property
    def native_value(self) -> str:
        """Return the badge name of the highest-threshold badge the kid has earned.

        If the kid has none, return "None".
        """
        highest_badge, _ = self._find_highest_badge()
        return highest_badge if highest_badge else "None"

    @property
    def icon(self):
        """Return the icon for the highest badge. Fall back if none found."""
        highest_badge, _ = self._find_highest_badge()
        if highest_badge:
            badge_data = next(
                (
                    info
                    for bid, info in self.coordinator.badges_data.items()
                    if info.get("name") == highest_badge
                ),
                {},
            )
            return badge_data.get("icon", const.DEFAULT_TROPHY_ICON)
        return const.DEFAULT_TROPHY_OUTLINE

    @property
    def extra_state_attributes(self):
        """Provide additional details."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        highest_badge, highest_val = self._find_highest_badge()

        current_multiplier = const.DEFAULT_KID_POINTS_MULTIPLIER
        friendly_labels = []

        if highest_badge:
            badge_data = next(
                (
                    info
                    for bid, info in self.coordinator.badges_data.items()
                    if info.get("name") == highest_badge
                ),
                {},
            )
            current_multiplier = badge_data.get(
                "points_multiplier", const.DEFAULT_KID_POINTS_MULTIPLIER
            )
            stored_labels = badge_data.get("badge_labels", [])
            friendly_labels = [
                get_friendly_label(self.hass, label) for label in stored_labels
            ]

        # Compute points needed for next badge:
        current_points = kid_info.get(const.DATA_KID_POINTS, const.DEFAULT_ZERO)

        # Gather thresholds for badges that are higher than current points
        thresholds = [
            badge.get("threshold_value", const.DEFAULT_ZERO)
            for badge in self.coordinator.badges_data.values()
            if badge.get("threshold_value", const.DEFAULT_ZERO) > current_points
        ]
        if thresholds:
            next_threshold = min(thresholds)
            points_to_next_badge = next_threshold - current_points
        else:
            points_to_next_badge = const.DEFAULT_ZERO

        return {
            const.ATTR_KID_NAME: self._kid_name,
            const.ATTR_ALL_EARNED_BADGES: kid_info.get(const.DATA_KID_BADGES, []),
            const.ATTR_HIGHEST_BADGE_THRESHOLD_VALUE: highest_val
            if highest_badge
            else const.DEFAULT_ZERO,
            const.ATTR_POINTS_MULTIPLIER: current_multiplier,
            const.ATTR_POINTS_TO_NEXT_BADGE: points_to_next_badge,
            const.ATTR_LABELS: friendly_labels,
        }


# ------------------------------------------------------------------------------------------
class BadgeSensor(CoordinatorEntity, SensorEntity):
    """Sensor representing a single badge in KidsChores."""

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_SENSOR_BADGE_SENSOR

    def __init__(
        self,
        coordinator: KidsChoresDataCoordinator,
        entry: ConfigEntry,
        badge_id: str,
        badge_name: str,
    ):
        """Initialize the sensor."""

        super().__init__(coordinator)
        self._entry = entry
        self._badge_id = badge_id
        self._badge_name = badge_name
        self._attr_unique_id = f"{entry.entry_id}_{badge_id}_badge_sensor"
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_BADGE_NAME: badge_name
        }
        self.entity_id = f"{const.SENSOR_KC_PREFIX}{badge_name}_badge"

    @property
    def native_value(self) -> float:
        """The sensor state is the threshold_value for the badge."""
        badge_info = self.coordinator.badges_data.get(self._badge_id, {})
        return badge_info.get("threshold_value", const.DEFAULT_ZERO)

    @property
    def extra_state_attributes(self):
        """Provide additional badge data, including which kids currently have it."""
        badge_info = self.coordinator.badges_data.get(self._badge_id, {})
        threshold_type = (
            badge_info.get(
                const.DATA_BADGE_THRESHOLD_TYPE, const.BADGE_THRESHOLD_TYPE_POINTS
            ),
        )
        points_multiplier = badge_info.get(
            const.DATA_BADGE_POINTS_MULTIPLIER, const.DEFAULT_KID_POINTS_MULTIPLIER
        )
        description = badge_info.get(const.DATA_BADGE_DESCRIPTION, const.CONF_EMPTY)

        kids_earned_ids = badge_info.get(const.DATA_BADGE_EARNED_BY, [])

        stored_labels = badge_info.get(const.DATA_BADGE_LABELS, [])
        friendly_labels = [
            get_friendly_label(self.hass, label) for label in stored_labels
        ]

        award_points = badge_info.get(const.DATA_BADGE_AWARD_POINTS, const.DEFAULT_ZERO)

        award_reward_id = badge_info.get(
            const.DATA_BADGE_AWARD_REWARD, const.CONF_EMPTY
        )
        if award_reward_id and award_reward_id != const.CONF_EMPTY:
            reward_info = self.coordinator.rewards_data.get(award_reward_id)
            award_reward = (
                reward_info.get(const.DATA_REWARD_NAME, award_reward_id)
                if reward_info
                else award_reward_id
            )
        else:
            award_reward = const.CONF_EMPTY

        # Convert each kid_id to kid_name
        kids_earned_names = []
        for kid_id in kids_earned_ids:
            kid = self.coordinator.kids_data.get(kid_id)
            if kid is not None:
                kids_earned_names.append(kid.get(const.DATA_KID_NAME, f"Kid {kid_id}"))
            else:
                kids_earned_names.append(f"Kid {kid_id} (not found)")

        # Convert required chore_id to chore_name
        req_chore_ids = badge_info.get(const.DATA_BADGE_REQUIRED_CHORES, [])
        req_chore_names = [
            self.coordinator.chores_data.get(chore_id, {}).get(
                const.DATA_CHORE_NAME, chore_id
            )
            for chore_id in req_chore_ids
        ]

        badge_type = badge_info.get(const.DATA_BADGE_TYPE, const.BADGE_TYPE_CUMULATIVE)

        attributes = {
            const.ATTR_DESCRIPTION: description,
            const.ATTR_POINTS_MULTIPLIER: points_multiplier,
            const.ATTR_AWARD_POINTS: award_points,
            const.ATTR_AWARD_REWARD: award_reward,
            const.ATTR_KIDS_EARNED: kids_earned_names,
            const.ATTR_LABELS: friendly_labels,
        }

        if badge_type == const.BADGE_TYPE_CUMULATIVE:
            attributes[const.ATTR_THRESHOLD_VALUE] = badge_info.get(
                const.DATA_BADGE_THRESHOLD_VALUE, const.DEFAULT_BADGE_THRESHOLD_VALUE
            )
        elif badge_type == const.BADGE_TYPE_DAILY:
            attributes[const.ATTR_DAILY_THRESHOLD] = badge_info.get(
                const.DATA_BADGE_DAILY_THRESHOLD
            )
        elif badge_type == const.BADGE_TYPE_PERIODIC:
            attributes[const.ATTR_RESET_SCHEDULE] = badge_info.get(
                const.DATA_BADGE_RESET_SCHEDULE, const.CONF_WEEKLY
            )
            attributes[const.ATTR_START_DATE] = badge_info.get(
                const.DATA_BADGE_START_DATE, const.CONF_EMPTY
            )
            attributes[const.ATTR_END_DATE] = badge_info.get(
                const.DATA_BADGE_END_DATE, const.CONF_EMPTY
            )
            attributes[const.ATTR_PERIODIC_RECURRENT] = badge_info.get(
                const.DATA_BADGE_PERIODIC_RECURRENT, False
            )
            attributes[const.ATTR_THRESHOLD_VALUE] = badge_info.get(
                const.DATA_BADGE_THRESHOLD_VALUE, const.DEFAULT_BADGE_THRESHOLD_VALUE
            )
            attributes[const.ATTR_REQUIRED_CHORES] = req_chore_names
        elif badge_type == const.BADGE_TYPE_ACHIEVEMENT_LINKED:
            associated_achievement_id = badge_info.get(
                const.DATA_BADGE_ASSOCIATED_ACHIEVEMENT, const.CONF_EMPTY
            )
            if (
                associated_achievement_id
                and associated_achievement_id != const.CONF_EMPTY
            ):
                achievement_info = self.coordinator.achievements_data.get(
                    associated_achievement_id
                )
                associated_achievement = (
                    achievement_info.get(
                        const.DATA_ACHIEVEMENT_NAME, associated_achievement_id
                    )
                    if achievement_info
                    else associated_achievement_id
                )
            else:
                associated_achievement = const.CONF_EMPTY
            attributes[const.ATTR_ASSOCIATED_ACHIEVEMENT] = associated_achievement

        elif badge_type == const.BADGE_TYPE_CHALLENGE_LINKED:
            associated_challenge_id = badge_info.get(
                const.DATA_BADGE_ASSOCIATED_CHALLENGE, const.CONF_EMPTY
            )
            if associated_challenge_id and associated_challenge_id != const.CONF_EMPTY:
                challenge_info = self.coordinator.challenges_data.get(
                    associated_challenge_id
                )
                associated_challenge = (
                    challenge_info.get(
                        const.DATA_CHALLENGE_NAME, associated_challenge_id
                    )
                    if challenge_info
                    else associated_challenge_id
                )
            else:
                associated_challenge = const.CONF_EMPTY
            attributes[const.ATTR_ASSOCIATED_CHALLENGE] = associated_challenge

        elif badge_type == const.BADGE_TYPE_SPECIAL_OCCASION:
            attributes[const.ATTR_OCCASION_TYPE] = badge_info.get(
                const.DATA_BADGE_OCCASION_TYPE, const.CONF_HOLIDAY
            )
            attributes[const.ATTR_TRIGGER_INFO] = badge_info.get(
                const.DATA_BADGE_TRIGGER_INFO, const.CONF_EMPTY
            )
            attributes[const.ATTR_OCCASION_DATE] = badge_info.get(
                const.DATA_BADGE_SPECIAL_OCCASION_DATE, const.CONF_EMPTY
            )

        return attributes

    @property
    def icon(self) -> str:
        """Return the badge's custom icon if set, else default."""
        badge_info = self.coordinator.badges_data.get(self._badge_id, {})
        return badge_info.get("icon", const.DEFAULT_BADGE_ICON)


# ------------------------------------------------------------------------------------------
class PendingChoreApprovalsSensor(CoordinatorEntity, SensorEntity):
    """Sensor listing all pending chore approvals."""

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_SENSOR_PENDING_CHORES_APPROVALS_SENSOR

    def __init__(self, coordinator, entry):
        """Initialize the sensor."""

        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_pending_chore_approvals"
        self._attr_icon = "mdi:clipboard-check-outline"
        self.entity_id = f"{const.SENSOR_KC_PREFIX}global_chore_pending_approvals"

    @property
    def native_value(self):
        """Return a summary of pending chore approvals."""
        approvals = self.coordinator._data.get(const.DATA_PENDING_CHORE_APPROVALS, [])
        return f"{len(approvals)} pending chores"

    @property
    def extra_state_attributes(self):
        """Return detailed pending chores."""
        approvals = self.coordinator._data.get(const.DATA_PENDING_CHORE_APPROVALS, [])
        grouped_by_kid = {}

        for approval in approvals:
            kid_name = (
                self.coordinator._get_kid_name_by_id(approval["kid_id"])
                or const.UNKNOWN_KID
            )
            chore_info = self.coordinator.chores_data.get(approval["chore_id"], {})
            chore_name = chore_info.get(const.DATA_CHORE_NAME, const.UNKNOWN_CHORE)

            timestamp = approval["timestamp"]

            if kid_name not in grouped_by_kid:
                grouped_by_kid[kid_name] = []

            grouped_by_kid[kid_name].append(
                {
                    const.ATTR_CHORE_NAME: chore_name,
                    const.ATTR_CLAIMED_ON: timestamp,
                }
            )

        return grouped_by_kid


# ------------------------------------------------------------------------------------------
class PendingRewardApprovalsSensor(CoordinatorEntity, SensorEntity):
    """Sensor listing all pending reward approvals."""

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_SENSOR_PENDING_REWARDS_APPROVALS_SENSOR

    def __init__(self, coordinator, entry):
        """Initialize the sensor."""

        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_pending_reward_approvals"
        self._attr_icon = "mdi:gift-open-outline"
        self.entity_id = f"{const.SENSOR_KC_PREFIX}global_reward_pending_approvals"

    @property
    def native_value(self):
        """Return a summary of pending reward approvals."""
        approvals = self.coordinator._data.get(const.DATA_PENDING_REWARD_APPROVALS, [])
        return f"{len(approvals)} pending rewards"

    @property
    def extra_state_attributes(self):
        """Return detailed pending rewards."""
        approvals = self.coordinator._data.get(const.DATA_PENDING_REWARD_APPROVALS, [])
        grouped_by_kid = {}

        for approval in approvals:
            kid_name = (
                self.coordinator._get_kid_name_by_id(approval["kid_id"])
                or const.UNKNOWN_KID
            )
            reward_info = self.coordinator.rewards_data.get(approval["reward_id"], {})
            reward_name = reward_info.get("name", const.UNKNOWN_REWARD)

            timestamp = approval["timestamp"]

            if kid_name not in grouped_by_kid:
                grouped_by_kid[kid_name] = []

            grouped_by_kid[kid_name].append(
                {
                    const.ATTR_REWARD_NAME: reward_name,
                    const.ATTR_REDEEMED_ON: timestamp,
                }
            )

        return grouped_by_kid


# ------------------------------------------------------------------------------------------
class SharedChoreGlobalStateSensor(CoordinatorEntity, SensorEntity):
    """Sensor that shows the global state of a shared chore."""

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_SENSOR_SHARED_CHORE_GLOBAL_STATUS_SENSOR

    def __init__(
        self,
        coordinator: KidsChoresDataCoordinator,
        entry: ConfigEntry,
        chore_id: str,
        chore_name: str,
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._chore_id = chore_id
        self._chore_name = chore_name
        self._attr_unique_id = f"{entry.entry_id}_{chore_id}_global_state"
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_CHORE_NAME: chore_name,
        }
        self.entity_id = f"{const.SENSOR_KC_PREFIX}global_chore_status_{chore_name}"

    @property
    def native_value(self) -> str:
        """Return the global state for the chore."""
        chore_info = self.coordinator.chores_data.get(self._chore_id, {})
        return chore_info.get(const.DATA_CHORE_STATE, const.CHORE_STATE_UNKNOWN)

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional attributes for the chore."""
        chore_info = self.coordinator.chores_data.get(self._chore_id, {})
        assigned_kids_ids = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
        assigned_kids_names = [
            self.coordinator._get_kid_name_by_id(k_id) or f"Kid {k_id}"
            for k_id in assigned_kids_ids
        ]

        stored_labels = chore_info.get("chore_labels", [])
        friendly_labels = [
            get_friendly_label(self.hass, label) for label in stored_labels
        ]

        total_approvals_today = const.DEFAULT_ZERO
        for kid_id in assigned_kids_ids:
            kid_data = self.coordinator.kids_data.get(kid_id, {})
            total_approvals_today += kid_data.get("today_chore_approvals", {}).get(
                self._chore_id, const.DEFAULT_ZERO
            )

        attributes = {
            const.ATTR_CHORE_NAME: self._chore_name,
            const.ATTR_DESCRIPTION: chore_info.get("description", const.CONF_EMPTY),
            const.ATTR_RECURRING_FREQUENCY: chore_info.get(
                "recurring_frequency", "None"
            ),
            const.ATTR_APPLICABLE_DAYS: chore_info.get("applicable_days", []),
            const.ATTR_DUE_DATE: chore_info.get("due_date", "Not set"),
            const.ATTR_DEFAULT_POINTS: chore_info.get(
                "default_points", const.DEFAULT_ZERO
            ),
            const.ATTR_PARTIAL_ALLOWED: chore_info.get("partial_allowed", False),
            const.ATTR_ALLOW_MULTIPLE_CLAIMS_PER_DAY: chore_info.get(
                "allow_multiple_claims_per_day", False
            ),
            const.ATTR_CHORE_APPROVALS_TODAY: total_approvals_today,
            const.ATTR_ASSIGNED_KIDS: assigned_kids_names,
            const.ATTR_LABELS: friendly_labels,
        }

        if chore_info.get("recurring_frequency") == const.FREQUENCY_CUSTOM:
            attributes[const.ATTR_CUSTOM_FREQUENCY_INTERVAL] = chore_info.get(
                "custom_interval"
            )
            attributes[const.ATTR_CUSTOM_FREQUENCY_UNIT] = chore_info.get(
                "custom_interval_unit"
            )

        return attributes

    @property
    def icon(self) -> str:
        """Return the icon for the chore sensor."""
        chore_info = self.coordinator.chores_data.get(self._chore_id, {})
        return chore_info.get("icon", const.DEFAULT_CHORE_SENSOR_ICON)


# ------------------------------------------------------------------------------------------
class RewardStatusSensor(CoordinatorEntity, SensorEntity):
    """Shows the status of a reward for a particular kid."""

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_SENSOR_REWARD_STATUS_SENSOR

    def __init__(
        self,
        coordinator: KidsChoresDataCoordinator,
        entry: ConfigEntry,
        kid_id: str,
        kid_name: str,
        reward_id: str,
        reward_name: str,
    ):
        """Initialize the sensor."""

        super().__init__(coordinator)
        self._entry = entry
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._reward_id = reward_id
        self._reward_name = reward_name
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_{reward_id}_reward_status"
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_KID_NAME: kid_name,
            const.TRANS_KEY_SENSOR_ATTR_REWARD_NAME: reward_name,
        }
        self.entity_id = (
            f"{const.SENSOR_KC_PREFIX}{kid_name}_reward_status_{reward_name}"
        )

    @property
    def native_value(self) -> str:
        """Return the current reward status: 'Not Claimed', 'Claimed', or 'Approved'."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        if self._reward_id in kid_info.get(const.DATA_KID_PENDING_REWARDS, []):
            return const.REWARD_STATE_CLAIMED
        if self._reward_id in kid_info.get(const.DATA_KID_REDEEMED_REWARDS, []):
            return const.REWARD_STATE_APPROVED
        return const.REWARD_STATE_NOT_CLAIMED

    @property
    def extra_state_attributes(self) -> dict:
        """Provide extra attributes about the reward."""
        reward_info = self.coordinator.rewards_data.get(self._reward_id, {})
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})

        stored_labels = reward_info.get("reward_labels", [])
        friendly_labels = [
            get_friendly_label(self.hass, label) for label in stored_labels
        ]

        attributes = {
            const.ATTR_KID_NAME: self._kid_name,
            const.ATTR_REWARD_NAME: self._reward_name,
            const.ATTR_DESCRIPTION: reward_info.get("description", const.CONF_EMPTY),
            const.ATTR_COST: reward_info.get("cost", const.DEFAULT_REWARD_COST),
            const.ATTR_REWARD_CLAIMS_COUNT: kid_info.get(
                const.DATA_KID_REWARD_CLAIMS, {}
            ).get(self._reward_id, const.DEFAULT_ZERO),
            const.ATTR_REWARD_APPROVALS_COUNT: kid_info.get(
                const.DATA_KID_REWARD_APPROVALS, {}
            ).get(self._reward_id, const.DEFAULT_ZERO),
            const.ATTR_LABELS: friendly_labels,
        }

        return attributes

    @property
    def icon(self) -> str:
        """Use the reward's custom icon if set, else fallback."""
        reward_info = self.coordinator.rewards_data.get(self._reward_id, {})
        return reward_info.get("icon", const.DEFAULT_REWARD_ICON)


# ------------------------------------------------------------------------------------------
class PenaltyAppliesSensor(CoordinatorEntity, SensorEntity):
    """Sensor tracking how many times each penalty has been applied to a kid."""

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_SENSOR_PENALTY_APPLIES_SENSOR

    def __init__(self, coordinator, entry, kid_id, kid_name, penalty_id, penalty_name):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._penalty_id = penalty_id
        self._penalty_name = penalty_name
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_{penalty_id}_penalty_applies"
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_KID_NAME: kid_name,
            const.TRANS_KEY_SENSOR_ATTR_PENALTY_NAME: penalty_name,
        }
        self.entity_id = (
            f"{const.SENSOR_KC_PREFIX}{kid_name}_penalties_applied_{penalty_name}"
        )

    @property
    def native_value(self):
        """Return the number of times the penalty has been applied."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        return kid_info.get(const.DATA_KID_PENALTY_APPLIES, {}).get(
            self._penalty_id, const.DEFAULT_ZERO
        )

    @property
    def extra_state_attributes(self):
        """Expose additional details like penalty points and description."""
        penalty_info = self.coordinator.penalties_data.get(self._penalty_id, {})

        stored_labels = penalty_info.get("penalty_labels", [])
        friendly_labels = [
            get_friendly_label(self.hass, label) for label in stored_labels
        ]

        return {
            const.ATTR_KID_NAME: self._kid_name,
            const.ATTR_PENALTY_NAME: self._penalty_name,
            const.ATTR_DESCRIPTION: penalty_info.get("description", const.CONF_EMPTY),
            const.ATTR_PENALTY_POINTS: penalty_info.get(
                "points", const.DEFAULT_PENALTY_POINTS
            ),
            const.ATTR_LABELS: friendly_labels,
        }

    @property
    def icon(self):
        """Return the chore's custom icon if set, else fallback."""
        penalty_info = self.coordinator.penalties_data.get(self._penalty_id, {})
        return penalty_info.get("icon", const.DEFAULT_PENALTY_ICON)


# ------------------------------------------------------------------------------------------
class KidPointsEarnedDailySensor(CoordinatorEntity, SensorEntity):
    """Sensor for how many net points a kid earned today."""

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_SENSOR_KID_POINTS_EARNED_DAILY_SENSOR

    def __init__(self, coordinator, entry, kid_id, kid_name, points_label, points_icon):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._points_label = points_label
        self._points_icon = points_icon
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_points_earned_daily"
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_KID_NAME: kid_name,
        }
        self.entity_id = f"{const.SENSOR_KC_PREFIX}{kid_name}_points_earned_daily"

    @property
    def native_value(self):
        """Return how many net points the kid has earned so far today."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        return kid_info.get(const.DATA_KID_POINTS_EARNED_TODAY, const.DEFAULT_ZERO)

    @property
    def native_unit_of_measurement(self):
        """Return the points label."""
        return self._points_label or const.LABEL_POINTS

    @property
    def icon(self):
        """Use the points' custom icon if set, else fallback."""
        return self._points_icon or const.DEFAULT_POINTS_ICON


# ------------------------------------------------------------------------------------------
class KidPointsEarnedWeeklySensor(CoordinatorEntity, SensorEntity):
    """Sensor for how many net points a kid earned this week."""

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_SENSOR_KID_POINTS_EARNED_WEEKLY_SENSOR

    def __init__(self, coordinator, entry, kid_id, kid_name, points_label, points_icon):
        """Initialize the sensor."""

        super().__init__(coordinator)
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._points_label = points_label
        self._points_icon = points_icon
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_points_earned_weekly"
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_KID_NAME: kid_name,
        }
        self.entity_id = f"{const.SENSOR_KC_PREFIX}{kid_name}_points_earned_weekly"

    @property
    def native_value(self):
        """Return how many net points the kid has earned this week."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        return kid_info.get(const.DATA_KID_POINTS_EARNED_WEEKLY, const.DEFAULT_ZERO)

    @property
    def native_unit_of_measurement(self):
        """Return the points label."""
        return self._points_label or const.LABEL_POINTS

    @property
    def icon(self):
        """Use the points' custom icon if set, else fallback."""
        return self._points_icon or const.DEFAULT_POINTS_ICON


# ------------------------------------------------------------------------------------------
class KidPointsEarnedMonthlySensor(CoordinatorEntity, SensorEntity):
    """Sensor for how many net points a kid earned this month."""

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_SENSOR_KID_POINTS_EARNED_MONTHLY_SENSOR

    def __init__(self, coordinator, entry, kid_id, kid_name, points_label, points_icon):
        """Initialize the sensor."""

        super().__init__(coordinator)
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._points_label = points_label
        self._points_icon = points_icon
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_points_earned_monthly"
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_KID_NAME: kid_name,
        }
        self.entity_id = f"{const.SENSOR_KC_PREFIX}{kid_name}_points_earned_monthly"

    @property
    def native_value(self):
        """Return how many net points the kid has earned this month."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        return kid_info.get(const.DATA_KID_POINTS_EARNED_MONTHLY, const.DEFAULT_ZERO)

    @property
    def native_unit_of_measurement(self):
        """Return the points label."""
        return self._points_label or const.LABEL_POINTS

    @property
    def icon(self):
        """Use the points' custom icon if set, else fallback."""
        return self._points_icon or const.DEFAULT_POINTS_ICON


# ------------------------------------------------------------------------------------------
class AchievementSensor(CoordinatorEntity, SensorEntity):
    """Sensor representing an achievement."""

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_SENSOR_ACHIEVEMENT_STATE_SENSOR

    def __init__(self, coordinator, entry, achievement_id, achievement_name):
        """Initialize the AchievementSensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._achievement_id = achievement_id
        self._achievement_name = achievement_name
        self._attr_unique_id = f"{entry.entry_id}_{achievement_id}_achievement"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_ACHIEVEMENT_NAME: achievement_name,
        }
        self.entity_id = (
            f"{const.SENSOR_KC_PREFIX}achievement_status_{achievement_name}"
        )

    @property
    def native_value(self):
        """Return the overall progress percentage toward the achievement."""

        achievement = self.coordinator.achievements_data.get(self._achievement_id, {})
        target = achievement.get("target_value", 1)
        assigned_kids = achievement.get("assigned_kids", [])

        if not assigned_kids:
            return const.DEFAULT_ZERO

        ach_type = achievement.get("type")
        if ach_type == const.ACHIEVEMENT_TYPE_TOTAL:
            total_current = const.DEFAULT_ZERO
            total_effective_target = const.DEFAULT_ZERO

            for kid_id in assigned_kids:
                progress_data = achievement.get("progress", {}).get(kid_id, {})
                baseline = (
                    progress_data.get("baseline", const.DEFAULT_ZERO)
                    if isinstance(progress_data, dict)
                    else const.DEFAULT_ZERO
                )
                current_total = self.coordinator.kids_data.get(kid_id, {}).get(
                    "completed_chores_total", const.DEFAULT_ZERO
                )
                total_current += current_total
                total_effective_target += baseline + target

            percent = (
                (total_current / total_effective_target * 100)
                if total_effective_target > const.DEFAULT_ZERO
                else const.DEFAULT_ZERO
            )

        elif ach_type == const.ACHIEVEMENT_TYPE_STREAK:
            total_current = const.DEFAULT_ZERO

            for kid_id in assigned_kids:
                progress_data = achievement.get("progress", {}).get(kid_id, {})
                total_current += (
                    progress_data.get("current_streak", const.DEFAULT_ZERO)
                    if isinstance(progress_data, dict)
                    else const.DEFAULT_ZERO
                )

            global_target = target * len(assigned_kids)

            percent = (
                (total_current / global_target * 100)
                if global_target > const.DEFAULT_ZERO
                else const.DEFAULT_ZERO
            )

        elif ach_type == const.ACHIEVEMENT_TYPE_DAILY_MIN:
            total_progress = const.DEFAULT_ZERO

            for kid_id in assigned_kids:
                daily = self.coordinator.kids_data.get(kid_id, {}).get(
                    "completed_chores_today", const.DEFAULT_ZERO
                )
                kid_progress = (
                    100
                    if daily >= target
                    else (daily / target * 100)
                    if target > const.DEFAULT_ZERO
                    else const.DEFAULT_ZERO
                )
                total_progress += kid_progress

            percent = total_progress / len(assigned_kids)

        else:
            percent = const.DEFAULT_ZERO

        return min(100, round(percent, 1))

    @property
    def extra_state_attributes(self):
        """Return extra attributes for this achievement."""
        achievement = self.coordinator.achievements_data.get(self._achievement_id, {})
        progress = achievement.get("progress", {})
        kids_progress = {}

        earned_by = []
        for kid_id, data in progress.items():
            if data.get("awarded", False):
                kid_name = self.coordinator._get_kid_name_by_id(kid_id) or kid_id
                earned_by.append(kid_name)

        associated_chore = ""
        selected_chore_id = achievement.get("selected_chore_id")
        if selected_chore_id:
            associated_chore = self.coordinator.chores_data.get(
                selected_chore_id, {}
            ).get("name", const.CONF_EMPTY)

        assigned_kids_ids = achievement.get("assigned_kids", [])
        assigned_kids_names = [
            self.coordinator._get_kid_name_by_id(k_id) or f"Kid {k_id}"
            for k_id in assigned_kids_ids
        ]
        ach_type = achievement.get("type")
        for kid_id in assigned_kids_ids:
            kid_name = self.coordinator._get_kid_name_by_id(kid_id) or kid_id
            progress_data = achievement.get("progress", {}).get(kid_id, {})
            if ach_type == const.ACHIEVEMENT_TYPE_TOTAL:
                kids_progress[kid_name] = progress_data.get(
                    "current_value", const.DEFAULT_ZERO
                )
            elif ach_type == const.ACHIEVEMENT_TYPE_STREAK:
                kids_progress[kid_name] = progress_data.get(
                    "current_streak", const.DEFAULT_ZERO
                )
            elif achievement.get("type") == const.ACHIEVEMENT_TYPE_DAILY_MIN:
                kids_progress[kid_name] = self.coordinator.kids_data.get(
                    kid_id, {}
                ).get("completed_chores_today", const.DEFAULT_ZERO)
            else:
                kids_progress[kid_name] = const.DEFAULT_ZERO

        stored_labels = achievement.get("achievement_labels", [])
        friendly_labels = [
            get_friendly_label(self.hass, label) for label in stored_labels
        ]

        return {
            const.ATTR_ACHIEVEMENT_NAME: self._achievement_name,
            const.ATTR_DESCRIPTION: achievement.get("description", const.CONF_EMPTY),
            const.ATTR_ASSIGNED_KIDS: assigned_kids_names,
            const.ATTR_TYPE: ach_type,
            const.ATTR_ASSOCIATED_CHORE: associated_chore,
            const.ATTR_CRITERIA: achievement.get("criteria", const.CONF_EMPTY),
            const.ATTR_TARGET_VALUE: achievement.get("target_value"),
            const.ATTR_REWARD_POINTS: achievement.get("reward_points"),
            const.ATTR_KIDS_EARNED: earned_by,
            const.ATTR_LABELS: friendly_labels,
        }

    @property
    def icon(self):
        """Return an icon; you could choose a trophy icon."""
        achievement_info = self.coordinator.achievements_data.get(
            self._achievement_id, {}
        )
        return achievement_info.get("icon", const.DEFAULT_ACHIEVEMENTS_ICON)


# ------------------------------------------------------------------------------------------
class ChallengeSensor(CoordinatorEntity, SensorEntity):
    """Sensor representing a challenge."""

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_SENSOR_CHALLENGE_STATE_SENSOR

    def __init__(self, coordinator, entry, challenge_id, challenge_name):
        """Initialize the ChallengeSensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._challenge_id = challenge_id
        self._challenge_name = challenge_name
        self._attr_unique_id = f"{entry.entry_id}_{challenge_id}_challenge"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_CHALLENGE_NAME: challenge_name,
        }
        self.entity_id = f"{const.SENSOR_KC_PREFIX}challenge_status_{challenge_name}"

    @property
    def native_value(self):
        """Return the overall progress percentage toward the challenge."""

        challenge = self.coordinator.challenges_data.get(self._challenge_id, {})
        target = challenge.get("target_value", 1)
        assigned_kids = challenge.get("assigned_kids", [])

        if not assigned_kids:
            return const.DEFAULT_ZERO

        challenge_type = challenge.get("type")
        total_progress = const.DEFAULT_ZERO

        for kid_id in assigned_kids:
            progress_data = challenge.get("progress", {}).get(kid_id, {})

            if challenge_type == const.CHALLENGE_TYPE_TOTAL_WITHIN_WINDOW:
                total_progress += progress_data.get("count", const.DEFAULT_ZERO)

            elif challenge_type == const.CHALLENGE_TYPE_DAILY_MIN:
                if isinstance(progress_data, dict):
                    daily_counts = progress_data.get("daily_counts", {})
                    total_progress += sum(daily_counts.values())

                else:
                    total_progress += const.DEFAULT_ZERO

            else:
                total_progress += const.DEFAULT_ZERO

        global_target = target * len(assigned_kids)

        percent = (
            (total_progress / global_target * 100)
            if global_target > const.DEFAULT_ZERO
            else const.DEFAULT_ZERO
        )

        return min(100, round(percent, 1))

    @property
    def extra_state_attributes(self):
        """Return extra attributes for this challenge."""
        challenge = self.coordinator.challenges_data.get(self._challenge_id, {})
        progress = challenge.get("progress", {})
        kids_progress = {}
        challenge_type = challenge.get("type")

        earned_by = []
        for kid_id, data in progress.items():
            if data.get("awarded", False):
                kid_name = self.coordinator._get_kid_name_by_id(kid_id) or kid_id
                earned_by.append(kid_name)

        associated_chore = ""
        selected_chore_id = challenge.get("selected_chore_id")
        if selected_chore_id:
            associated_chore = self.coordinator.chores_data.get(
                selected_chore_id, {}
            ).get("name", const.CONF_EMPTY)

        assigned_kids_ids = challenge.get("assigned_kids", [])
        assigned_kids_names = [
            self.coordinator._get_kid_name_by_id(k_id) or f"Kid {k_id}"
            for k_id in assigned_kids_ids
        ]

        for kid_id in assigned_kids_ids:
            kid_name = self.coordinator._get_kid_name_by_id(kid_id) or kid_id
            progress_data = challenge.get("progress", {}).get(kid_id, {})
            if challenge_type == const.CHALLENGE_TYPE_TOTAL_WITHIN_WINDOW:
                kids_progress[kid_name] = progress_data.get("count", const.DEFAULT_ZERO)
            elif challenge_type == const.CHALLENGE_TYPE_DAILY_MIN:
                if isinstance(progress_data, dict):
                    kids_progress[kid_name] = sum(
                        progress_data.get("daily_counts", {}).values()
                    )
                else:
                    kids_progress[kid_name] = const.DEFAULT_ZERO
            else:
                kids_progress[kid_name] = const.DEFAULT_ZERO

        stored_labels = challenge.get("challenge_labels", [])
        friendly_labels = [
            get_friendly_label(self.hass, label) for label in stored_labels
        ]

        return {
            const.ATTR_CHALLENGE_NAME: self._challenge_name,
            const.ATTR_DESCRIPTION: challenge.get("description", const.CONF_EMPTY),
            const.ATTR_ASSIGNED_KIDS: assigned_kids_names,
            const.ATTR_TYPE: challenge_type,
            const.ATTR_ASSOCIATED_CHORE: associated_chore,
            const.ATTR_CRITERIA: challenge.get("criteria", const.CONF_EMPTY),
            const.ATTR_TARGET_VALUE: challenge.get("target_value"),
            const.ATTR_REWARD_POINTS: challenge.get("reward_points"),
            const.ATTR_START_DATE: challenge.get("start_date"),
            const.ATTR_END_DATE: challenge.get("end_date"),
            const.ATTR_KIDS_EARNED: earned_by,
            const.ATTR_LABELS: friendly_labels,
        }

    @property
    def icon(self):
        """Return an icon for challenges (you might want to choose one that fits your theme)."""
        challenge_info = self.coordinator.challenges_data.get(self._challenge_id, {})
        return challenge_info.get("icon", const.DEFAULT_ACHIEVEMENTS_ICON)


# ------------------------------------------------------------------------------------------
class AchievementProgressSensor(CoordinatorEntity, SensorEntity):
    """Sensor representing a kid's progress toward a specific achievement."""

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_SENSOR_ACHIEVEMENT_PROGRESS_SENSOR

    def __init__(
        self,
        coordinator: KidsChoresDataCoordinator,
        entry: ConfigEntry,
        kid_id: str,
        kid_name: str,
        achievement_id: str,
        achievement_name: str,
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._achievement_id = achievement_id
        self._achievement_name = achievement_name
        self._attr_unique_id = (
            f"{entry.entry_id}_{kid_id}_{achievement_id}_achievement_progress"
        )
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_KID_NAME: kid_name,
            const.TRANS_KEY_SENSOR_ATTR_ACHIEVEMENT_NAME: achievement_name,
        }
        self.entity_id = (
            f"{const.SENSOR_KC_PREFIX}{kid_name}_achievement_status_{achievement_name}"
        )

    @property
    def native_value(self) -> float:
        """Return the progress percentage toward the achievement."""
        achievement = self.coordinator.achievements_data.get(self._achievement_id, {})
        target = achievement.get("target_value", 1)
        ach_type = achievement.get("type")

        if ach_type == const.ACHIEVEMENT_TYPE_TOTAL:
            progress_data = achievement.get("progress", {}).get(self._kid_id, {})

            baseline = (
                progress_data.get("baseline", const.DEFAULT_ZERO)
                if isinstance(progress_data, dict)
                else const.DEFAULT_ZERO
            )

            current_total = self.coordinator.kids_data.get(self._kid_id, {}).get(
                "completed_chores_total", const.DEFAULT_ZERO
            )

            effective_target = baseline + target

            percent = (
                (current_total / effective_target * 100)
                if effective_target > const.DEFAULT_ZERO
                else const.DEFAULT_ZERO
            )

        elif ach_type == const.ACHIEVEMENT_TYPE_STREAK:
            progress_data = achievement.get("progress", {}).get(self._kid_id, {})

            progress = (
                progress_data.get("current_streak", const.DEFAULT_ZERO)
                if isinstance(progress_data, dict)
                else const.DEFAULT_ZERO
            )

            percent = (
                (progress / target * 100)
                if target > const.DEFAULT_ZERO
                else const.DEFAULT_ZERO
            )

        elif ach_type == const.ACHIEVEMENT_TYPE_DAILY_MIN:
            daily = self.coordinator.kids_data.get(self._kid_id, {}).get(
                "completed_chores_today", const.DEFAULT_ZERO
            )

            percent = (
                (daily / target * 100)
                if target > const.DEFAULT_ZERO
                else const.DEFAULT_ZERO
            )

        else:
            percent = const.DEFAULT_ZERO

        return min(100, round(percent, 1))

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes for the achievement progress."""
        achievement = self.coordinator.achievements_data.get(self._achievement_id, {})
        target = achievement.get("target_value", 1)
        progress_data = achievement.get("progress", {}).get(self._kid_id, {})
        raw_progress = const.DEFAULT_ZERO

        awarded = (
            progress_data.get("awarded", False)
            if isinstance(progress_data, dict)
            else False
        )

        if achievement.get("type") == const.ACHIEVEMENT_TYPE_TOTAL:
            raw_progress = (
                progress_data.get("current_value", const.DEFAULT_ZERO)
                if isinstance(progress_data, dict)
                else const.DEFAULT_ZERO
            )

        elif achievement.get("type") == const.ACHIEVEMENT_TYPE_STREAK:
            raw_progress = (
                progress_data.get("current_streak", const.DEFAULT_ZERO)
                if isinstance(progress_data, dict)
                else const.DEFAULT_ZERO
            )

        elif achievement.get("type") == const.ACHIEVEMENT_TYPE_DAILY_MIN:
            raw_progress = self.coordinator.kids_data.get(self._kid_id, {}).get(
                "completed_chores_today", const.DEFAULT_ZERO
            )

        associated_chore = ""
        selected_chore_id = achievement.get("selected_chore_id")
        if selected_chore_id:
            associated_chore = self.coordinator.chores_data.get(
                selected_chore_id, {}
            ).get("name", const.CONF_EMPTY)

        assigned_kids_ids = achievement.get("assigned_kids", [])
        assigned_kids_names = [
            self.coordinator._get_kid_name_by_id(k_id) or f"Kid {k_id}"
            for k_id in assigned_kids_ids
        ]

        stored_labels = achievement.get("achievement_labels", [])
        friendly_labels = [
            get_friendly_label(self.hass, label) for label in stored_labels
        ]

        return {
            const.ATTR_ACHIEVEMENT_NAME: self._achievement_name,
            const.ATTR_DESCRIPTION: achievement.get("description", const.CONF_EMPTY),
            const.ATTR_ASSIGNED_KIDS: assigned_kids_names,
            const.ATTR_TYPE: achievement.get("type"),
            const.ATTR_ASSOCIATED_CHORE: associated_chore,
            const.ATTR_CRITERIA: achievement.get("criteria", const.CONF_EMPTY),
            const.ATTR_TARGET_VALUE: target,
            const.ATTR_REWARD_POINTS: achievement.get("reward_points"),
            const.ATTR_RAW_PROGRESS: raw_progress,
            const.ATTR_AWARDED: awarded,
            const.ATTR_LABELS: friendly_labels,
        }

    @property
    def icon(self) -> str:
        """Return the icon for the achievement.

        Use the icon provided in the achievement data if set, else fallback to default.
        """
        achievement = self.coordinator.achievements_data.get(self._achievement_id, {})
        return achievement.get("icon", const.DEFAULT_ACHIEVEMENTS_ICON)


# ------------------------------------------------------------------------------------------
class ChallengeProgressSensor(CoordinatorEntity, SensorEntity):
    """Sensor representing a kid's progress toward a specific challenge."""

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_SENSOR_CHALLENGE_PROGRESS_SENSOR

    def __init__(
        self,
        coordinator: KidsChoresDataCoordinator,
        entry: ConfigEntry,
        kid_id: str,
        kid_name: str,
        challenge_id: str,
        challenge_name: str,
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._challenge_id = challenge_id
        self._challenge_name = challenge_name
        self._attr_unique_id = (
            f"{entry.entry_id}_{kid_id}_{challenge_id}_challenge_progress"
        )
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_KID_NAME: kid_name,
            const.TRANS_KEY_SENSOR_ATTR_CHALLENGE_NAME: challenge_name,
        }
        self.entity_id = (
            f"{const.SENSOR_KC_PREFIX}{kid_name}_challenge_status_{challenge_name}"
        )

    @property
    def native_value(self) -> float:
        """Return the challenge progress percentage."""
        challenge = self.coordinator.challenges_data.get(self._challenge_id, {})
        target = challenge.get("target_value", 1)
        challenge_type = challenge.get("type")
        progress_data = challenge.get("progress", {}).get(self._kid_id)

        if challenge_type == const.CHALLENGE_TYPE_TOTAL_WITHIN_WINDOW:
            raw_progress = (
                progress_data.get("count", const.DEFAULT_ZERO)
                if isinstance(progress_data, dict)
                else const.DEFAULT_ZERO
            )

        elif challenge_type == const.CHALLENGE_TYPE_DAILY_MIN:
            if isinstance(progress_data, dict):
                daily_counts = progress_data.get("daily_counts", {})
                raw_progress = sum(daily_counts.values())
                # Optionally, compute target as required_daily * number_of_days:
                start_date = dt_util.parse_datetime(challenge.get("start_date"))
                end_date = dt_util.parse_datetime(challenge.get("end_date"))

                if start_date and end_date:
                    num_days = (end_date.date() - start_date.date()).days + 1

                else:
                    num_days = 1
                required_daily = challenge.get("required_daily", 1)
                target = required_daily * num_days

            else:
                raw_progress = const.DEFAULT_ZERO

        else:
            raw_progress = const.DEFAULT_ZERO

        percent = (
            (raw_progress / target * 100)
            if target > const.DEFAULT_ZERO
            else const.DEFAULT_ZERO
        )

        return min(100, round(percent, 1))

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes for the challenge progress."""
        challenge = self.coordinator.challenges_data.get(self._challenge_id, {})
        target = challenge.get("target_value", 1)
        challenge_type = challenge.get("type")
        progress_data = challenge.get("progress", {}).get(self._kid_id, {})
        awarded = (
            progress_data.get("awarded", False)
            if isinstance(progress_data, dict)
            else False
        )

        if challenge_type == const.CHALLENGE_TYPE_TOTAL_WITHIN_WINDOW:
            raw_progress = (
                progress_data.get("count", const.DEFAULT_ZERO)
                if isinstance(progress_data, dict)
                else const.DEFAULT_ZERO
            )
        elif challenge_type == const.CHALLENGE_TYPE_DAILY_MIN:
            if isinstance(progress_data, dict):
                daily_counts = progress_data.get("daily_counts", {})
                raw_progress = sum(daily_counts.values())
            else:
                raw_progress = const.DEFAULT_ZERO
        else:
            raw_progress = const.DEFAULT_ZERO

        associated_chore = ""
        selected_chore_id = challenge.get("selected_chore_id")
        if selected_chore_id:
            associated_chore = self.coordinator.chores_data.get(
                selected_chore_id, {}
            ).get("name", const.CONF_EMPTY)

        assigned_kids_ids = challenge.get("assigned_kids", [])
        assigned_kids_names = [
            self.coordinator._get_kid_name_by_id(k_id) or f"Kid {k_id}"
            for k_id in assigned_kids_ids
        ]

        stored_labels = challenge.get("challenge_labels", [])
        friendly_labels = [
            get_friendly_label(self.hass, label) for label in stored_labels
        ]

        return {
            const.ATTR_CHALLENGE_NAME: self._challenge_name,
            const.ATTR_DESCRIPTION: challenge.get("description", const.CONF_EMPTY),
            const.ATTR_ASSIGNED_KIDS: assigned_kids_names,
            const.ATTR_TYPE: challenge_type,
            const.ATTR_ASSOCIATED_CHORE: associated_chore,
            const.ATTR_CRITERIA: challenge.get("criteria", const.CONF_EMPTY),
            const.ATTR_TARGET_VALUE: target,
            const.ATTR_REWARD_POINTS: challenge.get("reward_points"),
            const.ATTR_START_DATE: challenge.get("start_date"),
            const.ATTR_END_DATE: challenge.get("end_date"),
            const.ATTR_RAW_PROGRESS: raw_progress,
            const.ATTR_AWARDED: awarded,
            const.ATTR_LABELS: friendly_labels,
        }

    @property
    def icon(self) -> str:
        """Return the icon for the challenge.

        Use the icon provided in the challenge data if set, else fallback to default.
        """
        challenge = self.coordinator.challenges_data.get(self._challenge_id, {})
        return challenge.get("icon", const.DEFAULT_CHALLENGES_ICON)


# ------------------------------------------------------------------------------------------
class KidHighestStreakSensor(CoordinatorEntity, SensorEntity):
    """Sensor returning the highest current streak among streak-type achievements for a kid."""

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_SENSOR_KID_HIGHEST_STREAK_SENSOR

    def __init__(
        self,
        coordinator: KidsChoresDataCoordinator,
        entry: ConfigEntry,
        kid_id: str,
        kid_name: str,
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_highest_streak"
        self._attr_native_unit_of_measurement = UnitOfTime.DAYS
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_KID_NAME: kid_name,
        }
        self.entity_id = f"{const.SENSOR_KC_PREFIX}{kid_name}_highest_streak"

    @property
    def native_value(self) -> int:
        """Return the highest current streak among all streak achievements for the kid."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        return kid_info.get(const.DATA_KID_OVERALL_CHORE_STREAK, const.DEFAULT_ZERO)

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes including individual streaks per achievement."""
        streaks = {}
        for achievement in self.coordinator.achievements_data.values():
            if achievement.get("type") == const.ACHIEVEMENT_TYPE_STREAK:
                achievement_name = achievement.get("name", "Unnamed Achievement")
                progress_for_kid = achievement.get("progress", {}).get(self._kid_id)

                if isinstance(progress_for_kid, dict):
                    streaks[achievement_name] = progress_for_kid.get(
                        "current_streak", const.DEFAULT_ZERO
                    )

                elif isinstance(progress_for_kid, int):
                    streaks[achievement_name] = progress_for_kid

        return {"streaks_by_achievement": streaks}

    @property
    def icon(self) -> str:
        """Return an icon for 'highest streak'. You can choose any default or allow config overrides."""
        return const.DEFAULT_STREAK_ICON


# ------------------------------------------------------------------------------------------
class BonusAppliesSensor(CoordinatorEntity, SensorEntity):
    """Sensor tracking how many times each bonus has been applied to a kid."""

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_SENSOR_BONUS_APPLIES_SENSOR

    def __init__(self, coordinator, entry, kid_id, kid_name, bonus_id, bonus_name):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._bonus_id = bonus_id
        self._bonus_name = bonus_name
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_{bonus_id}_bonus_applies"
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_KID_NAME: kid_name,
            const.TRANS_KEY_SENSOR_ATTR_BONUS_NAME: bonus_name,
        }
        self.entity_id = (
            f"{const.SENSOR_KC_PREFIX}{kid_name}_bonuses_applied_{bonus_name}"
        )

    @property
    def native_value(self):
        """Return the number of times the bonus has been applied."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        return kid_info.get(const.DATA_KID_BONUS_APPLIES, {}).get(
            self._bonus_id, const.DEFAULT_ZERO
        )

    @property
    def extra_state_attributes(self):
        """Expose additional details like bonus points and description."""
        bonus_info = self.coordinator.bonuses_data.get(self._bonus_id, {})

        stored_labels = bonus_info.get("bonus_labels", [])
        friendly_labels = [
            get_friendly_label(self.hass, label) for label in stored_labels
        ]

        return {
            const.ATTR_KID_NAME: self._kid_name,
            const.ATTR_BONUS_NAME: self._bonus_name,
            const.ATTR_DESCRIPTION: bonus_info.get("description", const.CONF_EMPTY),
            const.ATTR_BONUS_POINTS: bonus_info.get(
                "points", const.DEFAULT_BONUS_POINTS
            ),
            const.ATTR_LABELS: friendly_labels,
        }

    @property
    def icon(self):
        """Return the bonus's custom icon if set, else fallback."""
        bonus_info = self.coordinator.bonuses_data.get(self._bonus_id, {})
        return bonus_info.get("icon", const.DEFAULT_BONUS_ICON)
