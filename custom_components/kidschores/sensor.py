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

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_registry import async_get
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import const
from . import kc_helpers as kh
from .coordinator import KidsChoresDataCoordinator


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
        kid_name = kid_info.get(
            const.DATA_KID_NAME, f"{const.TRANS_KEY_LABEL_KID} {kid_id}"
        )

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
            chore_name = chore_info.get(
                const.DATA_CHORE_NAME,
                f"{const.TRANS_KEY_LABEL_CHORE} {chore_id}",
            )

        # Penalty Applies
        for penalty_id, penalty_info in coordinator.penalties_data.items():
            penalty_name = penalty_info.get(
                const.DATA_PENALTY_NAME,
                f"{const.TRANS_KEY_LABEL_PENALTY} {penalty_id}",
            )
            entities.append(
                PenaltyAppliesSensor(
                    coordinator, entry, kid_id, kid_name, penalty_id, penalty_name
                )
            )

        # Bonus Applies
        for bonus_id, bonus_info in coordinator.bonuses_data.items():
            bonus_name = bonus_info.get(
                const.DATA_BONUS_NAME,
                f"{const.TRANS_KEY_LABEL_BONUS} {bonus_id}",
            )
            entities.append(
                BonusAppliesSensor(
                    coordinator, entry, kid_id, kid_name, bonus_id, bonus_name
                )
            )

        # KidBadgeSensor for each non-cumulative badge
        badge_progress_data = kid_info.get(const.DATA_KID_BADGE_PROGRESS, {})
        for badge_id, progress_info in badge_progress_data.items():
            badge_type = progress_info.get(const.DATA_KID_BADGE_PROGRESS_TYPE)
            if badge_type != const.BADGE_TYPE_CUMULATIVE:
                badge_name = progress_info.get(
                    const.DATA_KID_BADGE_PROGRESS_NAME,
                    f"{const.TRANS_KEY_LABEL_BADGE} {badge_id}",
                )
                entities.append(
                    KidBadgeSensor(
                        coordinator, entry, kid_id, kid_name, badge_id, badge_name
                    )
                )

        # Achivement Progress per Kid
        for achievement_id, achievement in coordinator.achievements_data.items():
            if kid_id in achievement.get(const.DATA_ACHIEVEMENT_ASSIGNED_KIDS, []):
                achievement_name = achievement.get(
                    const.DATA_ACHIEVEMENT_NAME,
                    f"{const.TRANS_KEY_LABEL_ACHIEVEMENT} {achievement_id}",
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
                    const.DATA_CHALLENGE_NAME,
                    f"{const.TRANS_KEY_LABEL_CHALLENGE} {challenge_id}",
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
        chore_name = chore_info.get(
            const.DATA_CHORE_NAME, f"{const.TRANS_KEY_LABEL_CHORE} {chore_id}"
        )
        assigned_kids_ids = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
        for kid_id in assigned_kids_ids:
            kid_name = (
                kh.get_kid_name_by_id(coordinator, kid_id)
                or f"{const.TRANS_KEY_LABEL_KID} {kid_id}"
            )
            entities.append(
                ChoreStatusSensor(
                    coordinator, entry, kid_id, kid_name, chore_id, chore_name
                )
            )

    # For each shared chore, add a global state sensor
    for chore_id, chore_info in coordinator.chores_data.items():
        if chore_info.get(const.DATA_CHORE_SHARED_CHORE, False):
            chore_name = chore_info.get(
                const.DATA_CHORE_NAME,
                f"{const.TRANS_KEY_LABEL_CHORE} {chore_id}",
            )
            entities.append(
                SharedChoreGlobalStateSensor(coordinator, entry, chore_id, chore_name)
            )

    # For each Reward, add a RewardStatusSensor
    for reward_id, reward_info in coordinator.rewards_data.items():
        reward_name = reward_info.get(
            const.DATA_REWARD_NAME, f"{const.TRANS_KEY_LABEL_REWARD} {reward_id}"
        )

        # For each kid, create the reward status sensor
        for kid_id, kid_info in coordinator.kids_data.items():
            kid_name = kid_info.get(
                const.DATA_KID_NAME, f"{const.TRANS_KEY_LABEL_KID} {kid_id}"
            )
            entities.append(
                RewardStatusSensor(
                    coordinator, entry, kid_id, kid_name, reward_id, reward_name
                )
            )

    # For each Badge, add a BadgeSensor
    for badge_id, badge_info in coordinator.badges_data.items():
        badge_name = badge_info.get(
            const.DATA_BADGE_NAME, f"{const.TRANS_KEY_LABEL_BADGE} {badge_id}"
        )
        entities.append(BadgeSensor(coordinator, entry, badge_id, badge_name))

    # For each Achievement, add an AchievementSensor
    for achievement_id, achievement in coordinator.achievements_data.items():
        achievement_name = achievement.get(
            const.DATA_ACHIEVEMENT_NAME,
            f"{const.TRANS_KEY_LABEL_ACHIEVEMENT} {achievement_id}",
        )
        entities.append(
            AchievementSensor(coordinator, entry, achievement_id, achievement_name)
        )

    # For each Challenge, add a ChallengeSensor
    for challenge_id, challenge in coordinator.challenges_data.items():
        challenge_name = challenge.get(
            const.DATA_CHALLENGE_NAME,
            f"{const.TRANS_KEY_LABEL_CHALLENGE} {challenge_id}",
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
        """Include points, description, etc. Uses new per-chore data where possible."""
        chore_info = self.coordinator.chores_data.get(self._chore_id, {})
        shared = chore_info.get(const.DATA_CHORE_SHARED_CHORE, False)
        global_state = chore_info.get(const.DATA_CHORE_STATE, const.CHORE_STATE_UNKNOWN)

        assigned_kids_ids = chore_info.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
        assigned_kids_names = [
            kh.get_kid_name_by_id(self.coordinator, k_id)
            or f"{const.TRANS_KEY_LABEL_KID} {k_id}"
            for k_id in assigned_kids_ids
        ]

        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        kid_chore_data = kid_info.get(const.DATA_KID_CHORE_DATA, {}).get(
            self._chore_id, {}
        )
        periods = kid_chore_data.get(const.DATA_KID_CHORE_DATA_PERIODS, {})
        all_time_stats = periods.get(
            const.DATA_KID_CHORE_DATA_PERIODS_ALL_TIME, {}
        ).get(const.PERIOD_ALL_TIME, {})

        # Use new per-chore data for counts and streaks
        claims_count = all_time_stats.get(
            const.DATA_KID_CHORE_DATA_PERIOD_CLAIMED, const.DEFAULT_ZERO
        )
        approvals_count = all_time_stats.get(
            const.DATA_KID_CHORE_DATA_PERIOD_APPROVED, const.DEFAULT_ZERO
        )

        # Get today's and yesterday's ISO dates
        today_local_iso = kh.get_today_local_date().isoformat()
        yesterday_local_iso = kh.adjust_datetime_by_interval(
            today_local_iso,
            interval_unit=const.CONF_DAYS,
            delta=-1,
            require_future=False,
            return_type=const.HELPER_RETURN_ISO_DATE,
        )

        daily_periods = periods.get(const.DATA_KID_CHORE_DATA_PERIODS_DAILY, {})

        # Try to get the current streak from today's data; if not present, fallback to yesterday's
        current_streak = daily_periods.get(today_local_iso, {}).get(
            const.DATA_KID_CHORE_DATA_PERIOD_LONGEST_STREAK
        ) or daily_periods.get(yesterday_local_iso, {}).get(
            const.DATA_KID_CHORE_DATA_PERIOD_LONGEST_STREAK, const.DEFAULT_ZERO
        )

        highest_streak = all_time_stats.get(
            const.DATA_KID_CHORE_DATA_PERIOD_LONGEST_STREAK, const.DEFAULT_ZERO
        )
        points_earned = all_time_stats.get(
            const.DATA_KID_CHORE_DATA_PERIOD_POINTS, const.DEFAULT_ZERO
        )
        overdue_count = all_time_stats.get(
            const.DATA_KID_CHORE_DATA_PERIOD_OVERDUE, const.DEFAULT_ZERO
        )
        disapproved_count = all_time_stats.get(
            const.DATA_KID_CHORE_DATA_PERIOD_DISAPPROVED, const.DEFAULT_ZERO
        )
        last_longest_streak_date = kid_chore_data.get(
            const.DATA_KID_CHORE_DATA_LAST_LONGEST_STREAK_ALL_TIME
        )

        stored_labels = chore_info.get(const.DATA_CHORE_LABELS, [])
        friendly_labels = [
            kh.get_friendly_label(self.hass, label) for label in stored_labels
        ]

        attributes = {
            const.ATTR_KID_NAME: self._kid_name,
            const.ATTR_CHORE_NAME: self._chore_name,
            const.ATTR_DESCRIPTION: chore_info.get(
                const.DATA_CHORE_DESCRIPTION, const.CONF_EMPTY
            ),
            const.ATTR_ASSIGNED_KIDS: assigned_kids_names,
            const.ATTR_LABELS: friendly_labels,
            const.ATTR_DEFAULT_POINTS: chore_info.get(
                const.DATA_CHORE_DEFAULT_POINTS, const.DEFAULT_ZERO
            ),
            const.ATTR_PARTIAL_ALLOWED: chore_info.get(
                const.DATA_CHORE_PARTIAL_ALLOWED, False
            ),
            const.ATTR_ALLOW_MULTIPLE_CLAIMS_PER_DAY: chore_info.get(
                const.DATA_CHORE_ALLOW_MULTIPLE_CLAIMS_PER_DAY, False
            ),
            const.ATTR_CHORE_POINTS_EARNED: points_earned,
            const.ATTR_CHORE_APPROVALS_COUNT: approvals_count,
            const.ATTR_CHORE_CLAIMS_COUNT: claims_count,
            const.ATTR_CHORE_DISAPPROVED_COUNT: disapproved_count,
            const.ATTR_CHORE_OVERDUE_COUNT: overdue_count,
            const.ATTR_CHORE_CURRENT_STREAK: current_streak,
            const.ATTR_CHORE_HIGHEST_STREAK: highest_streak,
            const.ATTR_CHORE_LAST_LONGEST_STREAK_DATE: last_longest_streak_date,
            const.ATTR_SHARED_CHORE: shared,
            const.ATTR_GLOBAL_STATE: global_state,
            const.ATTR_DUE_DATE: chore_info.get(
                const.DATA_CHORE_DUE_DATE, const.DUE_DATE_NOT_SET
            ),
            const.ATTR_RECURRING_FREQUENCY: chore_info.get(
                const.DATA_CHORE_RECURRING_FREQUENCY, const.CONF_NONE_TEXT
            ),
            const.ATTR_APPLICABLE_DAYS: chore_info.get(
                const.DATA_CHORE_APPLICABLE_DAYS, []
            ),
        }

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

        # Show today's approvals if allowed
        if chore_info.get(const.DATA_CHORE_ALLOW_MULTIPLE_CLAIMS_PER_DAY, False):
            today_approvals = (
                periods.get(const.DATA_KID_CHORE_DATA_PERIODS_DAILY, {})
                .get(kh.get_today_local_date().isoformat(), {})
                .get(const.DATA_KID_CHORE_DATA_PERIOD_APPROVED, const.DEFAULT_ZERO)
            )
            attributes[const.ATTR_CHORE_APPROVALS_TODAY] = today_approvals

        # Add claim, approve, disapprove button entity ids to attributes for direct ui access.
        button_types = [
            (
                const.BUTTON_KC_UID_SUFFIX_APPROVE,
                const.ATTR_CHORE_APPROVE_BUTTON_ENTITY_ID,
            ),
            (
                const.BUTTON_KC_UID_SUFFIX_DISAPPROVE,
                const.ATTR_CHORE_DISAPPROVE_BUTTON_ENTITY_ID,
            ),
            (const.BUTTON_KC_UID_SUFFIX_CLAIM, const.ATTR_CHORE_CLAIM_BUTTON_ENTITY_ID),
        ]
        button_entity_ids = {}
        try:
            entity_registry = async_get(self.hass)
            for suffix, attr_name in button_types:
                unique_id = (
                    f"{self._entry.entry_id}_{self._kid_id}_{self._chore_id}{suffix}"
                )
                entity_id = None
                for entity in entity_registry.entities.values():
                    if entity.unique_id == unique_id:
                        entity_id = entity.entity_id
                        break
                button_entity_ids[attr_name] = entity_id
        except Exception:
            for _, attr_name in button_types:
                button_entity_ids[attr_name] = None

        # Add button entity IDs to the attributes
        attributes.update(button_entity_ids)

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

    @property
    def extra_state_attributes(self):
        """Expose all point stats as attributes."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        point_stats = kid_info.get(const.DATA_KID_POINT_STATS, {})
        attributes = {
            const.ATTR_KID_NAME: self._kid_name,
        }
        # Add all point stats as attributes, prefixed for clarity
        for key, value in point_stats.items():
            attributes[f"point_stat_{key}"] = value
        return attributes


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
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}{const.SENSOR_KC_UID_SUFFIX_KID_MAX_POINTS_EVER_SENSOR}"
        self._entry = entry
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_KID_NAME: kid_name
        }
        self.entity_id = f"{const.SENSOR_KC_PREFIX}{kid_name}{const.SENSOR_KC_EID_SUFFIX_KID_MAX_POINTS_EARNED_SENSOR}"

    @property
    def native_value(self):
        """Return the highest points total the kid has ever reached."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        point_stats = kid_info.get(const.DATA_KID_POINT_STATS, {})
        return point_stats.get(
            const.DATA_KID_POINT_STATS_HIGHEST_BALANCE, const.DEFAULT_ZERO
        )

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
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}{const.SENSOR_KC_UID_SUFFIX_COMPLETED_TOTAL_SENSOR}"
        self._attr_native_unit_of_measurement = const.DEFAULT_CHORES_UNIT
        self._attr_icon = const.DEFAULT_COMPLETED_CHORES_TOTAL_SENSOR_ICON
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_KID_NAME: kid_name
        }
        self.entity_id = f"{const.SENSOR_KC_PREFIX}{kid_name}{const.SENSOR_KC_EID_MIDFIX_CHORES_COMPLETED_TOTAL_SENSOR}"

    @property
    def native_value(self):
        """Return the total number of chores completed by the kid."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        stats = kid_info.get(const.DATA_KID_CHORE_STATS, {})
        return stats.get(
            const.DATA_KID_CHORE_STATS_APPROVED_ALL_TIME, const.DEFAULT_ZERO
        )

    @property
    def extra_state_attributes(self):
        """Return all available chore stats as attributes."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        stats = kid_info.get(const.DATA_KID_CHORE_STATS, {})
        attributes = {
            const.ATTR_KID_NAME: self._kid_name,
        }
        # Add all stats as attributes, prefixed for clarity
        for key, value in stats.items():
            attributes[f"chore_stat_{key}"] = value
        return attributes


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
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}{const.SENSOR_KC_UID_SUFFIX_COMPLETED_DAILY_SENSOR}"
        self._attr_native_unit_of_measurement = const.DEFAULT_CHORES_UNIT
        self._attr_icon = const.DEFAULT_COMPLETED_CHORES_DAILY_SENSOR_ICON
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_KID_NAME: kid_name
        }
        self.entity_id = f"{const.SENSOR_KC_PREFIX}{kid_name}{const.SENSOR_KC_EID_MIDFIX_CHORES_COMPLETED_DAILY_SENSOR}"

    @property
    def native_value(self):
        """Return the number of chores completed today."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        stats = kid_info.get(const.DATA_KID_CHORE_STATS, {})
        return stats.get(const.DATA_KID_CHORE_STATS_APPROVED_TODAY, const.DEFAULT_ZERO)


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
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}{const.SENSOR_KC_UID_SUFFIX_COMPLETED_WEEKLY_SENSOR}"
        self._attr_native_unit_of_measurement = const.DEFAULT_CHORES_UNIT
        self._attr_icon = const.DEFAULT_COMPLETED_CHORES_WEEKLY_SENSOR_ICON
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_KID_NAME: kid_name
        }
        self.entity_id = f"{const.SENSOR_KC_PREFIX}{kid_name}{const.SENSOR_KC_EID_MIDFIX_CHORES_COMPLETED_WEEKLY_SENSOR}"

    @property
    def native_value(self):
        """Return the number of chores completed this week."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        stats = kid_info.get(const.DATA_KID_CHORE_STATS, {})
        return stats.get(const.DATA_KID_CHORE_STATS_APPROVED_WEEK, const.DEFAULT_ZERO)


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
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}{const.SENSOR_KC_UID_SUFFIX_COMPLETED_MONTHLY_SENSOR}"
        self._attr_native_unit_of_measurement = const.DEFAULT_CHORES_UNIT
        self._attr_icon = const.DEFAULT_COMPLETED_CHORES_MONTHLY_SENSOR_ICON
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_KID_NAME: kid_name
        }
        self.entity_id = f"{const.SENSOR_KC_PREFIX}{kid_name}{const.SENSOR_KC_EID_MIDFIX_CHORES_COMPLETED_MONTHLY_SENSOR}"

    @property
    def native_value(self):
        """Return the number of chores completed this month."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        stats = kid_info.get(const.DATA_KID_CHORE_STATS, {})
        return stats.get(const.DATA_KID_CHORE_STATS_APPROVED_MONTH, const.DEFAULT_ZERO)


# ------------------------------------------------------------------------------------------
class KidHighestBadgeSensor(CoordinatorEntity, SensorEntity):
    """Sensor that returns the highest cumulative badge a kid currently has,
    and calculates how many points are needed to reach the next cumulative badge.
    """

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_SENSOR_KIDS_HIGHEST_BADGE_SENSOR

    def __init__(self, coordinator, entry, kid_id, kid_name):
        """Initialize the sensor."""

        super().__init__(coordinator)
        self._entry = entry
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}{const.SENSOR_KC_UID_SUFFIX_KID_HIGHEST_BADGE_SENSOR}"
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_KID_NAME: kid_name
        }
        self.entity_id = f"{const.SENSOR_KC_PREFIX}{kid_name}{const.SENSOR_KC_EID_MIDFIX_KID_HIGHEST_BADGE_SENSOR}"

    @property
    def native_value(self) -> str:
        """Return the badge name of the highest-threshold badge the kid has earned."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        cumulative_badge_progress_info = kid_info.get(
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS, {}
        )
        highest_badge_name = cumulative_badge_progress_info.get(
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_HIGHEST_EARNED_BADGE_NAME,
            const.CONF_NONE_TEXT,
        )
        return highest_badge_name

    @property
    def icon(self):
        """Return the icon for the highest badge."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        cumulative_badge_progress_info = kid_info.get(
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS, {}
        )
        highest_badge_id = cumulative_badge_progress_info.get(
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_HIGHEST_EARNED_BADGE_ID,
            const.CONF_NONE_TEXT,
        )
        highest_badge_info = self.coordinator.badges_data.get(highest_badge_id, {})
        highest_badge_icon = highest_badge_info.get(
            const.DATA_BADGE_ICON, const.DEFAULT_TROPHY_ICON
        )
        return highest_badge_icon

    @property
    def extra_state_attributes(self):
        """Provide additional details about the highest cumulative badge,
        including the points needed to reach the next cumulative badge,
        reset schedule, maintenance rules, description, and awards if present.
        Also shows baseline points, cycle points, grace_end_date, and points to maintenance if applicable.
        """
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        earned_badge_list = [
            badge_name.get(const.DATA_KID_BADGES_EARNED_NAME)
            for badge_name in kid_info.get(const.DATA_KID_BADGES_EARNED, {}).values()
        ]
        cumulative_badge_progress_info = kid_info.get(
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS, {}
        )
        current_badge_id = cumulative_badge_progress_info.get(
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CURRENT_BADGE_ID,
            const.CONF_NONE_TEXT,
        )
        current_badge_name = cumulative_badge_progress_info.get(
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CURRENT_BADGE_NAME,
            const.CONF_NONE_TEXT,
        )
        badge_status = cumulative_badge_progress_info.get(
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_STATUS,
            const.CONF_NONE_TEXT,
        )
        highest_badge_threshold_value = cumulative_badge_progress_info.get(
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_HIGHEST_EARNED_THRESHOLD,
            const.DEFAULT_ZERO,
        )
        points_to_next_badge = cumulative_badge_progress_info.get(
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_NEXT_HIGHER_POINTS_NEEDED,
            const.DEFAULT_ZERO,
        )
        baseline_points = cumulative_badge_progress_info.get(
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_BASELINE,
            const.DEFAULT_ZERO,
        )
        cycle_points = cumulative_badge_progress_info.get(
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_CYCLE_POINTS,
            const.DEFAULT_ZERO,
        )
        grace_end_date = cumulative_badge_progress_info.get(
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_MAINTENANCE_GRACE_END_DATE,
            None,
        )

        current_badge_info = self.coordinator.badges_data.get(current_badge_id, {})

        stored_labels = current_badge_info.get(const.DATA_BADGE_LABELS, [])
        friendly_labels = [
            kh.get_friendly_label(self.hass, label) for label in stored_labels
        ]

        extra_attrs = {}
        # Add description if present
        description = current_badge_info.get(const.DATA_BADGE_DESCRIPTION, "")
        if description:
            extra_attrs[const.DATA_BADGE_DESCRIPTION] = description

        # Add baseline points, cycle points, and grace_end_date using constants
        extra_attrs[const.ATTR_BADGE_CUMULATIVE_BASELINE_POINTS] = baseline_points
        extra_attrs[const.ATTR_BADGE_CUMULATIVE_CYCLE_POINTS] = cycle_points

        target_info = current_badge_info.get(const.DATA_BADGE_TARGET, {})

        # maintenance_rules is an int inside target_info
        maintenance_rules = target_info.get(const.DATA_BADGE_MAINTENANCE_RULES, 0)
        maintenance_end_date = cumulative_badge_progress_info.get(
            const.DATA_KID_CUMULATIVE_BADGE_PROGRESS_MAINTENANCE_END_DATE, None
        )
        if maintenance_rules > 0 and maintenance_end_date:
            extra_attrs[const.ATTR_BADGE_CUMULATIVE_MAINTENANCE_END_DATE] = (
                maintenance_end_date
            )
            extra_attrs[const.ATTR_BADGE_CUMULATIVE_GRACE_END_DATE] = grace_end_date
            extra_attrs[const.ATTR_BADGE_CUMULATIVE_MAINTENANCE_POINTS_REQUIRED] = (
                maintenance_rules
            )
            points_to_maintenance = max(0, maintenance_rules - cycle_points)
            extra_attrs[const.ATTR_BADGE_CUMULATIVE_POINTS_TO_MAINTENANCE] = (
                points_to_maintenance
            )

        # Add reset_schedule fields if recurring_frequency is present
        reset_schedule = current_badge_info.get(const.DATA_BADGE_RESET_SCHEDULE, {})
        if reset_schedule:
            extra_attrs[const.DATA_BADGE_RESET_SCHEDULE] = reset_schedule

        # Add Target fields if present
        if target_info:
            extra_attrs[const.DATA_BADGE_TARGET] = target_info

        # Add awards if present
        awards_info = current_badge_info.get(const.DATA_BADGE_AWARDS, {})
        if awards_info:
            extra_attrs[const.DATA_BADGE_AWARDS] = awards_info

        return {
            const.ATTR_KID_NAME: self._kid_name,
            const.ATTR_LABELS: friendly_labels,
            const.ATTR_ALL_EARNED_BADGES: earned_badge_list,
            const.ATTR_HIGHEST_BADGE_THRESHOLD_VALUE: highest_badge_threshold_value,
            const.ATTR_POINTS_TO_NEXT_BADGE: points_to_next_badge,
            const.ATTR_CURRENT_BADGE_ID: current_badge_id,
            const.ATTR_CURRENT_BADGE_NAME: current_badge_name,
            const.ATTR_BADGE_STATUS: badge_status,
            **extra_attrs,
        }


# ------------------------------------------------------------------------------------------
class KidBadgeSensor(CoordinatorEntity, SensorEntity):
    """Sensor for a kid's progress on a specific non-cumulative badge."""

    _attr_has_entity_name = True
    _attr_translation_key = "kid_badge_sensor"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(
        self,
        coordinator: KidsChoresDataCoordinator,
        entry: ConfigEntry,
        kid_id: str,
        kid_name: str,
        badge_id: str,
        badge_name: str,
    ):
        """Initialize the KidBadgeSensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._badge_id = badge_id
        self._badge_name = badge_name
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_{badge_id}_badge_progress"
        self._attr_translation_placeholders = {
            "kid_name": kid_name,
            "badge_name": badge_name,
        }
        self.entity_id = f"{const.SENSOR_KC_PREFIX}{kid_name}_badge_status_{badge_name}"

    @property
    def native_value(self) -> float:
        """Return the badge's overall progress as a percentage."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        badge_progress = kid_info.get(const.DATA_KID_BADGE_PROGRESS, {}).get(
            self._badge_id, {}
        )
        progress = badge_progress.get(
            const.DATA_KID_BADGE_PROGRESS_OVERALL_PROGRESS, 0.0
        )
        return round(progress * 100, 1)

    @property
    def extra_state_attributes(self) -> dict:
        """Return the badge progress details as attributes."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        badge_progress = kid_info.get(const.DATA_KID_BADGE_PROGRESS, {}).get(
            self._badge_id, {}
        )

        # Build a dictionary with only the requested fields
        attributes = {
            const.DATA_KID_BADGE_PROGRESS_NAME: badge_progress.get(
                const.DATA_KID_BADGE_PROGRESS_NAME
            ),
            const.DATA_KID_BADGE_PROGRESS_TYPE: badge_progress.get(
                const.DATA_KID_BADGE_PROGRESS_TYPE
            ),
            const.DATA_KID_BADGE_PROGRESS_STATUS: badge_progress.get(
                const.DATA_KID_BADGE_PROGRESS_STATUS
            ),
            const.DATA_KID_BADGE_PROGRESS_TARGET_TYPE: badge_progress.get(
                const.DATA_KID_BADGE_PROGRESS_TARGET_TYPE
            ),
            const.DATA_KID_BADGE_PROGRESS_TARGET_THRESHOLD_VALUE: badge_progress.get(
                const.DATA_KID_BADGE_PROGRESS_TARGET_THRESHOLD_VALUE
            ),
            const.DATA_KID_BADGE_PROGRESS_RECURRING_FREQUENCY: badge_progress.get(
                const.DATA_KID_BADGE_PROGRESS_RECURRING_FREQUENCY
            ),
            const.DATA_KID_BADGE_PROGRESS_LAST_UPDATE_DAY: badge_progress.get(
                const.DATA_KID_BADGE_PROGRESS_LAST_UPDATE_DAY
            ),
            const.DATA_KID_BADGE_PROGRESS_OVERALL_PROGRESS: badge_progress.get(
                const.DATA_KID_BADGE_PROGRESS_OVERALL_PROGRESS
            ),
            const.DATA_KID_BADGE_PROGRESS_CRITERIA_MET: badge_progress.get(
                const.DATA_KID_BADGE_PROGRESS_CRITERIA_MET
            ),
        }

        # Convert tracked chore IDs to friendly names and add to attributes
        tracked_chore_ids = attributes.get(
            const.DATA_KID_BADGE_PROGRESS_TRACKED_CHORES, []
        )
        if tracked_chore_ids:
            chore_names = [
                self.coordinator.chores_data.get(chore_id, {}).get(
                    const.DATA_CHORE_NAME, chore_id
                )
                for chore_id in tracked_chore_ids
            ]
            attributes[const.DATA_KID_BADGE_PROGRESS_TRACKED_CHORES] = chore_names

        return attributes

    @property
    def icon(self) -> str:
        """Return the icon for the badge."""
        badge_info = self.coordinator.badges_data.get(self._badge_id, {})
        return badge_info.get(const.DATA_BADGE_ICON, const.DEFAULT_BADGE_ICON)


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
        super().__init__(coordinator)
        self._entry = entry
        self._badge_id = badge_id
        self._badge_name = badge_name
        self._attr_unique_id = (
            f"{entry.entry_id}_{badge_id}{const.SENSOR_KC_UID_SUFFIX_BADGE_SENSOR}"
        )
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_BADGE_NAME: badge_name
        }
        self.entity_id = f"{const.SENSOR_KC_PREFIX}{badge_name}{const.SENSOR_KC_EID_SUFFIX_BADGE_SENSOR}"

    @property
    def native_value(self) -> int:
        """State: number of kids who have earned this badge."""
        badge_info = self.coordinator.badges_data.get(self._badge_id, {})
        kids_earned_ids = badge_info.get(const.DATA_BADGE_EARNED_BY, [])
        return len(kids_earned_ids)

    @property
    def extra_state_attributes(self):
        """Full badge info, including per-kid earned stats and periods."""
        badge_info = self.coordinator.badges_data.get(self._badge_id, {})
        attributes = {}

        # Basic badge info
        attributes[const.ATTR_FRIENDLY_NAME] = badge_info.get(const.DATA_BADGE_NAME)
        attributes[const.ATTR_DESCRIPTION] = badge_info.get(
            const.DATA_BADGE_DESCRIPTION, const.CONF_EMPTY
        )
        attributes[const.ATTR_BADGE_TYPE] = badge_info.get(
            const.DATA_BADGE_TYPE, const.BADGE_TYPE_CUMULATIVE
        )
        attributes[const.ATTR_LABELS] = [
            kh.get_friendly_label(self.hass, label)
            for label in badge_info.get(const.DATA_BADGE_LABELS, [])
        ]
        # Per-kid earned stats
        kids_earned_ids = badge_info.get(const.DATA_BADGE_EARNED_BY, [])
        kids_earned = []
        for kid_id in kids_earned_ids:
            kid_info = self.coordinator.kids_data.get(kid_id)
            if not kid_info:
                continue
            kids_earned.append(kid_info.get(const.DATA_KID_NAME, kid_id))

        attributes[const.ATTR_KIDS_EARNED] = kids_earned

        # Per-kid assigned stats
        kids_assigned_ids = badge_info.get(const.DATA_BADGE_ASSIGNED_TO, [])
        kids_assigned = []
        for kid_id in kids_assigned_ids:
            kid_info = self.coordinator.kids_data.get(kid_id)
            if not kid_info:
                continue
            kids_assigned.append(kid_info.get(const.DATA_KID_NAME, kid_id))

        attributes[const.ATTR_KIDS_ASSIGNED] = kids_assigned

        attributes[const.ATTR_TARGET] = badge_info.get(const.DATA_BADGE_TARGET, None)
        attributes[const.ATTR_ASSOCIATED_ACHIEVEMENT] = badge_info.get(
            const.DATA_BADGE_ASSOCIATED_ACHIEVEMENT, None
        )
        attributes[const.ATTR_ASSOCIATED_CHALLENGE] = badge_info.get(
            const.DATA_BADGE_ASSOCIATED_CHALLENGE, None
        )
        occasion_type = badge_info.get(const.DATA_BADGE_OCCASION_TYPE, None)
        if occasion_type:
            attributes[const.ATTR_OCCASION_TYPE] = occasion_type
        attributes[const.ATTR_REQUIRED_CHORES] = [
            self.coordinator.chores_data.get(chore_id, {}).get(
                const.DATA_CHORE_NAME, chore_id
            )
            for chore_id in badge_info.get(const.DATA_BADGE_REQUIRED_CHORES_LEGACY, [])
        ]

        # Awards info
        awards_data = badge_info.get(const.DATA_BADGE_AWARDS, {})

        # Add friendly names for award items
        award_items = awards_data.get(const.DATA_BADGE_AWARDS_AWARD_ITEMS, [])
        friendly_award_names = []
        for item in award_items:
            if item.startswith(const.AWARD_ITEMS_PREFIX_REWARD):
                reward_id = item.split(":", 1)[1]
                reward_info = self.coordinator.rewards_data.get(reward_id, {})
                friendly_name = reward_info.get(
                    const.DATA_REWARD_NAME, f"Reward: {reward_id}"
                )
                friendly_award_names.append(
                    f"{const.AWARD_ITEMS_PREFIX_REWARD}{friendly_name}"
                )
            elif item.startswith(const.AWARD_ITEMS_PREFIX_BONUS):
                bonus_id = item.split(":", 1)[1]
                bonus_info = self.coordinator.bonuses_data.get(bonus_id, {})
                friendly_name = bonus_info.get(
                    const.DATA_BONUS_NAME, f"Bonus: {bonus_id}"
                )
                friendly_award_names.append(
                    f"{const.AWARD_ITEMS_PREFIX_BONUS}{friendly_name}"
                )
            elif item.startswith(const.AWARD_ITEMS_PREFIX_PENALTY):
                penalty_id = item.split(":", 1)[1]
                penalty_info = self.coordinator.penalties_data.get(penalty_id, {})
                friendly_name = penalty_info.get(
                    const.DATA_PENALTY_NAME, f"Penalty: {penalty_id}"
                )
                friendly_award_names.append(
                    f"{const.AWARD_ITEMS_PREFIX_PENALTY}{friendly_name}"
                )
        attributes[const.ATTR_BADGE_AWARDS] = friendly_award_names

        attributes[const.ATTR_RESET_SCHEDULE] = badge_info.get(
            const.DATA_BADGE_RESET_SCHEDULE, None
        )

        return attributes

    @property
    def icon(self) -> str:
        badge_info = self.coordinator.badges_data.get(self._badge_id, {})
        return badge_info.get(const.DATA_BADGE_ICON, const.DEFAULT_BADGE_ICON)


# ------------------------------------------------------------------------------------------
class PendingChoreApprovalsSensor(CoordinatorEntity, SensorEntity):
    """Sensor listing all pending chore approvals."""

    _attr_has_entity_name = True
    _attr_translation_key = const.TRANS_KEY_SENSOR_PENDING_CHORES_APPROVALS_SENSOR

    def __init__(self, coordinator, entry):
        """Initialize the sensor."""

        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}{const.SENSOR_KC_UID_SUFFIX_PENDING_CHORE_APPROVALS_SENSOR}"
        self._attr_icon = const.DEFAULT_PENDING_CHORE_APPROVALS_SENSOR_ICON
        self._attr_native_unit_of_measurement = const.DEFAULT_PENDING_CHORES_UNIT
        self.entity_id = f"{const.SENSOR_KC_PREFIX}{const.SENSOR_KC_EID_SUFFIX_PENDING_CHORE_APPROVALS_SENSOR}"

    @property
    def native_value(self):
        """Return a summary of pending chore approvals."""
        approvals = self.coordinator._data.get(const.DATA_PENDING_CHORE_APPROVALS, [])
        return f"{len(approvals)}"

    @property
    def extra_state_attributes(self):
        """Return detailed pending chores."""
        approvals = self.coordinator._data.get(const.DATA_PENDING_CHORE_APPROVALS, [])
        grouped_by_kid = {}

        for approval in approvals:
            kid_name = (
                kh.get_kid_name_by_id(self.coordinator, approval[const.DATA_KID_ID])
                or const.UNKNOWN_KID
            )
            chore_info = self.coordinator.chores_data.get(
                approval[const.DATA_CHORE_ID], {}
            )
            chore_name = chore_info.get(const.DATA_CHORE_NAME, const.UNKNOWN_CHORE)

            timestamp = approval[const.DATA_CHORE_TIMESTAMP]

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
        self._attr_unique_id = f"{entry.entry_id}{const.SENSOR_KC_UID_SUFFIX_PENDING_REWARD_APPROVALS_SENSOR}"
        self._attr_icon = const.DEFAULT_PENDING_REWARD_APPROVALS_SENSOR_ICON
        self._attr_native_unit_of_measurement = const.DEFAULT_PENDING_REWARDS_UNIT
        self.entity_id = f"{const.SENSOR_KC_PREFIX}{const.SENSOR_KC_EID_SUFFIX_PENDING_REWARD_APPROVALS_SENSOR}"

    @property
    def native_value(self):
        """Return a summary of pending reward approvals."""
        approvals = self.coordinator._data.get(const.DATA_PENDING_REWARD_APPROVALS, [])
        return f"{len(approvals)}"

    @property
    def extra_state_attributes(self):
        """Return detailed pending rewards."""
        approvals = self.coordinator._data.get(const.DATA_PENDING_REWARD_APPROVALS, [])
        grouped_by_kid = {}

        for approval in approvals:
            kid_name = (
                kh.get_kid_name_by_id(self.coordinator, approval[const.DATA_KID_ID])
                or const.UNKNOWN_KID
            )
            reward_info = self.coordinator.rewards_data.get(
                approval[const.DATA_REWARD_ID], {}
            )
            reward_name = reward_info.get(const.DATA_REWARD_NAME, const.UNKNOWN_REWARD)

            timestamp = approval[const.DATA_REWARD_TIMESTAMP]

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
        self._attr_unique_id = f"{entry.entry_id}_{chore_id}{const.SENSOR_KC_UID_SUFFIX_SHARED_CHORE_GLOBAL_STATE_SENSOR}"
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_CHORE_NAME: chore_name,
        }
        self.entity_id = f"{const.SENSOR_KC_PREFIX}{const.SENSOR_KC_EID_MIDFIX_SHARED_CHORE_GLOBAL_STATUS_SENSOR}{chore_name}"

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
            kh.get_kid_name_by_id(self.coordinator, k_id)
            or f"{const.TRANS_KEY_LABEL_KID} {k_id}"
            for k_id in assigned_kids_ids
        ]

        stored_labels = chore_info.get(const.DATA_CHORE_LABELS, [])
        friendly_labels = [
            kh.get_friendly_label(self.hass, label) for label in stored_labels
        ]

        total_approvals_today = const.DEFAULT_ZERO
        for kid_id in assigned_kids_ids:
            kid_data = self.coordinator.kids_data.get(kid_id, {})
            total_approvals_today += kid_data.get(
                const.DATA_KID_TODAY_CHORE_APPROVALS, {}
            ).get(self._chore_id, const.DEFAULT_ZERO)

        attributes = {
            const.ATTR_CHORE_NAME: self._chore_name,
            const.ATTR_DESCRIPTION: chore_info.get(
                const.DATA_CHORE_DESCRIPTION, const.CONF_EMPTY
            ),
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
            const.ATTR_CHORE_APPROVALS_TODAY: total_approvals_today,
            const.ATTR_ASSIGNED_KIDS: assigned_kids_names,
            const.ATTR_LABELS: friendly_labels,
        }

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
    def icon(self) -> str:
        """Return the icon for the chore sensor."""
        chore_info = self.coordinator.chores_data.get(self._chore_id, {})
        return chore_info.get(const.DATA_CHORE_ICON, const.DEFAULT_CHORE_SENSOR_ICON)


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
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_{reward_id}{const.SENSOR_KC_UID_SUFFIX_REWARD_STATUS_SENSOR}"
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_KID_NAME: kid_name,
            const.TRANS_KEY_SENSOR_ATTR_REWARD_NAME: reward_name,
        }
        self.entity_id = f"{const.SENSOR_KC_PREFIX}{kid_name}{const.SENSOR_KC_EID_MIDFIX_REWARD_STATUS_SENSOR}{reward_name}"

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

        stored_labels = reward_info.get(const.DATA_REWARD_LABELS, [])
        friendly_labels = [
            kh.get_friendly_label(self.hass, label) for label in stored_labels
        ]

        attributes = {
            const.ATTR_KID_NAME: self._kid_name,
            const.ATTR_REWARD_NAME: self._reward_name,
            const.ATTR_DESCRIPTION: reward_info.get(
                const.DATA_REWARD_DESCRIPTION, const.CONF_EMPTY
            ),
            const.ATTR_COST: reward_info.get(
                const.DATA_REWARD_COST, const.DEFAULT_REWARD_COST
            ),
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
        return reward_info.get(const.DATA_REWARD_ICON, const.DEFAULT_REWARD_ICON)


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
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_{penalty_id}{const.SENSOR_KC_UID_SUFFIX_PENALTY_APPLIES_SENSOR}"
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_KID_NAME: kid_name,
            const.TRANS_KEY_SENSOR_ATTR_PENALTY_NAME: penalty_name,
        }
        self.entity_id = f"{const.SENSOR_KC_PREFIX}{kid_name}{const.SENSOR_KC_EID_MIDFIX_PENALTY_APPLIES_SENSOR}{penalty_name}"

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

        stored_labels = penalty_info.get(const.DATA_PENALTY_LABELS, [])
        friendly_labels = [
            kh.get_friendly_label(self.hass, label) for label in stored_labels
        ]

        return {
            const.ATTR_KID_NAME: self._kid_name,
            const.ATTR_PENALTY_NAME: self._penalty_name,
            const.ATTR_DESCRIPTION: penalty_info.get(
                const.DATA_PENALTY_DESCRIPTION, const.CONF_EMPTY
            ),
            const.ATTR_PENALTY_POINTS: penalty_info.get(
                const.DATA_PENALTY_POINTS, const.DEFAULT_PENALTY_POINTS
            ),
            const.ATTR_LABELS: friendly_labels,
        }

    @property
    def icon(self):
        """Return the chore's custom icon if set, else fallback."""
        penalty_info = self.coordinator.penalties_data.get(self._penalty_id, {})
        return penalty_info.get(const.DATA_PENALTY_ICON, const.DEFAULT_PENALTY_ICON)


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
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}{const.SENSOR_KC_UID_SUFFIX_KID_POINTS_EARNED_DAILY_SENSOR}"
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_KID_NAME: kid_name,
        }
        self.entity_id = f"{const.SENSOR_KC_PREFIX}{kid_name}{const.SENSOR_KC_EID_SUFFIX_KID_POINTS_EARNED_DAILY_SENSOR}"

    @property
    def native_value(self):
        """Return how many net points the kid has earned so far today."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        point_stats = kid_info.get(const.DATA_KID_POINT_STATS, {})
        return point_stats.get(const.DATA_KID_POINT_STATS_NET_TODAY, const.DEFAULT_ZERO)

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
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}{const.SENSOR_KC_UID_SUFFIX_KID_POINTS_EARNED_WEEKLY_SENSOR}"
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_KID_NAME: kid_name,
        }
        self.entity_id = f"{const.SENSOR_KC_PREFIX}{kid_name}{const.SENSOR_KC_EID_SUFFIX_KID_POINTS_EARNED_WEEKLY_SENSOR}"

    @property
    def native_value(self):
        """Return how many net points the kid has earned this week."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        point_stats = kid_info.get(const.DATA_KID_POINT_STATS, {})
        return point_stats.get(const.DATA_KID_POINT_STATS_NET_WEEK, const.DEFAULT_ZERO)

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
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}{const.SENSOR_KC_UID_SUFFIX_KID_POINTS_EARNED_MONTHLY_SENSOR}"
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_KID_NAME: kid_name,
        }
        self.entity_id = f"{const.SENSOR_KC_PREFIX}{kid_name}{const.SENSOR_KC_EID_SUFFIX_KID_POINTS_EARNED_MONTHLY_SENSOR}"

    @property
    def native_value(self):
        """Return how many net points the kid has earned this month."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        point_stats = kid_info.get(const.DATA_KID_POINT_STATS, {})
        return point_stats.get(const.DATA_KID_POINT_STATS_NET_MONTH, const.DEFAULT_ZERO)

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
        self._attr_unique_id = f"{entry.entry_id}_{achievement_id}{const.SENSOR_KC_UID_SUFFIX_ACHIEVEMENT_SENSOR}"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_ACHIEVEMENT_NAME: achievement_name,
        }
        self.entity_id = f"{const.SENSOR_KC_PREFIX}{const.SENSOR_KC_EID_MIDFIX_ACHIEVEMENT_SENSOR}{achievement_name}"

    @property
    def native_value(self):
        """Return the overall progress percentage toward the achievement."""

        achievement = self.coordinator.achievements_data.get(self._achievement_id, {})
        target = achievement.get(const.DATA_ACHIEVEMENT_TARGET_VALUE, 1)
        assigned_kids = achievement.get(const.DATA_ACHIEVEMENT_ASSIGNED_KIDS, [])

        if not assigned_kids:
            return const.DEFAULT_ZERO

        ach_type = achievement.get(const.DATA_ACHIEVEMENT_TYPE)
        if ach_type == const.ACHIEVEMENT_TYPE_TOTAL:
            total_current = const.DEFAULT_ZERO
            total_effective_target = const.DEFAULT_ZERO

            for kid_id in assigned_kids:
                progress_data = achievement.get(
                    const.DATA_ACHIEVEMENT_PROGRESS, {}
                ).get(kid_id, {})
                baseline = (
                    progress_data.get(
                        const.DATA_ACHIEVEMENT_BASELINE, const.DEFAULT_ZERO
                    )
                    if isinstance(progress_data, dict)
                    else const.DEFAULT_ZERO
                )
                current_total = self.coordinator.kids_data.get(kid_id, {}).get(
                    const.DATA_KID_COMPLETED_CHORES_TOTAL_LEGACY, const.DEFAULT_ZERO
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
                progress_data = achievement.get(
                    const.DATA_ACHIEVEMENT_PROGRESS, {}
                ).get(kid_id, {})
                total_current += (
                    progress_data.get(
                        const.DATA_ACHIEVEMENT_CURRENT_STREAK, const.DEFAULT_ZERO
                    )
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
                    const.DATA_KID_COMPLETED_CHORES_TODAY_LEGACY, const.DEFAULT_ZERO
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
        progress = achievement.get(const.DATA_ACHIEVEMENT_PROGRESS, {})
        kids_progress = {}

        earned_by = []
        for kid_id, data in progress.items():
            if data.get(const.DATA_ACHIEVEMENT_AWARDED, False):
                kid_name = kh.get_kid_name_by_id(self.coordinator, kid_id) or kid_id
                earned_by.append(kid_name)

        associated_chore = const.CONF_EMPTY
        selected_chore_id = achievement.get(const.DATA_ACHIEVEMENT_SELECTED_CHORE_ID)
        if selected_chore_id:
            associated_chore = self.coordinator.chores_data.get(
                selected_chore_id, {}
            ).get(const.DATA_CHORE_NAME, const.CONF_EMPTY)

        assigned_kids_ids = achievement.get(const.DATA_ACHIEVEMENT_ASSIGNED_KIDS, [])
        assigned_kids_names = [
            kh.get_kid_name_by_id(self.coordinator, k_id)
            or f"{const.TRANS_KEY_LABEL_KID} {k_id}"
            for k_id in assigned_kids_ids
        ]
        ach_type = achievement.get(const.DATA_ACHIEVEMENT_TYPE)
        for kid_id in assigned_kids_ids:
            kid_name = kh.get_kid_name_by_id(self.coordinator, kid_id) or kid_id
            progress_data = achievement.get(const.DATA_ACHIEVEMENT_PROGRESS, {}).get(
                kid_id, {}
            )
            if ach_type == const.ACHIEVEMENT_TYPE_TOTAL:
                kids_progress[kid_name] = progress_data.get(
                    const.DATA_ACHIEVEMENT_CURRENT_VALUE, const.DEFAULT_ZERO
                )
            elif ach_type == const.ACHIEVEMENT_TYPE_STREAK:
                kids_progress[kid_name] = progress_data.get(
                    const.DATA_ACHIEVEMENT_CURRENT_STREAK, const.DEFAULT_ZERO
                )
            elif (
                achievement.get(const.DATA_ACHIEVEMENT_TYPE)
                == const.ACHIEVEMENT_TYPE_DAILY_MIN
            ):
                kids_progress[kid_name] = self.coordinator.kids_data.get(
                    kid_id, {}
                ).get(const.DATA_KID_COMPLETED_CHORES_TODAY_LEGACY, const.DEFAULT_ZERO)
            else:
                kids_progress[kid_name] = const.DEFAULT_ZERO

        stored_labels = achievement.get(const.DATA_ACHIEVEMENT_LABELS, [])
        friendly_labels = [
            kh.get_friendly_label(self.hass, label) for label in stored_labels
        ]

        return {
            const.ATTR_ACHIEVEMENT_NAME: self._achievement_name,
            const.ATTR_DESCRIPTION: achievement.get(
                const.DATA_ACHIEVEMENT_DESCRIPTION, const.CONF_EMPTY
            ),
            const.ATTR_ASSIGNED_KIDS: assigned_kids_names,
            const.ATTR_TYPE: ach_type,
            const.ATTR_ASSOCIATED_CHORE: associated_chore,
            const.ATTR_CRITERIA: achievement.get(
                const.DATA_ACHIEVEMENT_CRITERIA, const.CONF_EMPTY
            ),
            const.ATTR_TARGET_VALUE: achievement.get(
                const.DATA_ACHIEVEMENT_TARGET_VALUE
            ),
            const.ATTR_REWARD_POINTS: achievement.get(
                const.DATA_ACHIEVEMENT_REWARD_POINTS
            ),
            const.ATTR_KIDS_EARNED: earned_by,
            const.ATTR_LABELS: friendly_labels,
        }

    @property
    def icon(self):
        """Return an icon; you could choose a trophy icon."""
        achievement_info = self.coordinator.achievements_data.get(
            self._achievement_id, {}
        )
        return achievement_info.get(
            const.DATA_ACHIEVEMENT_ICON, const.DEFAULT_ACHIEVEMENTS_ICON
        )


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
        self._attr_unique_id = f"{entry.entry_id}_{challenge_id}{const.SENSOR_KC_UID_SUFFIX_CHALLENGE_SENSOR}"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_CHALLENGE_NAME: challenge_name,
        }
        self.entity_id = f"{const.SENSOR_KC_PREFIX}{const.SENSOR_KC_EID_MIDFIX_CHALLENGE_SENSOR}{challenge_name}"

    @property
    def native_value(self):
        """Return the overall progress percentage toward the challenge."""

        challenge = self.coordinator.challenges_data.get(self._challenge_id, {})
        target = challenge.get(const.DATA_CHALLENGE_TARGET_VALUE, 1)
        assigned_kids = challenge.get(const.DATA_CHALLENGE_ASSIGNED_KIDS, [])

        if not assigned_kids:
            return const.DEFAULT_ZERO

        challenge_type = challenge.get(const.DATA_CHALLENGE_TYPE)
        total_progress = const.DEFAULT_ZERO

        for kid_id in assigned_kids:
            progress_data = challenge.get(const.DATA_CHALLENGE_PROGRESS, {}).get(
                kid_id, {}
            )

            if challenge_type == const.CHALLENGE_TYPE_TOTAL_WITHIN_WINDOW:
                total_progress += progress_data.get(
                    const.DATA_CHALLENGE_COUNT, const.DEFAULT_ZERO
                )

            elif challenge_type == const.CHALLENGE_TYPE_DAILY_MIN:
                if isinstance(progress_data, dict):
                    daily_counts = progress_data.get(
                        const.DATA_CHALLENGE_DAILY_COUNTS, {}
                    )
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
        progress = challenge.get(const.DATA_CHALLENGE_PROGRESS, {})
        kids_progress = {}
        challenge_type = challenge.get(const.DATA_CHALLENGE_TYPE)

        earned_by = []
        for kid_id, data in progress.items():
            if data.get(const.DATA_CHALLENGE_AWARDED, False):
                kid_name = kh.get_kid_name_by_id(self.coordinator, kid_id) or kid_id
                earned_by.append(kid_name)

        associated_chore = const.CONF_EMPTY
        selected_chore_id = challenge.get(const.DATA_CHALLENGE_SELECTED_CHORE_ID)
        if selected_chore_id:
            associated_chore = self.coordinator.chores_data.get(
                selected_chore_id, {}
            ).get(const.DATA_CHORE_NAME, const.CONF_EMPTY)

        assigned_kids_ids = challenge.get(const.DATA_CHALLENGE_ASSIGNED_KIDS, [])
        assigned_kids_names = [
            kh.get_kid_name_by_id(self.coordinator, k_id)
            or f"{const.TRANS_KEY_LABEL_KID} {k_id}"
            for k_id in assigned_kids_ids
        ]

        for kid_id in assigned_kids_ids:
            kid_name = kh.get_kid_name_by_id(self.coordinator, kid_id) or kid_id
            progress_data = challenge.get(const.DATA_CHALLENGE_PROGRESS, {}).get(
                kid_id, {}
            )
            if challenge_type == const.CHALLENGE_TYPE_TOTAL_WITHIN_WINDOW:
                kids_progress[kid_name] = progress_data.get(
                    const.DATA_CHALLENGE_COUNT, const.DEFAULT_ZERO
                )
            elif challenge_type == const.CHALLENGE_TYPE_DAILY_MIN:
                if isinstance(progress_data, dict):
                    kids_progress[kid_name] = sum(
                        progress_data.get(
                            const.DATA_CHALLENGE_DAILY_COUNTS, {}
                        ).values()
                    )
                else:
                    kids_progress[kid_name] = const.DEFAULT_ZERO
            else:
                kids_progress[kid_name] = const.DEFAULT_ZERO

        stored_labels = challenge.get(const.DATA_CHALLENGE_LABELS, [])
        friendly_labels = [
            kh.get_friendly_label(self.hass, label) for label in stored_labels
        ]

        return {
            const.ATTR_CHALLENGE_NAME: self._challenge_name,
            const.ATTR_DESCRIPTION: challenge.get(
                const.DATA_CHALLENGE_DESCRIPTION, const.CONF_EMPTY
            ),
            const.ATTR_ASSIGNED_KIDS: assigned_kids_names,
            const.ATTR_TYPE: challenge_type,
            const.ATTR_ASSOCIATED_CHORE: associated_chore,
            const.ATTR_CRITERIA: challenge.get(
                const.DATA_CHALLENGE_CRITERIA, const.CONF_EMPTY
            ),
            const.ATTR_TARGET_VALUE: challenge.get(const.DATA_CHALLENGE_TARGET_VALUE),
            const.ATTR_REWARD_POINTS: challenge.get(const.DATA_CHALLENGE_REWARD_POINTS),
            const.ATTR_START_DATE: challenge.get(const.DATA_CHALLENGE_START_DATE),
            const.ATTR_END_DATE: challenge.get(const.DATA_CHALLENGE_END_DATE),
            const.ATTR_KIDS_EARNED: earned_by,
            const.ATTR_LABELS: friendly_labels,
        }

    @property
    def icon(self):
        """Return an icon for challenges (you might want to choose one that fits your theme)."""
        challenge_info = self.coordinator.challenges_data.get(self._challenge_id, {})
        return challenge_info.get(
            const.DATA_CHALLENGE_ICON, const.DEFAULT_ACHIEVEMENTS_ICON
        )


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
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_{achievement_id}{const.SENSOR_KC_UID_SUFFIX_ACHIEVEMENT_PROGRESS_SENSOR}"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_KID_NAME: kid_name,
            const.TRANS_KEY_SENSOR_ATTR_ACHIEVEMENT_NAME: achievement_name,
        }
        self.entity_id = f"{const.SENSOR_KC_PREFIX}{kid_name}{const.SENSOR_KC_EID_MIDFIX_ACHIEVEMENT_PROGRESS_SENSOR}{achievement_name}"

    @property
    def native_value(self) -> float:
        """Return the progress percentage toward the achievement."""
        achievement = self.coordinator.achievements_data.get(self._achievement_id, {})
        target = achievement.get(const.DATA_ACHIEVEMENT_TARGET_VALUE, 1)
        ach_type = achievement.get(const.DATA_ACHIEVEMENT_TYPE)

        if ach_type == const.ACHIEVEMENT_TYPE_TOTAL:
            progress_data = achievement.get(const.DATA_ACHIEVEMENT_PROGRESS, {}).get(
                self._kid_id, {}
            )

            baseline = (
                progress_data.get(const.DATA_ACHIEVEMENT_BASELINE, const.DEFAULT_ZERO)
                if isinstance(progress_data, dict)
                else const.DEFAULT_ZERO
            )

            current_total = self.coordinator.kids_data.get(self._kid_id, {}).get(
                const.DATA_KID_COMPLETED_CHORES_TODAY_LEGACY, const.DEFAULT_ZERO
            )

            effective_target = baseline + target

            percent = (
                (current_total / effective_target * 100)
                if effective_target > const.DEFAULT_ZERO
                else const.DEFAULT_ZERO
            )

        elif ach_type == const.ACHIEVEMENT_TYPE_STREAK:
            progress_data = achievement.get(const.DATA_ACHIEVEMENT_PROGRESS, {}).get(
                self._kid_id, {}
            )

            progress = (
                progress_data.get(
                    const.DATA_ACHIEVEMENT_CURRENT_STREAK, const.DEFAULT_ZERO
                )
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
                const.DATA_KID_COMPLETED_CHORES_TOTAL_LEGACY, const.DEFAULT_ZERO
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
        target = achievement.get(const.DATA_ACHIEVEMENT_TARGET_VALUE, 1)
        progress_data = achievement.get(const.DATA_ACHIEVEMENT_PROGRESS, {}).get(
            self._kid_id, {}
        )
        raw_progress = const.DEFAULT_ZERO

        awarded = (
            progress_data.get(const.DATA_ACHIEVEMENT_AWARDED, False)
            if isinstance(progress_data, dict)
            else False
        )

        if achievement.get(const.DATA_ACHIEVEMENT_TYPE) == const.ACHIEVEMENT_TYPE_TOTAL:
            raw_progress = (
                progress_data.get(
                    const.DATA_ACHIEVEMENT_CURRENT_VALUE, const.DEFAULT_ZERO
                )
                if isinstance(progress_data, dict)
                else const.DEFAULT_ZERO
            )

        elif (
            achievement.get(const.DATA_ACHIEVEMENT_TYPE)
            == const.ACHIEVEMENT_TYPE_STREAK
        ):
            raw_progress = (
                progress_data.get(
                    const.DATA_ACHIEVEMENT_CURRENT_STREAK, const.DEFAULT_ZERO
                )
                if isinstance(progress_data, dict)
                else const.DEFAULT_ZERO
            )

        elif (
            achievement.get(const.DATA_ACHIEVEMENT_TYPE)
            == const.ACHIEVEMENT_TYPE_DAILY_MIN
        ):
            raw_progress = self.coordinator.kids_data.get(self._kid_id, {}).get(
                const.DATA_KID_COMPLETED_CHORES_TODAY_LEGACY, const.DEFAULT_ZERO
            )

        associated_chore = const.CONF_EMPTY
        selected_chore_id = achievement.get(const.DATA_ACHIEVEMENT_SELECTED_CHORE_ID)
        if selected_chore_id:
            associated_chore = self.coordinator.chores_data.get(
                selected_chore_id, {}
            ).get(const.DATA_CHORE_NAME, const.CONF_EMPTY)

        assigned_kids_ids = achievement.get(const.DATA_ACHIEVEMENT_ASSIGNED_KIDS, [])
        assigned_kids_names = [
            kh.get_kid_name_by_id(self.coordinator, k_id)
            or f"{const.TRANS_KEY_LABEL_KID} {k_id}"
            for k_id in assigned_kids_ids
        ]

        stored_labels = achievement.get(const.DATA_ACHIEVEMENT_LABELS, [])
        friendly_labels = [
            kh.get_friendly_label(self.hass, label) for label in stored_labels
        ]

        return {
            const.ATTR_ACHIEVEMENT_NAME: self._achievement_name,
            const.ATTR_DESCRIPTION: achievement.get(
                const.DATA_ACHIEVEMENT_DESCRIPTION, const.CONF_EMPTY
            ),
            const.ATTR_ASSIGNED_KIDS: assigned_kids_names,
            const.ATTR_TYPE: achievement.get(const.DATA_ACHIEVEMENT_TYPE),
            const.ATTR_ASSOCIATED_CHORE: associated_chore,
            const.ATTR_CRITERIA: achievement.get(
                const.DATA_ACHIEVEMENT_CRITERIA, const.CONF_EMPTY
            ),
            const.ATTR_TARGET_VALUE: target,
            const.ATTR_REWARD_POINTS: achievement.get(
                const.DATA_ACHIEVEMENT_REWARD_POINTS
            ),
            const.ATTR_RAW_PROGRESS: raw_progress,
            const.ATTR_AWARDED: awarded,
            const.ATTR_LABELS: friendly_labels,
        }

    @property
    def icon(self) -> str:
        """Return the icon for the achievement."""
        achievement = self.coordinator.achievements_data.get(self._achievement_id, {})
        return achievement.get(
            const.DATA_ACHIEVEMENT_ICON, const.DEFAULT_ACHIEVEMENTS_ICON
        )


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
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_{challenge_id}{const.SENSOR_KC_UID_SUFFIX_CHALLENGE_PROGRESS_SENSOR}"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_KID_NAME: kid_name,
            const.TRANS_KEY_SENSOR_ATTR_CHALLENGE_NAME: challenge_name,
        }
        self.entity_id = f"{const.SENSOR_KC_PREFIX}{kid_name}{const.SENSOR_KC_EID_MIDFIX_CHALLENGE_PROGRESS_SENSOR}{challenge_name}"

    @property
    def native_value(self) -> float:
        """Return the challenge progress percentage."""
        challenge = self.coordinator.challenges_data.get(self._challenge_id, {})
        target = challenge.get(const.DATA_CHALLENGE_TARGET_VALUE, 1)
        challenge_type = challenge.get(const.DATA_CHALLENGE_TYPE)
        progress_data = challenge.get(const.DATA_CHALLENGE_PROGRESS, {}).get(
            self._kid_id
        )

        if challenge_type == const.CHALLENGE_TYPE_TOTAL_WITHIN_WINDOW:
            raw_progress = (
                progress_data.get(const.DATA_CHALLENGE_COUNT, const.DEFAULT_ZERO)
                if isinstance(progress_data, dict)
                else const.DEFAULT_ZERO
            )

        elif challenge_type == const.CHALLENGE_TYPE_DAILY_MIN:
            if isinstance(progress_data, dict):
                daily_counts = progress_data.get(const.DATA_CHALLENGE_DAILY_COUNTS, {})
                raw_progress = sum(daily_counts.values())

                start_date = dt_util.parse_datetime(
                    challenge.get(const.DATA_CHALLENGE_START_DATE)
                )
                end_date = dt_util.parse_datetime(
                    challenge.get(const.DATA_CHALLENGE_END_DATE)
                )

                if start_date and end_date:
                    num_days = (end_date.date() - start_date.date()).days + 1

                else:
                    num_days = 1
                required_daily = challenge.get(const.DATA_CHALLENGE_REQUIRED_DAILY, 1)
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
        target = challenge.get(const.DATA_CHALLENGE_TARGET_VALUE, 1)
        challenge_type = challenge.get(const.DATA_CHALLENGE_TYPE)
        progress_data = challenge.get(const.DATA_CHALLENGE_PROGRESS, {}).get(
            self._kid_id, {}
        )
        awarded = (
            progress_data.get(const.DATA_CHALLENGE_AWARDED, False)
            if isinstance(progress_data, dict)
            else False
        )

        if challenge_type == const.CHALLENGE_TYPE_TOTAL_WITHIN_WINDOW:
            raw_progress = (
                progress_data.get(const.DATA_CHALLENGE_COUNT, const.DEFAULT_ZERO)
                if isinstance(progress_data, dict)
                else const.DEFAULT_ZERO
            )
        elif challenge_type == const.CHALLENGE_TYPE_DAILY_MIN:
            if isinstance(progress_data, dict):
                daily_counts = progress_data.get(const.DATA_CHALLENGE_DAILY_COUNTS, {})
                raw_progress = sum(daily_counts.values())
            else:
                raw_progress = const.DEFAULT_ZERO
        else:
            raw_progress = const.DEFAULT_ZERO

        associated_chore = const.CONF_EMPTY
        selected_chore_id = challenge.get(const.DATA_CHALLENGE_SELECTED_CHORE_ID)
        if selected_chore_id:
            associated_chore = self.coordinator.chores_data.get(
                selected_chore_id, {}
            ).get(const.DATA_CHORE_NAME, const.CONF_EMPTY)

        assigned_kids_ids = challenge.get(const.DATA_CHALLENGE_ASSIGNED_KIDS, [])
        assigned_kids_names = [
            kh.get_kid_name_by_id(self.coordinator, k_id)
            or f"{const.TRANS_KEY_LABEL_KID} {k_id}"
            for k_id in assigned_kids_ids
        ]

        stored_labels = challenge.get(const.DATA_CHALLENGE_LABELS, [])
        friendly_labels = [
            kh.get_friendly_label(self.hass, label) for label in stored_labels
        ]

        return {
            const.ATTR_CHALLENGE_NAME: self._challenge_name,
            const.ATTR_DESCRIPTION: challenge.get(
                const.DATA_CHALLENGE_DESCRIPTION, const.CONF_EMPTY
            ),
            const.ATTR_ASSIGNED_KIDS: assigned_kids_names,
            const.ATTR_TYPE: challenge_type,
            const.ATTR_ASSOCIATED_CHORE: associated_chore,
            const.ATTR_CRITERIA: challenge.get(
                const.DATA_CHALLENGE_CRITERIA, const.CONF_EMPTY
            ),
            const.ATTR_TARGET_VALUE: target,
            const.ATTR_REWARD_POINTS: challenge.get(const.DATA_CHALLENGE_REWARD_POINTS),
            const.ATTR_START_DATE: challenge.get(const.DATA_CHALLENGE_START_DATE),
            const.ATTR_END_DATE: challenge.get(const.DATA_CHALLENGE_END_DATE),
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
        return challenge.get(const.DATA_CHALLENGE_ICON, const.DEFAULT_CHALLENGES_ICON)


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
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}{const.SENSOR_KC_UID_SUFFIX_KID_HIGHEST_STREAK_SENSOR}"
        self._attr_native_unit_of_measurement = UnitOfTime.DAYS
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_KID_NAME: kid_name,
        }
        self.entity_id = f"{const.SENSOR_KC_PREFIX}{kid_name}{const.SENSOR_KC_EID_MIDFIX_KID_HIGHEST_STREAK_SENSOR}"

    @property
    def native_value(self) -> int:
        """Return the highest current streak among all streak achievements for the kid."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        chore_stats = kid_info.get(const.DATA_KID_CHORE_STATS, {})
        return chore_stats.get(
            const.DATA_KID_CHORE_STATS_LONGEST_STREAK_ALL_TIME, const.DEFAULT_ZERO
        )

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes including individual streaks per achievement."""
        streaks = {}
        for achievement in self.coordinator.achievements_data.values():
            if (
                achievement.get(const.DATA_ACHIEVEMENT_TYPE)
                == const.ACHIEVEMENT_TYPE_STREAK
            ):
                achievement_name = achievement.get(
                    const.DATA_ACHIEVEMENT_NAME, const.ERROR_UNNAMED_ACHIEVEMENT
                )
                progress_for_kid = achievement.get(
                    const.DATA_ACHIEVEMENT_PROGRESS, {}
                ).get(self._kid_id)

                if isinstance(progress_for_kid, dict):
                    streaks[achievement_name] = progress_for_kid.get(
                        const.DATA_ACHIEVEMENT_CURRENT_STREAK, const.DEFAULT_ZERO
                    )

                elif isinstance(progress_for_kid, int):
                    streaks[achievement_name] = progress_for_kid

        return {const.ATTR_STREAKS_BY_ACHIEVEMENT: streaks}

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
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_{bonus_id}{const.SENSOR_KC_UID_SUFFIX_BONUS_APPLIES_SENSOR}"
        self._attr_translation_placeholders = {
            const.TRANS_KEY_SENSOR_ATTR_KID_NAME: kid_name,
            const.TRANS_KEY_SENSOR_ATTR_BONUS_NAME: bonus_name,
        }
        self.entity_id = f"{const.SENSOR_KC_PREFIX}{kid_name}{const.SENSOR_KC_EID_MIDFIX_BONUS_APPLIES_SENSOR}{bonus_name}"

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

        stored_labels = bonus_info.get(const.DATA_BONUS_LABELS, [])
        friendly_labels = [
            kh.get_friendly_label(self.hass, label) for label in stored_labels
        ]

        return {
            const.ATTR_KID_NAME: self._kid_name,
            const.ATTR_BONUS_NAME: self._bonus_name,
            const.ATTR_DESCRIPTION: bonus_info.get(
                const.DATA_BONUS_DESCRIPTION, const.CONF_EMPTY
            ),
            const.ATTR_BONUS_POINTS: bonus_info.get(
                const.DATA_BONUS_POINTS, const.DEFAULT_BONUS_POINTS
            ),
            const.ATTR_LABELS: friendly_labels,
        }

    @property
    def icon(self):
        """Return the bonus's custom icon if set, else fallback."""
        bonus_info = self.coordinator.bonuses_data.get(self._bonus_id, {})
        return bonus_info.get(const.DATA_BONUS_ICON, const.DEFAULT_BONUS_ICON)
