# File: const.py
"""Constants for the KidsChores integration.

This file centralizes configuration keys, defaults, labels, domain names,
event names, and platform identifiers for consistency across the integration.
It also supports localization by defining all labels and UI texts used in sensors,
services, and options flow.
"""

import logging

import homeassistant.util.dt as dt_util
from homeassistant.const import Platform


def set_default_timezone(hass):
    """Set the default timezone based on the Home Assistant configuration."""
    global DEFAULT_TIME_ZONE
    DEFAULT_TIME_ZONE = dt_util.get_time_zone(hass.config.time_zone)


# ------------------------------------------------------------------------------------------------
# General / Integration Information
# ------------------------------------------------------------------------------------------------
# Integration Name
KIDSCHORES_TITLE = "KidsChores"

# Integration Domain
DOMAIN = "kidschores"

# Logger
LOGGER = logging.getLogger(__package__)

# Supported Platforms
PLATFORMS = [
    Platform.BUTTON,
    Platform.CALENDAR,
    Platform.SELECT,
    Platform.SENSOR,
]

# Coordinator
COORDINATOR = "coordinator"
COORDINATOR_SUFFIX = "_coordinator"

# Storage and Versioning
STORAGE_MANAGER = "storage_manager"
STORAGE_KEY = "kidschores_data"
STORAGE_VERSION = 1

# Default timezone: initially None, to be set once hass is available.
DEFAULT_TIME_ZONE = None

# Migration Flags
MIGRATION_PERFORMED = "migration_performed"
MIGRATION_KEY_VERSION = "migration_key_version"
MIGRATION_KEY_VERSION_NUMBER = 40

# Migration Data
MIGRATION_DATA_LEGACY_ORPHAN = "legacy_orphan"

# Update Interval
DEFAULT_UPDATE_INTERVAL = 5

# ------------------------------------------------------------------------------------------------
# Configuration Keys
# ------------------------------------------------------------------------------------------------

# ConfigFlow Steps
CONFIG_FLOW_STEP_ACHIEVEMENT_COUNT = "achievement_count"
CONFIG_FLOW_STEP_ACHIEVEMENTS = "achievements"
CONFIG_FLOW_STEP_BADGE_COUNT = "badge_count"
CONFIG_FLOW_STEP_BADGES = "badges"
CONFIG_FLOW_STEP_BONUS_COUNT = "bonus_count"
CONFIG_FLOW_STEP_BONUSES = "bonuses"
CONFIG_FLOW_STEP_CHALLENGE_COUNT = "challenge_count"
CONFIG_FLOW_STEP_CHALLENGES = "challenges"
CONFIG_FLOW_STEP_CHORE_COUNT = "chore_count"
CONFIG_FLOW_STEP_CHORES = "chores"
CONFIG_FLOW_STEP_FINISH = "finish"
CONFIG_FLOW_STEP_INTRO = "intro"
CONFIG_FLOW_STEP_KID_COUNT = "kid_count"
CONFIG_FLOW_STEP_KIDS = "kids"
CONFIG_FLOW_STEP_PARENT_COUNT = "parent_count"
CONFIG_FLOW_STEP_PARENTS = "parents"
CONFIG_FLOW_STEP_PENALTY_COUNT = "penalty_count"
CONFIG_FLOW_STEP_PENALTIES = "penalties"
CONFIG_FLOW_STEP_POINTS = "points_label"
CONFIG_FLOW_STEP_REWARD_COUNT = "reward_count"
CONFIG_FLOW_STEP_REWARDS = "rewards"

# OptionsFlow Management Menus Keys
OPTIONS_FLOW_DIC_ACHIEVEMENT = "achievement"
OPTIONS_FLOW_DIC_BADGE = "badge"
OPTIONS_FLOW_DIC_BONUS = "bonus"
OPTIONS_FLOW_DIC_CHALLENGE = "challenge"
OPTIONS_FLOW_DIC_CHORE = "chore"
OPTIONS_FLOW_DIC_KID = "kid"
OPTIONS_FLOW_DIC_PARENT = "parent"
OPTIONS_FLOW_DIC_PENALTY = "penalty"
OPTIONS_FLOW_DIC_REWARD = "reward"

OPTIONS_FLOW_ACTIONS_ADD = "add"
OPTIONS_FLOW_ACTIONS_BACK = "back"
OPTIONS_FLOW_ACTIONS_DELETE = "delete"
OPTIONS_FLOW_ACTIONS_EDIT = "edit"

OPTIONS_FLOW_ACHIEVEMENTS = "manage_achievement"
OPTIONS_FLOW_BADGES = "manage_badge"
OPTIONS_FLOW_BONUSES = "manage_bonus"
OPTIONS_FLOW_CHALLENGES = "manage_challenge"
OPTIONS_FLOW_CHORES = "manage_chore"
OPTIONS_FLOW_FINISH = "done"
OPTIONS_FLOW_GENERAL_OPTIONS = "general_options"
OPTIONS_FLOW_KIDS = "manage_kid"
OPTIONS_FLOW_PARENTS = "manage_parent"
OPTIONS_FLOW_PENALTIES = "manage_penalty"
OPTIONS_FLOW_POINTS = "manage_points"
OPTIONS_FLOW_REWARDS = "manage_reward"

# OptionsFlow Configuration Keys
CONF_ACHIEVEMENTS = "achievements"
CONF_BADGES = "badges"
CONF_BONUSES = "bonuses"
CONF_CHALLENGES = "challenges"
CONF_CHORES = "chores"
CONF_KIDS = "kids"
CONF_PARENTS = "parents"
CONF_PENALTIES = "penalties"
CONF_REWARDS = "rewards"

# OptionsFlow Steps
OPTIONS_FLOW_STEP_INIT = "init"
OPTIONS_FLOW_STEP_MANAGE_ENTITY = "manage_entity"
OPTIONS_FLOW_STEP_MANAGE_GENERAL_OPTIONS = "manage_general_options"
OPTIONS_FLOW_STEP_MANAGE_POINTS = "manage_points"
OPTIONS_FLOW_STEP_SELECT_ENTITY = "select_entity"

OPTIONS_FLOW_STEP_ADD_ACHIEVEMENT = "add_achievement"
OPTIONS_FLOW_STEP_ADD_BADGE = "add_badge"
OPTIONS_FLOW_STEP_ADD_BADGE_ACHIEVEMENT = "add_badge_achievement"
OPTIONS_FLOW_STEP_ADD_BADGE_CHALLENGE = "add_badge_challenge"
OPTIONS_FLOW_STEP_ADD_BADGE_CUMULATIVE = "add_badge_cumulative"
OPTIONS_FLOW_STEP_ADD_BADGE_DAILY = "add_badge_daily"
OPTIONS_FLOW_STEP_ADD_BADGE_PERIODIC = "add_badge_periodic"
OPTIONS_FLOW_STEP_ADD_BADGE_SPECIAL = "add_badge_special"
OPTIONS_FLOW_STEP_ADD_BONUS = "add_bonus"
OPTIONS_FLOW_STEP_ADD_CHALLENGE = "add_challenge"
OPTIONS_FLOW_STEP_ADD_CHORE = "add_chore"
OPTIONS_FLOW_STEP_ADD_KID = "add_kid"
OPTIONS_FLOW_STEP_ADD_PARENT = "add_parent"
OPTIONS_FLOW_STEP_ADD_PENALTY = "add_penalty"
OPTIONS_FLOW_STEP_ADD_REWARD = "add_reward"

OPTIONS_FLOW_STEP_EDIT_ACHIEVEMENT = "edit_achievement"
OPTIONS_FLOW_STEP_EDIT_BADGE_ACHIEVEMENT = "edit_badge_achievement"
OPTIONS_FLOW_STEP_EDIT_BADGE_CHALLENGE = "edit_badge_challenge"
OPTIONS_FLOW_STEP_EDIT_BADGE_CUMULATIVE = "edit_badge_cumulative"
OPTIONS_FLOW_STEP_EDIT_BADGE_DAILY = "edit_badge_daily"
OPTIONS_FLOW_STEP_EDIT_BADGE_PERIODIC = "edit_badge_periodic"
OPTIONS_FLOW_STEP_EDIT_BADGE_SPECIAL = "edit_badge_special"
OPTIONS_FLOW_STEP_EDIT_BONUS = "edit_bonus"
OPTIONS_FLOW_STEP_EDIT_CHALLENGE = "edit_challenge"
OPTIONS_FLOW_STEP_EDIT_CHORE = "edit_chore"
OPTIONS_FLOW_STEP_EDIT_KID = "edit_kid"
OPTIONS_FLOW_STEP_EDIT_PARENT = "edit_parent"
OPTIONS_FLOW_STEP_EDIT_PENALTY = "edit_penalty"
OPTIONS_FLOW_STEP_EDIT_REWARD = "edit_reward"

OPTIONS_FLOW_STEP_DELETE_ACHIEVEMENT = "delete_achievement"
OPTIONS_FLOW_STEP_DELETE_BADGE = "delete_badge"
OPTIONS_FLOW_STEP_DELETE_BONUS = "delete_bonus"
OPTIONS_FLOW_STEP_DELETE_CHALLENGE = "delete_challenge"
OPTIONS_FLOW_STEP_DELETE_CHORE = "delete_chore"
OPTIONS_FLOW_STEP_DELETE_KID = "delete_kid"
OPTIONS_FLOW_STEP_DELETE_PARENT = "delete_parent"
OPTIONS_FLOW_STEP_DELETE_PENALTY = "delete_penalty"
OPTIONS_FLOW_STEP_DELETE_REWARD = "delete_reward"

# ConfigFlow & OptionsFlow User Input Fields

# GLOBAL
CFOF_GLOBAL_INPUT_INTERNAL_ID = "internal_id"

# KIDS
CFOF_KIDS_INPUT_ENABLE_MOBILE_NOTIFICATIONS = "enable_mobile_notifications"
CFOF_KIDS_INPUT_ENABLE_PERSISTENT_NOTIFICATIONS = "enable_persistent_notifications"
CFOF_KIDS_INPUT_HA_USER = "ha_user"
CFOF_KIDS_INPUT_KID_COUNT = "kid_count"
CFOF_KIDS_INPUT_KID_NAME = "kid_name"
CFOF_KIDS_INPUT_MOBILE_NOTIFY_SERVICE = "mobile_notify_service"

# PARENTS
CFOF_PARENTS_INPUT_ASSOCIATED_KIDS = "associated_kids"
CFOF_PARENTS_INPUT_ENABLE_MOBILE_NOTIFICATIONS = "enable_mobile_notifications"
CFOF_PARENTS_INPUT_ENABLE_PERSISTENT_NOTIFICATIONS = "enable_persistent_notifications"
CFOF_PARENTS_INPUT_HA_USER = "ha_user_id"
CFOF_PARENTS_INPUT_MOBILE_NOTIFY_SERVICE = "mobile_notify_service"
CFOF_PARENTS_INPUT_NAME = "parent_name"
CFOF_PARENTS_INPUT_PARENT_COUNT = "parent_count"

# CHORES
CFOF_CHORES_INPUT_ALLOW_MULTIPLE_CLAIMS = "allow_multiple_claims_per_day"
CFOF_CHORES_INPUT_APPLICABLE_DAYS = "applicable_days"
CFOF_CHORES_INPUT_ASSIGNED_KIDS = "assigned_kids"
CFOF_CHORES_INPUT_CHORE_COUNT = "chore_count"
CFOF_CHORES_INPUT_CUSTOM_INTERVAL = "custom_interval"
CFOF_CHORES_INPUT_CUSTOM_INTERVAL_UNIT = "custom_interval_unit"
CFOF_CHORES_INPUT_DEFAULT_POINTS = "default_points"
CFOF_CHORES_INPUT_DESCRIPTION = "chore_description"
CFOF_CHORES_INPUT_DUE_DATE = "due_date"
CFOF_CHORES_INPUT_ICON = "icon"
CFOF_CHORES_INPUT_LABELS = "chore_labels"
CFOF_CHORES_INPUT_NAME = "chore_name"
CFOF_CHORES_INPUT_NOTIFY_ON_APPROVAL = "notify_on_approval"
CFOF_CHORES_INPUT_NOTIFY_ON_CLAIM = "notify_on_claim"
CFOF_CHORES_INPUT_NOTIFY_ON_DISAPPROVAL = "notify_on_disapproval"
CFOF_CHORES_INPUT_PARTIAL_ALLOWED = "partial_allowed"
CFOF_CHORES_INPUT_RECURRING_FREQUENCY = "recurring_frequency"
CFOF_CHORES_INPUT_SHARED_CHORE = "shared_chore"

# BADGES
CFOF_BADGES_INPUT_ASSIGNED_KIDS = "assigned_kids"
CFOF_BADGES_INPUT_ASSIGNED_TO = "assigned_to"
CFOF_BADGES_INPUT_ASSOCIATED_ACHIEVEMENT = "associated_achievement"
CFOF_BADGES_INPUT_ASSOCIATED_CHALLENGE = "associated_challenge"
CFOF_BADGES_INPUT_AWARD_ITEMS = "award_items"
CFOF_BADGES_INPUT_AWARD_MODE = "award_mode"
CFOF_BADGES_INPUT_AWARD_POINTS = "award_points"
CFOF_BADGES_INPUT_AWARD_POINTS_REWARD = "award_points_reward"
CFOF_BADGES_INPUT_AWARD_REWARD = "award_reward"
CFOF_BADGES_INPUT_BADGE_COUNT = "badge_count"
CFOF_BADGES_INPUT_CUSTOM_RESET_DATE = "custom_reset_date"
CFOF_BADGES_INPUT_DAILY_THRESHOLD = "daily_threshold"
CFOF_BADGES_INPUT_DAILY_THRESHOLD_TYPE = "threshold_type"
CFOF_BADGES_INPUT_DESCRIPTION = "badge_description"
CFOF_BADGES_INPUT_END_DATE = "end_date"
CFOF_BADGES_INPUT_ICON = "icon"
CFOF_BADGES_INPUT_LABELS = "badge_labels"
CFOF_BADGES_INPUT_MAINTENANCE_RULES = "maintenance_rules"
CFOF_BADGES_INPUT_NAME = "badge_name"
CFOF_BADGES_INPUT_OCCASION_DATE_UNUSED = "occasion_date"
CFOF_BADGES_INPUT_OCCASION_TYPE = "occasion_type"
CFOF_BADGES_INPUT_PERIODIC_RECURRENT_UNUSED = "recurrent"
CFOF_BADGES_INPUT_POINTS_MULTIPLIER = "points_multiplier"
CFOF_BADGES_INPUT_RESET_GRACE_PERIOD_UNUSED = "reset_grace_period"
CFOF_BADGES_INPUT_RESET_PERIODICALLY_UNUSED = "reset_periodically"
CFOF_BADGES_INPUT_RESET_RECURRENT_UNUSED = "recurrent"
CFOF_BADGES_INPUT_RESET_SCHEDULE = "reset_schedule"
CFOF_BADGES_INPUT_RESET_SCHEDULE_CUSTOM_INTERVAL = "custom_interval"
CFOF_BADGES_INPUT_RESET_SCHEDULE_CUSTOM_INTERVAL_UNIT = "custom_interval_unit"
CFOF_BADGES_INPUT_RESET_SCHEDULE_END_DATE = "end_date"
CFOF_BADGES_INPUT_RESET_SCHEDULE_GRACE_PERIOD_DAYS = "grace_period_days"
CFOF_BADGES_INPUT_RESET_SCHEDULE_RECURRING_FREQUENCY = "recurring_frequency"
CFOF_BADGES_INPUT_RESET_SCHEDULE_START_DATE = "start_date"
CFOF_BADGES_INPUT_REWARD_UNUSED = "reward"
CFOF_BADGES_INPUT_SELECTED_CHORES = "selected_chores"
CFOF_BADGES_INPUT_SPECIAL_OCCASION_RECURRENCY_UNUSED = "recurrent"
CFOF_BADGES_INPUT_SPECIAL_OCCASION_TYPE_UNUSED = "occasion_type"
CFOF_BADGES_INPUT_RESET_TYPE_UNUSED = "reset_type"
CFOF_BADGES_INPUT_REQUIRED_CHORES_UNUSED = "required_chores"
CFOF_BADGES_INPUT_START_DATE = "start_date"
CFOF_BADGES_INPUT_TARGET_TYPE = "target_type"
CFOF_BADGES_INPUT_TARGET_THRESHOLD_VALUE = "threshhold_value"
CFOF_BADGES_INPUT_THRESHOLD_TYPE_UNUSED = "threshold_type"
CFOF_BADGES_INPUT_THRESHOLD_VALUE_UNUSED = "threshold_value"
CFOF_BADGES_INPUT_TRIGGER_INFO_UNUSED = "trigger_info"
CFOF_BADGES_INPUT_TYPE = "badge_type"

# REWARDS
CFOF_REWARDS_INPUT_COST = "reward_cost"
CFOF_REWARDS_INPUT_DESCRIPTION = "reward_description"
CFOF_REWARDS_INPUT_ICON = "icon"
CFOF_REWARDS_INPUT_LABELS = "reward_labels"
CFOF_REWARDS_INPUT_NAME = "reward_name"
CFOF_REWARDS_INPUT_REWARD_COUNT = "reward_count"

# BONUSES
CFOF_BONUSES_INPUT_BONUS_COUNT = "bonus_count"
CFOF_BONUSES_INPUT_DESCRIPTION = "bonus_description"
CFOF_BONUSES_INPUT_ICON = "icon"
CFOF_BONUSES_INPUT_LABELS = "bonus_labels"
CFOF_BONUSES_INPUT_NAME = "bonus_name"
CFOF_BONUSES_INPUT_POINTS = "bonus_points"

# PENALTIES
CFOF_PENALTIES_INPUT_DESCRIPTION = "penalty_description"
CFOF_PENALTIES_INPUT_ICON = "icon"
CFOF_PENALTIES_INPUT_LABELS = "penalty_labels"
CFOF_PENALTIES_INPUT_NAME = "penalty_name"
CFOF_PENALTIES_INPUT_PENALTY_COUNT = "penalty_count"
CFOF_PENALTIES_INPUT_POINTS = "penalty_points"

# ACHIEVEMENTS
CFOF_ACHIEVEMENTS_INPUT_ACHIEVEMENT_COUNT = "achievement_count"
CFOF_ACHIEVEMENTS_INPUT_ASSIGNED_KIDS = "assigned_kids"
CFOF_ACHIEVEMENTS_INPUT_CRITERIA = "criteria"
CFOF_ACHIEVEMENTS_INPUT_DESCRIPTION = "description"
CFOF_ACHIEVEMENTS_INPUT_ICON = "icon"
CFOF_ACHIEVEMENTS_INPUT_LABELS = "achievement_labels"
CFOF_ACHIEVEMENTS_INPUT_NAME = "name"
CFOF_ACHIEVEMENTS_INPUT_REWARD_POINTS = "reward_points"
CFOF_ACHIEVEMENTS_INPUT_SELECTED_CHORE_ID = "selected_chore_id"
CFOF_ACHIEVEMENTS_INPUT_TARGET_VALUE = "target_value"
CFOF_ACHIEVEMENTS_INPUT_TYPE = "type"

# CHALLENGES
CFOF_CHALLENGES_INPUT_ASSIGNED_KIDS = "assigned_kids"
CFOF_CHALLENGES_INPUT_CHALLENGE_COUNT = "challenge_count"
CFOF_CHALLENGES_INPUT_CRITERIA = "criteria"
CFOF_CHALLENGES_INPUT_DESCRIPTION = "description"
CFOF_CHALLENGES_INPUT_END_DATE = "end_date"
CFOF_CHALLENGES_INPUT_ICON = "icon"
CFOF_CHALLENGES_INPUT_LABELS = "challenge_labels"
CFOF_CHALLENGES_INPUT_NAME = "name"
CFOF_CHALLENGES_INPUT_REWARD_POINTS = "reward_points"
CFOF_CHALLENGES_INPUT_SELECTED_CHORE_ID = "selected_chore_id"
CFOF_CHALLENGES_INPUT_START_DATE = "start_date"
CFOF_CHALLENGES_INPUT_TARGET_VALUE = "target_value"
CFOF_CHALLENGES_INPUT_TYPE = "type"

# OptionsFlow Input Fields
OPTIONS_FLOW_INPUT_ENTITY_NAME = "entity_name"
OPTIONS_FLOW_INPUT_INTERNAL_ID = "internal_id"
OPTIONS_FLOW_INPUT_MENU_SELECTION = "menu_selection"
OPTIONS_FLOW_INPUT_MANAGE_ACTION = "manage_action"

# OptionsFlow Data Fields
OPTIONS_FLOW_DATA_ENTITY_NAME = "name"

# OptionsFlow Placeholders
OPTIONS_FLOW_PLACEHOLDER_ACTION = "action"
OPTIONS_FLOW_PLACEHOLDER_ACHIEVEMENT_NAME = "achievement_name"
OPTIONS_FLOW_PLACEHOLDER_BADGE_NAME = "badge_name"
OPTIONS_FLOW_PLACEHOLDER_BONUS_NAME = "bonus_name"
OPTIONS_FLOW_PLACEHOLDER_CHALLENGE_NAME = "challenge_name"
OPTIONS_FLOW_PLACEHOLDER_CHORE_NAME = "chore_name"
OPTIONS_FLOW_PLACEHOLDER_ENTITY_TYPE = "entity_type"
OPTIONS_FLOW_PLACEHOLDER_KID_NAME = "kid_name"
OPTIONS_FLOW_PLACEHOLDER_PARENT_NAME = "parent_name"
OPTIONS_FLOW_PLACEHOLDER_PENALTY_NAME = "penalty_name"
OPTIONS_FLOW_PLACEHOLDER_REWARD_NAME = "reward_name"
OPTIONS_FLOW_PLACEHOLDER_SUMMARY = "summary"


# OptionsFlow Helpers
OPTIONS_FLOW_ASYNC_STEP_PREFIX = "async_step_"
OPTIONS_FLOW_ASYNC_STEP_ADD_PREFIX = "async_step_add_"
OPTIONS_FLOW_MENU_MANAGE_PREFIX = "manage_"


# Global configuration keys
CONF_BIRTHDAY = "birthday"
CONF_BIWEEKLY = "biweekly"
CONF_CALENDAR_SHOW_PERIOD = "calendar_show_period"
CONF_COST = "cost"
CONF_CUSTOM = "custom"
CONF_CUSTOM_1_MONTH = "custom_1_month"
CONF_CUSTOM_1_WEEK = "custom_1_week"
CONF_CUSTOM_1_YEAR = "custom_1_year"
CONF_DAILY = "daily"
CONF_DAY = "day"
CONF_DAYS = "days"
CONF_DAY_END = "day_end"
CONF_DESCRIPTION = "description"
CONF_DOT = "."
CONF_EMPTY = ""
CONF_HOLIDAY = "holiday"
CONF_HOUR = "hour"
CONF_HOURS = "hours"
CONF_ICON = "icon"
CONF_INTERNAL_ID = "internal_id"
CONF_LABEL = "label"
CONF_MINUTES = "minutes"
CONF_MONTHS = "months"
CONF_MONTHLY = "monthly"
CONF_MONTH_END = "month_end"
CONF_NAME = "name"
CONF_NONE = None
CONF_NONE_TEXT = "None"
CONF_POINTS = "points"
CONF_QUARTER = "quarter"
CONF_QUARTERLY = "quarterly"
CONF_QUARTERS = "quarters"
CONF_QUARTER_END = "quarter_end"
CONF_SHARED_CHORE = "shared_chore"
CONF_UNAVAILABLE = "unavailable"
CONF_UNKNOWN = "Unknown"
CONF_VALUE = "value"
CONF_WEEKS = "weeks"
CONF_WEEKLY = "weekly"
CONF_WEEK_END = "week_end"
CONF_YEAR_END = "year_end"
CONF_YEARLY = "yearly"
CONF_YEARS = "years"
CONF_YEAR_END = "year_end"

# Points configuration keys
CONF_POINTS_ICON = "points_icon"
CONF_POINTS_LABEL = "points_label"

# Kids configuration keys
CONF_HA_USER = "ha_user"

# Parents configuration keys
CONF_HA_USER_ID = "ha_user_id"
CONF_PARENT_NAME = "parent_name"
CONF_ASSOCIATED_KIDS = "associated_kids"

# Chores configuration keys
CONF_ALLOW_MULTIPLE_CLAIMS_PER_DAY = "allow_multiple_claims_per_day"
CONF_APPLICABLE_DAYS = "applicable_days"
CONF_ASSIGNED_KIDS = "assigned_kids"
CONF_CHORE_DESCRIPTION = "chore_description"
CONF_CHORE_LABELS = "chore_labels"
CONF_CHORE_NAME = "chore_name"
CONF_CUSTOM_INTERVAL = "custom_interval"
CONF_CUSTOM_INTERVAL_UNIT = "custom_interval_unit"
CONF_DEFAULT_POINTS = "default_points"
CONF_DUE_DATE = "due_date"
CONF_PARTIAL_ALLOWED = "partial_allowed"
CONF_RECURRING_FREQUENCY = "recurring_frequency"

# Notification configuration keys
CONF_ENABLE_MOBILE_NOTIFICATIONS = "enable_mobile_notifications"
CONF_ENABLE_PERSISTENT_NOTIFICATIONS = "enable_persistent_notifications"
CONF_MOBILE_NOTIFY_SERVICE = "mobile_notify_service"
CONF_NOTIFY_ON_APPROVAL = "notify_on_approval"
CONF_NOTIFY_ON_CLAIM = "notify_on_claim"
CONF_NOTIFY_ON_DISAPPROVAL = "notify_on_disapproval"

NOTIFICATION_EVENT = "mobile_app_notification_action"

# Badge configuration keys
CONF_BADGE_ASSIGNED_KIDS_UNUSED = "assigned_kids"
CONF_BADGE_ASSOCIATED_ACHIEVEMENT_UNUSED = "associated_achievement"
CONF_BADGE_ASSOCIATED_CHALLENGE_UNUSED = "associated_challenge"
CONF_BADGE_AWARD_MODE_UNUSED = "award_mode"
CONF_BADGE_AWARD_NONE_LEGACY = "award_none"
CONF_BADGE_AWARD_POINTS_UNUSED = "award_points"
CONF_BADGE_AWARD_REWARD_UNUSED = "award_reward"
CONF_BADGE_AWARD_POINTS_REWARD_UNUSED = "award_points_reward"
CONF_BADGE_CUSTOM_RESET_DATE_UNUSED = "custom_reset_date"
CONF_BADGE_DAILY_THRESHOLD_UNUSED = "daily_threshold"
CONF_BADGE_DAILY_THRESHOLD_TYPE_UNUSED = "daily_threshold_type"
CONF_BADGE_DESCRIPTION_UNUSED = "badge_description"
CONF_BADGE_END_DATE_UNUSED = "end_date"
CONF_BADGE_LABELS_UNUSED = "badge_labels"
CONF_BADGE_MAINTENANCE_RULES_UNUSED = "maintenance_rules"
CONF_BADGE_NAME_UNUSED = "badge_name"
CONF_BADGE_OCCASION_DATE_UNUSED = "occasion_date"
CONF_BADGE_OCCASION_TYPE_UNUSED = "occasion_type"
CONF_BADGE_PERIODIC_RECURRENT_UNUSED = "recurrent"
CONF_BADGE_POINTS_MULTIPLIER_UNUSED = "points_multiplier"
CONF_BADGE_REQUIRED_CHORES_UNUSED = "required_chores"
CONF_BADGE_RESET_GRACE_PERIOD_UNUSED = "reset_grace_period"
CONF_BADGE_RESET_PERIODICALLY_UNUSED = "reset_periodically"
CONF_BADGE_RESET_SCHEDULE_UNUSED = "reset_schedule"
CONF_BADGE_RESET_SCHEDULE_RECURRING_FREQUENCY_UNUSED = "recurring_frequency"
CONF_BADGE_RESET_TYPE_UNUSED = "reset_type"
CONF_BADGE_SPECIAL_OCCASION_RECURRENCY_UNUSED = "recurrent"
CONF_BADGE_START_DATE_UNUSED = "start_date"
CONF_BADGE_THRESHOLD_TYPE_UNUSED = "threshold_type"
CONF_BADGE_THRESHOLD_VALUE_UNUSED = "threshold_value"
CONF_BADGE_TYPE_UNUSED = "badge_type"

# Badge types
BADGE_TYPE_ACHIEVEMENT_LINKED = "achievement_linked"
BADGE_TYPE_CHALLENGE_LINKED = "challenge_linked"
BADGE_TYPE_CUMULATIVE = "cumulative"
BADGE_TYPE_DAILY = "daily"
BADGE_TYPE_PERIODIC = "periodic"
BADGE_TYPE_SPECIAL_OCCASION = "special_occasion"

# Reward configuration keys
CONF_REWARD_COST = "reward_cost"
CONF_REWARD_DESCRIPTION = "reward_description"
CONF_REWARD_LABELS = "reward_labels"
CONF_REWARD_NAME = "reward_name"

# Bonus configuration keys
CONF_BONUS_DESCRIPTION = "bonus_description"
CONF_BONUS_LABELS = "bonus_labels"
CONF_BONUS_NAME = "bonus_name"
CONF_BONUS_POINTS = "bonus_points"

# Penalty configuration keys
CONF_PENALTY_DESCRIPTION = "penalty_description"
CONF_PENALTY_LABELS = "penalty_labels"
CONF_PENALTY_NAME = "penalty_name"
CONF_PENALTY_POINTS = "penalty_points"

# Achievement configuration keys
CONF_ACHIEVEMENT_ASSIGNED_KIDS = "assigned_kids"
CONF_ACHIEVEMENT_CRITERIA = "criteria"
CONF_ACHIEVEMENT_LABELS = "achievement_labels"
CONF_ACHIEVEMENT_REWARD_POINTS = "reward_points"
CONF_ACHIEVEMENT_SELECTED_CHORE_ID = "selected_chore_id"
CONF_ACHIEVEMENT_TARGET_VALUE = "target_value"
CONF_ACHIEVEMENT_TYPE = "type"

# Achievement types
ACHIEVEMENT_TYPE_DAILY_MIN = "daily_minimum"
ACHIEVEMENT_TYPE_STREAK = "chore_streak"
ACHIEVEMENT_TYPE_TOTAL = "chore_total"

# Challenge configuration keys
CONF_CHALLENGE_ASSIGNED_KIDS = "assigned_kids"
CONF_CHALLENGE_CRITERIA = "criteria"
CONF_CHALLENGE_END_DATE = "end_date"
CONF_CHALLENGE_LABELS = "challenge_labels"
CONF_CHALLENGE_REWARD_POINTS = "reward_points"
CONF_CHALLENGE_SELECTED_CHORE_ID = "selected_chore_id"
CONF_CHALLENGE_START_DATE = "start_date"
CONF_CHALLENGE_TARGET_VALUE = "target_value"
CONF_CHALLENGE_TYPE = "type"

# Challenge types
CHALLENGE_TYPE_DAILY_MIN = "daily_minimum"
CHALLENGE_TYPE_TOTAL_WITHIN_WINDOW = "total_within_window"

# General Options
CONF_POINTS_ADJUST_VALUES = "points_adjust_values"
CONF_UPDATE_INTERVAL = "update_interval"


# ------------------------------------------------------------------------------------------------
# Data Keys
# ------------------------------------------------------------------------------------------------

# GLOBAL
DATA_ACHIEVEMENTS = "achievements"
DATA_ASSIGNED_KIDS = "assigned_kids"
DATA_BADGES = "badges"
DATA_BONUSES = "bonuses"
DATA_CHALLENGES = "challenges"
DATA_CHORES = "chores"
DATA_COORDINATOR = "coordinator"
DATA_GLOBAL_STATE_SUFFIX = "_global_state"
DATA_INTERNAL_ID = "internal_id"
DATA_KIDS = "kids"
DATA_LAST_CHANGE = "last_change"
DATA_NAME = "name"
DATA_PARENTS = "parents"
DATA_PENALTIES = "penalties"
DATA_PROGRESS = "progress"
DATA_REWARDS = "rewards"

# KIDS
DATA_KID_APPROVED_CHORES = "approved_chores"
DATA_KID_BADGE_GRACE_EXPIRY_UNUSED = "badge_grace_expiry"
DATA_KID_BADGE_EARNED_ID_UNUSED = "badge_id"
DATA_KID_BADGES_EARNED_NAME = "badge_name"
DATA_KID_BADGES_EARNED_LAST_AWARDED = "last_awarded_date"
DATA_KID_BADGES_EARNED_AWARD_COUNT = "award_count"
DATA_KID_BADGES_LEGACY = "badges"
DATA_KID_BADGES_EARNED = "badges_earned"
DATA_KID_BADGES_EARNED_PERIODS = "periods"
DATA_KID_BADGES_EARNED_PERIODS_DAILY = "daily"
DATA_KID_BADGES_EARNED_PERIODS_WEEKLY = "weekly"
DATA_KID_BADGES_EARNED_PERIODS_MONTHLY = "monthly"
DATA_KID_BADGES_EARNED_PERIODS_YEARLY = "yearly"


# Badge Progress Data Structure
DATA_KID_BADGE_PROGRESS = "badge_progress"

# Common Badge Progress Fields
DATA_KID_BADGE_PROGRESS_APPROVED_COUNT = "approved_count"
DATA_KID_BADGE_PROGRESS_CHORES_COMPLETED = "chores_completed"
DATA_KID_BADGE_PROGRESS_CHORES_CYCLE_COUNT = "chores_cycle_count"
DATA_KID_BADGE_PROGRESS_CHORES_TODAY = "chores_today"
DATA_KID_BADGE_PROGRESS_CRITERIA_MET = "criteria_met"
DATA_KID_BADGE_PROGRESS_CYCLE_COUNT = "cycle_count"
DATA_KID_BADGE_PROGRESS_DAYS_COMPLETED = "days_completed"
DATA_KID_BADGE_PROGRESS_DAYS_CYCLE_COUNT = "days_cycle_count"
DATA_KID_BADGE_PROGRESS_END_DATE = "end_date"
DATA_KID_BADGE_PROGRESS_LAST_AWARDED = "last_awarded"
DATA_KID_BADGE_PROGRESS_LAST_UPDATE_DAY = "last_update_day"
DATA_KID_BADGE_PROGRESS_NAME = "name"
DATA_KID_BADGE_PROGRESS_OVERALL_PROGRESS = "overall_progress"
DATA_KID_BADGE_PROGRESS_PENALTY_APPLIED = "penalty_applied"
DATA_KID_BADGE_PROGRESS_POINTS_CYCLE_COUNT = "points_cycle_count"
DATA_KID_BADGE_PROGRESS_POINTS_TODAY = "points_today"
DATA_KID_BADGE_PROGRESS_RECURRING_FREQUENCY = "recurring_frequency"
DATA_KID_BADGE_PROGRESS_START_DATE = "start_date"
DATA_KID_BADGE_PROGRESS_STATUS = "status"
DATA_KID_BADGE_PROGRESS_TARGET_THRESHOLD_VALUE = "threshold_value"
DATA_KID_BADGE_PROGRESS_TARGET_TYPE = "target_type"
DATA_KID_BADGE_PROGRESS_TODAY_COMPLETED = "today_completed"
DATA_KID_BADGE_PROGRESS_TOTAL_COUNT = "total_count"
DATA_KID_BADGE_PROGRESS_TRACKED_CHORES = "tracked_chores"
DATA_KID_BADGE_PROGRESS_TYPE = "badge_type"

# For Points Target Type
DATA_KID_BADGE_PROGRESS_POINTS_CYCLE_COUNT = "points_cycle_count"

# For Chore Count Target Type
DATA_KID_BADGE_PROGRESS_CHORES_CYCLE_COUNT = "chores_cycle_count"

# For All Required Chores Target Type
DATA_KID_BADGE_PROGRESS_DAYS_CYCLE_COUNT = "days_cycle_count"

# Shared fields for tracking across target types
DATA_KID_BADGE_PROGRESS_TRACKED_CHORES = "tracked_chores"
DATA_KID_BADGE_PROGRESS_CHORES_COMPLETED = "chores_completed"
DATA_KID_BADGE_PROGRESS_DAYS_COMPLETED = "days_completed"

DATA_KID_BONUS_APPLIES = "bonus_applies"
DATA_KID_CHORE_APPROVALS_LEGACY = "chore_approvals"
DATA_KID_CHORE_CLAIMS_LEGACY = "chore_claims"
DATA_KID_CHORE_STREAKS_LEGACY = "chore_streaks"
DATA_KID_CLAIMED_CHORES = "claimed_chores"
DATA_KID_COMPLETED_CHORES_MONTHLY_LEGACY = "completed_chores_monthly"
DATA_KID_COMPLETED_CHORES_TOTAL_LEGACY = "completed_chores_total"
DATA_KID_COMPLETED_CHORES_TODAY_LEGACY = "completed_chores_today"
DATA_KID_COMPLETED_CHORES_WEEKLY_LEGACY = "completed_chores_weekly"
DATA_KID_COMPLETED_CHORES_YEARLY_LEGACY = "completed_chores_yearly"

# Kid Chore Data Structure Constants
DATA_KID_CHORE_DATA = "chore_data"
DATA_KID_CHORE_DATA_STATE = "state"
DATA_KID_CHORE_DATA_NAME = "name"
DATA_KID_CHORE_DATA_DUE_DATE = "due_date"
DATA_KID_CHORE_DATA_LAST_APPROVED = "last_approved"
DATA_KID_CHORE_DATA_LAST_CLAIMED = "last_claimed"
DATA_KID_CHORE_DATA_LAST_DISAPPROVED = "last_disapproved"
DATA_KID_CHORE_DATA_LAST_OVERDUE = "last_overdue"
DATA_KID_CHORE_DATA_LAST_LONGEST_STREAK_ALL_TIME = "last_longest_streak_all_time"
DATA_KID_CHORE_DATA_TOTAL_COUNT = "total_count"
DATA_KID_CHORE_DATA_TOTAL_POINTS = "total_points"
DATA_KID_CHORE_DATA_PERIODS = "periods"
DATA_KID_CHORE_DATA_PERIODS_ALL_TIME = "all_time"
DATA_KID_CHORE_DATA_PERIODS_DAILY = "daily"
DATA_KID_CHORE_DATA_PERIODS_WEEKLY = "weekly"
DATA_KID_CHORE_DATA_PERIODS_MONTHLY = "monthly"
DATA_KID_CHORE_DATA_PERIODS_YEARLY = "yearly"
DATA_KID_CHORE_DATA_PERIOD_APPROVED = "approved"
DATA_KID_CHORE_DATA_PERIOD_CLAIMED = "claimed"
DATA_KID_CHORE_DATA_PERIOD_DISAPPROVED = "disapproved"
DATA_KID_CHORE_DATA_PERIOD_LONGEST_STREAK = "longest_streak"
DATA_KID_CHORE_DATA_PERIOD_OVERDUE = "overdue"
DATA_KID_CHORE_DATA_PERIOD_POINTS = "points"
DATA_KID_CHORE_DATA_BADGE_REFS = "badge_refs"

# Chore Stats Keys
DATA_KID_CHORE_STATS = "chore_stats"

# --- Approval Counts = Completion Counts ---
DATA_KID_CHORE_STATS_APPROVED_TODAY = "approved_today"
DATA_KID_CHORE_STATS_APPROVED_WEEK = "approved_week"
DATA_KID_CHORE_STATS_APPROVED_MONTH = "approved_month"
DATA_KID_CHORE_STATS_APPROVED_YEAR = "approved_year"
DATA_KID_CHORE_STATS_APPROVED_ALL_TIME = "approved_all_time"

# --- Most Completed Chore ---
DATA_KID_CHORE_STATS_MOST_COMPLETED_CHORE = "most_completed_chore"
DATA_KID_CHORE_STATS_MOST_COMPLETED_CHORE_WEEK = "most_completed_chore_week"
DATA_KID_CHORE_STATS_MOST_COMPLETED_CHORE_MONTH = "most_completed_chore_month"
DATA_KID_CHORE_STATS_MOST_COMPLETED_CHORE_YEAR = "most_completed_chore_year"

# --- Last Completion Date ---
DATA_KID_CHORE_DATA_APPROVED_LAST_DATE = "approved_last_date"

# --- Total Points from Chores ---
DATA_KID_CHORE_STATS_TOTAL_POINTS_FROM_CHORES_TODAY = "total_points_from_chores_today"
DATA_KID_CHORE_STATS_TOTAL_POINTS_FROM_CHORES_WEEK = "total_points_from_chores_week"
DATA_KID_CHORE_STATS_TOTAL_POINTS_FROM_CHORES_MONTH = "total_points_from_chores_month"
DATA_KID_CHORE_STATS_TOTAL_POINTS_FROM_CHORES_YEAR = "total_points_from_chores_year"
DATA_KID_CHORE_STATS_TOTAL_POINTS_FROM_CHORES_ALL_TIME = (
    "total_points_from_chores_all_time"
)

# --- Overdue Counts ---
DATA_KID_CHORE_STATS_OVERDUE_TODAY = "overdue_today"
DATA_KID_CHORE_STATS_OVERDUE_WEEK = "overdue_week"
DATA_KID_CHORE_STATS_OVERDUE_MONTH = "overdue_month"
DATA_KID_CHORE_STATS_OVERDUE_YEAR = "overdue_year"
DATA_KID_CHORE_STATS_OVERDUE_ALL_TIME = "overdue_count_all_time"

# --- Claimed Counts ---
DATA_KID_CHORE_STATS_CLAIMED_TODAY = "claimed_today"
DATA_KID_CHORE_STATS_CLAIMED_WEEK = "claimed_week"
DATA_KID_CHORE_STATS_CLAIMED_MONTH = "claimed_month"
DATA_KID_CHORE_STATS_CLAIMED_YEAR = "claimed_year"
DATA_KID_CHORE_STATS_CLAIMED_ALL_TIME = "claimed_all_time"

# --- Claimed but Not Approved ---
DATA_KID_CHORE_STATS_DISAPPROVED_TODAY = "disapproved_today"
DATA_KID_CHORE_STATS_DISAPPROVED_WEEK = "disapproved_week"
DATA_KID_CHORE_STATS_DISAPPROVED_MONTH = "disapproved_month"
DATA_KID_CHORE_STATS_DISAPPROVED_YEAR = "disapproved_year"
DATA_KID_CHORE_STATS_DISAPPROVED_ALL_TIME = "disapproved_all_time"

# --- Chores Current Stats ---
DATA_KID_CHORE_STATS_CURRENT_DUE_TODAY = "current_due_today"
DATA_KID_CHORE_STATS_CURRENT_OVERDUE = "current_overdue"
DATA_KID_CHORE_STATS_CURRENT_CLAIMED = "current_claimed"
DATA_KID_CHORE_STATS_CURRENT_APPROVED = "current_approved"

# --- Longest Streaks ---
DATA_KID_CHORE_STATS_LONGEST_STREAK_WEEK = "longest_streak_week"
DATA_KID_CHORE_STATS_LONGEST_STREAK_MONTH = "longest_streak_month"
DATA_KID_CHORE_STATS_LONGEST_STREAK_YEAR = "longest_streak_year"
DATA_KID_CHORE_STATS_LONGEST_STREAK_ALL_TIME = "longest_streak_all_time"

# --- Average Chores Per Day ---
DATA_KID_CHORE_STATS_AVG_PER_DAY_MONTH = "avg_per_day_month"
DATA_KID_CHORE_STATS_AVG_PER_DAY_WEEK = "avg_per_day_week"


# --- Badge Progress Tracking ---
DATA_KID_CUMULATIVE_BADGE_PROGRESS = "cumulative_badge_progress"

# Current badge (in effect)
DATA_KID_CUMULATIVE_BADGE_PROGRESS_CURRENT_BADGE_ID = "current_badge_id"
DATA_KID_CUMULATIVE_BADGE_PROGRESS_CURRENT_BADGE_NAME = "current_badge_name"
DATA_KID_CUMULATIVE_BADGE_PROGRESS_CURRENT_THRESHOLD = "current_threshold"

# Highest earned badge (lifetime)
DATA_KID_CUMULATIVE_BADGE_PROGRESS_HIGHEST_EARNED_BADGE_ID = "highest_earned_badge_id"
DATA_KID_CUMULATIVE_BADGE_PROGRESS_HIGHEST_EARNED_BADGE_NAME = (
    "highest_earned_badge_name"
)
DATA_KID_CUMULATIVE_BADGE_PROGRESS_HIGHEST_EARNED_THRESHOLD = "highest_earned_threshold"

# Next higher badge
DATA_KID_CUMULATIVE_BADGE_PROGRESS_NEXT_HIGHER_BADGE_ID = "next_higher_badge_id"
DATA_KID_CUMULATIVE_BADGE_PROGRESS_NEXT_HIGHER_BADGE_NAME = "next_higher_badge_name"
DATA_KID_CUMULATIVE_BADGE_PROGRESS_NEXT_HIGHER_THRESHOLD = "next_higher_threshold"
DATA_KID_CUMULATIVE_BADGE_PROGRESS_NEXT_HIGHER_POINTS_NEEDED = (
    "next_higher_points_needed"
)

# Next lower badge
DATA_KID_CUMULATIVE_BADGE_PROGRESS_NEXT_LOWER_BADGE_ID = "next_lower_badge_id"
DATA_KID_CUMULATIVE_BADGE_PROGRESS_NEXT_LOWER_BADGE_NAME = "next_lower_badge_name"
DATA_KID_CUMULATIVE_BADGE_PROGRESS_NEXT_LOWER_THRESHOLD = "next_lower_threshold"

# Maintenance tracking
DATA_KID_CUMULATIVE_BADGE_PROGRESS_BASELINE = "baseline"
DATA_KID_CUMULATIVE_BADGE_PROGRESS_CYCLE_POINTS = "cycle_points"
DATA_KID_CUMULATIVE_BADGE_PROGRESS_STATUS = "status"
DATA_KID_CUMULATIVE_BADGE_PROGRESS_MAINTENANCE_END_DATE = "maintenance_end_date"
DATA_KID_CUMULATIVE_BADGE_PROGRESS_MAINTENANCE_GRACE_END_DATE = (
    "maintenance_grace_end_date"
)
DATA_KID_CURRENT_STREAK = "current_streak"
DATA_KID_ENABLE_NOTIFICATIONS = "enable_notifications"
DATA_KID_HA_USER_ID = "ha_user_id"
DATA_KID_ID = "kid_id"
DATA_KID_INTERNAL_ID = "internal_id"
DATA_KID_LAST_BADGE_RESET = "last_badge_reset"
DATA_KID_LAST_CHORE_DATE = "last_chore_date"
DATA_KID_LAST_STREAK_DATE = "last_date"
DATA_KID_MAX_POINTS_EVER = "max_points_ever"
DATA_KID_MAX_STREAK = "max_streak"
DATA_KID_MOBILE_NOTIFY_SERVICE = "mobile_notify_service"
DATA_KID_NAME = "name"
DATA_KID_OVERDUE_CHORES = "overdue_chores"
DATA_KID_OVERDUE_NOTIFICATIONS = "overdue_notifications"
DATA_KID_OVERALL_CHORE_STREAK = "overall_chore_streak"
DATA_KID_PENALTY_APPLIES = "penalty_applies"
DATA_KID_PENDING_REWARDS = "pending_rewards"
DATA_KID_PERIODIC_BADGE_POINTS_UNUSED = "periodic_badge_points"
DATA_KID_PERIODIC_BADGE_PROGRESS_UNUSED = "periodic_badge_progress"
DATA_KID_PERIODIC_BADGE_SUCCESS_UNUSED = "periodic_badge_success"
DATA_KID_POINTS = "points"
DATA_KID_POINTS_EARNED_MONTHLY_LEGACY = "points_earned_monthly"
DATA_KID_POINTS_EARNED_TODAY_LEGACY = "points_earned_today"
DATA_KID_POINTS_EARNED_WEEKLY_LEGACY = "points_earned_weekly"
DATA_KID_POINTS_EARNED_YEARLY_LEGACY = "points_earned_yearly"
DATA_KID_POINTS_MULTIPLIER = "points_multiplier"
DATA_KID_PRE_RESET_BADGE_UNUSED = "pre_reset_badge"
DATA_KID_REDEEMED_REWARDS = "redeemed_rewards"
DATA_KID_REWARD_APPROVALS = "reward_approvals"
DATA_KID_REWARD_CLAIMS = "reward_claims"
DATA_KID_TODAY_CHORE_APPROVALS = "today_chore_approvals"
DATA_KID_USE_PERSISTENT_NOTIFICATIONS = "use_persistent_notifications"

# ——————————————————————————————————————————————
# Kid Point History Data Structure
# ——————————————————————————————————————————————

# Top‑level key for storing period‑by‑period point history
DATA_KID_POINT_DATA = "point_data"

# Sub‑section containing all period buckets
DATA_KID_POINT_DATA_PERIODS = "periods"

# Individual period buckets
DATA_KID_POINT_DATA_PERIODS_DAILY = "daily"
DATA_KID_POINT_DATA_PERIODS_WEEKLY = "weekly"
DATA_KID_POINT_DATA_PERIODS_MONTHLY = "monthly"
DATA_KID_POINT_DATA_PERIODS_YEARLY = "yearly"

# Within each period entry:
#   – points_total: net delta for that period
#   – by_source: breakdown of delta by source type
DATA_KID_POINT_DATA_PERIOD_POINTS_TOTAL = "points_total"
DATA_KID_POINT_DATA_PERIOD_BY_SOURCE = "by_source"

# Point Sources
# --- Point Source Types (all plural) ---
POINTS_SOURCE_CHORES = "chores"
POINTS_SOURCE_BONUSES = "bonuses"
POINTS_SOURCE_PENALTIES = "penalties"
POINTS_SOURCE_BADGES = "badges"
POINTS_SOURCE_ACHIEVEMENTS = "achievements"
POINTS_SOURCE_CHALLENGES = "challenges"
POINTS_SOURCE_REWARDS = "rewards"
POINTS_SOURCE_MANUAL = "manual"
POINTS_SOURCE_OTHER = "other"

# Example list of valid sources for UI/enumeration:
POINTS_SOURCE_OPTIONS = [
    {CONF_VALUE: POINTS_SOURCE_CHORES, CONF_LABEL: "Chores"},
    {CONF_VALUE: POINTS_SOURCE_BONUSES, CONF_LABEL: "Bonuses"},
    {CONF_VALUE: POINTS_SOURCE_PENALTIES, CONF_LABEL: "Penalties"},
    {CONF_VALUE: POINTS_SOURCE_BADGES, CONF_LABEL: "Badges"},
    {CONF_VALUE: POINTS_SOURCE_ACHIEVEMENTS, CONF_LABEL: "Achievements"},
    {CONF_VALUE: POINTS_SOURCE_CHALLENGES, CONF_LABEL: "Challenges"},
    {CONF_VALUE: POINTS_SOURCE_REWARDS, CONF_LABEL: "Rewards"},
    {CONF_VALUE: POINTS_SOURCE_OTHER, CONF_LABEL: "Other"},
]

# --- Kid Point Stats (modeled after chore stats) ---
DATA_KID_POINT_STATS = "point_stats"

# --- Per-period totals ---
DATA_KID_POINT_STATS_EARNED_TODAY = "points_earned_today"
DATA_KID_POINT_STATS_EARNED_WEEK = "points_earned_week"
DATA_KID_POINT_STATS_EARNED_MONTH = "points_earned_month"
DATA_KID_POINT_STATS_EARNED_YEAR = "points_earned_year"
DATA_KID_POINT_STATS_EARNED_ALL_TIME = "points_earned_all_time"

# --- Per-period by-source breakdowns ---
DATA_KID_POINT_STATS_BY_SOURCE_TODAY = "points_by_source_today"
DATA_KID_POINT_STATS_BY_SOURCE_WEEK = "points_by_source_week"
DATA_KID_POINT_STATS_BY_SOURCE_MONTH = "points_by_source_month"
DATA_KID_POINT_STATS_BY_SOURCE_YEAR = "points_by_source_year"
DATA_KID_POINT_STATS_BY_SOURCE_ALL_TIME = "points_by_source_all_time"

# --- Per-period spent (negative deltas) ---
DATA_KID_POINT_STATS_SPENT_TODAY = "points_spent_today"
DATA_KID_POINT_STATS_SPENT_WEEK = "points_spent_week"
DATA_KID_POINT_STATS_SPENT_MONTH = "points_spent_month"
DATA_KID_POINT_STATS_SPENT_YEAR = "points_spent_year"
DATA_KID_POINT_STATS_SPENT_ALL_TIME = "points_spent_all_time"

# --- Per-period net (earned - spent) ---
DATA_KID_POINT_STATS_NET_TODAY = "points_net_today"
DATA_KID_POINT_STATS_NET_WEEK = "points_net_week"
DATA_KID_POINT_STATS_NET_MONTH = "points_net_month"
DATA_KID_POINT_STATS_NET_YEAR = "points_net_year"
DATA_KID_POINT_STATS_NET_ALL_TIME = "points_net_all_time"

# --- Streaks (days with positive points) ---
DATA_KID_POINT_STATS_EARNING_STREAK_CURRENT = "points_earning_streak_current"
DATA_KID_POINT_STATS_EARNING_STREAK_LONGEST = "points_earning_streak_longest"

# --- Averages ---
DATA_KID_POINT_STATS_AVG_PER_DAY_WEEK = "avg_points_per_day_week"
DATA_KID_POINT_STATS_AVG_PER_DAY_MONTH = "avg_points_per_day_month"
DATA_KID_POINT_STATS_AVG_PER_CHORE = "avg_points_per_chore"

# --- Highest balance ever (highest balance) ---
DATA_KID_POINT_STATS_HIGHEST_BALANCE = "highest_balance"

# --- All time point stats ---
DATA_KID_POINTS_EARNED_ALL_TIME = "points_earned_all_time"
DATA_KID_POINTS_SPENT_ALL_TIME = "points_spent_all_time"
DATA_KID_POINTS_NET_ALL_TIME = "points_net_all_time"
DATA_KID_POINTS_BY_SOURCE_ALL_TIME = "points_by_source_all_time"

# PARENTS
DATA_PARENT_ASSOCIATED_KIDS = "associated_kids"
DATA_PARENT_ENABLE_NOTIFICATIONS = "enable_notifications"
DATA_PARENT_HA_USER_ID = "ha_user_id"
DATA_PARENT_INTERNAL_ID = "internal_id"
DATA_PARENT_MOBILE_NOTIFY_SERVICE = "mobile_notify_service"
DATA_PARENT_NAME = "name"
DATA_PARENT_USE_PERSISTENT_NOTIFICATIONS = "use_persistent_notifications"

# CHORES
DATA_CHORE_ALLOW_MULTIPLE_CLAIMS_PER_DAY = "allow_multiple_claims_per_day"
DATA_CHORE_APPLICABLE_DAYS = "applicable_days"
DATA_CHORE_ASSIGNED_KIDS = "assigned_kids"
DATA_CHORE_CUSTOM_INTERVAL = "custom_interval"
DATA_CHORE_CUSTOM_INTERVAL_UNIT = "custom_interval_unit"
DATA_CHORE_DEFAULT_POINTS = "default_points"
DATA_CHORE_DESCRIPTION = "description"
DATA_CHORE_DUE_DATE = "due_date"
DATA_CHORE_ICON = "icon"
DATA_CHORE_ID = "chore_id"
DATA_CHORE_INTERNAL_ID = "internal_id"
DATA_CHORE_LABELS = "chore_labels"
DATA_CHORE_LAST_CLAIMED = "last_claimed"
DATA_CHORE_LAST_COMPLETED = "last_completed"
DATA_CHORE_NAME = "name"
DATA_CHORE_NOTIFY_ON_APPROVAL = "notify_on_approval"
DATA_CHORE_NOTIFY_ON_CLAIM = "notify_on_claim"
DATA_CHORE_NOTIFY_ON_DISAPPROVAL = "notify_on_disapproval"
DATA_CHORE_PARTIAL_ALLOWED = "partial_allowed"
DATA_CHORE_RECURRING_FREQUENCY = "recurring_frequency"
DATA_CHORE_SHARED_CHORE = "shared_chore"
DATA_CHORE_STATE = "state"
DATA_CHORE_TIMESTAMP = "timestamp"

# BADGES
DATA_BADGE_ASSIGNED_TO = "assigned_to"
DATA_BADGE_ASSOCIATED_ACHIEVEMENT = "associated_achievement"
DATA_BADGE_ASSOCIATED_CHALLENGE = "associated_challenge"
DATA_BADGE_AWARDS = "awards"
DATA_BADGE_AWARDS_AWARD_ITEMS = "award_items"
DATA_BADGE_AWARDS_AWARD_POINTS = "award_points"
DATA_BADGE_AWARDS_AWARD_POINTS_REWARD = "award_points_reward"
DATA_BADGE_AWARDS_AWARD_REWARD = "award_reward"
DATA_BADGE_AWARDS_POINT_MULTIPLIER = "points_multiplier"
DATA_BADGE_DESCRIPTION = "description"
DATA_BADGE_EARNED_BY = "earned_by"
DATA_BADGE_ICON = "icon"
DATA_BADGE_ID = "badge_id"
DATA_BADGE_INTERNAL_ID = "internal_id"
DATA_BADGE_LABELS = "badge_labels"
DATA_BADGE_MAINTENANCE_RULES = "maintenance_rules"
DATA_BADGE_NAME = "name"
DATA_BADGE_OCCASION_TYPE = "occasion_type"
DATA_BADGE_RESET_SCHEDULE = "reset_schedule"
DATA_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL = "custom_interval"
DATA_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL_UNIT = "custom_interval_unit"
DATA_BADGE_RESET_SCHEDULE_END_DATE = "end_date"
DATA_BADGE_RESET_SCHEDULE_GRACE_PERIOD_DAYS = "grace_period_days"
DATA_BADGE_RESET_SCHEDULE_GRACE_PERIOD_DAYS = "grace_period_days"
DATA_BADGE_RESET_SCHEDULE_RECURRING_FREQUENCY = "recurring_frequency"
DATA_BADGE_RESET_SCHEDULE_START_DATE = "start_date"
DATA_BADGE_SPECIAL_OCCASION_TYPE = "occasion_type"
DATA_BADGE_TARGET = "target"
DATA_BADGE_TARGET_THRESHOLD_VALUE = "threshold_value"
DATA_BADGE_TARGET_TYPE = "target_type"
DATA_BADGE_TRACKED_CHORES = "tracked_chores"
DATA_BADGE_TRACKED_CHORES_SELECTED_CHORES = "selected_chores"
DATA_BADGE_TYPE = "badge_type"

# BADGES - DEPRECATED but used in migration
DATA_BADGE_THRESHOLD_TYPE_LEGACY = "threshold_type"  # USED IN MIGRATION TO 4.0
DATA_BADGE_THRESHOLD_VALUE_LEGACY = "threshold_value"  # USED IN  MIGRATION TO 4.0
DATA_BADGE_CHORE_COUNT_TYPE_LEGACY = "chore_count_type"  # USED IN  MIGRATION TO 4.0
DATA_BADGE_POINTS_MULTIPLIER_LEGACY = "points_multiplier"  # USED IN  MIGRATION TO 4.0


# BADGES - DEPRECATED Constants
DATA_BADGE_REQUIRED_CHORES_LEGACY = "required_chores"  # NEEDS TO BE REMOVED AFTER FIX
DATA_BADGE_RESET_GRACE_PERIOD_UNUSED = (
    "reset_grace_period"  # NEEDS TO BE REMOVED AFTER FIX
)
DATA_BADGE_RESET_PERIODICALLY_UNUSED = (
    "reset_periodically"  # NEEDS TO BE REMOVED AFTER FIX
)
DATA_BADGE_RESET_TYPE_UNUSED = "reset_type"  # NEEDS TO BE REMOVED AFTER FIX
# DATA_BADGE_ASSIGNED_KIDS = "assigned_kids"
# DATA_BADGE_CRITERIA_MODE = "criteria_mode"
# DATA_BADGE_CRITERIA_MODE_CHORES = "chores"
# DATA_BADGE_CRITERIA_MODE_POINTS = "points"
# DATA_BADGE_CUSTOM_RESET_DATE = "custom_reset_date"
DATA_BADGE_DAILY_THRESHOLD_UNUSED = "daily_threshold"
# DATA_BADGE_DAILY_THRESHOLD_TYPE = "threshold_type"
DATA_BADGE_END_DATE_UNUSED = "end_date"
# DATA_BADGE_LAST_RESET = "last_reset"
# DATA_BADGE_OCCASION_DATE = "occasion_date"
# DATA_BADGE_ONE_TIME_REWARD = "one_time_reward"
DATA_BADGE_PERIODIC_RECURRENT_UNUSED = "recurrent"
DATA_BADGE_SPECIAL_OCCASION_DATE_UNUSED = "occasion_date"
DATA_BADGE_SPECIAL_OCCASION_LAST_AWARDED_LEGACY = "last_awarded"
DATA_BADGE_SPECIAL_OCCASION_RECURRENCY_UNUSED = "recurrent"
DATA_BADGE_START_DATE_UNUSED = "start_date"
# DATA_BADGE_RESET_CRITERIA = "reset_criteria"
# DATA_BADGE_REWARD = "reward"
# DATA_BADGE_TRIGGER_INFO = "trigger_info"
# DATA_BADGE_TYPE_TOTAL = "total"


# REWARDS
DATA_REWARD_COST = "cost"
DATA_REWARD_DESCRIPTION = "description"
DATA_REWARD_ICON = "icon"
DATA_REWARD_ID = "reward_id"
DATA_REWARD_INTERNAL_ID = "internal_id"
DATA_REWARD_LABELS = "reward_labels"
DATA_REWARD_NAME = "name"
DATA_REWARD_NOTIFICATION_ID = "notification_id"
DATA_REWARD_TIMESTAMP = "timestamp"

# BONUSES
DATA_BONUS_DESCRIPTION = "description"
DATA_BONUS_ICON = "icon"
DATA_BONUS_ID = "bonus_id"
DATA_BONUS_INTERNAL_ID = "internal_id"
DATA_BONUS_LABELS = "bonus_labels"
DATA_BONUS_NAME = "name"
DATA_BONUS_POINTS = "points"

# PENALTIES
DATA_PENALTY_DESCRIPTION = "description"
DATA_PENALTY_ICON = "icon"
DATA_PENALTY_ID = "penalty_id"
DATA_PENALTY_INTERNAL_ID = "internal_id"
DATA_PENALTY_LABELS = "penalty_labels"
DATA_PENALTY_NAME = "name"
DATA_PENALTY_POINTS = "points"

# ACHIEVEMENTS
DATA_ACHIEVEMENT_ASSIGNED_KIDS = "assigned_kids"
DATA_ACHIEVEMENT_AWARDED = "awarded"
DATA_ACHIEVEMENT_BASELINE = "baseline"
DATA_ACHIEVEMENT_CRITERIA = "criteria"
DATA_ACHIEVEMENT_CURRENT_STREAK = "current_streak"
DATA_ACHIEVEMENT_CURRENT_VALUE = "current_value"
DATA_ACHIEVEMENT_DESCRIPTION = "description"
DATA_ACHIEVEMENT_ICON = "icon"
DATA_ACHIEVEMENT_ID = "achievement_id"
DATA_ACHIEVEMENT_INTERNAL_ID = "internal_id"
DATA_ACHIEVEMENT_LABELS = "achievement_labels"
DATA_ACHIEVEMENT_LAST_AWARDED_DATE = "last_awarded_date"
DATA_ACHIEVEMENT_NAME = "name"
DATA_ACHIEVEMENT_PROGRESS = "progress"
DATA_ACHIEVEMENT_PROGRESS_SUFFIX = "_achievement_progress"
DATA_ACHIEVEMENT_REWARD_POINTS = "reward_points"
DATA_ACHIEVEMENT_SELECTED_CHORE_ID = "selected_chore_id"
DATA_ACHIEVEMENT_TARGET_VALUE = "target_value"
DATA_ACHIEVEMENT_TYPE = "type"

# CHALLENGES
DATA_CHALLENGE_ASSIGNED_KIDS = "assigned_kids"
DATA_CHALLENGE_AWARDED = "awarded"
DATA_CHALLENGE_COUNT = "count"
DATA_CHALLENGE_CRITERIA = "criteria"
DATA_CHALLENGE_DAILY_COUNTS = "daily_counts"
DATA_CHALLENGE_DESCRIPTION = "description"
DATA_CHALLENGE_END_DATE = "end_date"
DATA_CHALLENGE_ICON = "icon"
DATA_CHALLENGE_ID = "challenge_id"
DATA_CHALLENGE_INTERNAL_ID = "internal_id"
DATA_CHALLENGE_LABELS = "challenge_labels"
DATA_CHALLENGE_NAME = "name"
DATA_CHALLENGE_PROGRESS = "progress"
DATA_CHALLENGE_PROGRESS_SUFFIX = "_challenge_progress"
DATA_CHALLENGE_REQUIRED_DAILY = "required_daily"
DATA_CHALLENGE_REWARD_POINTS = "reward_points"
DATA_CHALLENGE_SELECTED_CHORE_ID = "selected_chore_id"
DATA_CHALLENGE_START_DATE = "start_date"
DATA_CHALLENGE_TARGET_VALUE = "target_value"
DATA_CHALLENGE_TYPE = "type"

# Runtime Data Keys
DATA_PENDING_CHORE_APPROVALS = "pending_chore_approvals"
DATA_PENDING_REWARD_APPROVALS = "pending_reward_approvals"

# ------------------------------------------------------------------------------------------------
# Frequencies
# ------------------------------------------------------------------------------------------------
FREQUENCY_BIWEEKLY = "biweekly"
FREQUENCY_CUSTOM = "custom"
FREQUENCY_CUSTOM_1_MONTH = "custom_1_month"
FREQUENCY_CUSTOM_1_QUARTER = "custom_1_quarter"
FREQUENCY_CUSTOM_1_WEEK = "custom_1_week"
FREQUENCY_CUSTOM_1_YEAR = "custom_1_year"
FREQUENCY_DAILY = "daily"
FREQUENCY_MONTHLY = "monthly"
FREQUENCY_NONE = "none"
FREQUENCY_QUARTERLY = "quarterly"
FREQUENCY_WEEKLY = "weekly"
FREQUENCY_YEARLY = "yearly"

# ------------------------------------------------------------------------------------------------
# Periods
# ------------------------------------------------------------------------------------------------
PERIOD_DAY_END = "day_end"
PERIOD_MONTH_END = "month_end"
PERIOD_QUARTER_END = "quarter_end"
PERIOD_WEEK_END = "week_end"
PERIOD_YEAR_END = "year_end"
PERIOD_ALL_TIME = "all_time"


# ------------------------------------------------------------------------------------------------
# Default Icons
# ------------------------------------------------------------------------------------------------
DEFAULT_ACHIEVEMENTS_ICON = "mdi:trophy-award"
DEFAULT_BADGE_ICON = "mdi:shield-star-outline"
DEFAULT_BONUS_ICON = "mdi:seal"
DEFAULT_CALENDAR_ICON = "mdi:calendar"
DEFAULT_CHALLENGES_ICON = "mdi:trophy"
DEFAULT_CHORE_ICON = "mdi:checkbox-marked-circle-auto-outline"
DEFAULT_CHORE_APPROVE_ICON = "mdi:checkbox-marked-circle-outline"
DEFAULT_CHORE_CLAIM_ICON = "mdi:clipboard-check-outline"
DEFAULT_CHORE_SENSOR_ICON = "mdi:checkbox-blank-circle-outline"
DEFAULT_COMPLETED_CHORES_DAILY_SENSOR_ICON = "mdi:clipboard-check-outline"
DEFAULT_COMPLETED_CHORES_MONTHLY_SENSOR_ICON = "mdi:clipboard-list-outline"
DEFAULT_COMPLETED_CHORES_TOTAL_SENSOR_ICON = "mdi:clipboard-text-clock-outline"
DEFAULT_COMPLETED_CHORES_WEEKLY_SENSOR_ICON = "mdi:clipboard-check-multiple-outline"
DEFAULT_DISAPPROVE_ICON = "mdi:close-circle-outline"
DEFAULT_ICON = "mdi:star-outline"
DEFAULT_PENALTY_ICON = "mdi:alert-outline"
DEFAULT_PENDING_CHORE_APPROVALS_SENSOR_ICON = "mdi:checkbox-blank-badge-outline"
DEFAULT_PENDING_REWARD_APPROVALS_SENSOR_ICON = "mdi:gift-open-outline"
DEFAULT_POINTS_ADJUST_MINUS_ICON = "mdi:minus-circle-outline"
DEFAULT_POINTS_ADJUST_MINUS_MULTIPLE_ICON = "mdi:minus-circle-multiple-outline"
DEFAULT_POINTS_ADJUST_PLUS_ICON = "mdi:plus-circle-outline"
DEFAULT_POINTS_ADJUST_PLUS_MULTIPLE_ICON = "mdi:plus-circle-multiple-outline"
DEFAULT_POINTS_ICON = "mdi:star-outline"
DEFAULT_STREAK_ICON = "mdi:blur-linear"
DEFAULT_REWARD_ICON = "mdi:gift-outline"
DEFAULT_TROPHY_ICON = "mdi:trophy"
DEFAULT_TROPHY_OUTLINE = "mdi:trophy-outline"


# ------------------------------------------------------------------------------------------------
# Default Values
# ------------------------------------------------------------------------------------------------
DEFAULT_ACHIEVEMENT_REWARD_POINTS = 0
DEFAULT_ACHIEVEMENT_TARGET = 1
DEFAULT_APPLICABLE_DAYS = []
DEFAULT_BADGE_AWARD_MODE_UNUSED = "award_none"
DEFAULT_BADGE_AWARD_POINTS = 0
DEFAULT_BADGE_DAILY_THRESHOLD_UNUSED = 5
DEFAULT_BADGE_MAINTENANCE_THRESHOLD = 0  # Added
DEFAULT_BADGE_RESET_GRACE_PERIOD_UNUSED = 0
DEFAULT_BADGE_REWARD_UNUSED = 0
DEFAULT_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL_UNIT = CONF_NONE
DEFAULT_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL = CONF_NONE
DEFAULT_BADGE_RESET_SCHEDULE_END_DATE = CONF_NONE
DEFAULT_BADGE_RESET_SCHEDULE_GRACE_PERIOD_DAYS = 0
DEFAULT_BADGE_RESET_SCHEDULE_START_DATE = CONF_NONE
DEFAULT_BADGE_RESET_SCHEDULE_RECURRING_FREQUENCY = FREQUENCY_NONE
DEFAULT_BADGE_RESET_SCHEDULE = {
    DATA_BADGE_RESET_SCHEDULE_RECURRING_FREQUENCY: DEFAULT_BADGE_RESET_SCHEDULE_RECURRING_FREQUENCY,
    DATA_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL: DEFAULT_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL,
    DATA_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL_UNIT: DEFAULT_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL_UNIT,
    DATA_BADGE_RESET_SCHEDULE_START_DATE: DEFAULT_BADGE_RESET_SCHEDULE_START_DATE,
    DATA_BADGE_RESET_SCHEDULE_END_DATE: DEFAULT_BADGE_RESET_SCHEDULE_END_DATE,
    DATA_BADGE_RESET_SCHEDULE_GRACE_PERIOD_DAYS: DEFAULT_BADGE_RESET_SCHEDULE_GRACE_PERIOD_DAYS,
}
DEFAULT_BADGE_TARGET_TYPE = "points"
DEFAULT_BADGE_TARGET_THRESHOLD_VALUE = 50
DEFAULT_BADGE_TARGET = {
    "type": DEFAULT_BADGE_TARGET_TYPE,
    "value": DEFAULT_BADGE_TARGET_THRESHOLD_VALUE,
}
DEFAULT_BADGE_THRESHOLD_VALUE_LEGACY = 50
DEFAULT_BADGE_THRESHOLD_TYPE_UNUSED = "points"
DEFAULT_BONUS_POINTS = 1
DEFAULT_CALENDAR_SHOW_PERIOD = 90
DEFAULT_CHALLENGE_REWARD_POINTS = 0
DEFAULT_CHALLENGE_TARGET = 1
DEFAULT_CHORES_UNIT = "Chores"
DEFAULT_DAILY_RESET_TIME = {"hour": 0, "minute": 0, "second": 0}
DEFAULT_DUE_TIME = {"hour": 23, "minute": 59, "second": 0}
DEFAULT_HOUR = 0
DEFAULT_KID_POINTS_MULTIPLIER = 1
DEFAULT_MONTHLY_RESET_DAY = 1
DEFAULT_MULTIPLE_CLAIMS_PER_DAY = False
DEFAULT_NOTIFY_DELAY_REMINDER = 24
DEFAULT_NOTIFY_ON_APPROVAL = True
DEFAULT_NOTIFY_ON_CLAIM = True
DEFAULT_NOTIFY_ON_DISAPPROVAL = True
DEFAULT_PARTIAL_ALLOWED = False
DEFAULT_PENALTY_POINTS = 1
DEFAULT_PENDING_CHORES_UNIT = "Pending Chores"
DEFAULT_PENDING_REWARDS_UNIT = "Pending Rewards"
DEFAULT_POINTS = 5
DEFAULT_POINTS_ADJUST_VALUES = [+1, -1, +2, -2, +10, -10]
DEFAULT_POINTS_LABEL = "Points"
DEFAULT_POINTS_MULTIPLIER = 1.0
DEFAULT_REWARD_COST = 10
DEFAULT_REMINDER_DELAY = 30
DEFAULT_WEEKLY_RESET_DAY = 0
DEFAULT_YEAR_END_DAY = 31
DEFAULT_YEAR_END_HOUR = 23
DEFAULT_YEAR_END_MINUTE = 59
DEFAULT_YEAR_END_MONTH = 12
DEFAULT_YEAR_END_SECOND = 0
DEFAULT_ZERO = 0


# ------------------------------------------------------------------------------------------------
# Badge Threshold Types
# ------------------------------------------------------------------------------------------------
# Badge Target Types for all supported badge logic

BADGE_TARGET_THRESHOLD_TYPE_POINTS = "points"
BADGE_TARGET_THRESHOLD_TYPE_POINTS_CHORES = "points_chores"
BADGE_TARGET_THRESHOLD_TYPE_CHORE_COUNT = "chore_count"
BADGE_TARGET_THRESHOLD_TYPE_DAYS_SELECTED_CHORES = "days_all_chores"
BADGE_TARGET_THRESHOLD_TYPE_DAYS_80PCT_CHORES = "days_80pct_chores"
BADGE_TARGET_THRESHOLD_TYPE_DAYS_SELECTED_CHORES_NO_OVERDUE = (
    "days_all_chores_no_overdue"
)
BADGE_TARGET_THRESHOLD_TYPE_DAYS_SELECTED_DUE_CHORES = "days_all_due_chores"
BADGE_TARGET_THRESHOLD_TYPE_DAYS_80PCT_DUE_CHORES = "days_80pct_due_chores"
BADGE_TARGET_THRESHOLD_TYPE_DAYS_SELECTED_DUE_CHORES_NO_OVERDUE = (
    "days_all_due_chores_no_overdue"
)
BADGE_TARGET_THRESHOLD_TYPE_DAYS_MIN_3_CHORES = "days_min_3_chores"
BADGE_TARGET_THRESHOLD_TYPE_DAYS_MIN_5_CHORES = "days_min_5_chores"
BADGE_TARGET_THRESHOLD_TYPE_DAYS_MIN_7_CHORES = "days_min_7_chores"
BADGE_TARGET_THRESHOLD_TYPE_STREAK_SELECTED_CHORES = "streak_all_chores"
BADGE_TARGET_THRESHOLD_TYPE_STREAK_80PCT_CHORES = "streak_80pct_chores"
BADGE_TARGET_THRESHOLD_TYPE_STREAK_SELECTED_CHORES_NO_OVERDUE = (
    "streak_all_chores_no_overdue"
)
BADGE_TARGET_THRESHOLD_TYPE_STREAK_80PCT_DUE_CHORES = "streak_80pct_due_chores"
BADGE_TARGET_THRESHOLD_TYPE_STREAK_SELECTED_DUE_CHORES_NO_OVERDUE = (
    "streak_all_due_chores_no_overdue"
)

# Legacy
BADGE_THRESHOLD_TYPE_CHORE_COUNT = "chore_count"
BADGE_THRESHOLD_TYPE_POINTS = "points"


# ------------------------------------------------------------------------------------------------
# States
# ------------------------------------------------------------------------------------------------

# Chore States
CHORE_STATE_APPROVED = "approved"
CHORE_STATE_APPROVED_IN_PART = "approved_in_part"
CHORE_STATE_CLAIMED = "claimed"
CHORE_STATE_CLAIMED_IN_PART = "claimed_in_part"
CHORE_STATE_INDEPENDENT = "independent"
CHORE_STATE_OVERDUE = "overdue"
CHORE_STATE_PENDING = "pending"
CHORE_STATE_UNKNOWN = "unknown"

# Reward States
REWARD_STATE_APPROVED = "approved"
REWARD_STATE_CLAIMED = "claimed"
REWARD_STATE_NOT_CLAIMED = "not_claimed"

# Badge States
BADGE_STATE_IN_PROGRESS = "in_progress"
BADGE_STATE_EARNED = "earned"
BADGE_STATE_ACTIVE_CYCLE = "active_cycle"
CUMULATIVE_BADGE_STATE_ACTIVE = "active"
CUMULATIVE_BADGE_STATE_GRACE = "grace"
CUMULATIVE_BADGE_STATE_DEMOTED = "demoted"

# ------------------------------------------------------------------------------------------------
# Actions
# ------------------------------------------------------------------------------------------------

# Action titles for notifications
ACTION_TITLE_APPROVE = "Approve"
ACTION_TITLE_DISAPPROVE = "Disapprove"
ACTION_TITLE_REMIND_30 = "Remind in 30 mins"

# Action identifiers
ACTION_APPROVE_CHORE = "APPROVE_CHORE"
ACTION_APPROVE_REWARD = "APPROVE_REWARD"
ACTION_DISAPPROVE_CHORE = "DISAPPROVE_CHORE"
ACTION_DISAPPROVE_REWARD = "DISAPPROVE_REWARD"
ACTION_REMIND_30 = "REMIND_30"


# ------------------------------------------------------------------------------------------------
# Entities Attributes
# ------------------------------------------------------------------------------------------------
ATTR_ACHIEVEMENT_NAME = "achievement_name"
ATTR_ALL_EARNED_BADGES = "all_earned_badges"
ATTR_ALLOW_MULTIPLE_CLAIMS_PER_DAY = "allow_multiple_claims_per_day"
ATTR_APPLICABLE_DAYS = "applicable_days"
ATTR_AWARDED = "awarded"
ATTR_BADGE_AWARDS = "awards"
ATTR_ASSIGNED_KIDS = "assigned_kids"
ATTR_ASSOCIATED_ACHIEVEMENT = "associated_achievement"
ATTR_ASSOCIATED_CHALLENGE = "associated_challenge"
ATTR_ASSOCIATED_CHORE = "associated_chore"
ATTR_AWARD_POINTS = "award_points"
ATTR_AWARD_REWARD = "award_reward"
ATTR_BADGE_AWARD_MODE = "award_mode"
ATTR_BADGE_STATUS = "badge_status"
ATTR_BADGE_TYPE = "badge_type"
ATTR_BONUS_NAME = "bonus_name"
ATTR_BONUS_POINTS = "bonus_points"
ATTR_CHALLENGE_NAME = "challenge_name"
ATTR_CHALLENGE_TYPE = "challenge_type"
ATTR_CHORE_APPROVALS_COUNT = "chore_approvals_count"
ATTR_CHORE_APPROVALS_TODAY = "chore_approvals_today"
ATTR_CHORE_CLAIMS_COUNT = "chore_claims_count"
ATTR_CHORE_CURRENT_STREAK = "chore_current_streak"
ATTR_CHORE_HIGHEST_STREAK = "chore_highest_streak"
ATTR_CHORE_POINTS_EARNED = "chore_points_earned"
ATTR_CHORE_OVERDUE_COUNT = "chore_overdue_count"
ATTR_CHORE_DISAPPROVED_COUNT = "chore_disapproved_count"
ATTR_CHORE_LAST_LONGEST_STREAK_DATE = "chore_last_longest_streak_date"
ATTR_CHORE_APPROVE_BUTTON_ENTITY_ID = "approve_button_eid"
ATTR_CHORE_CLAIM_BUTTON_ENTITY_ID = "claim_button_eid"
ATTR_CHORE_DISAPPROVE_BUTTON_ENTITY_ID = "disapprove_button_eid"
ATTR_CHORE_NAME = "chore_name"
ATTR_CLAIMED_ON = "Claimed on"
ATTR_COST = "cost"
ATTR_CRITERIA = "criteria"
ATTR_BADGE_CUMULATIVE_BASELINE_POINTS = "baseline_points"
ATTR_BADGE_CUMULATIVE_CYCLE_POINTS = "cycle_points"
ATTR_BADGE_CUMULATIVE_GRACE_END_DATE = "maintenance_grace_end_date"
ATTR_BADGE_CUMULATIVE_MAINTENANCE_POINTS_REQUIRED = "maintenance_points_required"
ATTR_BADGE_CUMULATIVE_MAINTENANCE_END_DATE = "maintenance_end_date"
ATTR_BADGE_CUMULATIVE_POINTS_TO_MAINTENANCE = "maintenance_points_remaining"
ATTR_CURRENT_BADGE_ID = "current_badge_id"
ATTR_CURRENT_BADGE_NAME = "current_badge_name"
ATTR_CUSTOM_FREQUENCY_INTERVAL = "custom_frequency_interval"
ATTR_CUSTOM_FREQUENCY_UNIT = "custom_frequency_unit"
ATTR_DAILY_THRESHOLD = "daily_threshold"
ATTR_DEFAULT_POINTS = "default_points"
ATTR_DESCRIPTION = "description"
ATTR_DUE_DATE = "due_date"
ATTR_END_DATE = "end_date"
ATTR_FRIENDLY_NAME = "friendly_name"
ATTR_GLOBAL_STATE = "global_state"
ATTR_HIGHEST_BADGE_THRESHOLD_VALUE = "highest_badge_threshold_value"
ATTR_KID_NAME = "kid_name"
ATTR_LABELS = "labels"
ATTR_LAST_CLAIMED = "last_claimed"
ATTR_LAST_COMPLETED = "last_completed"
ATTR_KIDS_EARNED = "kids_earned"
ATTR_KIDS_ASSIGNED = "kids_assigned"
ATTR_OCCASION_DATE = "occasion_date"
ATTR_OCCASION_TYPE = "occasion_type"
ATTR_PARTIAL_ALLOWED = "partial_allowed"
ATTR_PENALTY_NAME = "penalty_name"
ATTR_PENALTY_POINTS = "penalty_points"
ATTR_PERIODIC_RECURRENT = "recurrent"
ATTR_POINTS_MULTIPLIER = "points_multiplier"
ATTR_POINTS_TO_NEXT_BADGE = "points_to_next_badge"
ATTR_RAW_PROGRESS = "raw_progress"
ATTR_RECURRING_FREQUENCY = "recurring_frequency"
ATTR_REQUIRED_CHORES = "required_chores"
ATTR_REDEEMED_ON = "Redeemed on"
ATTR_RESET_SCHEDULE = "reset_schedule"
ATTR_REWARD_APPROVALS_COUNT = "reward_approvals_count"
ATTR_REWARD_CLAIMS_COUNT = "reward_claims_count"
ATTR_REWARD_NAME = "reward_name"
ATTR_REWARD_POINTS = "reward_points"
ATTR_SIGN_LABEL = "sign_label"
ATTR_START_DATE = "start_date"
ATTR_STREAKS_BY_ACHIEVEMENT = "streaks_by_achievement"
ATTR_SHARED_CHORE = "shared_chore"
ATTR_TARGET = "target"
ATTR_TARGET_VALUE = "target_value"
ATTR_THRESHOLD_TYPE = "threshold_type"
ATTR_THRESHOLD_VALUE = "threshold_value"

ATTR_TRIGGER_INFO = "trigger_info"
ATTR_TYPE = "type"


# ------------------------------------------------------------------------------------------------
# Sensors
# ------------------------------------------------------------------------------------------------

# Sensor Prefixes
SENSOR_KC_PREFIX = "sensor.kc_"

# Sensor Unique ID Suffixes
SENSOR_KC_UID_SUFFIX_ACHIEVEMENT_SENSOR = "_achievement"
SENSOR_KC_UID_SUFFIX_ACHIEVEMENT_PROGRESS_SENSOR = "_achievement_progress"
SENSOR_KC_UID_SUFFIX_BADGE_PROGRESS_SENSOR = "_badge_progress"
SENSOR_KC_UID_SUFFIX_BADGE_SENSOR = "_badge_sensor"
SENSOR_KC_UID_SUFFIX_BONUS_APPLIES_SENSOR = "_bonus_applies"
SENSOR_KC_UID_SUFFIX_CHALLENGE_SENSOR = "_challenge"
SENSOR_KC_UID_SUFFIX_CHALLENGE_PROGRESS_SENSOR = "_challenge_progress"
SENSOR_KC_UID_SUFFIX_COMPLETED_DAILY_SENSOR = "_completed_daily"
SENSOR_KC_UID_SUFFIX_COMPLETED_MONTHLY_SENSOR = "_completed_monthly"
SENSOR_KC_UID_SUFFIX_COMPLETED_TOTAL_SENSOR = "_completed_total"
SENSOR_KC_UID_SUFFIX_COMPLETED_WEEKLY_SENSOR = "_completed_weekly"
SENSOR_KC_UID_SUFFIX_CHORE_STATUS_SENSOR = "_status"
SENSOR_KC_UID_SUFFIX_KID_HIGHEST_BADGE_SENSOR = "_highest_badge"
SENSOR_KC_UID_SUFFIX_KID_HIGHEST_STREAK_SENSOR = "_highest_streak"
SENSOR_KC_UID_SUFFIX_KID_MAX_POINTS_EVER_SENSOR = "_max_points_ever"
SENSOR_KC_UID_SUFFIX_KID_POINTS_EARNED_DAILY_SENSOR = "_points_earned_daily"
SENSOR_KC_UID_SUFFIX_KID_POINTS_EARNED_MONTHLY_SENSOR = "_points_earned_monthly"
SENSOR_KC_UID_SUFFIX_KID_POINTS_EARNED_WEEKLY_SENSOR = "_points_earned_weekly"
SENSOR_KC_UID_SUFFIX_KID_POINTS_SENSOR = "_points"
SENSOR_KC_UID_SUFFIX_PENALTY_APPLIES_SENSOR = "_penalty_applies"
SENSOR_KC_UID_SUFFIX_PENDING_CHORE_APPROVALS_SENSOR = "_pending_chore_approvals"
SENSOR_KC_UID_SUFFIX_PENDING_REWARD_APPROVALS_SENSOR = "_pending_reward_approvals"
SENSOR_KC_UID_SUFFIX_REWARD_STATUS_SENSOR = "_reward_status"
SENSOR_KC_UID_SUFFIX_SHARED_CHORE_GLOBAL_STATE_SENSOR = "_global_state"

# Sensor Entity ID Mid & Suffixes
SENSOR_KC_EID_MIDFIX_ACHIEVEMENT_PROGRESS_SENSOR = "_achievement_status_"
SENSOR_KC_EID_MIDFIX_ACHIEVEMENT_SENSOR = "achievement_status_"
SENSOR_KC_EID_MIDFIX_BADGE_PROGRESS_SENSOR = "_badge_status_"
SENSOR_KC_EID_MIDFIX_BONUS_APPLIES_SENSOR = "_bonuses_applied_"
SENSOR_KC_EID_MIDFIX_CHALLENGE_PROGRESS_SENSOR = "_challenge_status_"
SENSOR_KC_EID_MIDFIX_CHALLENGE_SENSOR = "challenge_status_"
SENSOR_KC_EID_MIDFIX_CHORE_STATUS_SENSOR = "_chore_status_"
SENSOR_KC_EID_MIDFIX_CHORES_COMPLETED_DAILY_SENSOR = "_chores_completed_daily"
SENSOR_KC_EID_MIDFIX_CHORES_COMPLETED_MONTHLY_SENSOR = "_chores_completed_monthly"
SENSOR_KC_EID_MIDFIX_CHORES_COMPLETED_TOTAL_SENSOR = "_chores_completed_total"
SENSOR_KC_EID_MIDFIX_CHORES_COMPLETED_WEEKLY_SENSOR = "_chores_completed_weekly"
SENSOR_KC_EID_MIDFIX_KID_HIGHEST_BADGE_SENSOR = "_highest_badge"
SENSOR_KC_EID_MIDFIX_KID_HIGHEST_STREAK_SENSOR = "_highest_streak"
SENSOR_KC_EID_MIDFIX_PENALTY_APPLIES_SENSOR = "_penalties_applied_"
SENSOR_KC_EID_MIDFIX_REWARD_STATUS_SENSOR = "_reward_status_"
SENSOR_KC_EID_MIDFIX_SHARED_CHORE_GLOBAL_STATUS_SENSOR = "global_chore_status_"
SENSOR_KC_EID_SUFFIX_BADGE_SENSOR = "_badge"
SENSOR_KC_EID_SUFFIX_KID_MAX_POINTS_EARNED_SENSOR = "_points_max_ever"
SENSOR_KC_EID_SUFFIX_KID_POINTS_EARNED_DAILY_SENSOR = "_points_earned_daily"
SENSOR_KC_EID_SUFFIX_KID_POINTS_EARNED_MONTHLY_SENSOR = "_points_earned_monthly"
SENSOR_KC_EID_SUFFIX_KID_POINTS_EARNED_WEEKLY_SENSOR = "_points_earned_weekly"
SENSOR_KC_EID_SUFFIX_KID_POINTS_SENSOR = "_points"
SENSOR_KC_EID_SUFFIX_PENDING_CHORE_APPROVALS_SENSOR = "global_chore_pending_approvals"
SENSOR_KC_EID_SUFFIX_PENDING_REWARD_APPROVALS_SENSOR = "global_reward_pending_approvals"

# ------------------------------------------------------------------------------------------------
# Selects
# ------------------------------------------------------------------------------------------------

# Select Prefixes
SELECT_KC_PREFIX = "select.kc_"

# Select Unique ID Mid & Suffixes
SELECT_KC_UID_MIDFIX_CHORES_SELECT = "_chores_select_"
SELECT_KC_UID_SUFFIX_BONUSES_SELECT = "_bonuses_select"
SELECT_KC_UID_SUFFIX_CHORES_SELECT = "_chores_select"
SELECT_KC_UID_SUFFIX_PENALTIES_SELECT = "_penalties_select"
SELECT_KC_UID_SUFFIX_REWARDS_SELECT = "_rewards_select"

# Select Entity ID Mid & Suffixes
SELECT_KC_EID_SUFFIX_ALL_BONUSES = "all_bonuses"
SELECT_KC_EID_SUFFIX_ALL_CHORES = "all_chores"
SELECT_KC_EID_SUFFIX_ALL_PENALTIES = "all_penalties"
SELECT_KC_EID_SUFFIX_ALL_REWARDS = "all_rewards"
SELECT_KC_EID_SUFFIX_CHORE_LIST = "_chore_list"

# ------------------------------------------------------------------------------------------------
# Buttons
# ------------------------------------------------------------------------------------------------

# Button Prefixes
BUTTON_KC_PREFIX = "button.kc_"

# Button Unique ID Mid & Suffixes
BUTTON_KC_UID_MIDFIX_ADJUST_POINTS = "_adjust_points_"
BUTTON_KC_UID_SUFFIX_APPROVE = "_approve"
BUTTON_KC_UID_SUFFIX_APPROVE_REWARD = "_approve_reward"
BUTTON_KC_UID_SUFFIX_CLAIM = "_claim"
BUTTON_KC_UID_SUFFIX_DISAPPROVE = "_disapprove"
BUTTON_KC_UID_SUFFIX_DISAPPROVE_REWARD = "_disapprove_reward"

# Button Entity ID Mid & Suffixes
BUTTON_KC_EID_MIDFIX_BONUS = "_bonus_"
BUTTON_KC_EID_MIDFIX_CHORE_APPROVAL = "_chore_approval_"
BUTTON_KC_EID_MIDFIX_CHORE_CLAIM = "_chore_claim_"
BUTTON_KC_EID_MIDFIX_CHORE_DISAPPROVAL = "_chore_disapproval_"
BUTTON_KC_EID_MIDFIX_PENALTY = "_penalty_"
BUTTON_KC_EID_MIDFIX_REWARD_APPROVAL = "_reward_approval_"
BUTTON_KC_EID_MIDFIX_REWARD_CLAIM = "_reward_claim_"
BUTTON_KC_EID_MIDFIX_REWARD_DISAPPROVAL = "_reward_disapproval_"
BUTTON_KC_EID_SUFFIX_POINTS = "_points"

# ------------------------------------------------------------------------------------------------
# Calendars
# ------------------------------------------------------------------------------------------------

# Calendar Prefixes
CALENDAR_KC_PREFIX = "calendar.kc_"

# Calendar Unique ID Mid & Suffixes
CALENDAR_KC_UID_SUFFIX_CALENDAR = "_calendar"

# ------------------------------------------------------------------------------------------------
# Helper Return Types
# ------------------------------------------------------------------------------------------------
HELPER_RETURN_DATE = "date"
HELPER_RETURN_DATETIME = "datetime"
HELPER_RETURN_DATETIME_LOCAL = "datetime_local"
HELPER_RETURN_DATETIME_UTC = "datetime_utc"
HELPER_RETURN_ISO_DATE = "iso_date"
HELPER_RETURN_ISO_DATETIME = "iso_datetime"

# ------------------------------------------------------------------------------------------------
# Services
# ------------------------------------------------------------------------------------------------
SERVICE_ADJUST_POINTS = "adjust_points"
SERVICE_APPLY_BONUS = "apply_bonus"
SERVICE_APPLY_PENALTY = "apply_penalty"
SERVICE_APPROVE_CHORE = "approve_chore"
SERVICE_APPROVE_REWARD = "approve_reward"
SERVICE_CLAIM_CHORE = "claim_chore"
SERVICE_DISAPPROVE_CHORE = "disapprove_chore"
SERVICE_DISAPPROVE_REWARD = "disapprove_reward"
SERVICE_REDEEM_REWARD = "redeem_reward"
SERVICE_REMOVE_AWARDED_BADGES = "remove_awarded_badges"
SERVICE_RESET_ALL_CHORES = "reset_all_chores"
SERVICE_RESET_ALL_DATA = "reset_all_data"
SERVICE_RESET_BONUSES = "reset_bonuses"
SERVICE_RESET_OVERDUE_CHORES = "reset_overdue_chores"
SERVICE_RESET_PENALTIES = "reset_penalties"
SERVICE_RESET_REWARDS = "reset_rewards"
SERVICE_SET_CHORE_DUE_DATE = "set_chore_due_date"
SERVICE_SKIP_CHORE_DUE_DATE = "skip_chore_due_date"


# ------------------------------------------------------------------------------------------------
# Field Names (for service calls)
# ------------------------------------------------------------------------------------------------
FIELD_BADGE_NAME = "badge_name"
FIELD_BONUS_NAME = "bonus_name"
FIELD_CHORE_ID = "chore_id"
FIELD_CHORE_NAME = "chore_name"
FIELD_DUE_DATE = "due_date"
FIELD_KID_NAME = "kid_name"
FIELD_PARENT_NAME = "parent_name"
FIELD_PENALTY_NAME = "penalty_name"
FIELD_POINTS_AWARDED = "points_awarded"
FIELD_REWARD_NAME = "reward_name"


# ------------------------------------------------------------------------------------------------
# Labels
# ------------------------------------------------------------------------------------------------
LABEL_BADGES = "Badges"
LABEL_COMPLETED_DAILY = "Daily Completed Chores"
LABEL_COMPLETED_MONTHLY = "Monthly Completed Chores"
LABEL_COMPLETED_WEEKLY = "Weekly Completed Chores"
LABEL_NONE = ""
LABEL_POINTS = "Points"


# ------------------------------------------------------------------------------------------------
# Button Prefixes
# ------------------------------------------------------------------------------------------------
BUTTON_BONUS_PREFIX = "bonus_button_"
BUTTON_PENALTY_PREFIX = "penalty_button_"
BUTTON_REWARD_PREFIX = "reward_button_"


# ------------------------------------------------------------------------------------------------
# Errors and Warnings
# ------------------------------------------------------------------------------------------------
DUE_DATE_NOT_SET = "Not Set"
ERROR_BONUS_NOT_FOUND = "Bonus not found."
ERROR_BONUS_NOT_FOUND_FMT = "Bonus '{}' not found"
ERROR_CHORE_NOT_FOUND = "Chore not found."
ERROR_CHORE_NOT_FOUND_FMT = "Chore '{}' not found"
ERROR_INVALID_POINTS = "Invalid points."
ERROR_KID_NOT_FOUND = "Kid not found."
ERROR_KID_NOT_FOUND_FMT = "Kid '{}' not found"
ERROR_NOT_AUTHORIZED_ACTION_FMT = "Not authorized to {}."
ERROR_NOT_AUTHORIZED_FMT = "User not authorized to {} for this kid."
ERROR_PENALTY_NOT_FOUND = "Penalty not found."
ERROR_PENALTY_NOT_FOUND_FMT = "Penalty '{}' not found"
ERROR_REWARD_NOT_FOUND = "Reward not found."
ERROR_REWARD_NOT_FOUND_FMT = "Reward '{}' not found"
ERROR_UNNAMED_ACHIEVEMENT = "Unnamed Achievement"
ERROR_USER_NOT_AUTHORIZED = "User is not authorized to perform this action."
MSG_NO_ENTRY_FOUND = "No KidsChores entry found"

# Unknown States
UNKNOWN_CHALLENGE = "Unknown Challenge"
UNKNOWN_CHORE = "Unknown Chore"
UNKNOWN_KID = "Unknown Kid"
UNKNOWN_REWARD = "Unknown Reward"
UNKNOWN_ENTITY = "Unknown Entity"

# Config Flow & Options Flow Error Keys
CFOP_ERROR_ACHIEVEMENT_NAME = "name"
CFOP_ERROR_BADGE_NAME = "badge_name"
CFOP_ERROR_BASE = "base"
CFOP_ERROR_BONUS_NAME = "bonus_name"
CFOP_ERROR_CHALLENGE_NAME = "name"
CFOP_ERROR_CHORE_NAME = "chore_name"
CFOP_ERROR_DUE_DATE = "due_date"
CFOP_ERROR_END_DATE = "end_date"
CFOP_ERROR_KID_NAME = "kid_name"
CFPO_ERROR_PARENT_NAME = "parent_name"
CFOP_ERROR_PENALTY_NAME = "penalty_name"
CFOP_ERROR_REWARD_NAME = "reward_name"
CFOP_ERROR_SELECT_CHORE_ID = "selected_chore_id"
CFOP_ERROR_START_DATE = "start_date"


# ------------------------------------------------------------------------------------------------
# Parent Approval Workflow
# ------------------------------------------------------------------------------------------------
PARENT_APPROVAL_REQUIRED = True  # Enable parent approval for certain actions
HA_USERNAME_LINK_ENABLED = True  # Enable linking kids to HA usernames


# ------------------------------------------------------------------------------------------------
# Calendar Attributes
# ------------------------------------------------------------------------------------------------
ATTR_CAL_ALL_DAY = "all_day"
ATTR_CAL_DESCRIPTION = "description"
ATTR_CAL_END = "end"
ATTR_CAL_MANUFACTURER = "manufacturer"
ATTR_CAL_START = "start"
ATTR_CAL_SUMMARY = "summary"


# ------------------------------------------------------------------------------------------------
# Translation Keys
# ------------------------------------------------------------------------------------------------
# Global
TRANS_KEY_LABEL_ACHIEVEMENT = "Achievement"
TRANS_KEY_LABEL_BADGE = "Badge"
TRANS_KEY_LABEL_BONUS = "Bonus"
TRANS_KEY_LABEL_CHALLENGE = "Challenge"
TRANS_KEY_LABEL_CHORE = "Chore"
TRANS_KEY_LABEL_KID = "Kid"
TRANS_KEY_LABEL_PENALTY = "Penalty"
TRANS_KEY_LABEL_REWARD = "Reward"
TRANS_KEY_NO_DUE_DATE = "No due date set"

# ConfigFlow & OptionsFlow Translation Keys
TRANS_KEY_CFOF_BADGE_ASSIGNED_TO = "assigned_to"
TRANS_KEY_CFOF_BADGE_ASSOCIATED_ACHIEVEMENT = "associated_achievement"
TRANS_KEY_CFOF_BADGE_AWARD_ITEMS = "award_items"
TRANS_KEY_CFOF_BADGE_AWARD_MODE_UNUSED = "award_mode"  # Added
TRANS_KEY_CFOF_BADGE_AWARD_REWARD_UNUSED = "award_reward"  # Added
TRANS_KEY_CFOF_BADGE_ASSOCIATED_CHALLENGE = "associated_challenge"
TRANS_KEY_CFOF_BADGE_LABELS = "badge_labels"
TRANS_KEY_CFOF_BADGE_OCCASION_TYPE = "occasion_type"
TRANS_KEY_CFOF_BADGE_RESET_SCHEDULE_END_DATE_REQUIRED = "end_date_required"
TRANS_KEY_CFOF_BADGE_RESET_SCHEDULE = "reset_schedule"
TRANS_KEY_CFOF_BADGE_RESET_SCHEDULE_RECURRING_FREQUENCY = "recurring_frequency"
TRANS_KEY_CFOF_BADGE_RESET_SCHEDULE_START_DATE_REQUIRED = "start_date_required"
TRANS_KEY_CFOF_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL_UNIT = "custom_interval_unit"
TRANS_KEY_CFOF_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL = "custom_interval"
TRANS_KEY_CFOF_BADGE_SELECTED_CHORES = "selected_chores"
TRANS_KEY_CFOF_BADGE_TARGET_TYPE = "target_type"
TRANS_KEY_CFOF_BADGE_TYPE = "badge_type"
TRANS_KEY_CFOF_CHORE_MUST_BE_SELECTED = "a_chore_must_be_selected"
TRANS_KEY_CFOF_DUE_DATE_IN_PAST = "due_date_in_past"
TRANS_KEY_CFOF_DUPLICATE_ACHIEVEMENT = "duplicate_achievement"
TRANS_KEY_CFOF_DUPLICATE_BADGE = "duplicate_badge"
TRANS_KEY_CFOF_DUPLICATE_BONUS = "duplicate_bonus"
TRANS_KEY_CFOF_DUPLICATE_CHALLENGE = "duplicate_challenge"
TRANS_KEY_CFOF_DUPLICATE_CHORE = "duplicate_chore"
TRANS_KEY_CFOF_DUPLICATE_KID = "duplicate_kid"
TRANS_KEY_CFOF_DUPLICATE_PARENT = "duplicate_parent"
TRANS_KEY_CFOF_DUPLICATE_PENALTY = "duplicate_penalty"
TRANS_KEY_CFOF_DUPLICATE_REWARD = "duplicate_reward"
TRANS_KEY_CFOF_END_DATE_IN_PAST = "end_date_in_past"
TRANS_KEY_CFOF_END_DATE_NOT_AFTER_START_DATE = "end_date_not_after_start_date"
TRANS_KEY_CFOF_ERROR_ASSIGNED_KIDS = "At least one kid must be assigned."
TRANS_KEY_ERROR_SINGLE_INSTANCE = "single_instance_allowed"
TRANS_KEY_CFOF_ERROR_AWARD_POINTS_MINIMUM = (
    "Award points must be greater than 0 if points are selected."
)
TRANS_KEY_CFOF_ERROR_AWARD_INVALID_MULTIPLIER = "Invalid multiplier value."
TRANS_KEY_CFOF_ERROR_AWARD_INVALID_AWARD_ITEM = "invalid_award_item_selected"
TRANS_KEY_CFOF_ERROR_BADGE_ACHIEVEMENT_REQUIRED = "Associated achievement is required."
TRANS_KEY_CFOF_ERROR_BADGE_CHALLENGE_REQUIRED = "Associated challenge is required."
TRANS_KEY_CFOF_ERROR_BADGE_OCCASION_TYPE_REQUIRED = "Occasion type is required."
TRANS_KEY_CFOF_ERROR_BADGE_CUSTOM_RESET_DATE_REQUIRED = (
    "Custom reset date is required when reset type is custom."
)
TRANS_KEY_CFOF_ERROR_BADGE_END_DATE_REQUIRED = (
    "End date is required when reset schedule is custom."
)
TRANS_KEY_CFOF_ERROR_BADGE_RESET_TYPE_REQUIRED = (
    "Reset type is required when periodic reset is enabled."
)
TRANS_KEY_CFOF_ERROR_BADGE_START_DATE_REQUIRED = (
    "Start date is required when reset schedule is custom."
)
TRANS_KEY_CFOF_ERROR_REWARD_SELECTION = (
    "An award reward must be selected when award mode is {}."
)
TRANS_KEY_CFOF_ERROR_POINTS_MULTIPLIER_REQUIRED = "Points multiplier >0 is required."
TRANS_KEY_CFOF_ERROR_THRESHOLD_REQUIRED = "Threshold value >0 is required."
TRANS_KEY_CFOF_INVALID_ACHIEVEMENT = "invalid_achievement"
TRANS_KEY_CFOF_INVALID_ACHIEVEMENT_COUNT = "invalid_achievement_count"
TRANS_KEY_CFOF_INVALID_ACHIEVEMENT_NAME = "invalid_achievement_name"
TRANS_KEY_CFOF_INVALID_ACTION = "invalid_action"
TRANS_KEY_CFOF_INVALID_BADGE = "invalid_badge"
TRANS_KEY_CFOF_INVALID_BADGE_COUNT = "invalid_badge_count"
TRANS_KEY_CFOF_INVALID_BADGE_NAME = "invalid_badge_name"
TRANS_KEY_CFOF_INVALID_BADGE_TARGET_THRESHOLD_VALUE = (
    "invalid_badge_target_threshold_value"
)
TRANS_KEY_CFOF_INVALID_BADGE_TYPE = "invalid_badge_type"
TRANS_KEY_CFOF_INVALID_BONUS = "invalid_bonus"
TRANS_KEY_CFOF_INVALID_BONUS_COUNT = "invalid_bonus_count"
TRANS_KEY_CFOF_INVALID_BONUS_NAME = "invalid_bonus_name"
TRANS_KEY_CFOF_INVALID_CHALLENGE = "invalid_challenge"
TRANS_KEY_CFOF_INVALID_CHALLENGE_COUNT = "invalid_challenge_count"
TRANS_KEY_CFOF_INVALID_CHALLENGE_NAME = "invalid_challenge_name"
TRANS_KEY_CFOF_INVALID_CHORE = "invalid_chore"
TRANS_KEY_CFOF_INVALID_CHORE_COUNT = "invalid_chore_count"
TRANS_KEY_CFOF_INVALID_CHORE_NAME = "invalid_chore_name"
TRANS_KEY_CFOF_INVALID_DUE_DATE = "invalid_due_date"
TRANS_KEY_CFOF_INVALID_END_DATE = "invalid_end_date"
TRANS_KEY_CFOF_INVALID_ENTITY = "invalid_entity"
TRANS_KEY_CFOF_INVALID_KID = "invalid_kid"
TRANS_KEY_CFOF_INVALID_KID_COUNT = "invalid_kid_count"
TRANS_KEY_CFOF_INVALID_KID_NAME = "invalid_kid_name"
TRANS_KEY_CFOF_INVALID_PARENT = "invalid_parent"
TRANS_KEY_CFOF_INVALID_PARENT_COUNT = "invalid_parent_count"
TRANS_KEY_CFOF_INVALID_PARENT_NAME = "invalid_parent_name"
TRANS_KEY_CFOF_INVALID_PENALTY = "invalid_penalty"
TRANS_KEY_CFOF_INVALID_PENALTY_COUNT = "invalid_penalty_count"
TRANS_KEY_CFOF_INVALID_PENALTY_NAME = "invalid_penalty_name"
TRANS_KEY_CFOF_INVALID_REWARD = "invalid_reward"
TRANS_KEY_CFOF_INVALID_REWARD_COUNT = "invalid_reward_count"
TRANS_KEY_CFOF_INVALID_REWARD_NAME = "invalird_reward_name"
TRANS_KEY_CFOF_INVALID_START_DATE = "invalid_start_date"
TRANS_KEY_CFOF_MAIN_MENU = "main_menu"
TRANS_KEY_CFOF_MANAGE_ACTIONS = "manage_actions"
TRANS_KEY_CFOF_NO_ENTITY_TYPE = "no_{}s"
TRANS_KEY_CFOF_POINTS_ADJUST = "points_adjust_options"
TRANS_KEY_CFOF_REQUIRED_CHORES = "required_chores"
TRANS_KEY_CFOP_RESET_SCHEDULE = "reset_schedule"
TRANS_KEY_CFOF_START_DATE_IN_PAST = "start_date_in_past"
TRANS_KEY_CFOF_SETUP_COMPLETE = "setup_complete"
TRANS_KEY_CFOF_SUMMARY_ACHIEVEMENTS = "Achievements: "
TRANS_KEY_CFOF_SUMMARY_BADGES = "Badges: "
TRANS_KEY_CFOF_SUMMARY_BONUSES = "Bonuses: "
TRANS_KEY_CFOF_SUMMARY_CHALLENGES = "Challenges: "
TRANS_KEY_CFOF_SUMMARY_CHORES = "Chores: "
TRANS_KEY_CFOF_SUMMARY_KIDS = "Kids: "
TRANS_KEY_CFOF_SUMMARY_PARENTS = "Parents: "
TRANS_KEY_CFOF_SUMMARY_PENALTIES = "Penalties: "
TRANS_KEY_CFOF_SUMMARY_REWARDS = "Rewards: "

# Flow Helpers Translation Keys
TRANS_KEY_FLOW_HELPERS_APPLICABLE_DAYS = "applicable_days"
TRANS_KEY_FLOW_HELPERS_ASSIGNED_KIDS = "assigned_kids"
TRANS_KEY_FLOW_HELPERS_ASSOCIATED_ACHIEVEMENT = "associated_achievement"
TRANS_KEY_FLOW_HELPERS_ASSOCIATED_CHALLENGE = "associated_challenge"
TRANS_KEY_FLOW_HELPERS_ASSOCIATED_KIDS = "associated_kids"
TRANS_KEY_FLOW_HELPERS_AWARD_MODE = "award_mode"
TRANS_KEY_FLOW_HELPERS_AWARD_REWARD = "award_reward"
TRANS_KEY_FLOW_HELPERS_CUSTOM_INTERVAL_UNIT = "custom_interval_unit"
TRANS_KEY_FLOW_HELPERS_DAILY_THRESHOLD_TYPE = "daily_threshold_type"
TRANS_KEY_FLOW_HELPERS_MAIN_MENU = "main_menu"
TRANS_KEY_FLOW_HELPERS_MANAGE_ACTIONS = "manage_actions"
TRANS_KEY_FLOW_HELPERS_OCCASION_TYPE = "occasion_type"
TRANS_KEY_FLOW_HELPERS_ONE_TIME_REWARD = "one_time_reward"
TRANS_KEY_FLOW_HELPERS_PERIOD = "period"
TRANS_KEY_FLOW_HELPERS_RECURRING_FREQUENCY = "recurring_frequency"
TRANS_KEY_FLOW_HELPERS_RESET_CRITERIA = "reset_criteria"
TRANS_KEY_FLOW_HELPERS_RESET_TYPE = "reset_type"
TRANS_KEY_FLOW_HELPERS_SELECTED_CHORE_ID = "selected_chore_id"
TRANS_KEY_FLOW_HELPERS_THRESHOLD_TYPE = "threshold_type"

# Sensor Translation Keys
TRANS_KEY_SENSOR_ACHIEVEMENT_PROGRESS_SENSOR = "achievement_progress_sensor"
TRANS_KEY_SENSOR_ACHIEVEMENT_STATE_SENSOR = "achievement_state_sensor"
TRANS_KEY_SENSOR_BADGE_SENSOR = "badge_sensor"
TRANS_KEY_SENSOR_BONUS_APPLIES_SENSOR = "bonus_applies_sensor"
TRANS_KEY_SENSOR_CHALLENGE_PROGRESS_SENSOR = "challenge_progress_sensor"
TRANS_KEY_SENSOR_CHALLENGE_STATE_SENSOR = "challenge_state_sensor"
TRANS_KEY_SENSOR_CHORES_COMPLETED_DAILY_SENSOR = "chores_completed_daily_sensor"
TRANS_KEY_SENSOR_CHORES_COMPLETED_MONTHLY_SENSOR = "chores_completed_monthly_sensor"
TRANS_KEY_SENSOR_CHORES_COMPLETED_TOTAL_SENSOR = "chores_completed_total_sensor"
TRANS_KEY_SENSOR_CHORES_COMPLETED_WEEKLY_SENSOR = "chores_completed_weekly_sensor"
TRANS_KEY_SENSOR_CHORE_STATUS_SENSOR = "chore_status_sensor"
TRANS_KEY_SENSOR_KID_HIGHEST_STREAK_SENSOR = "kid_highest_streak_sensor"
TRANS_KEY_SENSOR_KID_MAX_POINTS_EVER_SENSOR = "kid_max_points_ever_sensor"
TRANS_KEY_SENSOR_KID_POINTS_EARNED_DAILY_SENSOR = "kid_points_earned_daily_sensor"
TRANS_KEY_SENSOR_KID_POINTS_EARNED_MONTHLY_SENSOR = "kid_points_earned_monthly_sensor"
TRANS_KEY_SENSOR_KID_POINTS_EARNED_WEEKLY_SENSOR = "kid_points_earned_weekly_sensor"
TRANS_KEY_SENSOR_KID_POINTS_SENSOR = "kid_points_sensor"
TRANS_KEY_SENSOR_KIDS_HIGHEST_BADGE_SENSOR = "kids_highest_badge_sensor"
TRANS_KEY_SENSOR_PENALTY_APPLIES_SENSOR = "penalty_applies_sensor"
TRANS_KEY_SENSOR_PENDING_CHORES_APPROVALS_SENSOR = "pending_chores_approvals_sensor"
TRANS_KEY_SENSOR_PENDING_REWARDS_APPROVALS_SENSOR = "pending_rewards_approvals_sensor"
TRANS_KEY_SENSOR_REWARD_STATUS_SENSOR = "reward_status_sensor"
TRANS_KEY_SENSOR_SHARED_CHORE_GLOBAL_STATUS_SENSOR = "shared_chore_global_status_sensor"


# Sensor Attributes Translation Keys
TRANS_KEY_SENSOR_ATTR_ACHIEVEMENT_NAME = "achievement_name"
TRANS_KEY_SENSOR_ATTR_BADGE_NAME = "badge_name"
TRANS_KEY_SENSOR_ATTR_BONUS_NAME = "bonus_name"
TRANS_KEY_SENSOR_ATTR_CHALLENGE_NAME = "challenge_name"
TRANS_KEY_SENSOR_ATTR_CHORE_NAME = "chore_name"
TRANS_KEY_SENSOR_ATTR_KID_NAME = "kid_name"
TRANS_KEY_SENSOR_ATTR_PENALTY_NAME = "penalty_name"
TRANS_KEY_SENSOR_ATTR_POINTS = "points"
TRANS_KEY_SENSOR_ATTR_REWARD_NAME = "reward_name"

# Select Translation Keys
TRANS_KEY_SELECT_BASE = "kc_select_base"
TRANS_KEY_SELECT_BONUSES = "bonuses_select"
TRANS_KEY_SELECT_CHORES = "chores_select"
TRANS_KEY_SELECT_CHORES_KID = "chores_kid_select"
TRANS_KEY_SELECT_PENALTIES = "penalties_select"
TRANS_KEY_SELECT_REWARDS = "rewards_select"

# Select Labels
TRANS_KEY_SELECT_LABEL_ALL_BONUSES = "All Bonuses"
TRANS_KEY_SELECT_LABEL_ALL_CHORES = "All Chores"
TRANS_KEY_SELECT_LABEL_ALL_PENALTIES = "All Penalties"
TRANS_KEY_SELECT_LABEL_ALL_REWARDS = "All Rewards"
TRANS_KEY_SELECT_LABEL_CHORES_FOR = "Chores for"

# Button Translation Keys
TRANS_KEY_BUTTON_APPROVE_CHORE_BUTTON = "approve_chore_button"
TRANS_KEY_BUTTON_APPROVE_REWARD_BUTTON = "approve_reward_button"
TRANS_KEY_BUTTON_BONUS_BUTTON = "bonus_button"
TRANS_KEY_BUTTON_CLAIM_CHORE_BUTTON = "claim_chore_button"
TRANS_KEY_BUTTON_CLAIM_REWARD_BUTTON = "claim_reward_button"
TRANS_KEY_BUTTON_DELTA_PLUS_LABEL = "+"
TRANS_KEY_BUTTON_DELTA_MINUS_TEXT = "minus_"
TRANS_KEY_BUTTON_DELTA_PLUS_TEXT = "plus_"
TRANS_KEY_BUTTON_DISAPPROVE_CHORE_BUTTON = "disapprove_chore_button"
TRANS_KEY_BUTTON_DISAPPROVE_REWARD_BUTTON = "disapprove_reward_button"
TRANS_KEY_BUTTON_MANUAL_ADJUSTMENT_BUTTON = "manual_adjustment_button"
TRANS_KEY_BUTTON_PENALTY_BUTTON = "penalty_button"


# Button Attributes Translation Keys
TRANS_KEY_BUTTON_ATTR_BONUS_NAME = "bonus_name"
TRANS_KEY_BUTTON_ATTR_CHORE_NAME = "chore_name"
TRANS_KEY_BUTTON_ATTR_KID_NAME = "kid_name"
TRANS_KEY_BUTTON_ATTR_PENALTY_NAME = "penalty_name"
TRANS_KEY_BUTTON_ATTR_POINTS_LABEL = "points_label"
TRANS_KEY_BUTTON_ATTR_REWARD_NAME = "reward_name"
TRANS_KEY_BUTTON_ATTR_SIGN_LABEL = "sign_label"

# Calendar Attributes Translation Keys
TRANS_KEY_CALENDAR_NAME = f"{KIDSCHORES_TITLE} Calendar"

# FMT Errors Translation Keys
TRANS_KEY_FMT_ERROR_ADJUST_POINTS = "adjust_points"
TRANS_KEY_FMT_ERROR_APPLY_BONUS = "apply_bonus"
TRANS_KEY_FMT_ERROR_APPLY_PENALTIES = "apply_penalties"
TRANS_KEY_FMT_ERROR_APPROVE_CHORES = "approve_chores"
TRANS_KEY_FMT_ERROR_APPROVE_REWARDS = "approve_rewards"
TRANS_KEY_FMT_ERROR_CLAIM_CHORES = "claim_chores"
TRANS_KEY_FMT_ERROR_DISAPPROVE_CHORES = "disapprove_chores"
TRANS_KEY_FMT_ERROR_DISAPPROVE_REWARDS = "disapprove_rewards"
TRANS_KEY_FMT_ERROR_REDEEM_REWARDS = "redeem_rewards"

# ------------------------------------------------------------------------------------------------
# Notification Keys
# ------------------------------------------------------------------------------------------------
NOTIFY_ACTION = "action"
NOTIFY_ACTIONS = "actions"
NOTIFY_CREATE = "create"
NOTIFY_DATA = "data"
NOTIFY_DEFAULT_PARENT_NAME = "Parent"
NOTIFY_DOMAIN = "notify"
NOTIFY_MESSAGE = "message"
NOTIFY_NOTIFICATION_ID = "notification_id"
NOTIFY_PARENT_NAME = "parent_name"
NOTIFY_PERSISTENT_NOTIFICATION = "persistent_notification"
NOTIFY_TITLE = "title"


# ------------------------------------------------------------------------------------------------
# List Keys
# ------------------------------------------------------------------------------------------------

# Recurring Frequency
FREQUENCY_OPTIONS = [
    FREQUENCY_NONE,
    FREQUENCY_DAILY,
    FREQUENCY_WEEKLY,
    FREQUENCY_BIWEEKLY,
    FREQUENCY_MONTHLY,
    FREQUENCY_CUSTOM,
]

# Weekday Options
WEEKDAY_OPTIONS = {
    "mon": "Monday",
    "tue": "Tuesday",
    "wed": "Wednesday",
    "thu": "Thursday",
    "fri": "Friday",
    "sat": "Saturday",
    "sun": "Sunday",
}

# Chore Custom Interval Reset Periods
CUSTOM_INTERVAL_UNIT_OPTIONS = [CONF_EMPTY, CONF_DAYS, CONF_WEEKS, CONF_MONTHS]

# Badge Type to Options Flow Add Step Name Mapping
OPTIONS_FLOW_ADD_STEP = {
    BADGE_TYPE_ACHIEVEMENT_LINKED: OPTIONS_FLOW_STEP_ADD_BADGE_ACHIEVEMENT,
    BADGE_TYPE_CHALLENGE_LINKED: OPTIONS_FLOW_STEP_ADD_BADGE_CHALLENGE,
    BADGE_TYPE_CUMULATIVE: OPTIONS_FLOW_STEP_ADD_BADGE_CUMULATIVE,
    BADGE_TYPE_DAILY: OPTIONS_FLOW_STEP_ADD_BADGE_DAILY,
    BADGE_TYPE_PERIODIC: OPTIONS_FLOW_STEP_ADD_BADGE_PERIODIC,
    BADGE_TYPE_SPECIAL_OCCASION: OPTIONS_FLOW_STEP_ADD_BADGE_SPECIAL,
}

# Badge Type to Options Flow Edit Step Name Mapping
OPTIONS_FLOW_EDIT_STEP = {
    BADGE_TYPE_ACHIEVEMENT_LINKED: OPTIONS_FLOW_STEP_EDIT_BADGE_ACHIEVEMENT,
    BADGE_TYPE_CHALLENGE_LINKED: OPTIONS_FLOW_STEP_EDIT_BADGE_CHALLENGE,
    BADGE_TYPE_CUMULATIVE: OPTIONS_FLOW_STEP_EDIT_BADGE_CUMULATIVE,
    BADGE_TYPE_DAILY: OPTIONS_FLOW_STEP_EDIT_BADGE_DAILY,
    BADGE_TYPE_PERIODIC: OPTIONS_FLOW_STEP_EDIT_BADGE_PERIODIC,
    BADGE_TYPE_SPECIAL_OCCASION: OPTIONS_FLOW_STEP_EDIT_BADGE_SPECIAL,
}

# Badge Type to Config Flow Step Name Mapping
CONFIG_FLOW_STEP = {
    BADGE_TYPE_ACHIEVEMENT_LINKED: CONFIG_FLOW_STEP_ACHIEVEMENTS,
    BADGE_TYPE_CHALLENGE_LINKED: CONFIG_FLOW_STEP_CHALLENGES,
    BADGE_TYPE_CUMULATIVE: CONFIG_FLOW_STEP_BADGES,
    BADGE_TYPE_DAILY: CONFIG_FLOW_STEP_BADGES,
    BADGE_TYPE_PERIODIC: CONFIG_FLOW_STEP_BADGES,
    BADGE_TYPE_SPECIAL_OCCASION: CONFIG_FLOW_STEP_BADGES,
}

# Badge Award Mode
AWARD_MODE_OPTIONS_UNUSED = [
    CONF_BADGE_AWARD_NONE_LEGACY,
    CONF_BADGE_AWARD_POINTS_UNUSED,
    CONF_BADGE_AWARD_REWARD_UNUSED,
    CONF_BADGE_AWARD_POINTS_REWARD_UNUSED,
]

AWARD_ITEMS_KEY_POINTS = "points"
AWARD_ITEMS_KEY_POINTS_MULTIPLIER = "multiplier"
AWARD_ITEMS_KEY_REWARDS = "rewards"
AWARD_ITEMS_KEY_BONUSES = "bonuses"
AWARD_ITEMS_KEY_PENALTIES = "penalties"

AWARD_ITEMS_LABEL_POINTS = "POINTS:"
AWARD_ITEMS_LABEL_POINTS_MULTIPLIER = "POINTS MULTIPLIER:"
AWARD_ITEMS_LABEL_REWARD = "REWARD:"
AWARD_ITEMS_LABEL_BONUS = "BONUS:"
AWARD_ITEMS_LABEL_PENALTY = "PENALTY:"

AWARD_ITEMS_PREFIX_POINTS = "points:"
AWARD_ITEMS_PREFIX_POINTS_MULTIPLIER = "multiplier:"
AWARD_ITEMS_PREFIX_REWARD = "reward:"
AWARD_ITEMS_PREFIX_BONUS = "bonus:"
AWARD_ITEMS_PREFIX_PENALTY = "penalty:"

# DEPRECATED - Badge Threshold Type
THRESHOLD_TYPE_OPTIONS = [BADGE_THRESHOLD_TYPE_POINTS, BADGE_THRESHOLD_TYPE_CHORE_COUNT]

# Badge Cumulative Reset Period
BADGE_CUMULATIVE_RESET_TYPE_OPTIONS = [
    {"value": FREQUENCY_WEEKLY, "label": "Weekly"},
    {"value": FREQUENCY_BIWEEKLY, "label": "Biweekly"},
    {"value": FREQUENCY_MONTHLY, "label": "Monthly"},
    {"value": FREQUENCY_QUARTERLY, "label": "Quarterly"},
    {"value": FREQUENCY_YEARLY, "label": "Yearly"},
    {"value": PERIOD_WEEK_END, "label": "Week-End"},
    {"value": PERIOD_MONTH_END, "label": "Month-End"},
    {"value": PERIOD_QUARTER_END, "label": "Quarter-End"},
    {"value": PERIOD_YEAR_END, "label": "Year-End"},
    {"value": FREQUENCY_CUSTOM_1_WEEK, "label": "Custom 1-Week"},
    {"value": FREQUENCY_CUSTOM_1_MONTH, "label": "Custom 1-Month"},
    {"value": FREQUENCY_CUSTOM_1_YEAR, "label": "Custom 1-Year"},
]


# Badge Periodic Reset Schedule
BADGE_RESET_SCHEDULE_OPTIONS = [
    {"value": FREQUENCY_NONE, "label": "None"},
    {"value": FREQUENCY_DAILY, "label": "Daily"},
    {"value": FREQUENCY_WEEKLY, "label": "Weekly"},
    {"value": FREQUENCY_BIWEEKLY, "label": "Biweekly"},
    {"value": FREQUENCY_MONTHLY, "label": "Monthly"},
    {"value": FREQUENCY_QUARTERLY, "label": "Quarterly"},
    {"value": FREQUENCY_YEARLY, "label": "Yearly"},
    {"value": PERIOD_WEEK_END, "label": "Week-End"},
    {"value": PERIOD_MONTH_END, "label": "Month-End"},
    {"value": PERIOD_QUARTER_END, "label": "Quarter-End"},
    {"value": PERIOD_YEAR_END, "label": "Year-End"},
    {"value": CONF_CUSTOM, "label": "Custom (define period below)"},
]

# Badge target handler constants for handler mapping keys
BADGE_HANDLER_PARAM_PERCENT_REQUIRED = "percent_required"
BADGE_HANDLER_PARAM_ONLY_DUE_TODAY = "only_due_today"
BADGE_HANDLER_PARAM_REQUIRE_NO_OVERDUE = "require_no_overdue"
BADGE_HANDLER_PARAM_MIN_COUNT = "min_count"
BADGE_HANDLER_PARAM_FROM_CHORES_ONLY = "from_chores_only"

# Badge Special Occasion Types
OCCASION_TYPE_OPTIONS = [CONF_BIRTHDAY, CONF_HOLIDAY, CONF_CUSTOM]

TARGET_TYPE_OPTIONS = [
    {CONF_VALUE: BADGE_TARGET_THRESHOLD_TYPE_POINTS, CONF_LABEL: "Points Earned"},
    {
        CONF_VALUE: BADGE_TARGET_THRESHOLD_TYPE_POINTS_CHORES,
        CONF_LABEL: "Points Earned (From Chores)",
    },
    {
        CONF_VALUE: BADGE_TARGET_THRESHOLD_TYPE_CHORE_COUNT,
        CONF_LABEL: "Chores Completed",
    },
    {
        CONF_VALUE: BADGE_TARGET_THRESHOLD_TYPE_DAYS_SELECTED_CHORES,
        CONF_LABEL: "Days Selected Chores Completed",
    },
    {
        CONF_VALUE: BADGE_TARGET_THRESHOLD_TYPE_DAYS_80PCT_CHORES,
        CONF_LABEL: "Days 80% of Selected Chores Completed",
    },
    {
        CONF_VALUE: BADGE_TARGET_THRESHOLD_TYPE_DAYS_SELECTED_CHORES_NO_OVERDUE,
        CONF_LABEL: "Days Selected Chores Completed (No Overdue)",
    },
    {
        CONF_VALUE: BADGE_TARGET_THRESHOLD_TYPE_DAYS_SELECTED_DUE_CHORES,
        CONF_LABEL: "Days Selected Due Chores Completed",
    },
    {
        CONF_VALUE: BADGE_TARGET_THRESHOLD_TYPE_DAYS_80PCT_DUE_CHORES,
        CONF_LABEL: "Days 80% of Selected Due Chores Completed",
    },
    {
        CONF_VALUE: BADGE_TARGET_THRESHOLD_TYPE_DAYS_SELECTED_DUE_CHORES_NO_OVERDUE,
        CONF_LABEL: "Days Selected Due Chores Completed (No Overdue)",
    },
    {
        CONF_VALUE: BADGE_TARGET_THRESHOLD_TYPE_DAYS_MIN_3_CHORES,
        CONF_LABEL: "Days Minimum 3 Chores Completed",
    },
    {
        CONF_VALUE: BADGE_TARGET_THRESHOLD_TYPE_DAYS_MIN_5_CHORES,
        CONF_LABEL: "Days Minimum 5 Chores Completed",
    },
    {
        CONF_VALUE: BADGE_TARGET_THRESHOLD_TYPE_DAYS_MIN_7_CHORES,
        CONF_LABEL: "Days Minimum 7 Chores Completed",
    },
    {
        CONF_VALUE: BADGE_TARGET_THRESHOLD_TYPE_STREAK_SELECTED_CHORES,
        CONF_LABEL: "Streak: Selected Chores Completed",
    },
    {
        CONF_VALUE: BADGE_TARGET_THRESHOLD_TYPE_STREAK_80PCT_CHORES,
        CONF_LABEL: "Streak: 80% of Selected Chores Completed",
    },
    {
        CONF_VALUE: BADGE_TARGET_THRESHOLD_TYPE_STREAK_SELECTED_CHORES_NO_OVERDUE,
        CONF_LABEL: "Streak: Selected Chores Completed (No Overdue)",
    },
    {
        CONF_VALUE: BADGE_TARGET_THRESHOLD_TYPE_STREAK_80PCT_DUE_CHORES,
        CONF_LABEL: "Streak: 80% of Selected Due Chores Completed",
    },
    {
        CONF_VALUE: BADGE_TARGET_THRESHOLD_TYPE_STREAK_SELECTED_DUE_CHORES_NO_OVERDUE,
        CONF_LABEL: "Streak: Selected Due Chores Completed (No Overdue)",
    },
]


# Badge types for include_target component
INCLUDE_TARGET_BADGE_TYPES = [
    BADGE_TYPE_CUMULATIVE,
    BADGE_TYPE_PERIODIC,
    BADGE_TYPE_DAILY,
    BADGE_TYPE_SPECIAL_OCCASION,
]

# Badge types for include_special_occasion component
INCLUDE_SPECIAL_OCCASION_BADGE_TYPES = [
    BADGE_TYPE_SPECIAL_OCCASION,
]

# Badge types for include_achievement_linked component
INCLUDE_ACHIEVEMENT_LINKED_BADGE_TYPES = [
    BADGE_TYPE_ACHIEVEMENT_LINKED,
]

# Badge types for include_challenge_linked component
INCLUDE_CHALLENGE_LINKED_BADGE_TYPES = [
    BADGE_TYPE_CHALLENGE_LINKED,
]

# Badge types for include_tracked_chores component
INCLUDE_TRACKED_CHORES_BADGE_TYPES = [BADGE_TYPE_PERIODIC, BADGE_TYPE_DAILY]

# Badge types for include_assigned_to component
INCLUDE_ASSIGNED_TO_BADGE_TYPES = [
    BADGE_TYPE_CUMULATIVE,
    BADGE_TYPE_DAILY,
    BADGE_TYPE_PERIODIC,
    BADGE_TYPE_SPECIAL_OCCASION,
]

# Badge types for include_awards component
INCLUDE_AWARDS_BADGE_TYPES = [
    BADGE_TYPE_CUMULATIVE,
    BADGE_TYPE_PERIODIC,
    BADGE_TYPE_DAILY,
    BADGE_TYPE_SPECIAL_OCCASION,
    BADGE_TYPE_ACHIEVEMENT_LINKED,
    BADGE_TYPE_CHALLENGE_LINKED,
]

# Badge types for include_award-penalties component
INCLUDE_PENALTIES_BADGE_TYPES = [
    BADGE_TYPE_PERIODIC,
    BADGE_TYPE_DAILY,
]


# Badge types for include_reset_schedule component
INCLUDE_RESET_SCHEDULE_BADGE_TYPES = [
    BADGE_TYPE_CUMULATIVE,
    BADGE_TYPE_PERIODIC,
    BADGE_TYPE_SPECIAL_OCCASION,
    BADGE_TYPE_DAILY,
]

# Achievement Type Options
ACHIEVEMENT_TYPE_OPTIONS = [
    {"value": ACHIEVEMENT_TYPE_STREAK, "label": "Chore Streak"},
    {"value": ACHIEVEMENT_TYPE_TOTAL, "label": "Chore Total"},
    {"value": ACHIEVEMENT_TYPE_DAILY_MIN, "label": "Daily Minimum Chores"},
]

# Challenge Type Options
CHALLENGE_TYPE_OPTIONS = [
    {"value": CHALLENGE_TYPE_DAILY_MIN, "label": "Minimum Chores per Day"},
    {
        "value": CHALLENGE_TYPE_TOTAL_WITHIN_WINDOW,
        "label": "Total Chores within Period",
    },
]

# Reward Options
REWARD_OPTION_NONE = [
    {
        "value": CONF_EMPTY,
        "label": LABEL_NONE,
    }
]
