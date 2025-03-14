# File: const.py
"""Constants for the KidsChores integration.

This file centralizes configuration keys, defaults, labels, domain names,
event names, and platform identifiers for consistency across the integration.
It also supports localization by defining all labels and UI texts used in sensors,
services, and options flow.
"""

import logging

from homeassistant.const import Platform

# --------------------------------------------------------------------
# General / Integration Information
# --------------------------------------------------------------------

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

# Storage and Versioning
STORAGE_KEY = "kidschores_data"  # Persistent storage key
STORAGE_VERSION = 1  # Storage version

# Update Interval
UPDATE_INTERVAL = 5  # Update interval for coordinator (in minutes)

# --------------------------------------------------------------------
# Configuration Keys
# --------------------------------------------------------------------

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
OPTIONS_FLOW_SELECT_ENTITY = "select_entity"
OPTIONS_FLOW_FINISH = "done"
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
CONF_GLOBAL = "global"
CONF_KIDS = "kids"
CONF_PARENTS = "parents"
CONF_PENALTIES = "penalties"
CONF_REWARDS = "rewards"

# OptionsFlow Steps
OPTIONS_FLOW_STEP_INIT = "init"
OPTIONS_FLOW_STEP_MANAGE_ENTITY = "manage_entity"
OPTIONS_FLOW_STEP_MANAGE_POINTS = "manage_points"
OPTIONS_FLOW_STEP_SELECT_ENTITY = "select_entity"

OPTIONS_FLOW_STEP_ADD_ACHIEVEMENT = "add_achievement"
OPTIONS_FLOW_STEP_ADD_BADGE = "add_badge"
OPTIONS_FLOW_STEP_ADD_BONUS = "add_bonus"
OPTIONS_FLOW_STEP_ADD_CHALLENGE = "add_challenge"
OPTIONS_FLOW_STEP_ADD_CHORE = "add_chore"
OPTIONS_FLOW_STEP_ADD_KID = "add_kid"
OPTIONS_FLOW_STEP_ADD_PARENT = "add_parent"
OPTIONS_FLOW_STEP_ADD_PENALTY = "add_penalty"
OPTIONS_FLOW_STEP_ADD_REWARD = "add_reward"

OPTIONS_FLOW_STEP_EDIT_ACHIEVEMENT = "edit_achievement"
OPTIONS_FLOW_STEP_EDIT_BADGE = "edit_badge"
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
CFOF_KIDS_INPUT_KID_NAME = "kid_name"
CFOF_KIDS_INPUT_MOBILE_NOTIFY_SERVICE = "mobile_notify_service"

# PARENTS
CFOF_PARENTS_INPUT_ASSOCIATED_KIDS = "associated_kids"
CFOF_PARENTS_INPUT_ENABLE_MOBILE_NOTIFICATIONS = "enable_mobile_notifications"
CFOF_PARENTS_INPUT_ENABLE_PERSISTENT_NOTIFICATIONS = "enable_persistent_notifications"
CFOF_PARENTS_INPUT_HA_USER = "ha_user_id"
CFOF_PARENTS_INPUT_MOBILE_NOTIFY_SERVICE = "mobile_notify_service"
CFOF_PARENTS_INPUT_NAME = "parent_name"

# CHORES
CFOF_CHORES_INPUT_ALLOW_MULTIPLE_CLAIMS = "allow_multiple_claims_per_day"
CFOF_CHORES_INPUT_APPLICABLE_DAYS = "applicable_days"
CFOF_CHORES_INPUT_ASSIGNED_KIDS = "asigned_kids"
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
CFOF_BADGES_INPUT_ASSOCIATED_ACHIEVEMENT = "associated_acchievement"
CFOF_BADGES_INPUT_ASSOCIATED_CHALLENGE = "associated_challenge"
CFOF_BADGES_INPUT_DAILY_THRESHOLD = "daily_threshold"
CFOF_BADGES_INPUT_DESCRIPTION = "badge_description"
CFOF_BADGES_INPUT_ICON = "icon"
CFOF_BADGES_INPUT_LABELS = "badge_labels"
CFOF_BADGES_INPUT_NAME = "badge_name"
CFOF_BADGES_INPUT_OCCASION_TYPE = "occasion_type"
CFOF_BADGES_INPUT_ONE_TIME_REWARD = "one_time_reward"
CFOF_BADGES_INPUT_PERIOD = "period"
CFOF_BADGES_INPUT_POINTS_MULTIPLIER = "points_multiplier"
CFOF_BADGES_INPUT_REWARD = "reward"
CFOF_BADGES_INPUT_RESET_CRITERIA = "reset_criteria"
CFOF_BADGES_INPUT_THRESHOLD_VALUE = "threshold_value"
CFOF_BADGES_INPUT_TRIGGER_INFO = "trigger_info"
CFOF_BADGES_INPUT_TYPE = "badge_type"

# REWARDS
CFOF_REWARDS_INPUT_COST = "reward_cost"
CFOF_REWARDS_INPUT_DESCRIPTION = "reward_description"
CFOF_REWARDS_INPUT_ICON = "icon"
CFOF_REWARDS_INPUT_LABELS = "reward_labels"
CFOF_REWARDS_INPUT_NAME = "reward_name"

# BONUSES
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
CFOF_PENALTIES_INPUT_POINTS = "penalty_points"

# ACHIEVEMENTS
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


# OptionsFlow Helpers
OPTIONS_FLOW_ASYNC_STEP_PREFIX = "async_step_"
OPTIONS_FLOW_ASYNC_STEP_ADD_PREFIX = "async_step_add_"
OPTIONS_FLOW_MENU_MANAGE_PREFIX = "manage_"

# Validation Keys
VALIDATION_DUE_DATE = "due_date"  # Optional due date for chores
VALIDATION_PARTIAL_ALLOWED = "partial_allowed"  # Allow partial points in chores
VALIDATION_THRESHOLD_TYPE = "threshold_type"  # Badge criteria type
VALIDATION_THRESHOLD_VALUE = "threshold_value"  # Badge criteria value

# Global configuration keys
CONF_DESCRIPTION = "description"
CONF_EMPTY = ""
CONF_INTERNAL_ID = "internal_id"
CONF_ICON = "icon"
CONF_NAME = "name"
CONF_COST = "cost"
CONF_DAYS = "days"
CONF_WEEKS = "weeks"
CONF_MONTHS = "months"
CONF_POINTS = "points"
CONF_WEEKLY = "weekly"
CONF_MONTHLY = "monthly"
CONF_CUSTOM = "custom"
CONF_BIWEEKLY = "biweekly"
CONF_YEAR_END = "year_end"
CONF_HOLIDAY = "holiday"
CONF_BIRTHDAY = "birthday"

# Points configuration keys
CONF_POINTS_ICON = "points_icon"
CONF_POINTS_LABEL = "points_label"

# Kids configuration keys
CONF_KIDNAME = "kid_name"
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
CONF_SHARED_CHORE = "shared_chore"


# Notification configuration keys
CONF_CHORE_NOTIFY_SERVICE = "chore_notify_service"
CONF_ENABLE_MOBILE_NOTIFICATIONS = "enable_mobile_notifications"
CONF_ENABLE_PERSISTENT_NOTIFICATIONS = "enable_persistent_notifications"
CONF_MOBILE_NOTIFY_SERVICE = "mobile_notify_service"
CONF_NOTIFY_ON_APPROVAL = "notify_on_approval"
CONF_NOTIFY_ON_CLAIM = "notify_on_claim"
CONF_NOTIFY_ON_DISAPPROVAL = "notify_on_disapproval"

NOTIFICATION_EVENT = "mobile_app_notification_action"

# Badge configuration keys
CONF_BADGE_ASSOCIATED_ACHIEVEMENT = "associated_achievement"
CONF_BADGE_ASSOCIATED_CHALLENGE = "associated_challenge"
CONF_BADGE_AWARD_MODE = "award_mode"
CONF_BADGE_AWARD_POINTS = "award_points"
CONF_BADGE_AWARD_REWARD = "award_reward"
CONF_BADGE_DESCRIPTION = "badge_description"
CONF_BADGE_DAILY_THRESHOLD = "daily_threshold"
CONF_BADGE_DAILY_THRESHOLD_TYPE = "daily_threshold_type"
CONF_BADGE_END_DATE = "end_date"
CONF_BADGE_LABELS = "badge_labels"
CONF_BADGE_MAINTENANCE_RULES = "maintenance_rules"
CONF_BADGE_NAME = "badge_name"
CONF_BADGE_OCCASION_DATE = "occasion_date"
CONF_BADGE_OCCASION_TYPE = "occasion_type"
CONF_BADGE_ONE_TIME_REWARD = "one_time_reward"
CONF_BADGE_PERIOD = "period"
CONF_BADGE_POINTS_MULTIPLIER = "points_multiplier"
CONF_BADGE_RESET_CRITERIA = "reset_criteria"
CONF_BADGE_RESET_GRACE_PERIOD = "reset_grace_period"
CONF_BADGE_RESET_PERIOD = "reset_period"
CONF_BADGE_RESET_PERIODICALLY = "reset_periodically"
CONF_BADGE_START_DATE = "start_date"
CONF_BADGE_THRESHOLD_TYPE = "threshold_type"
CONF_BADGE_THRESOLD_VALUE = "threshold_value"
CONF_BADGE_TRIGGER_INFO = "trigger_info"
CONF_BADGE_TYPE = "badge_type"

# Badge types
BADGE_TYPE_ACHIEVEMENT_LINKED = "achievement_linked"
BADGE_TYPE_CHALLENGE_LINKED = "challenge_linked"
BADGE_TYPE_CUMULATIVE = "cumulative"
BADGE_TYPE_DAILY = "daily"
BADGE_TYPE_PERIODIC = "periodic"
BADGE_TYPE_SPECIAL_OCCASION = "special_occasions"

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


# --------------------------------------------------------------------
# Data Keys
# --------------------------------------------------------------------

# GLOBAL
DATA_ACHIEVEMENTS = "achievements"
DATA_APPLICABLE_DAYS = "applicable_days"
DATA_ASSIGNED_KIDS = "assigned_kids"
DATA_BADGES = "badges"
DATA_BONUSES = "bonuses"
DATA_CHALLENGES = "challenges"
DATA_CHORES = "chores"
DATA_CRITERIA = "criteria"
DATA_CUSTOM_INTERVAL = "custom_interval"
DATA_CUSTOM_INTERVAL_UNIT = "custom_interval_unit"
DATA_DEFAULT_POINTS = "default_points"
DATA_DUE_DATE = "due_date"
DATA_ENABLE_NOTIFICATIONS = "enable_notifications"
DATA_HA_USER = "ha_user"
DATA_HA_USER_ID = "ha_user_id"
DATA_INTERNAL_ID = "internal_id"
DATA_KIDS = "kids"
DATA_LAST_CHANGE = "last_change"
DATA_LAST_CHORE_DATE = "last_chore_date"
DATA_MAX_POINTS_EVER = "max_points_ever"
DATA_MOBILE_NOTIFY_SERVICE = "mobile_notify_service"
DATA_NOTIFY_ON_APPROVAL = "notify_on_approval"
DATA_NOTIFY_ON_CLAIM = "notify_on_claim"
DATA_NOTIFY_ON_DISAPPROVAL = "notify_on_disapproval"
DATA_OVERALL_CHORE_STREAK = "overall_chore_streak"
DATA_OVERDUE_CHORES = "overdue_chores"
DATA_OVERDUE_NOTIFICATIONS = "overdue_notifications"
DATA_PARENTS = "parents"
DATA_PENALTIES = "penalties"
DATA_PENALTY_APPLIES = "penalty_applies"
DATA_POINTS_EARNED_MONTHLY = "points_earned_monthly"
DATA_POINTS_EARNED_TODAY = "points_earned_today"
DATA_POINTS_EARNED_WEEKLY = "points_earned_weekly"
DATA_RECURRING_FREQUENCY = "recurring_frequency"
DATA_REWARD_APPROVALS = "reward_approvals"
DATA_REWARD_CLAIMS = "reward_claims"
DATA_REWARDS = "rewards"
DATA_SELECTED_CHORE_ID = "selected_chore_id"

# KIDS
DATA_KID_APPROVED_CHORES = "approved_chores"
DATA_KID_BADGES = "badges"
DATA_KID_BONUS_APPLIES = "bonus_applies"
DATA_KID_CHORE_APPROVALS = "chore_approvals"
DATA_KID_CHORE_CLAIMS = "chore_claims"
DATA_KID_CHORE_STREAKS = "chore_streaks"
DATA_KID_CLAIMED_CHORES = "claimed_chores"
DATA_KID_COMPLETED_CHORES_MONTHLY = "completed_chores_monthly"
DATA_KID_COMPLETED_CHORES_TOTAL = "completed_chores_total"
DATA_KID_COMPLETED_CHORES_TODAY = "completed_chores_today"
DATA_KID_COMPLETED_CHORES_WEEKLY = "completed_chores_weekly"
DATA_KID_ENABLE_NOTIFICATIONS = "enable_notifications"
DATA_KID_HA_USER_ID = "ha_user_id"
DATA_KID_INTERNAL_ID = "internal_id"
DATA_KID_LAST_CHORE_DATE = "last_chore_date"
DATA_KID_MAX_POINTS_EVER = "max_points_ever"
DATA_KID_MOBILE_NOTIFY_SERVICE = "mobile_notify_service"
DATA_KID_NAME = "name"
DATA_KID_OVERDUE_CHORES = "overdue_chores"
DATA_KID_OVERDUE_NOTIFICATIONS = "overdue_notifications"
DATA_KID_OVERALL_CHORE_STREAK = "overall_chore_streak"
DATA_KID_PENALTY_APPLIES = "penalty_applies"
DATA_KID_PENDING_REWARDS = "pending_rewards"
DATA_KID_POINTS = "points"
DATA_KID_POINTS_EARNED_MONTHLY = "points_earned_monthly"
DATA_KID_POINTS_EARNED_TODAY = "points_earned_today"
DATA_KID_POINTS_EARNED_WEEKLY = "points_earned_weekly"
DATA_KID_POINTS_MULTIPLIER = "points_multiplier"
DATA_KID_REDEEMED_REWARDS = "redeemed_rewards"
DATA_KID_REWARD_APPROVALS = "reward_approvals"
DATA_KID_REWARD_CLAIMS = "reward_claims"
DATA_KID_USE_PERSISTENT_NOTIFICATIONS = "use_persistent_notifications"

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

# BADGES
DATA_BADGE_ASSOCIATED_ACHIEVEMENT = "associated_achievement"
DATA_BADGE_ASSOCIATED_CHALLENGE = "associated_challenge"
DATA_BADGE_DAILY_THRESHOLD = "daily_threshold"
DATA_BADGE_DESCRIPTION = "description"
DATA_BADGE_ICON = "icon"
DATA_BADGE_INTERNAL_ID = "internal_id"
DATA_BADGE_LABELS = "badge_labels"
DATA_BADGE_MAINTENANCE_RULES = "maintenance_rules"
DATA_BADGE_NAME = "name"
DATA_BADGE_ONE_TIME_REWARD = "one_time_reward"
DATA_BADGE_OCCASION_TYPE = "occasion_type"
DATA_BADGE_PERIOD = "period"
DATA_BADGE_POINTS_MULTIPLIER = "points_multiplier"
DATA_BADGE_REWARD = "reward"
DATA_BADGE_RESET_CRITERIA = "reset_criteria"
DATA_BADGE_RESET_GRACE_PERIOD = "reset_grace_period"
DATA_BADGE_RESET_PERIOD = "reset_period"
DATA_BADGE_RESET_PERIODICALLY = "reset_periodically"
DATA_BADGE_THRESHOLD_TYPE = "threshold_type"
DATA_BADGE_THRESHOLD_VALUE = "threshold_value"
DATA_BADGE_TYPE = "badge_type"
DATA_BADGE_TRIGGER_INFO = "trigger_info"

# REWARDS
DATA_REWARD_COST = "cost"
DATA_REWARD_DESCRIPTION = "description"
DATA_REWARD_ICON = "icon"
DATA_REWARD_INTERNAL_ID = "internal_id"
DATA_REWARD_LABELS = "reward_labels"
DATA_REWARD_NAME = "name"

# BONUSES
DATA_BONUS_DESCRIPTION = "description"
DATA_BONUS_ICON = "icon"
DATA_BONUS_INTERNAL_ID = "internal_id"
DATA_BONUS_LABELS = "bonus_labels"
DATA_BONUS_NAME = "name"
DATA_BONUS_POINTS = "points"

# PENALTIES
DATA_PENALTY_DESCRIPTION = "description"
DATA_PENALTY_ICON = "icon"
DATA_PENALTY_INTERNAL_ID = "internal_id"
DATA_PENALTY_LABELS = "penalty_labels"
DATA_PENALTY_NAME = "name"
DATA_PENALTY_POINTS = "points"

# ACHIEVEMENTS
DATA_ACHIEVEMENT_ASSIGNED_KIDS = "assigned_kids"
DATA_ACHIEVEMENT_CRITERIA = "criteria"
DATA_ACHIEVEMENT_DESCRIPTION = "description"
DATA_ACHIEVEMENT_ICON = "icon"
DATA_ACHIEVEMENT_INTERNAL_ID = "internal_id"
DATA_ACHIEVEMENT_LABELS = "achievement_labels"
DATA_ACHIEVEMENT_NAME = "name"
DATA_ACHIEVEMENT_PROGRESS = "progress"
DATA_ACHIEVEMENT_REWARD_POINTS = "reward_points"
DATA_ACHIEVEMENT_SELECTED_CHORE_ID = "selected_chore_id"
DATA_ACHIEVEMENT_TARGET_VALUE = "target_value"
DATA_ACHIEVEMENT_TYPE = "type"

# CHALLENGES
DATA_CHALLENGE_ASSIGNED_KIDS = "assigned_kids"
DATA_CHALLENGE_CRITERIA = "criteria"
DATA_CHALLENGE_DESCRIPTION = "description"
DATA_CHALLENGE_END_DATE = "end_date"
DATA_CHALLENGE_ICON = "icon"
DATA_CHALLENGE_INTERNAL_ID = "internal_id"
DATA_CHALLENGE_LABELS = "challenge_labels"
DATA_CHALLENGE_NAME = "name"
DATA_CHALLENGE_PROGRESS = "progress"
DATA_CHALLENGE_REWARD_POINTS = "reward_points"
DATA_CHALLENGE_SELECTED_CHORE_ID = "selected_chore_id"
DATA_CHALLENGE_START_DATE = "start_date"
DATA_CHALLENGE_TARGET_VALUE = "target_value"
DATA_CHALLENGE_TYPE = "type"

# Runtime Data Keys
DATA_CHORE_APPROVALS = "chore_approvals"
DATA_CHORE_CLAIMS = "chore_claims"
DATA_PENDING_CHORE_APPROVALS = "pending_chore_approvals"
DATA_PENDING_REWARD_APPROVALS = "pending_reward_approvals"


# --------------------------------------------------------------------
# Default Icons
# --------------------------------------------------------------------
DEFAULT_ACHIEVEMENTS_ICON = "mdi:trophy-award"
DEFAULT_BADGE_ICON = "mdi:shield-star-outline"
DEFAULT_BONUS_ICON = "mdi:seal"
DEFAULT_CALENDAR_ICON = "mdi:calendar"
DEFAULT_CHALLENGES_ICON = "mdi:trophy"
DEFAULT_CHORE_APPROVE_ICON = "mdi:checkbox-marked-circle-outline"
DEFAULT_CHORE_BINARY_ICON = "mdi:checkbox-blank-circle-outline"
DEFAULT_CHORE_CLAIM_ICON = "mdi:clipboard-check-outline"
DEFAULT_CHORE_SENSOR_ICON = "mdi:checkbox-blank-circle-outline"
DEFAULT_DISAPPROVE_ICON = "mdi:close-circle-outline"
DEFAULT_ICON = "mdi:star-outline"
DEFAULT_PENALTY_ICON = "mdi:alert-outline"
DEFAULT_POINTS_ADJUST_MINUS_ICON = "mdi:minus-circle-outline"
DEFAULT_POINTS_ADJUST_MINUS_MULTIPLE_ICON = "mdi:minus-circle-multiple-outline"
DEFAULT_POINTS_ADJUST_PLUS_ICON = "mdi:plus-circle-outline"
DEFAULT_POINTS_ADJUST_PLUS_MULTIPLE_ICON = "mdi:plus-circle-multiple-outline"
DEFAULT_POINTS_ICON = "mdi:star-outline"
DEFAULT_STREAK_ICON = "mdi:blur-linear"
DEFAULT_REWARD_ICON = "mdi:gift-outline"
DEFAULT_TROPHY_ICON = "mdi:trophy"
DEFAULT_TROPHY_OUTLINE = "mdi:trophy-outline"


# --------------------------------------------------------------------
# Default Values
# --------------------------------------------------------------------
DEFAULT_ACHIEVEMENT_REWARD_POINTS = 0
DEFAULT_ACHIEVEMENT_TARGET = 1
DEFAULT_APPLICABLE_DAYS = []
DEFAULT_BADGE_AWARD_MODE = "points"
DEFAULT_BADGE_AWARD_POINTS = 5
DEFAULT_BADGE_DAILY_THRESHOLD = 5
DEFAULT_BADGE_RESET_GRACE_PERIOD = 0
DEFAULT_BADGE_REWARD = 0
DEFAULT_BADGE_THRESHOLD_VALUE = 50
DEFAULT_BADGE_THRESOLD_TYPE = "points"
DEFAULT_BONUS_POINTS = 1
DEFAULT_CHALLENGE_REWARD_POINTS = 0
DEFAULT_CHALLENGE_TARGET = 1
DEFAULT_DAILY_RESET_TIME = {"hour": 0, "minute": 0, "second": 0}
DEFAULT_MONTHLY_RESET_DAY = 1
DEFAULT_MULTIPLE_CLAIMS_PER_DAY = False
DEFAULT_NOTIFICATIONS = True
DEFAULT_NOTIFY_ON_APPROVAL = True
DEFAULT_NOTIFY_ON_CLAIM = True
DEFAULT_NOTIFY_ON_DISAPPROVAL = True
DEFAULT_PARTIAL_ALLOWED = False
DEFAULT_PENALTY_POINTS = 1
DEFAULT_POINTS = 5
DEFAULT_POINTS_LABEL = "Points"
DEFAULT_POINTS_MULTIPLIER = 1
DEFAULT_REWARD_COST = 10
DEFAULT_REMINDER_DELAY = 30
DEFAULT_WEEKLY_RESET_DAY = 0


# --------------------------------------------------------------------
# Frequencies
# --------------------------------------------------------------------
FREQUENCY_BIWEEKLY = "biweekly"
FREQUENCY_CUSTOM = "custom"
FREQUENCY_DAILY = "daily"
FREQUENCY_MONTHLY = "monthly"
FREQUENCY_NONE = "none"
FREQUENCY_WEEKLY = "weekly"


# --------------------------------------------------------------------
# Badge Threshold Types
# --------------------------------------------------------------------
BADGE_THRESHOLD_TYPE_CHORE_COUNT = "chore_count"
BADGE_THRESHOLD_TYPE_POINTS = "points"


# --------------------------------------------------------------------
# States
# --------------------------------------------------------------------

# Chore States
CHORE_STATE_APPROVED = "approved"
CHORE_STATE_APPROVED_IN_PART = "approved_in_part"
CHORE_STATE_CLAIMED = "claimed"
CHORE_STATE_CLAIMED_IN_PART = "claimed_in_part"
CHORE_STATE_INDEPENDENT = "independent"
CHORE_STATE_OVERDUE = "overdue"
CHORE_STATE_PARTIAL = "partial"
CHORE_STATE_PENDING = "pending"
CHORE_STATE_UNKNOWN = "unknown"

# Reward States
REWARD_STATE_APPROVED = "approved"
REWARD_STATE_CLAIMED = "claimed"
REWARD_STATE_NOT_CLAIMED = "not_claimed"
REWARD_STATE_UNKNOWN = "unknown"

# --------------------------------------------------------------------
# Events
# --------------------------------------------------------------------
EVENT_CHORE_COMPLETED = "kidschores_chore_completed"
EVENT_REWARD_REDEEMED = "kidschores_reward_redeemed"


# --------------------------------------------------------------------
# Actions
# --------------------------------------------------------------------

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


# --------------------------------------------------------------------
# Sensor Attributes
# --------------------------------------------------------------------
ATTR_ACHIEVEMENT_NAME = "achievement_name"
ATTR_ALL_EARNED_BADGES = "all_earned_badges"
ATTR_ALLOW_MULTIPLE_CLAIMS_PER_DAY = "allow_multiple_claims_per_day"
ATTR_APPLICABLE_DAYS = "applicable_days"
ATTR_AWARDED = "awarded"
ATTR_ASSIGNED_KIDS = "assigned_kids"
ATTR_ASSOCIATED_CHORE = "associated_chore"
ATTR_BADGES = "badges"
ATTR_BONUS_NAME = "bonus_name"
ATTR_BONUS_POINTS = "bonus_points"
ATTR_CAL_ALL_DAY = "all_day"
ATTR_CAL_DESCRIPTION = "description"
ATTR_CAL_END = "end"
ATTR_CAL_MANUFACTURER = "manufacturer"
ATTR_CAL_START = "start"
ATTR_CAL_SUMMARY = "summary"
ATTR_CHALLENGE_NAME = "challenge_name"
ATTR_CHALLENGE_TYPE = "challenge_type"
ATTR_CHORE_APPROVALS_COUNT = "chore_approvals_count"
ATTR_CHORE_APPROVALS_TODAY = "chore_approvals_today"
ATTR_CHORE_CLAIMS_COUNT = "chore_claims_count"
ATTR_CHORE_CURRENT_STREAK = "chore_current_streak"
ATTR_CHORE_HIGHEST_STREAK = "chore_highest_streak"
ATTR_CHORE_NAME = "chore_name"
ATTR_CLAIMED_ON = "Claimed on"
ATTR_COST = "cost"
ATTR_CRITERIA = "criteria"
ATTR_CUSTOM_FREQUENCY_INTERVAL = "custom_frequency_interval"
ATTR_CUSTOM_FREQUENCY_UNIT = "custom_frequency_unit"
ATTR_DEFAULT_POINTS = "default_points"
ATTR_DESCRIPTION = "description"
ATTR_DUE_DATE = "due_date"
ATTR_END_DATE = "end_date"
ATTR_GLOBAL_STATE = "global_state"
ATTR_HIGHEST_BADGE_THRESHOLD_VALUE = "highest_badge_threshold_value"
ATTR_KID_NAME = "kid_name"
ATTR_KID_STATE = "kid_state"
ATTR_LABELS = "labels"
ATTR_KIDS_EARNED = "kids_earned"
ATTR_LAST_DATE = "last_date"
ATTR_PARTIAL_ALLOWED = "partial_allowed"
ATTR_PENALTY_NAME = "penalty_name"
ATTR_PENALTY_POINTS = "penalty_points"
ATTR_POINTS_MULTIPLIER = "points_multiplier"
ATTR_POINTS_TO_NEXT_BADGE = "points_to_next_badge"
ATTR_RAW_PROGRESS = "raw_progress"
ATTR_RAW_STREAK = "raw_streak"
ATTR_RECURRING_FREQUENCY = "recurring_frequency"
ATTR_REDEEMED_ON = "Redeemed on"
ATTR_REWARD_APPROVALS_COUNT = "reward_approvals_count"
ATTR_REWARD_CLAIMS_COUNT = "reward_claims_count"
ATTR_REWARD_NAME = "reward_name"
ATTR_REWARD_POINTS = "reward_points"
ATTR_START_DATE = "start_date"
ATTR_SHARED_CHORE = "shared_chore"
ATTR_TARGET_VALUE = "target_value"
ATTR_THRESHOLD_TYPE = "threshold_type"
ATTR_TYPE = "type"


# --------------------------------------------------------------------
# Sensor Types
# --------------------------------------------------------------------
SENSOR_TYPE_BADGES = "badges"
SENSOR_TYPE_BONUS_APPLIES = "bonus_applies"
SENSOR_TYPE_CHORE_APPROVALS = "chore_approvals"
SENSOR_TYPE_CHORE_CLAIMS = "chore_claims"
SENSOR_TYPE_COMPLETED_DAILY = "completed_daily"
SENSOR_TYPE_COMPLETED_MONTHLY = "completed_monthly"
SENSOR_TYPE_COMPLETED_WEEKLY = "completed_weekly"
SENSOR_TYPE_PENDING_CHORE_APPROVALS = "pending_chore_approvals"
SENSOR_TYPE_PENDING_REWARD_APPROVALS = "pending_reward_approvals"
SENSOR_TYPE_PENALTY_APPLIES = "penalty_applies"
SENSOR_TYPE_POINTS = "points"
SENSOR_TYPE_REWARD_APPROVALS = "reward_approvals"
SENSOR_TYPE_REWARD_CLAIMS = "reward_claims"


# --------------------------------------------------------------------
# Services
# --------------------------------------------------------------------
SERVICE_APPLY_BONUS = "apply_bonus"
SERVICE_APPLY_PENALTY = "apply_penalty"
SERVICE_APPROVE_CHORE = "approve_chore"
SERVICE_APPROVE_REWARD = "approve_reward"
SERVICE_CLAIM_CHORE = "claim_chore"
SERVICE_DISAPPROVE_CHORE = "disapprove_chore"
SERVICE_DISAPPROVE_REWARD = "disapprove_reward"
SERVICE_REDEEM_REWARD = "redeem_reward"
SERVICE_RESET_ALL_CHORES = "reset_all_chores"
SERVICE_RESET_ALL_DATA = "reset_all_data"
SERVICE_RESET_BONUSES = "reset_bonuses"
SERVICE_RESET_OVERDUE_CHORES = "reset_overdue_chores"
SERVICE_RESET_PENALTIES = "reset_penalties"
SERVICE_RESET_REWARDS = "reset_rewards"
SERVICE_SET_CHORE_DUE_DATE = "set_chore_due_date"
SERVICE_SKIP_CHORE_DUE_DATE = "skip_chore_due_date"


# --------------------------------------------------------------------
# Field Names (for service calls)
# --------------------------------------------------------------------
FIELD_BONUS_NAME = "bonus_name"
FIELD_CHORE_ID = "chore_id"
FIELD_CHORE_NAME = "chore_name"
FIELD_DUE_DATE = "due_date"
FIELD_KID_NAME = "kid_name"
FIELD_PARENT_NAME = "parent_name"
FIELD_PENALTY_NAME = "penalty_name"
FIELD_POINTS_AWARDED = "points_awarded"
FIELD_REWARD_NAME = "reward_name"


# --------------------------------------------------------------------
# Labels
# --------------------------------------------------------------------
LABEL_BADGES = "Badges"
LABEL_COMPLETED_DAILY = "Daily Completed Chores"
LABEL_COMPLETED_MONTHLY = "Monthly Completed Chores"
LABEL_COMPLETED_WEEKLY = "Weekly Completed Chores"
LABEL_NONE = ""
LABEL_POINTS = "Points"


# --------------------------------------------------------------------
# Button Prefixes
# --------------------------------------------------------------------
BUTTON_BONUS_PREFIX = "bonus_button_"
BUTTON_DISAPPROVE_CHORE_PREFIX = "disapprove_chore_button_"
BUTTON_DISAPPROVE_REWARD_PREFIX = "disapprove_reward_button_"
BUTTON_PENALTY_PREFIX = "penalty_button_"
BUTTON_REWARD_PREFIX = "reward_button_"


# --------------------------------------------------------------------
# Errors and Warnings
# --------------------------------------------------------------------
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
ERROR_USER_NOT_AUTHORIZED = "User is not authorized to perform this action."
MSG_NO_ENTRY_FOUND = "No KidsChores entry found"

# Unknown States
UNKNOWN_CHORE = "Unknown Chore"  # Error for unknown chore
UNKNOWN_KID = "Unknown Kid"  # Error for unknown kid
UNKNOWN_REWARD = "Unknown Reward"  # Error for unknown reward

# Config Flow & Options Flow Error Keys
CFOP_ERROR_ACHIEVEMENT_NAME = "name"
CFOP_ERROR_BADGE_NAME = "badge_name"
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


# --------------------------------------------------------------------
# Parent Approval Workflow
# --------------------------------------------------------------------
PARENT_APPROVAL_REQUIRED = True  # Enable parent approval for certain actions
HA_USERNAME_LINK_ENABLED = True  # Enable linking kids to HA usernames


# --------------------------------------------------------------------
# Calendar Attributes
# --------------------------------------------------------------------
ATTR_CAL_ALL_DAY = "all_day"
ATTR_CAL_DESCRIPTION = "description"
ATTR_CAL_END = "end"
ATTR_CAL_MANUFACTURER = "manufacturer"
ATTR_CAL_START = "start"
ATTR_CAL_SUMMARY = "summary"


# --------------------------------------------------------------------
# Translation Keys
# --------------------------------------------------------------------

# ConfigFlow & OptionsFlow translation keys
TRANS_KEY_ERROR_SINGLE_INSTANCE = "single_instance_allowed"
TRANS_KEY_OPTIONS_FLOW_BADGE_TYPE = "badge_type"
TRANS_KEY_OPTIONS_FLOW_CHORE_MUST_BE_SELECTED = "a_chore_must_be_selected"
TRANS_KEY_OPTIONS_FLOW_DUE_DATE_IN_PAST = "due_date_in_past"
TRANS_KEY_OPTIONS_FLOW_DUPLICATE_ACHIEVEMENT = "duplicate_achievement"
TRANS_KEY_OPTIONS_FLOW_DUPLICATE_BADGE = "duplicate_badge"
TRANS_KEY_OPTIONS_FLOW_DUPLICATE_BONUS = "duplicate_bonus"
TRANS_KEY_OPTIONS_FLOW_DUPLICATE_CHALLENGE = "duplicate_challenge"
TRANS_KEY_OPTIONS_FLOW_DUPLICATE_CHORE = "duplicate_chore"
TRANS_KEY_OPTIONS_FLOW_DUPLICATE_KID = "duplicate_kid"
TRANS_KEY_OPTIONS_FLOW_DUPLICATE_PARENT = "duplicate_parent"
TRANS_KEY_OPTIONS_FLOW_DUPLICATE_PENALTY = "duplicate_penalty"
TRANS_KEY_OPTIONS_FLOW_DUPLICATE_REWARD = "duplicate_reward"
TRANS_KEY_OPTIONS_FLOW_END_DATE_IN_PAST = "end_date_in_past"
TRANS_KEY_OPTIONS_FLOW_END_DATE_NOT_AFTER_START_DATE = "end_date_not_after_start_date"
TRANS_KEY_OPTIONS_FLOW_INVALID_ACTION = "invalid_action"
TRANS_KEY_OPTIONS_FLOW_INVALID_DUE_DATE = "invalid_due_date"
TRANS_KEY_OPTIONS_FLOW_INVALID_END_DATE = "invalid_end_date"
TRANS_KEY_OPTIONS_FLOW_INVALID_ENTITY = "invalid_entity"
TRANS_KEY_OPTIONS_FLOW_INVALID_KID_NAME = "invalid_kid_name"
TRANS_KEY_OPTIONS_FLOW_INVALID_START_DATE = "invalid_start_date"
TRANS_KEY_OPTIONS_FLOW_MAIN_MENU = "main_menu"
TRANS_KEY_OPTIONS_FLOW_MANAGE_ACTIONS = "manage_actions"
TRANS_KEY_OPTIONS_FLOW_NO_ENTITY_TYPE = "no_{}s"
TRANS_KEY_OPTIONS_FLOW_START_DATE_IN_PAST = "start_date_in_past"
TRANS_KEY_OPTIONS_FLOW_SETUP_COMPLETE = "setup_complete"


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
TRANS_KEY_FLOW_HELPERS_RESET_PERIOD = "reset_period"
TRANS_KEY_FLOW_HELPERS_SELECTED_CHORE_ID = "selected_chore_id"
TRANS_KEY_FLOW_HELPERS_THRESHOLD_TYPE = "threshold_type"


# --------------------------------------------------------------------
# List Keys
# --------------------------------------------------------------------

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

# Badge Award Mode
AWARD_MODE_OPTIONS = ["points", "reward"]

# Badge Threshold Type
THRESHOLD_TYPE_OPTIONS = ["points", "chore_count"]

# Badge Cumulative Reset Period
BADGE_CUMULATIVE_RESET_PERIOD_OPTIONS = [CONF_YEAR_END, CONF_CUSTOM]

# Badge Reset Period
BADGE_PERIOD_OPTIONS = [CONF_WEEKLY, CONF_BIWEEKLY, CONF_MONTHLY, CONF_CUSTOM]

# Badge Special Occasion Types
OCCASION_TYPE_OPTIONS = [CONF_BIRTHDAY, CONF_HOLIDAY, CONF_CUSTOM]

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
