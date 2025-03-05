# File: sensor.py
"""Sensors for the KidsChores integration.

This file defines all sensor entities for each Kid, Chore, Reward, and Badge.

Available Sensors:
01. KidPointsSensor .................... Kid's current total points
02. KidPointsEarnedDailySensor ......... Points earned by the kid today
03. KidPointsEarnedWeeklySensor ........ Points earned by the kid this week
04. KidPointsEarnedMonthlySensor ....... Points earned by the kid this month
05. KidMaxPointsEverSensor ............. The highest points total the kid has ever reached
06. CompletedChoresDailySensor ......... Chores completed by the kid today
07. CompletedChoresWeeklySensor ........ Chores completed by the kid this week
08. CompletedChoresMonthlySensor ....... Chores completed by the kid this month
09. CompletedChoresTotalSensor ......... Total chores completed by the kid
10.* KidBadgesSensor .................... Number of badges the kid currently has - DEPRECATE
11. KidHighestBadgeSensor .............. The highest (threshold) badge the kid holds
12. BadgeSensor ........................ One sensor per badge, showing its threshold & who earned it
13. ChoreStatusSensor .................. Shows current state (pending/claimed/approved, etc.) for each (kid, chore)
14. SharedChoreGlobalStateSensor ....... Shows current global state for shared chores
15. RewardStatusSensor ................. Shows current state (not claimed/claimed/approved) for each (kid, reward)
16. PenaltyAppliesSensor ............... Tracks how many times each penalty was applied for each kid
17.* RewardClaimsSensor ................. Number of times a reward was claimed by a kid - DEPRECATE
18.* RewardApprovalsSensor .............. Number of times a reward was approved for a kid - DEPRECATE
19.* ChoreClaimsSensor .................. Number of times a chore was claimed by a kid - DEPRECATE
20.* ChoreApprovalsSensor ............... Number of times a chore was approved for a kid - DEPRECATE
21. PendingChoreApprovalsSensor ........ Lists chores that are awaiting approval
22. PendingRewardApprovalsSensor ....... Lists rewards that are awaiting approval
23. AchievementSensor .................. Shows the achievement name, target value, reward points, and number of kids that have earned it
24. ChallengeSensor .................... Shows the challenge name, target, reward, and number of kids that have completed it
25. AchievementProgressSensor .......... Progress (in %) toward an achievement per kid
26. ChallengeProgressSensor ............ Progress (in %) toward a challenge per kid
27. KidHighestStreakSensor ............. The highest current streak (in days) among streak-type achievements for a kid
28.* ChoreStreakSensor .................. Current streak (in days) for a kid for a specific chore - DEPRECATE
"""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.components.sensor import SensorEntity
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    ACHIEVEMENT_TYPE_DAILY_MIN,
    ACHIEVEMENT_TYPE_STREAK,
    ACHIEVEMENT_TYPE_TOTAL,
    ATTR_ACHIEVEMENT_NAME,
    ATTR_ALL_EARNED_BADGES,
    ATTR_ALLOW_MULTIPLE_CLAIMS_PER_DAY,
    ATTR_APPLICABLE_DAYS,
    ATTR_ASSIGNED_KIDS,
    ATTR_ASSOCIATED_CHORE,
    ATTR_AWARDED,
    ATTR_BADGES,
    ATTR_CHALLENGE_NAME,
    ATTR_CHALLENGE_TYPE,
    ATTR_CLAIMED_ON,
    ATTR_CHORE_APPROVALS_COUNT,
    ATTR_CHORE_APPROVALS_TODAY,
    ATTR_CHORE_CLAIMS_COUNT,
    ATTR_CHORE_CURRENT_STREAK,
    ATTR_CHORE_HIGHEST_STREAK,
    ATTR_CHORE_NAME,
    ATTR_COST,
    ATTR_CRITERIA,
    ATTR_CUSTOM_FREQUENCY_INTERVAL,
    ATTR_CUSTOM_FREQUENCY_UNIT,
    ATTR_DEFAULT_POINTS,
    ATTR_DESCRIPTION,
    ATTR_DUE_DATE,
    ATTR_END_DATE,
    ATTR_HIGHEST_BADGE_THRESHOLD_VALUE,
    ATTR_GLOBAL_STATE,
    ATTR_KID_NAME,
    ATTR_KIDS_EARNED,
    ATTR_LABELS,
    ATTR_LAST_DATE,
    ATTR_PARTIAL_ALLOWED,
    ATTR_PENALTY_NAME,
    ATTR_PENALTY_POINTS,
    ATTR_POINTS_MULTIPLIER,
    ATTR_POINTS_TO_NEXT_BADGE,
    ATTR_RECURRING_FREQUENCY,
    ATTR_RAW_PROGRESS,
    ATTR_RAW_STREAK,
    ATTR_REDEEMED_ON,
    ATTR_REWARD_APPROVALS_COUNT,
    ATTR_REWARD_CLAIMS_COUNT,
    ATTR_REWARD_NAME,
    ATTR_REWARD_POINTS,
    ATTR_START_DATE,
    ATTR_SHARED_CHORE,
    ATTR_BONUS_NAME,
    ATTR_BONUS_POINTS,
    ATTR_TARGET_VALUE,
    ATTR_THRESHOLD_TYPE,
    ATTR_TYPE,
    CHALLENGE_TYPE_DAILY_MIN,
    CHALLENGE_TYPE_TOTAL_WITHIN_WINDOW,
    CHORE_STATE_APPROVED,
    CHORE_STATE_CLAIMED,
    CHORE_STATE_OVERDUE,
    CHORE_STATE_PENDING,
    CHORE_STATE_UNKNOWN,
    CONF_POINTS_ICON,
    CONF_POINTS_LABEL,
    DATA_PENDING_CHORE_APPROVALS,
    DATA_PENDING_REWARD_APPROVALS,
    DEFAULT_ACHIEVEMENTS_ICON,
    DEFAULT_BADGE_ICON,
    DEFAULT_CHALLENGES_ICON,
    DEFAULT_CHORE_SENSOR_ICON,
    DEFAULT_PENALTY_ICON,
    DEFAULT_PENALTY_POINTS,
    DEFAULT_POINTS_ICON,
    DEFAULT_POINTS_LABEL,
    DEFAULT_REWARD_COST,
    DEFAULT_REWARD_ICON,
    DEFAULT_BONUS_ICON,
    DEFAULT_BONUS_POINTS,
    DEFAULT_STREAK_ICON,
    DEFAULT_TROPHY_ICON,
    DEFAULT_TROPHY_OUTLINE,
    DOMAIN,
    DUE_DATE_NOT_SET,
    FREQUENCY_CUSTOM,
    LABEL_POINTS,
    REWARD_STATE_APPROVED,
    REWARD_STATE_CLAIMED,
    REWARD_STATE_NOT_CLAIMED,
    UNKNOWN_CHORE,
    UNKNOWN_KID,
    UNKNOWN_REWARD,
)
from .coordinator import KidsChoresDataCoordinator
from .kc_helpers import get_friendly_label


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    """Set up sensors for KidsChores integration."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: KidsChoresDataCoordinator = data["coordinator"]

    points_label = entry.options.get(CONF_POINTS_LABEL, DEFAULT_POINTS_LABEL)
    points_icon = entry.options.get(CONF_POINTS_ICON, DEFAULT_POINTS_ICON)
    entities = []

    # Sensor to detail number of Chores pending approval
    entities.append(PendingChoreApprovalsSensor(coordinator, entry))

    # Sensor to detail number of Rewards pending approval
    entities.append(PendingRewardApprovalsSensor(coordinator, entry))

    # For each kid, add standard sensors
    for kid_id, kid_info in coordinator.kids_data.items():
        kid_name = kid_info.get("name", f"Kid {kid_id}")

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

        # Badges Obtained by each Kid
        entities.append(KidBadgesSensor(coordinator, entry, kid_id, kid_name))

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

        # Reward Claims and Approvals
        for reward_id, reward_info in coordinator.rewards_data.items():
            reward_name = reward_info.get("name", f"Reward {reward_id}")
            entities.append(
                RewardClaimsSensor(
                    coordinator, entry, kid_id, kid_name, reward_id, reward_name
                )
            )

            # Rewards Approval Sensor
            entities.append(
                RewardApprovalsSensor(
                    coordinator, entry, kid_id, kid_name, reward_id, reward_name
                )
            )

        # Chore Claims and Approvals
        for chore_id, chore_info in coordinator.chores_data.items():
            if kid_id not in chore_info.get("assigned_kids", []):
                continue
            chore_name = chore_info.get("name", f"Chore {chore_id}")
            entities.append(
                ChoreClaimsSensor(
                    coordinator, entry, kid_id, kid_name, chore_id, chore_name
                )
            )

            # Chore Approvals Sensor
            entities.append(
                ChoreApprovalsSensor(
                    coordinator, entry, kid_id, kid_name, chore_id, chore_name
                )
            )

            # Chore Streak per Kid
            entities.append(
                ChoreStreakSensor(
                    coordinator, entry, kid_id, kid_name, chore_id, chore_name
                )
            )

        # Penalty Applies
        for penalty_id, penalty_info in coordinator.penalties_data.items():
            penalty_name = penalty_info.get("name", f"Penalty {penalty_id}")
            entities.append(
                PenaltyAppliesSensor(
                    coordinator, entry, kid_id, kid_name, penalty_id, penalty_name
                )
            )

        # Bonus Applies
        for bonus_id, bonus_info in coordinator.bonuses_data.items():
            bonus_name = bonus_info.get("name", f"Bonus {bonus_id}")
            entities.append(
                BonusAppliesSensor(
                    coordinator, entry, kid_id, kid_name, bonus_id, bonus_name
                )
            )

        # Achivement Progress per Kid
        for achievement_id, achievement in coordinator.achievements_data.items():
            if kid_id in achievement.get("assigned_kids", []):
                achievement_name = achievement.get(
                    "name", f"Achievement {achievement_id}"
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
            if kid_id in challenge.get("assigned_kids", []):
                challenge_name = challenge.get("name", f"Challenge {challenge_id}")
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
        chore_name = chore_info.get("name", f"Chore {chore_id}")
        assigned_kids_ids = chore_info.get("assigned_kids", [])
        for kid_id in assigned_kids_ids:
            kid_name = coordinator._get_kid_name_by_id(kid_id) or f"Kid {kid_id}"
            entities.append(
                ChoreStatusSensor(
                    coordinator, entry, kid_id, kid_name, chore_id, chore_name
                )
            )

    # For each shared chore, add a global state sensor
    for chore_id, chore_info in coordinator.chores_data.items():
        if chore_info.get("shared_chore", False):
            chore_name = chore_info.get("name", f"Chore {chore_id}")
            entities.append(
                SharedChoreGlobalStateSensor(coordinator, entry, chore_id, chore_name)
            )

    # For each Reward, add a RewardStatusSensor
    for reward_id, reward_info in coordinator.rewards_data.items():
        reward_name = reward_info.get("name", f"Reward {reward_id}")

        # For each kid, create the reward status sensor
        for kid_id, kid_info in coordinator.kids_data.items():
            kid_name = kid_info.get("name", f"Kid {kid_id}")
            entities.append(
                RewardStatusSensor(
                    coordinator, entry, kid_id, kid_name, reward_id, reward_name
                )
            )

    # For each Badge, add a BadgeSensor
    for badge_id, badge_info in coordinator.badges_data.items():
        badge_name = badge_info.get("name", f"Badge {badge_id}")
        entities.append(BadgeSensor(coordinator, entry, badge_id, badge_name))

    # For each Achievement, add an AchievementSensor
    for achievement_id, achievement in coordinator.achievements_data.items():
        achievement_name = achievement.get("name", f"Achievement {achievement_id}")
        entities.append(
            AchievementSensor(coordinator, entry, achievement_id, achievement_name)
        )

    # For each Challenge, add a ChallengeSensor
    for challenge_id, challenge in coordinator.challenges_data.items():
        challenge_name = challenge.get("name", f"Challenge {challenge_id}")
        entities.append(
            ChallengeSensor(coordinator, entry, challenge_id, challenge_name)
        )

    async_add_entities(entities)


# ------------------------------------------------------------------------------------------
class ChoreStatusSensor(CoordinatorEntity, SensorEntity):
    """Sensor for chore status: pending/claimed/approved/etc."""

    _attr_has_entity_name = True
    _attr_translation_key = "chore_status_sensor"

    def __init__(self, coordinator, entry, kid_id, kid_name, chore_id, chore_name):
        """Initialize the sensor."""

        super().__init__(coordinator)
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._chore_id = chore_id
        self._chore_name = chore_name
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_{chore_id}_status"
        self.entity_id = f"sensor.kc_{kid_name}_chore_status_{chore_name}"
        self._attr_translation_placeholders = {
            "kid_name": kid_name,
            "chore_name": chore_name,
        }

    @property
    def native_value(self):
        """Return the chore's state based on shared or individual tracking."""
        chore_info = self.coordinator.chores_data.get(self._chore_id, {})

        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        # The status of the kids chore should always be their own status, it's only global status that would show independent or in-part
        if self._chore_id in kid_info.get("approved_chores", []):
            return CHORE_STATE_APPROVED
        elif self._chore_id in kid_info.get("claimed_chores", []):
            return CHORE_STATE_CLAIMED
        elif self._chore_id in kid_info.get("overdue_chores", []):
            return CHORE_STATE_OVERDUE
        else:
            return CHORE_STATE_PENDING

    @property
    def extra_state_attributes(self):
        """Include points, description, etc."""
        chore_info = self.coordinator.chores_data.get(self._chore_id, {})
        shared = chore_info.get("shared_chore", False)
        global_state = chore_info.get("state", CHORE_STATE_UNKNOWN)

        assigned_kids_ids = chore_info.get("assigned_kids", [])
        assigned_kids_names = [
            self.coordinator._get_kid_name_by_id(k_id) or f"Kid {k_id}"
            for k_id in assigned_kids_ids
        ]

        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        chore_streak_data = kid_info.get("chore_streaks", {}).get(self._chore_id, {})
        current_streak = chore_streak_data.get("current_streak", 0)
        highest_streak = chore_streak_data.get("max_streak", 0)

        stored_labels = chore_info.get("chore_labels", [])
        friendly_labels = [
            get_friendly_label(self.hass, label) for label in stored_labels
        ]

        attributes = {
            ATTR_KID_NAME: self._kid_name,
            ATTR_CHORE_NAME: self._chore_name,
            ATTR_DESCRIPTION: chore_info.get("description", ""),
            ATTR_CHORE_CLAIMS_COUNT: kid_info.get("chore_claims", {}).get(
                self._chore_id, 0
            ),
            ATTR_CHORE_APPROVALS_COUNT: kid_info.get("chore_approvals", {}).get(
                self._chore_id, 0
            ),
            ATTR_CHORE_CURRENT_STREAK: current_streak,
            ATTR_CHORE_HIGHEST_STREAK: highest_streak,
            ATTR_SHARED_CHORE: shared,
            ATTR_GLOBAL_STATE: global_state,
            ATTR_RECURRING_FREQUENCY: chore_info.get("recurring_frequency", "None"),
            ATTR_APPLICABLE_DAYS: chore_info.get("applicable_days", []),
            ATTR_DUE_DATE: chore_info.get("due_date", DUE_DATE_NOT_SET),
            ATTR_DEFAULT_POINTS: chore_info.get("default_points", 0),
            ATTR_PARTIAL_ALLOWED: chore_info.get("partial_allowed", False),
            ATTR_ALLOW_MULTIPLE_CLAIMS_PER_DAY: chore_info.get(
                "allow_multiple_claims_per_day", False
            ),
            ATTR_ASSIGNED_KIDS: assigned_kids_names,
            ATTR_LABELS: friendly_labels,
        }

        if chore_info.get("allow_multiple_claims_per_day", False):
            today_approvals = kid_info.get("today_chore_approvals", {}).get(
                self._chore_id, 0
            )
            attributes[ATTR_CHORE_APPROVALS_TODAY] = today_approvals

        if chore_info.get("recurring_frequency") == FREQUENCY_CUSTOM:
            attributes[ATTR_CUSTOM_FREQUENCY_INTERVAL] = chore_info.get(
                "custom_interval"
            )
            attributes[ATTR_CUSTOM_FREQUENCY_UNIT] = chore_info.get(
                "custom_interval_unit"
            )

        return attributes

    @property
    def icon(self):
        """Use the chore's custom icon if set, else fallback."""
        chore_info = self.coordinator.chores_data.get(self._chore_id, {})
        return chore_info.get("icon", DEFAULT_CHORE_SENSOR_ICON)


# ------------------------------------------------------------------------------------------
class KidPointsSensor(CoordinatorEntity, SensorEntity):
    """Sensor for a kid's total points balance."""

    _attr_has_entity_name = True
    _attr_translation_key = "kid_points_sensor"

    def __init__(self, coordinator, entry, kid_id, kid_name, points_label, points_icon):
        """Initialize the sensor."""

        super().__init__(coordinator)
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._points_label = points_label
        self._points_icon = points_icon
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_points"
        self._attr_state_class = "measurement"
        self._attr_translation_placeholders = {
            "kid_name": kid_name,
            "points": self._points_label,
        }
        self.entity_id = f"sensor.kc_{kid_name}_points"

    @property
    def native_value(self):
        """Return the kid's total points."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        return kid_info.get("points", 0)

    @property
    def native_unit_of_measurement(self):
        """Return the points label."""
        return self._points_label or LABEL_POINTS

    @property
    def icon(self):
        """Use the points' custom icon if set, else fallback."""
        return self._points_icon or DEFAULT_POINTS_ICON


# ------------------------------------------------------------------------------------------
class KidMaxPointsEverSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing the maximum points a kid has ever reached."""

    _attr_has_entity_name = True
    _attr_translation_key = "kid_max_points_ever_sensor"

    def __init__(self, coordinator, entry, kid_id, kid_name, points_label, points_icon):
        """Initialize the sensor."""

        super().__init__(coordinator)
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._points_label = points_label
        self._points_icon = points_icon
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_max_points_ever"
        self._entry = entry
        self._attr_translation_placeholders = {"kid_name": kid_name}
        self.entity_id = f"sensor.kc_{kid_name}_points_max_ever"

    @property
    def native_value(self):
        """Return the highest points total the kid has ever reached."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        return kid_info.get("max_points_ever", 0)

    @property
    def icon(self):
        """Use the same icon as points or any custom icon you prefer."""
        return self._points_icon or DEFAULT_POINTS_ICON

    @property
    def native_unit_of_measurement(self):
        """Optionally display the same points label for consistency."""
        return self._points_label or LABEL_POINTS


# ------------------------------------------------------------------------------------------
class CompletedChoresTotalSensor(CoordinatorEntity, SensorEntity):
    """Sensor tracking the total number of chores a kid has completed since integration start."""

    _attr_has_entity_name = True
    _attr_translation_key = "chores_completed_total_sensor"

    def __init__(self, coordinator, entry, kid_id, kid_name):
        """Initialize the sensor."""

        super().__init__(coordinator)
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_completed_total"
        self._attr_native_unit_of_measurement = "chores"
        self._attr_icon = "mdi:clipboard-check-outline"
        self._attr_translation_placeholders = {"kid_name": kid_name}
        self.entity_id = f"sensor.kc_{kid_name}_chores_completed_total"

    @property
    def native_value(self):
        """Return the total number of chores completed by the kid."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        return kid_info.get("completed_chores_total", 0)


# ------------------------------------------------------------------------------------------
class CompletedChoresDailySensor(CoordinatorEntity, SensorEntity):
    """How many chores kid completed today."""

    _attr_has_entity_name = True
    _attr_translation_key = "chores_completed_daily_sensor"

    def __init__(self, coordinator, entry, kid_id, kid_name):
        """Initialize the sensor."""

        super().__init__(coordinator)
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_completed_daily"
        self._attr_native_unit_of_measurement = "chores"
        self._attr_translation_placeholders = {"kid_name": kid_name}
        self.entity_id = f"sensor.kc_{kid_name}_chores_completed_daily"

    @property
    def native_value(self):
        """Return the number of chores completed today."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        return kid_info.get("completed_chores_today", 0)


# ------------------------------------------------------------------------------------------
class CompletedChoresWeeklySensor(CoordinatorEntity, SensorEntity):
    """How many chores kid completed this week."""

    _attr_has_entity_name = True
    _attr_translation_key = "chores_completed_weekly_sensor"

    def __init__(self, coordinator, entry, kid_id, kid_name):
        """Initialize the sensor."""

        super().__init__(coordinator)
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_completed_weekly"
        self._attr_native_unit_of_measurement = "chores"
        self._attr_translation_placeholders = {"kid_name": kid_name}
        self.entity_id = f"sensor.kc_{kid_name}_chores_completed_weekly"

    @property
    def native_value(self):
        """Return the number of chores completed this week."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        return kid_info.get("completed_chores_weekly", 0)


# ------------------------------------------------------------------------------------------
class CompletedChoresMonthlySensor(CoordinatorEntity, SensorEntity):
    """How many chores kid completed this month."""

    _attr_has_entity_name = True
    _attr_translation_key = "chores_completed_monthly_sensor"

    def __init__(self, coordinator, entry, kid_id, kid_name):
        """Initialize the sensor."""

        super().__init__(coordinator)
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_completed_monthly"
        self._attr_native_unit_of_measurement = "chores"
        self._attr_translation_placeholders = {"kid_name": kid_name}
        self.entity_id = f"sensor.kc_{kid_name}_chores_completed_monthly"

    @property
    def native_value(self):
        """Return the number of chores completed this month."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        return kid_info.get("completed_chores_monthly", 0)


# DEPRECATE --------------------------------------------------------------------------------
class KidBadgesSensor(CoordinatorEntity, SensorEntity):
    """Sensor: number of badges earned + attribute with the list."""

    _attr_has_entity_name = True
    _attr_translation_key = "kid_badges_sensor"

    def __init__(self, coordinator, entry, kid_id, kid_name):
        """Initialize the sensor."""

        super().__init__(coordinator)
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_badges"
        self._attr_translation_placeholders = {"kid_name": kid_name}
        self.entity_id = f"sensor.kc_{kid_name}_badges"

    @property
    def native_value(self):
        """Return the number of badges the kid has earned."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        return len(kid_info.get("badges", []))

    @property
    def extra_state_attributes(self):
        """Include the list of badges the kid has earned."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        return {ATTR_BADGES: kid_info.get("badges", [])}


# ------------------------------------------------------------------------------------------
class KidHighestBadgeSensor(CoordinatorEntity, SensorEntity):
    """Sensor that returns the "highest" badge the kid currently has."""

    _attr_has_entity_name = True
    _attr_translation_key = "kids_highest_badge_sensor"

    def __init__(self, coordinator, entry, kid_id, kid_name):
        """Initialize the sensor."""

        super().__init__(coordinator)
        self._entry = entry
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_highest_badge"
        self._attr_translation_placeholders = {"kid_name": kid_name}
        self.entity_id = f"sensor.kc_{kid_name}_highest_badge"

    def _find_highest_badge(self):
        """Determine which badge has the highest ranking."""

        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        earned_badge_names = kid_info.get("badges", [])

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

            threshold_val = badge_data.get("threshold_value", 0)
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
            return badge_data.get("icon", DEFAULT_TROPHY_ICON)
        return DEFAULT_TROPHY_OUTLINE

    @property
    def extra_state_attributes(self):
        """Provide additional details."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        highest_badge, highest_val = self._find_highest_badge()

        current_multiplier = 1.0
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
            current_multiplier = badge_data.get("points_multiplier", 1.0)
            stored_labels = badge_data.get("badge_labels", [])
            friendly_labels = [
                get_friendly_label(self.hass, label) for label in stored_labels
            ]

        # Compute points needed for next badge:
        current_points = kid_info.get("points", 0)
        # Gather thresholds for badges that are higher than current points
        thresholds = [
            badge.get("threshold_value", 0)
            for badge in self.coordinator.badges_data.values()
            if badge.get("threshold_value", 0) > current_points
        ]
        if thresholds:
            next_threshold = min(thresholds)
            points_to_next_badge = next_threshold - current_points
        else:
            points_to_next_badge = 0

        return {
            ATTR_KID_NAME: self._kid_name,
            ATTR_ALL_EARNED_BADGES: kid_info.get("badges", []),
            ATTR_HIGHEST_BADGE_THRESHOLD_VALUE: highest_val if highest_badge else 0,
            ATTR_POINTS_MULTIPLIER: current_multiplier,
            ATTR_POINTS_TO_NEXT_BADGE: points_to_next_badge,
            ATTR_LABELS: friendly_labels,
        }


# ------------------------------------------------------------------------------------------
class BadgeSensor(CoordinatorEntity, SensorEntity):
    """Sensor representing a single badge in KidsChores."""

    _attr_has_entity_name = True
    _attr_translation_key = "badge_sensor"

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
        self._attr_translation_placeholders = {"badge_name": badge_name}
        self.entity_id = f"sensor.kc_{badge_name}_badge"

    @property
    def native_value(self) -> float:
        """The sensor state is the threshold_value for the badge."""
        badge_info = self.coordinator.badges_data.get(self._badge_id, {})
        return badge_info.get("threshold_value", 0)

    @property
    def extra_state_attributes(self):
        """Provide additional badge data, including which kids currently have it."""
        badge_info = self.coordinator.badges_data.get(self._badge_id, {})
        threshold_type = badge_info.get("threshold_type", "points")
        points_multiplier = badge_info.get("points_multiplier", 1.0)
        description = badge_info.get("description", "")

        kids_earned_ids = badge_info.get("earned_by", [])

        stored_labels = badge_info.get("badge_labels", [])
        friendly_labels = [
            get_friendly_label(self.hass, label) for label in stored_labels
        ]

        # Convert each kid_id to kid_name
        kids_earned_names = []
        for kid_id in kids_earned_ids:
            kid = self.coordinator.kids_data.get(kid_id)
            if kid is not None:
                kids_earned_names.append(kid.get("name", f"Kid {kid_id}"))
            else:
                kids_earned_names.append(f"Kid {kid_id} (not found)")

        return {
            ATTR_DESCRIPTION: description,
            ATTR_THRESHOLD_TYPE: threshold_type,
            ATTR_POINTS_MULTIPLIER: points_multiplier,
            ATTR_KIDS_EARNED: kids_earned_names,
            ATTR_LABELS: friendly_labels,
        }

    @property
    def icon(self) -> str:
        """Return the badge's custom icon if set, else default."""
        badge_info = self.coordinator.badges_data.get(self._badge_id, {})
        return badge_info.get("icon", DEFAULT_BADGE_ICON)


# ------------------------------------------------------------------------------------------
class PendingChoreApprovalsSensor(CoordinatorEntity, SensorEntity):
    """Sensor listing all pending chore approvals."""

    _attr_has_entity_name = True
    _attr_translation_key = "pending_chores_approvals_sensor"

    def __init__(self, coordinator, entry):
        """Initialize the sensor."""

        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_pending_chore_approvals"
        self._attr_icon = "mdi:clipboard-check-outline"
        self.entity_id = f"sensor.kc_global_chore_pending_approvals"

    @property
    def native_value(self):
        """Return a summary of pending chore approvals."""
        approvals = self.coordinator._data.get(DATA_PENDING_CHORE_APPROVALS, [])
        return f"{len(approvals)} pending chores"

    @property
    def extra_state_attributes(self):
        """Return detailed pending chores."""
        approvals = self.coordinator._data.get(DATA_PENDING_CHORE_APPROVALS, [])
        grouped_by_kid = {}

        for approval in approvals:
            kid_name = (
                self.coordinator._get_kid_name_by_id(approval["kid_id"]) or UNKNOWN_KID
            )
            chore_info = self.coordinator.chores_data.get(approval["chore_id"], {})
            chore_name = chore_info.get("name", UNKNOWN_CHORE)

            timestamp = approval["timestamp"]

            if kid_name not in grouped_by_kid:
                grouped_by_kid[kid_name] = []

            grouped_by_kid[kid_name].append(
                {
                    ATTR_CHORE_NAME: chore_name,
                    ATTR_CLAIMED_ON: timestamp,
                }
            )

        return grouped_by_kid


# ------------------------------------------------------------------------------------------
class PendingRewardApprovalsSensor(CoordinatorEntity, SensorEntity):
    """Sensor listing all pending reward approvals."""

    _attr_has_entity_name = True
    _attr_translation_key = "pending_rewards_approvals_sensor"

    def __init__(self, coordinator, entry):
        """Initialize the sensor."""

        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_pending_reward_approvals"
        self._attr_icon = "mdi:gift-open-outline"
        self.entity_id = f"sensor.kc_global_reward_pending_approvals"

    @property
    def native_value(self):
        """Return a summary of pending reward approvals."""
        approvals = self.coordinator._data.get(DATA_PENDING_REWARD_APPROVALS, [])
        return f"{len(approvals)} pending rewards"

    @property
    def extra_state_attributes(self):
        """Return detailed pending rewards."""
        approvals = self.coordinator._data.get(DATA_PENDING_REWARD_APPROVALS, [])
        grouped_by_kid = {}

        for approval in approvals:
            kid_name = (
                self.coordinator._get_kid_name_by_id(approval["kid_id"]) or UNKNOWN_KID
            )
            reward_info = self.coordinator.rewards_data.get(approval["reward_id"], {})
            reward_name = reward_info.get("name", UNKNOWN_REWARD)

            timestamp = approval["timestamp"]

            if kid_name not in grouped_by_kid:
                grouped_by_kid[kid_name] = []

            grouped_by_kid[kid_name].append(
                {
                    ATTR_REWARD_NAME: reward_name,
                    ATTR_REDEEMED_ON: timestamp,
                }
            )

        return grouped_by_kid


# DEPRECATE --------------------------------------------------------------------------------
class RewardClaimsSensor(CoordinatorEntity, SensorEntity):
    """Sensor tracking how many times each reward has been claimed by a kid."""

    _attr_has_entity_name = True
    _attr_translation_key = "reward_claims_sensor"

    def __init__(self, coordinator, entry, kid_id, kid_name, reward_id, reward_name):
        """Initialize the sensor."""

        super().__init__(coordinator)
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._reward_id = reward_id
        self._reward_name = reward_name
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_{reward_id}_reward_claims"
        self._attr_translation_placeholders = {
            "kid_name": kid_name,
            "reward_name": reward_name,
        }
        self.entity_id = f"sensor.kc_{kid_name}_reward_claims_{reward_name}"

    @property
    def native_value(self):
        """Return the number of times the reward has been claimed."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        return kid_info.get("reward_claims", {}).get(self._reward_id, 0)

    @property
    def icon(self):
        """Return the chore's custom icon if set, else fallback."""
        reward_info = self.coordinator.rewards_data.get(self._reward_id, {})
        return reward_info.get("icon", DEFAULT_REWARD_ICON)


# DEPRECATE --------------------------------------------------------------------------------
class RewardApprovalsSensor(CoordinatorEntity, SensorEntity):
    """Sensor tracking how many times each reward has been approved for a kid."""

    _attr_has_entity_name = True
    _attr_translation_key = "reward_approvals_sensor"

    def __init__(self, coordinator, entry, kid_id, kid_name, reward_id, reward_name):
        """Initialize the sensor."""

        super().__init__(coordinator)
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._reward_id = reward_id
        self._reward_name = reward_name
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_{reward_id}_reward_approvals"
        self._attr_translation_placeholders = {
            "kid_name": kid_name,
            "reward_name": reward_name,
        }
        self.entity_id = f"sensor.kc_{kid_name}_reward_approvals_{reward_name}"

    @property
    def native_value(self):
        """Return the number of times the reward has been approved."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        return kid_info.get("reward_approvals", {}).get(self._reward_id, 0)

    @property
    def icon(self):
        """Return the chore's custom icon if set, else fallback."""
        reward_info = self.coordinator.rewards_data.get(self._reward_id, {})
        return reward_info.get("icon", DEFAULT_REWARD_ICON)


# ------------------------------------------------------------------------------------------
class SharedChoreGlobalStateSensor(CoordinatorEntity, SensorEntity):
    """Sensor that shows the global state of a shared chore."""

    _attr_has_entity_name = True
    _attr_translation_key = "shared_chore_global_status_sensor"

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
            "chore_name": chore_name,
        }
        self.entity_id = f"sensor.kc_global_chore_status_{chore_name}"

    @property
    def native_value(self) -> str:
        """Return the global state for the chore."""
        chore_info = self.coordinator.chores_data.get(self._chore_id, {})
        return chore_info.get("state", CHORE_STATE_UNKNOWN)

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional attributes for the chore."""
        chore_info = self.coordinator.chores_data.get(self._chore_id, {})
        assigned_kids_ids = chore_info.get("assigned_kids", [])
        assigned_kids_names = [
            self.coordinator._get_kid_name_by_id(k_id) or f"Kid {k_id}"
            for k_id in assigned_kids_ids
        ]

        stored_labels = chore_info.get("chore_labels", [])
        friendly_labels = [
            get_friendly_label(self.hass, label) for label in stored_labels
        ]

        total_approvals_today = 0
        for kid_id in assigned_kids_ids:
            kid_data = self.coordinator.kids_data.get(kid_id, {})
            total_approvals_today += kid_data.get("today_chore_approvals", {}).get(
                self._chore_id, 0
            )

        attributes = {
            ATTR_CHORE_NAME: self._chore_name,
            ATTR_DESCRIPTION: chore_info.get("description", ""),
            ATTR_RECURRING_FREQUENCY: chore_info.get("recurring_frequency", "None"),
            ATTR_APPLICABLE_DAYS: chore_info.get("applicable_days", []),
            ATTR_DUE_DATE: chore_info.get("due_date", "Not set"),
            ATTR_DEFAULT_POINTS: chore_info.get("default_points", 0),
            ATTR_PARTIAL_ALLOWED: chore_info.get("partial_allowed", False),
            ATTR_ALLOW_MULTIPLE_CLAIMS_PER_DAY: chore_info.get(
                "allow_multiple_claims_per_day", False
            ),
            ATTR_CHORE_APPROVALS_TODAY: total_approvals_today,
            ATTR_ASSIGNED_KIDS: assigned_kids_names,
            ATTR_LABELS: friendly_labels,
        }

        if chore_info.get("recurring_frequency") == FREQUENCY_CUSTOM:
            attributes[ATTR_CUSTOM_FREQUENCY_INTERVAL] = chore_info.get(
                "custom_interval"
            )
            attributes[ATTR_CUSTOM_FREQUENCY_UNIT] = chore_info.get(
                "custom_interval_unit"
            )

        return attributes

    @property
    def icon(self) -> str:
        """Return the icon for the chore sensor."""
        chore_info = self.coordinator.chores_data.get(self._chore_id, {})
        return chore_info.get("icon", DEFAULT_CHORE_SENSOR_ICON)


# ------------------------------------------------------------------------------------------
class RewardStatusSensor(CoordinatorEntity, SensorEntity):
    """Shows the status of a reward for a particular kid."""

    _attr_has_entity_name = True
    _attr_translation_key = "reward_status_sensor"

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
            "kid_name": kid_name,
            "reward_name": reward_name,
        }
        self.entity_id = f"sensor.kc_{kid_name}_reward_status_{reward_name}"

    @property
    def native_value(self) -> str:
        """Return the current reward status: 'Not Claimed', 'Claimed', or 'Approved'."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        if self._reward_id in kid_info.get("pending_rewards", []):
            return REWARD_STATE_CLAIMED
        if self._reward_id in kid_info.get("redeemed_rewards", []):
            return REWARD_STATE_APPROVED
        return REWARD_STATE_NOT_CLAIMED

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
            ATTR_KID_NAME: self._kid_name,
            ATTR_REWARD_NAME: self._reward_name,
            ATTR_DESCRIPTION: reward_info.get("description", ""),
            ATTR_COST: reward_info.get("cost", DEFAULT_REWARD_COST),
            ATTR_REWARD_CLAIMS_COUNT: kid_info.get("reward_claims", {}).get(
                self._reward_id, 0
            ),
            ATTR_REWARD_APPROVALS_COUNT: kid_info.get("reward_approvals", {}).get(
                self._reward_id, 0
            ),
            ATTR_LABELS: friendly_labels,
        }

        return attributes

    @property
    def icon(self) -> str:
        """Use the reward's custom icon if set, else fallback."""
        reward_info = self.coordinator.rewards_data.get(self._reward_id, {})
        return reward_info.get("icon", DEFAULT_REWARD_ICON)


# DEPRECATE --------------------------------------------------------------------------------
class ChoreClaimsSensor(CoordinatorEntity, SensorEntity):
    """Sensor tracking how many times each chore has been claimed by a kid."""

    _attr_has_entity_name = True
    _attr_translation_key = "chore_claims_sensor"

    def __init__(self, coordinator, entry, kid_id, kid_name, chore_id, chore_name):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._chore_id = chore_id
        self._chore_name = chore_name
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_{chore_id}_chore_claims"
        self._attr_translation_placeholders = {
            "kid_name": kid_name,
            "chore_name": chore_name,
        }
        self.entity_id = f"sensor.kc_{kid_name}_chore_claims_{chore_name}"

    @property
    def native_value(self):
        """Return the number of times the chore has been claimed."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        return kid_info.get("chore_claims", {}).get(self._chore_id, 0)

    @property
    def icon(self):
        """Return the chore's custom icon if set, else fallback."""
        chore_info = self.coordinator.chores_data.get(self._chore_id, {})
        return chore_info.get("icon", DEFAULT_CHORE_SENSOR_ICON)


# DEPRECATE --------------------------------------------------------------------------------
class ChoreApprovalsSensor(CoordinatorEntity, SensorEntity):
    """Sensor tracking how many times each chore has been approved for a kid."""

    _attr_has_entity_name = True
    _attr_translation_key = "chore_approvals_sensor"

    def __init__(self, coordinator, entry, kid_id, kid_name, chore_id, chore_name):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._chore_id = chore_id
        self._chore_name = chore_name
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_{chore_id}_chore_approvals"
        self._attr_translation_placeholders = {
            "kid_name": kid_name,
            "chore_name": chore_name,
        }
        self.entity_id = f"sensor.kc_{kid_name}_chore_approvals_{chore_name}"

    @property
    def native_value(self):
        """Return the number of times the chore has been approved."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        return kid_info.get("chore_approvals", {}).get(self._chore_id, 0)

    @property
    def icon(self):
        """Return the chore's custom icon if set, else fallback."""
        chore_info = self.coordinator.chores_data.get(self._chore_id, {})
        return chore_info.get("icon", DEFAULT_CHORE_SENSOR_ICON)


# ------------------------------------------------------------------------------------------
class PenaltyAppliesSensor(CoordinatorEntity, SensorEntity):
    """Sensor tracking how many times each penalty has been applied to a kid."""

    _attr_has_entity_name = True
    _attr_translation_key = "penalty_applies_sensor"

    def __init__(self, coordinator, entry, kid_id, kid_name, penalty_id, penalty_name):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._penalty_id = penalty_id
        self._penalty_name = penalty_name
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_{penalty_id}_penalty_applies"
        self._attr_translation_placeholders = {
            "kid_name": kid_name,
            "penalty_name": penalty_name,
        }
        self.entity_id = f"sensor.kc_{kid_name}_penalties_applied_{penalty_name}"

    @property
    def native_value(self):
        """Return the number of times the penalty has been applied."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        return kid_info.get("penalty_applies", {}).get(self._penalty_id, 0)

    @property
    def extra_state_attributes(self):
        """Expose additional details like penalty points and description."""
        penalty_info = self.coordinator.penalties_data.get(self._penalty_id, {})

        stored_labels = penalty_info.get("penalty_labels", [])
        friendly_labels = [
            get_friendly_label(self.hass, label) for label in stored_labels
        ]

        return {
            ATTR_KID_NAME: self._kid_name,
            ATTR_PENALTY_NAME: self._penalty_name,
            ATTR_DESCRIPTION: penalty_info.get("description", ""),
            ATTR_PENALTY_POINTS: penalty_info.get("points", DEFAULT_PENALTY_POINTS),
            ATTR_LABELS: friendly_labels,
        }

    @property
    def icon(self):
        """Return the chore's custom icon if set, else fallback."""
        penalty_info = self.coordinator.penalties_data.get(self._penalty_id, {})
        return penalty_info.get("icon", DEFAULT_PENALTY_ICON)


# ------------------------------------------------------------------------------------------
class KidPointsEarnedDailySensor(CoordinatorEntity, SensorEntity):
    """Sensor for how many net points a kid earned today."""

    _attr_has_entity_name = True
    _attr_translation_key = "kid_points_earned_daily_sensor"

    def __init__(self, coordinator, entry, kid_id, kid_name, points_label, points_icon):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._points_label = points_label
        self._points_icon = points_icon
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_points_earned_daily"
        self._attr_translation_placeholders = {
            "kid_name": kid_name,
        }
        self.entity_id = f"sensor.kc_{kid_name}_points_earned_daily"

    @property
    def native_value(self):
        """Return how many net points the kid has earned so far today."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        return kid_info.get("points_earned_today", 0)

    @property
    def native_unit_of_measurement(self):
        """Return the points label."""
        return self._points_label or LABEL_POINTS

    @property
    def icon(self):
        """Use the points' custom icon if set, else fallback."""
        return self._points_icon or DEFAULT_POINTS_ICON


# ------------------------------------------------------------------------------------------
class KidPointsEarnedWeeklySensor(CoordinatorEntity, SensorEntity):
    """Sensor for how many net points a kid earned this week."""

    _attr_has_entity_name = True
    _attr_translation_key = "kid_points_earned_weekly_sensor"

    def __init__(self, coordinator, entry, kid_id, kid_name, points_label, points_icon):
        """Initialize the sensor."""

        super().__init__(coordinator)
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._points_label = points_label
        self._points_icon = points_icon
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_points_earned_weekly"
        self._attr_translation_placeholders = {
            "kid_name": kid_name,
        }
        self.entity_id = f"sensor.kc_{kid_name}_points_earned_weekly"

    @property
    def native_value(self):
        """Return how many net points the kid has earned this week."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        return kid_info.get("points_earned_weekly", 0)

    @property
    def native_unit_of_measurement(self):
        """Return the points label."""
        return self._points_label or LABEL_POINTS

    @property
    def icon(self):
        """Use the points' custom icon if set, else fallback."""
        return self._points_icon or DEFAULT_POINTS_ICON


# ------------------------------------------------------------------------------------------
class KidPointsEarnedMonthlySensor(CoordinatorEntity, SensorEntity):
    """Sensor for how many net points a kid earned this month."""

    _attr_has_entity_name = True
    _attr_translation_key = "kid_points_earned_monthly_sensor"

    def __init__(self, coordinator, entry, kid_id, kid_name, points_label, points_icon):
        """Initialize the sensor."""

        super().__init__(coordinator)
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._points_label = points_label
        self._points_icon = points_icon
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_points_earned_monthly"
        self._attr_translation_placeholders = {
            "kid_name": kid_name,
        }
        self.entity_id = f"sensor.kc_{kid_name}_points_earned_monthly"

    @property
    def native_value(self):
        """Return how many net points the kid has earned this month."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        return kid_info.get("points_earned_monthly", 0)

    @property
    def native_unit_of_measurement(self):
        """Return the points label."""
        return self._points_label or LABEL_POINTS

    @property
    def icon(self):
        """Use the points' custom icon if set, else fallback."""
        return self._points_icon or DEFAULT_POINTS_ICON


# ------------------------------------------------------------------------------------------
class AchievementSensor(CoordinatorEntity, SensorEntity):
    """Sensor representing an achievement."""

    _attr_has_entity_name = True
    _attr_translation_key = "achievement_state_sensor"

    def __init__(self, coordinator, entry, achievement_id, achievement_name):
        """Initialize the AchievementSensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._achievement_id = achievement_id
        self._achievement_name = achievement_name
        self._attr_unique_id = f"{entry.entry_id}_{achievement_id}_achievement"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_translation_placeholders = {
            "achievement_name": achievement_name,
        }
        self.entity_id = f"sensor.kc_achievement_status_{achievement_name}"

    @property
    def native_value(self):
        """Return the overall progress percentage toward the achievement."""

        achievement = self.coordinator.achievements_data.get(self._achievement_id, {})
        target = achievement.get("target_value", 1)
        assigned_kids = achievement.get("assigned_kids", [])

        if not assigned_kids:
            return 0

        ach_type = achievement.get("type")
        if ach_type == ACHIEVEMENT_TYPE_TOTAL:
            total_current = 0
            total_effective_target = 0

            for kid_id in assigned_kids:
                progress_data = achievement.get("progress", {}).get(kid_id, {})
                baseline = (
                    progress_data.get("baseline", 0)
                    if isinstance(progress_data, dict)
                    else 0
                )
                current_total = self.coordinator.kids_data.get(kid_id, {}).get(
                    "completed_chores_total", 0
                )
                total_current += current_total
                total_effective_target += baseline + target

            percent = (
                (total_current / total_effective_target * 100)
                if total_effective_target > 0
                else 0
            )

        elif ach_type == ACHIEVEMENT_TYPE_STREAK:
            total_current = 0

            for kid_id in assigned_kids:
                progress_data = achievement.get("progress", {}).get(kid_id, {})
                total_current += (
                    progress_data.get("current_streak", 0)
                    if isinstance(progress_data, dict)
                    else 0
                )

            global_target = target * len(assigned_kids)

            percent = (total_current / global_target * 100) if global_target > 0 else 0

        elif ach_type == ACHIEVEMENT_TYPE_DAILY_MIN:
            total_progress = 0

            for kid_id in assigned_kids:
                daily = self.coordinator.kids_data.get(kid_id, {}).get(
                    "completed_chores_today", 0
                )
                kid_progress = (
                    100
                    if daily >= target
                    else (daily / target * 100)
                    if target > 0
                    else 0
                )
                total_progress += kid_progress

            percent = total_progress / len(assigned_kids)

        else:
            percent = 0

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
            ).get("name", "")

        assigned_kids_ids = achievement.get("assigned_kids", [])
        assigned_kids_names = [
            self.coordinator._get_kid_name_by_id(k_id) or f"Kid {k_id}"
            for k_id in assigned_kids_ids
        ]
        ach_type = achievement.get("type")
        for kid_id in assigned_kids_ids:
            kid_name = self.coordinator._get_kid_name_by_id(kid_id) or kid_id
            progress_data = achievement.get("progress", {}).get(kid_id, {})
            if ach_type == ACHIEVEMENT_TYPE_TOTAL:
                kids_progress[kid_name] = progress_data.get("current_value", 0)
            elif ach_type == ACHIEVEMENT_TYPE_STREAK:
                kids_progress[kid_name] = progress_data.get("current_streak", 0)
            elif achievement.get("type") == ACHIEVEMENT_TYPE_DAILY_MIN:
                kids_progress[kid_name] = self.coordinator.kids_data.get(
                    kid_id, {}
                ).get("completed_chores_today", 0)
            else:
                kids_progress[kid_name] = 0

        stored_labels = achievement.get("achievement_labels", [])
        friendly_labels = [
            get_friendly_label(self.hass, label) for label in stored_labels
        ]

        return {
            ATTR_ACHIEVEMENT_NAME: self._achievement_name,
            ATTR_DESCRIPTION: achievement.get("description", ""),
            ATTR_ASSIGNED_KIDS: assigned_kids_names,
            ATTR_TYPE: ach_type,
            ATTR_ASSOCIATED_CHORE: associated_chore,
            ATTR_CRITERIA: achievement.get("criteria", ""),
            ATTR_TARGET_VALUE: achievement.get("target_value"),
            ATTR_REWARD_POINTS: achievement.get("reward_points"),
            ATTR_KIDS_EARNED: earned_by,
            ATTR_LABELS: friendly_labels,
        }

    @property
    def icon(self):
        """Return an icon; you could choose a trophy icon."""
        achievement_info = self.coordinator.achievements_data.get(
            self._achievement_id, {}
        )
        return achievement_info.get("icon", DEFAULT_ACHIEVEMENTS_ICON)


# ------------------------------------------------------------------------------------------
class ChallengeSensor(CoordinatorEntity, SensorEntity):
    """Sensor representing a challenge."""

    _attr_has_entity_name = True
    _attr_translation_key = "challenge_state_sensor"

    def __init__(self, coordinator, entry, challenge_id, challenge_name):
        """Initialize the ChallengeSensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._challenge_id = challenge_id
        self._challenge_name = challenge_name
        self._attr_unique_id = f"{entry.entry_id}_{challenge_id}_challenge"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_translation_placeholders = {
            "challenge_name": challenge_name,
        }
        self.entity_id = f"sensor.kc_challenge_status_{challenge_name}"

    @property
    def native_value(self):
        """Return the overall progress percentage toward the challenge."""

        challenge = self.coordinator.challenges_data.get(self._challenge_id, {})
        target = challenge.get("target_value", 1)
        assigned_kids = challenge.get("assigned_kids", [])

        if not assigned_kids:
            return 0

        challenge_type = challenge.get("type")
        total_progress = 0

        for kid_id in assigned_kids:
            progress_data = challenge.get("progress", {}).get(kid_id, {})

            if challenge_type == CHALLENGE_TYPE_TOTAL_WITHIN_WINDOW:
                total_progress += progress_data.get("count", 0)

            elif challenge_type == CHALLENGE_TYPE_DAILY_MIN:
                if isinstance(progress_data, dict):
                    daily_counts = progress_data.get("daily_counts", {})
                    total_progress += sum(daily_counts.values())

                else:
                    total_progress += 0

            else:
                total_progress += 0

        global_target = target * len(assigned_kids)

        percent = (total_progress / global_target * 100) if global_target > 0 else 0

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
            ).get("name", "")

        assigned_kids_ids = challenge.get("assigned_kids", [])
        assigned_kids_names = [
            self.coordinator._get_kid_name_by_id(k_id) or f"Kid {k_id}"
            for k_id in assigned_kids_ids
        ]

        for kid_id in assigned_kids_ids:
            kid_name = self.coordinator._get_kid_name_by_id(kid_id) or kid_id
            progress_data = challenge.get("progress", {}).get(kid_id, {})
            if challenge_type == CHALLENGE_TYPE_TOTAL_WITHIN_WINDOW:
                kids_progress[kid_name] = progress_data.get("count", 0)
            elif challenge_type == CHALLENGE_TYPE_DAILY_MIN:
                if isinstance(progress_data, dict):
                    kids_progress[kid_name] = sum(
                        progress_data.get("daily_counts", {}).values()
                    )
                else:
                    kids_progress[kid_name] = 0
            else:
                kids_progress[kid_name] = 0

        stored_labels = challenge.get("challenge_labels", [])
        friendly_labels = [
            get_friendly_label(self.hass, label) for label in stored_labels
        ]

        return {
            ATTR_CHALLENGE_NAME: self._challenge_name,
            ATTR_DESCRIPTION: challenge.get("description", ""),
            ATTR_ASSIGNED_KIDS: assigned_kids_names,
            ATTR_TYPE: challenge_type,
            ATTR_ASSOCIATED_CHORE: associated_chore,
            ATTR_CRITERIA: challenge.get("criteria", ""),
            ATTR_TARGET_VALUE: challenge.get("target_value"),
            ATTR_REWARD_POINTS: challenge.get("reward_points"),
            ATTR_START_DATE: challenge.get("start_date"),
            ATTR_END_DATE: challenge.get("end_date"),
            ATTR_KIDS_EARNED: earned_by,
            ATTR_LABELS: friendly_labels,
        }

    @property
    def icon(self):
        """Return an icon for challenges (you might want to choose one that fits your theme)."""
        challenge_info = self.coordinator.challenges_data.get(self._challenge_id, {})
        return challenge_info.get("icon", DEFAULT_ACHIEVEMENTS_ICON)


# ------------------------------------------------------------------------------------------
class AchievementProgressSensor(CoordinatorEntity, SensorEntity):
    """Sensor representing a kid's progress toward a specific achievement."""

    _attr_has_entity_name = True
    _attr_translation_key = "achievement_progress_sensor"

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
            "kid_name": kid_name,
            "achievement_name": achievement_name,
        }
        self.entity_id = f"sensor.kc_{kid_name}_achievement_status_{achievement_name}"

    @property
    def native_value(self) -> float:
        """Return the progress percentage toward the achievement."""
        achievement = self.coordinator.achievements_data.get(self._achievement_id, {})
        target = achievement.get("target_value", 1)
        ach_type = achievement.get("type")

        if ach_type == ACHIEVEMENT_TYPE_TOTAL:
            progress_data = achievement.get("progress", {}).get(self._kid_id, {})

            baseline = (
                progress_data.get("baseline", 0)
                if isinstance(progress_data, dict)
                else 0
            )

            current_total = self.coordinator.kids_data.get(self._kid_id, {}).get(
                "completed_chores_total", 0
            )

            effective_target = baseline + target

            percent = (
                (current_total / effective_target * 100) if effective_target > 0 else 0
            )

        elif ach_type == ACHIEVEMENT_TYPE_STREAK:
            progress_data = achievement.get("progress", {}).get(self._kid_id, {})

            progress = (
                progress_data.get("current_streak", 0)
                if isinstance(progress_data, dict)
                else 0
            )

            percent = (progress / target * 100) if target > 0 else 0

        elif ach_type == ACHIEVEMENT_TYPE_DAILY_MIN:
            daily = self.coordinator.kids_data.get(self._kid_id, {}).get(
                "completed_chores_today", 0
            )

            percent = (daily / target * 100) if target > 0 else 0

        else:
            percent = 0

        return min(100, round(percent, 1))

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes for the achievement progress."""
        achievement = self.coordinator.achievements_data.get(self._achievement_id, {})
        target = achievement.get("target_value", 1)
        progress_data = achievement.get("progress", {}).get(self._kid_id, {})
        awarded = (
            progress_data.get("awarded", False)
            if isinstance(progress_data, dict)
            else False
        )

        if achievement.get("type") == ACHIEVEMENT_TYPE_TOTAL:
            raw_progress = (
                progress_data.get("current_value", 0)
                if isinstance(progress_data, dict)
                else 0
            )

        elif achievement.get("type") == ACHIEVEMENT_TYPE_STREAK:
            raw_progress = (
                progress_data.get("current_streak", 0)
                if isinstance(progress_data, dict)
                else 0
            )

        elif achievement.get("type") == ACHIEVEMENT_TYPE_DAILY_MIN:
            raw_progress = self.coordinator.kids_data.get(self._kid_id, {}).get(
                "completed_chores_today", 0
            )

        associated_chore = ""
        selected_chore_id = achievement.get("selected_chore_id")
        if selected_chore_id:
            associated_chore = self.coordinator.chores_data.get(
                selected_chore_id, {}
            ).get("name", "")

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
            ATTR_ACHIEVEMENT_NAME: self._achievement_name,
            ATTR_DESCRIPTION: achievement.get("description", ""),
            ATTR_ASSIGNED_KIDS: assigned_kids_names,
            ATTR_TYPE: achievement.get("type"),
            ATTR_ASSOCIATED_CHORE: associated_chore,
            ATTR_CRITERIA: achievement.get("criteria", ""),
            ATTR_TARGET_VALUE: target,
            ATTR_REWARD_POINTS: achievement.get("reward_points"),
            ATTR_RAW_PROGRESS: raw_progress,
            ATTR_AWARDED: awarded,
            ATTR_LABELS: friendly_labels,
        }

    @property
    def icon(self) -> str:
        """Return the icon for the achievement.

        Use the icon provided in the achievement data if set, else fallback to default.
        """
        achievement = self.coordinator.achievements_data.get(self._achievement_id, {})
        return achievement.get("icon", DEFAULT_ACHIEVEMENTS_ICON)


# ------------------------------------------------------------------------------------------
class ChallengeProgressSensor(CoordinatorEntity, SensorEntity):
    """Sensor representing a kid's progress toward a specific challenge."""

    _attr_has_entity_name = True
    _attr_translation_key = "challenge_progress_sensor"

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
            "kid_name": kid_name,
            "challenge_name": challenge_name,
        }
        self.entity_id = f"sensor.kc_{kid_name}_challenge_status_{challenge_name}"

    @property
    def native_value(self) -> float:
        """Return the challenge progress percentage."""
        challenge = self.coordinator.challenges_data.get(self._challenge_id, {})
        target = challenge.get("target_value", 1)
        challenge_type = challenge.get("type")
        progress_data = challenge.get("progress", {}).get(self._kid_id)

        if challenge_type == CHALLENGE_TYPE_TOTAL_WITHIN_WINDOW:
            raw_progress = (
                progress_data.get("count", 0) if isinstance(progress_data, dict) else 0
            )

        elif challenge_type == CHALLENGE_TYPE_DAILY_MIN:
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
                raw_progress = 0

        else:
            raw_progress = 0

        percent = (raw_progress / target * 100) if target > 0 else 0

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

        if challenge_type == CHALLENGE_TYPE_TOTAL_WITHIN_WINDOW:
            raw_progress = (
                progress_data.get("count", 0) if isinstance(progress_data, dict) else 0
            )
        elif challenge_type == CHALLENGE_TYPE_DAILY_MIN:
            if isinstance(progress_data, dict):
                daily_counts = progress_data.get("daily_counts", {})
                raw_progress = sum(daily_counts.values())
            else:
                raw_progress = 0
        else:
            raw_progress = 0

        associated_chore = ""
        selected_chore_id = challenge.get("selected_chore_id")
        if selected_chore_id:
            associated_chore = self.coordinator.chores_data.get(
                selected_chore_id, {}
            ).get("name", "")

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
            ATTR_CHALLENGE_NAME: self._challenge_name,
            ATTR_DESCRIPTION: challenge.get("description", ""),
            ATTR_ASSIGNED_KIDS: assigned_kids_names,
            ATTR_TYPE: challenge_type,
            ATTR_ASSOCIATED_CHORE: associated_chore,
            ATTR_CRITERIA: challenge.get("criteria", ""),
            ATTR_TARGET_VALUE: target,
            ATTR_REWARD_POINTS: challenge.get("reward_points"),
            ATTR_START_DATE: challenge.get("start_date"),
            ATTR_END_DATE: challenge.get("end_date"),
            ATTR_RAW_PROGRESS: raw_progress,
            ATTR_AWARDED: awarded,
            ATTR_LABELS: friendly_labels,
        }

    @property
    def icon(self) -> str:
        """Return the icon for the challenge.

        Use the icon provided in the challenge data if set, else fallback to default.
        """
        challenge = self.coordinator.challenges_data.get(self._challenge_id, {})
        return challenge.get("icon", DEFAULT_CHALLENGES_ICON)


# ------------------------------------------------------------------------------------------
class KidHighestStreakSensor(CoordinatorEntity, SensorEntity):
    """Sensor returning the highest current streak among streak-type achievements for a kid."""

    _attr_has_entity_name = True
    _attr_translation_key = "kid_highest_streak_sensor"

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
            "kid_name": kid_name,
        }
        self.entity_id = f"sensor.kc_{kid_name}_highest_streak"

    @property
    def native_value(self) -> int:
        """Return the highest current streak among all streak achievements for the kid."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        return kid_info.get("overall_chore_streak", 0)

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes including individual streaks per achievement."""
        streaks = {}
        for achievement in self.coordinator.achievements_data.values():
            if achievement.get("type") == ACHIEVEMENT_TYPE_STREAK:
                achievement_name = achievement.get("name", "Unnamed Achievement")
                progress_for_kid = achievement.get("progress", {}).get(self._kid_id)

                if isinstance(progress_for_kid, dict):
                    streaks[achievement_name] = progress_for_kid.get(
                        "current_streak", 0
                    )

                elif isinstance(progress_for_kid, int):
                    streaks[achievement_name] = progress_for_kid

        return {"streaks_by_achievement": streaks}

    @property
    def icon(self) -> str:
        """Return an icon for 'highest streak'. You can choose any default or allow config overrides."""
        return DEFAULT_STREAK_ICON


# ------------------------------------------------------------------------------------------
class ChoreStreakSensor(CoordinatorEntity, SensorEntity):
    """Sensor returning the current streak for a specific chore for a given kid."""

    _attr_has_entity_name = True
    _attr_translation_key = "chore_streak_sensor"

    def __init__(
        self,
        coordinator: KidsChoresDataCoordinator,
        entry: ConfigEntry,
        kid_id: str,
        kid_name: str,
        chore_id: str,
        chore_name: str,
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._chore_id = chore_id
        self._chore_name = chore_name
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_{chore_id}_streak"
        self._attr_native_unit_of_measurement = UnitOfTime.DAYS
        self._attr_translation_placeholders = {
            "kid_name": kid_name,
            "chore_name": chore_name,
        }
        self.entity_id = f"sensor.kc_{kid_name}_chore_streak_{chore_name}"

    @property
    def native_value(self) -> int:
        """Return the current streak (in days) for this kid and chore."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        streaks = kid_info.get("chore_streaks", {})
        streak_info = streaks.get(self._chore_id, {})
        return streak_info.get("current_streak", 0)

    @property
    def extra_state_attributes(self) -> dict:
        """Return extra attributes such as the last approved date for this streak."""
        attributes = {}
        for achievement in self.coordinator.achievements_data.values():
            if (
                achievement.get("type") == ACHIEVEMENT_TYPE_STREAK
                and achievement.get("selected_chore_id") == self._chore_id
            ):
                progress_for_kid = achievement.get("progress", {}).get(self._kid_id)

                if isinstance(progress_for_kid, dict):
                    attributes[ATTR_LAST_DATE] = progress_for_kid.get("last_date")
                    attributes[ATTR_RAW_STREAK] = progress_for_kid.get(
                        "current_streak", 0
                    )

                elif isinstance(progress_for_kid, int):
                    attributes[ATTR_LAST_DATE] = None
                    attributes[ATTR_RAW_STREAK] = progress_for_kid
                break
        return attributes

    @property
    def icon(self) -> str:
        """Return the chore's custom icon if set, else fallback."""
        chore_info = self.coordinator.chores_data.get(self._chore_id, {})
        return chore_info.get("icon", DEFAULT_CHORE_SENSOR_ICON)


# ------------------------------------------------------------------------------------------
class BonusAppliesSensor(CoordinatorEntity, SensorEntity):
    """Sensor tracking how many times each bonus has been applied to a kid."""

    _attr_has_entity_name = True
    _attr_translation_key = "bonus_applies_sensor"

    def __init__(self, coordinator, entry, kid_id, kid_name, bonus_id, bonus_name):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._kid_id = kid_id
        self._kid_name = kid_name
        self._bonus_id = bonus_id
        self._bonus_name = bonus_name
        self._attr_unique_id = f"{entry.entry_id}_{kid_id}_{bonus_id}_bonus_applies"
        self._attr_translation_placeholders = {
            "kid_name": kid_name,
            "bonus_name": bonus_name,
        }
        self.entity_id = f"sensor.kc_{kid_name}_bonuses_applied_{bonus_name}"

    @property
    def native_value(self):
        """Return the number of times the bonus has been applied."""
        kid_info = self.coordinator.kids_data.get(self._kid_id, {})
        return kid_info.get("bonus_applies", {}).get(self._bonus_id, 0)

    @property
    def extra_state_attributes(self):
        """Expose additional details like bonus points and description."""
        bonus_info = self.coordinator.bonuses_data.get(self._bonus_id, {})

        stored_labels = bonus_info.get("bonus_labels", [])
        friendly_labels = [
            get_friendly_label(self.hass, label) for label in stored_labels
        ]

        return {
            ATTR_KID_NAME: self._kid_name,
            ATTR_BONUS_NAME: self._bonus_name,
            ATTR_DESCRIPTION: bonus_info.get("description", ""),
            ATTR_BONUS_POINTS: bonus_info.get("points", DEFAULT_BONUS_POINTS),
            ATTR_LABELS: friendly_labels,
        }

    @property
    def icon(self):
        """Return the bonus's custom icon if set, else fallback."""
        bonus_info = self.coordinator.bonuses_data.get(self._bonus_id, {})
        return bonus_info.get("icon", DEFAULT_BONUS_ICON)
