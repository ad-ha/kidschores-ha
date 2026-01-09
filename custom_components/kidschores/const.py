# File: const.py
# pylint: disable=too-many-lines  # Constants module requires 2300+ lines for complete integration config
"""Constants for the KidsChores integration.

This file centralizes configuration keys, defaults, labels, domain names,
event names, and platform identifiers for consistency across the integration.
It also supports localization by defining all labels and UI texts used in sensors,
services, and options flow.
"""

import logging
from typing import Final

import homeassistant.util.dt as dt_util
from homeassistant.const import Platform


def set_default_timezone(hass):
    """Set the default timezone based on the Home Assistant configuration."""
    global DEFAULT_TIME_ZONE  # pylint: disable=global-statement
    DEFAULT_TIME_ZONE = dt_util.get_time_zone(hass.config.time_zone)


# ================================================================================================
# General / Integration Information
# ================================================================================================

KIDSCHORES_TITLE: Final = "KidsChores"
DOMAIN: Final = "kidschores"
LOGGER: Final = logging.getLogger(__package__)

# Supported platforms
PLATFORMS: Final = [
    Platform.BUTTON,
    Platform.CALENDAR,
    Platform.DATETIME,
    Platform.SELECT,
    Platform.SENSOR,
]

# Coordinator
COORDINATOR: Final = "coordinator"
COORDINATOR_SUFFIX: Final = "_coordinator"

# Storage
STORAGE_MANAGER: Final = "storage_manager"
STORAGE_KEY: Final = "kidschores_data"
STORAGE_KEY_LINKED_USERS: Final = "linked_users"
STORAGE_VERSION: Final = 1

# Default timezone (set once hass is available)
# pylint: disable=invalid-name
DEFAULT_TIME_ZONE = None  # noqa: N816

# Schema version for config→storage migration
DATA_SCHEMA_VERSION: Final = "schema_version"
SCHEMA_VERSION_STORAGE_ONLY: Final = (
    42  # v42: Storage-only mode (staying on v42 per 2025-12-19 decision)
)

# Float precision for stored numeric values (points, chore stats, etc.)
# Prevents Python float arithmetic drift (e.g., 27.499999999999996 → 27.5)
DATA_FLOAT_PRECISION: Final = 2

# Storage metadata section (for future v43+)
DATA_META: Final = "meta"
DATA_META_SCHEMA_VERSION: Final = "schema_version"
DATA_META_LAST_MIGRATION_DATE: Final = "last_migration_date"
DATA_META_MIGRATIONS_APPLIED: Final = "migrations_applied"

# Storage Data Keys (Phase 2b)
# Top-level keys in .storage/kidschores_data (not entity-specific DATA_KID_*, DATA_CHORE_*, etc.)
DATA_KEY_KIDS: Final = "kids"
DATA_KEY_PARENTS: Final = "parents"
DATA_KEY_CHORES: Final = "chores"
DATA_KEY_REWARDS: Final = "rewards"
DATA_KEY_BADGES: Final = "badges"
DATA_KEY_ACHIEVEMENTS: Final = "achievements"
DATA_KEY_CHALLENGES: Final = "challenges"
DATA_KEY_LINKED_USERS: Final = "linked_users"  # Matches STORAGE_KEY_LINKED_USERS

# Entity Type Identifiers (Phase 2 Step 2 - DRY Refactoring)
# Used in generic entity lookup functions to identify entity type
ENTITY_TYPE_KID: Final = "kid"
ENTITY_TYPE_CHORE: Final = "chore"
ENTITY_TYPE_REWARD: Final = "reward"
ENTITY_TYPE_PENALTY: Final = "penalty"
ENTITY_TYPE_BADGE: Final = "badge"
ENTITY_TYPE_BONUS: Final = "bonus"
ENTITY_TYPE_PARENT: Final = "parent"
ENTITY_TYPE_ACHIEVEMENT: Final = "achievement"
ENTITY_TYPE_CHALLENGE: Final = "challenge"

# Storage Structure Keys (Phase 3 - config_flow remediation)
# Common keys used in storage file structure validation and diagnostics
DATA_KEY_VERSION: Final = "version"  # Schema version key
DATA_KEY_DATA: Final = "data"  # Main data container key
DATA_KEY_KEY: Final = "key"  # Storage manager key parameter
DATA_KEY_HOME_ASSISTANT: Final = "home_assistant"  # Diagnostic format detection

# Storage Path Segment (Phase 3)
STORAGE_PATH_SEGMENT: Final = ".storage"  # Storage directory name

# Format Strings (Phase 2b)
# Date/time format patterns used across the integration
FORMAT_DATETIME_ISO: Final = "%Y-%m-%dT%H:%M:%S.%f%z"  # ISO 8601 with timezone
FORMAT_DATETIME_DISPLAY: Final = "%Y-%m-%d %H:%M"  # Human-readable datetime
FORMAT_DATE_ONLY: Final = "%Y-%m-%d"  # Date without time

# Update interval (seconds)
DEFAULT_UPDATE_INTERVAL: Final = 5


# ================================================================================================
# Core Constants (used by other constants)
# ================================================================================================

# Time Units
TIME_UNIT_DAY: Final = "day"
TIME_UNIT_DAYS: Final = "days"
TIME_UNIT_HOUR: Final = "hour"
TIME_UNIT_HOURS: Final = "hours"
TIME_UNIT_MINUTE: Final = "minute"
TIME_UNIT_MINUTES: Final = "minutes"
TIME_UNIT_MONTH: Final = "month"
TIME_UNIT_MONTHS: Final = "months"
TIME_UNIT_QUARTER: Final = "quarter"
TIME_UNIT_QUARTERS: Final = "quarters"
TIME_UNIT_WEEK: Final = "week"
TIME_UNIT_WEEKS: Final = "weeks"
TIME_UNIT_YEAR: Final = "year"
TIME_UNIT_YEARS: Final = "years"

# Frequencies
FREQUENCY_BIWEEKLY: Final = "biweekly"
FREQUENCY_CUSTOM: Final = "custom"
FREQUENCY_CUSTOM_1_MONTH: Final = "custom_1_month"
FREQUENCY_CUSTOM_1_QUARTER: Final = "custom_1_quarter"
FREQUENCY_CUSTOM_1_WEEK: Final = "custom_1_week"
FREQUENCY_CUSTOM_1_YEAR: Final = "custom_1_year"
FREQUENCY_DAILY: Final = "daily"
FREQUENCY_MONTHLY: Final = "monthly"
FREQUENCY_NONE: Final = "none"
FREQUENCY_QUARTERLY: Final = "quarterly"
FREQUENCY_WEEKLY: Final = "weekly"
FREQUENCY_YEARLY: Final = "yearly"

# Periods
PERIOD_ALL_TIME: Final = "all_time"
PERIOD_DAY_END: Final = "day_end"
PERIOD_MONTH_END: Final = "month_end"
PERIOD_QUARTER_END: Final = "quarter_end"
PERIOD_WEEK_END: Final = "week_end"
PERIOD_YEAR_END: Final = "year_end"

# Sentinel Values
SENTINEL_EMPTY: Final = ""
SENTINEL_NONE: Final = None
SENTINEL_NONE_TEXT: Final = "None"

# Display Values
DISPLAY_DOT: Final = "."
DISPLAY_UNKNOWN: Final = "Unknown"

# Occasion Types
OCCASION_BIRTHDAY: Final = "birthday"
OCCASION_HOLIDAY: Final = "holiday"


# ================================================================================================
# Configuration Keys (CONF_*)
# ================================================================================================

# Flow Management
# ConfigFlow steps
CONFIG_FLOW_STEP_ACHIEVEMENT_COUNT: Final = "achievement_count"
CONFIG_FLOW_STEP_ACHIEVEMENTS: Final = "achievements"
CONFIG_FLOW_STEP_BADGE_COUNT: Final = "badge_count"
CONFIG_FLOW_STEP_BADGES: Final = "badges"
CONFIG_FLOW_STEP_BONUS_COUNT: Final = "bonus_count"
CONFIG_FLOW_STEP_BONUSES: Final = "bonuses"
CONFIG_FLOW_STEP_CHALLENGE_COUNT: Final = "challenge_count"
CONFIG_FLOW_STEP_CHALLENGES: Final = "challenges"
CONFIG_FLOW_STEP_CHORE_COUNT: Final = "chore_count"
CONFIG_FLOW_STEP_CHORES: Final = "chores"
CONFIG_FLOW_STEP_FINISH: Final = "finish"
CONFIG_FLOW_STEP_DATA_RECOVERY: Final = "data_recovery"
CONFIG_FLOW_STEP_INTRO: Final = "intro"
CONFIG_FLOW_STEP_KID_COUNT: Final = "kid_count"
CONFIG_FLOW_STEP_KIDS: Final = "kids"
CONFIG_FLOW_STEP_PARENT_COUNT: Final = "parent_count"
CONFIG_FLOW_STEP_PARENTS: Final = "parents"
CONFIG_FLOW_STEP_PENALTY_COUNT: Final = "penalty_count"
CONFIG_FLOW_STEP_PENALTIES: Final = "penalties"
CONFIG_FLOW_STEP_POINTS: Final = "points_label"
CONFIG_FLOW_STEP_RECONFIGURE: Final = "reconfigure"
CONFIG_FLOW_STEP_REWARD_COUNT: Final = "reward_count"
CONFIG_FLOW_STEP_REWARDS: Final = "rewards"

# Config Flow Abort Reasons (Phase 3b)
CONFIG_FLOW_ABORT_RECONFIGURE_FAILED: Final = "reconfigure_failed"
CONFIG_FLOW_ABORT_RECONFIGURE_SUCCESSFUL: Final = "reconfigure_successful"

# OptionsFlow Management Menus Keys
OPTIONS_FLOW_DIC_ACHIEVEMENT: Final = "achievement"
OPTIONS_FLOW_DIC_BADGE: Final = "badge"
OPTIONS_FLOW_DIC_BONUS: Final = "bonus"
OPTIONS_FLOW_DIC_CHALLENGE: Final = "challenge"
OPTIONS_FLOW_DIC_CHORE: Final = "chore"
OPTIONS_FLOW_DIC_KID: Final = "kid"
OPTIONS_FLOW_DIC_PARENT: Final = "parent"
OPTIONS_FLOW_DIC_PENALTY: Final = "penalty"
OPTIONS_FLOW_DIC_REWARD: Final = "reward"

# OptionsFlow Backup Management Menu
OPTIONS_FLOW_RESTORE_BACKUP: Final = "restore_backup"
OPTIONS_FLOW_BACKUP_ACTION_SELECT: Final = "select_backup_action"
OPTIONS_FLOW_BACKUP_ACTION_CREATE: Final = "create_backup"
OPTIONS_FLOW_BACKUP_ACTION_DELETE: Final = "delete_backup"
OPTIONS_FLOW_BACKUP_ACTION_RESTORE: Final = "restore_backup"
OPTIONS_FLOW_ACTIONS_ADD: Final = "add"
OPTIONS_FLOW_ACTIONS_BACK: Final = "back"
OPTIONS_FLOW_ACTIONS_DELETE: Final = "delete"
OPTIONS_FLOW_ACTIONS_EDIT: Final = "edit"
OPTIONS_FLOW_ACHIEVEMENTS: Final = "manage_achievement"
OPTIONS_FLOW_BADGES: Final = "manage_badge"
OPTIONS_FLOW_BONUSES: Final = "manage_bonus"
OPTIONS_FLOW_CHALLENGES: Final = "manage_challenge"
OPTIONS_FLOW_CHORES: Final = "manage_chore"
OPTIONS_FLOW_FINISH: Final = "done"
OPTIONS_FLOW_GENERAL_OPTIONS: Final = "general_options"
OPTIONS_FLOW_KIDS: Final = "manage_kid"
OPTIONS_FLOW_PARENTS: Final = "manage_parent"
OPTIONS_FLOW_PENALTIES: Final = "manage_penalty"
OPTIONS_FLOW_POINTS: Final = "manage_points"
OPTIONS_FLOW_REWARDS: Final = "manage_reward"

# OptionsFlow Steps
OPTIONS_FLOW_STEP_INIT: Final = "init"
OPTIONS_FLOW_STEP_MANAGE_ENTITY: Final = "manage_entity"
OPTIONS_FLOW_STEP_MANAGE_GENERAL_OPTIONS: Final = "manage_general_options"
OPTIONS_FLOW_STEP_MANAGE_POINTS: Final = "manage_points"
OPTIONS_FLOW_STEP_RESTORE_BACKUP: Final = "restore_backup"
OPTIONS_FLOW_STEP_CONFIRM_RESTORE: Final = "confirm_restore"
OPTIONS_FLOW_STEP_SELECT_ENTITY: Final = "select_entity"

# OptionsFlow Backup Management Steps
OPTIONS_FLOW_STEP_BACKUP_ACTIONS: Final = "backup_actions_menu"
OPTIONS_FLOW_STEP_SELECT_BACKUP_TO_DELETE: Final = "select_backup_to_delete"
OPTIONS_FLOW_STEP_SELECT_BACKUP_TO_RESTORE: Final = "select_backup_to_restore"
OPTIONS_FLOW_STEP_CREATE_MANUAL_BACKUP: Final = "create_manual_backup"
OPTIONS_FLOW_STEP_CREATE_BACKUP_CONFIRM: Final = "create_backup_confirm"
OPTIONS_FLOW_STEP_CREATE_BACKUP_SUCCESS: Final = "create_backup_success"
OPTIONS_FLOW_STEP_DELETE_BACKUP_CONFIRM: Final = "delete_backup_confirm"
OPTIONS_FLOW_STEP_RESTORE_BACKUP_CONFIRM: Final = "restore_backup_confirm"
OPTIONS_FLOW_STEP_PASTE_JSON_RESTORE: Final = "paste_json_restore"

OPTIONS_FLOW_STEP_ADD_ACHIEVEMENT: Final = "add_achievement"
OPTIONS_FLOW_STEP_ADD_BADGE: Final = "add_badge"
OPTIONS_FLOW_STEP_ADD_BADGE_ACHIEVEMENT: Final = "add_badge_achievement"
OPTIONS_FLOW_STEP_ADD_BADGE_CHALLENGE: Final = "add_badge_challenge"
OPTIONS_FLOW_STEP_ADD_BADGE_CUMULATIVE: Final = "add_badge_cumulative"
OPTIONS_FLOW_STEP_ADD_BADGE_DAILY: Final = "add_badge_daily"
OPTIONS_FLOW_STEP_ADD_BADGE_PERIODIC: Final = "add_badge_periodic"
OPTIONS_FLOW_STEP_ADD_BADGE_SPECIAL: Final = "add_badge_special"
OPTIONS_FLOW_STEP_ADD_BONUS: Final = "add_bonus"
OPTIONS_FLOW_STEP_ADD_CHALLENGE: Final = "add_challenge"
OPTIONS_FLOW_STEP_ADD_CHORE: Final = "add_chore"
OPTIONS_FLOW_STEP_ADD_KID: Final = "add_kid"
OPTIONS_FLOW_STEP_ADD_PARENT: Final = "add_parent"
OPTIONS_FLOW_STEP_ADD_PENALTY: Final = "add_penalty"
OPTIONS_FLOW_STEP_ADD_REWARD: Final = "add_reward"

OPTIONS_FLOW_STEP_EDIT_ACHIEVEMENT: Final = "edit_achievement"
OPTIONS_FLOW_STEP_EDIT_BADGE_ACHIEVEMENT: Final = "edit_badge_achievement"
OPTIONS_FLOW_STEP_EDIT_BADGE_CHALLENGE: Final = "edit_badge_challenge"
OPTIONS_FLOW_STEP_EDIT_BADGE_CUMULATIVE: Final = "edit_badge_cumulative"
OPTIONS_FLOW_STEP_EDIT_BADGE_DAILY: Final = "edit_badge_daily"
OPTIONS_FLOW_STEP_EDIT_BADGE_PERIODIC: Final = "edit_badge_periodic"
OPTIONS_FLOW_STEP_EDIT_BADGE_SPECIAL: Final = "edit_badge_special"
OPTIONS_FLOW_STEP_EDIT_BONUS: Final = "edit_bonus"
OPTIONS_FLOW_STEP_EDIT_CHALLENGE: Final = "edit_challenge"
OPTIONS_FLOW_STEP_EDIT_CHORE: Final = "edit_chore"
OPTIONS_FLOW_STEP_EDIT_CHORE_PER_KID_DATES: Final = "edit_chore_per_kid_dates"
OPTIONS_FLOW_STEP_EDIT_KID: Final = "edit_kid"
OPTIONS_FLOW_STEP_EDIT_PARENT: Final = "edit_parent"
OPTIONS_FLOW_STEP_EDIT_PENALTY: Final = "edit_penalty"
OPTIONS_FLOW_STEP_EDIT_REWARD: Final = "edit_reward"

OPTIONS_FLOW_STEP_DELETE_ACHIEVEMENT: Final = "delete_achievement"
OPTIONS_FLOW_STEP_DELETE_BADGE: Final = "delete_badge"
OPTIONS_FLOW_STEP_DELETE_BONUS: Final = "delete_bonus"
OPTIONS_FLOW_STEP_DELETE_CHALLENGE: Final = "delete_challenge"
OPTIONS_FLOW_STEP_DELETE_CHORE: Final = "delete_chore"
OPTIONS_FLOW_STEP_DELETE_KID: Final = "delete_kid"
OPTIONS_FLOW_STEP_DELETE_PARENT: Final = "delete_parent"
OPTIONS_FLOW_STEP_DELETE_PENALTY: Final = "delete_penalty"
OPTIONS_FLOW_STEP_DELETE_REWARD: Final = "delete_reward"

# ConfigFlow & OptionsFlow User Input Fields

# GLOBAL
CFOF_GLOBAL_INPUT_INTERNAL_ID: Final = "internal_id"

# DATA RECOVERY
CFOF_DATA_RECOVERY_INPUT_SELECTION: Final = "backup_selection"
CFOF_DATA_RECOVERY_INPUT_JSON_DATA: Final = "json_data"
CFOF_RESTORE_BACKUP_INPUT_SELECTION: Final = "backup_file"

# KIDS
CFOF_KIDS_INPUT_DASHBOARD_LANGUAGE: Final = "dashboard_language"
CFOF_KIDS_INPUT_ENABLE_MOBILE_NOTIFICATIONS: Final = "enable_mobile_notifications"
CFOF_KIDS_INPUT_ENABLE_PERSISTENT_NOTIFICATIONS: Final = (
    "enable_persistent_notifications"
)
CFOF_KIDS_INPUT_HA_USER: Final = "ha_user"
CFOF_KIDS_INPUT_KID_COUNT: Final = "kid_count"
CFOF_KIDS_INPUT_KID_NAME: Final = "kid_name"
CFOF_KIDS_INPUT_MOBILE_NOTIFY_SERVICE: Final = "mobile_notify_service"

# PARENTS
CFOF_PARENTS_INPUT_ASSOCIATED_KIDS: Final = "associated_kids"
CFOF_PARENTS_INPUT_ENABLE_MOBILE_NOTIFICATIONS: Final = "enable_mobile_notifications"
CFOF_PARENTS_INPUT_ENABLE_PERSISTENT_NOTIFICATIONS: Final = (
    "enable_persistent_notifications"
)
CFOF_PARENTS_INPUT_HA_USER: Final = "ha_user_id"
CFOF_PARENTS_INPUT_MOBILE_NOTIFY_SERVICE: Final = "mobile_notify_service"
CFOF_PARENTS_INPUT_NAME: Final = "parent_name"
CFOF_PARENTS_INPUT_PARENT_COUNT: Final = "parent_count"

# CHORES
CFOF_CHORES_INPUT_APPROVAL_RESET_TYPE: Final = "approval_reset_type"
CFOF_CHORES_INPUT_APPLICABLE_DAYS: Final = "applicable_days"
CFOF_CHORES_INPUT_ASSIGNED_KIDS: Final = "assigned_kids"
CFOF_CHORES_INPUT_CHORE_COUNT: Final = "chore_count"
CFOF_CHORES_INPUT_CUSTOM_INTERVAL: Final = "custom_interval"
CFOF_CHORES_INPUT_CUSTOM_INTERVAL_UNIT: Final = "custom_interval_unit"
CFOF_CHORES_INPUT_DEFAULT_POINTS: Final = "default_points"
CFOF_CHORES_INPUT_DESCRIPTION: Final = "chore_description"
CFOF_CHORES_INPUT_DUE_DATE: Final = "due_date"
CFOF_CHORES_INPUT_ICON: Final = "icon"
CFOF_CHORES_INPUT_COMPLETION_CRITERIA: Final = "completion_criteria"
CFOF_CHORES_INPUT_LABELS: Final = "chore_labels"
CFOF_CHORES_INPUT_NAME: Final = "chore_name"
CFOF_CHORES_INPUT_NOTIFY_ON_APPROVAL: Final = "notify_on_approval"
CFOF_CHORES_INPUT_NOTIFY_ON_CLAIM: Final = "notify_on_claim"
CFOF_CHORES_INPUT_NOTIFY_ON_DISAPPROVAL: Final = "notify_on_disapproval"
CFOF_CHORES_INPUT_RECURRING_FREQUENCY: Final = "recurring_frequency"
CFOF_CHORES_INPUT_SHARED_CHORE: Final = "shared_chore"
CFOF_CHORES_INPUT_OVERDUE_HANDLING_TYPE: Final = "overdue_handling_type"
CFOF_CHORES_INPUT_APPROVAL_RESET_PENDING_CLAIM_ACTION: Final = (
    "approval_reset_pending_claim_action"
)
CFOF_CHORES_INPUT_APPLY_TEMPLATE_TO_ALL: Final = "apply_template_to_all"
CFOF_CHORES_INPUT_AUTO_APPROVE: Final = "auto_approve"
CFOF_CHORES_INPUT_SHOW_ON_CALENDAR: Final = "show_on_calendar"
CFOF_CHORES_INPUT_NOTIFICATIONS: Final = "chore_notifications"

# BADGES
CFOF_BADGES_INPUT_ASSIGNED_KIDS: Final = "assigned_kids"
CFOF_BADGES_INPUT_ASSIGNED_TO: Final = "assigned_to"
CFOF_BADGES_INPUT_ASSOCIATED_ACHIEVEMENT: Final = "associated_achievement"
CFOF_BADGES_INPUT_ASSOCIATED_CHALLENGE: Final = "associated_challenge"
CFOF_BADGES_INPUT_AWARD_ITEMS: Final = "award_items"
CFOF_BADGES_INPUT_AWARD_MODE: Final = "award_mode"
CFOF_BADGES_INPUT_AWARD_POINTS: Final = "award_points"
CFOF_BADGES_INPUT_AWARD_REWARD: Final = "award_reward"
CFOF_BADGES_INPUT_BADGE_COUNT: Final = "badge_count"
CFOF_BADGES_INPUT_DAILY_THRESHOLD: Final = "daily_threshold"
CFOF_BADGES_INPUT_DAILY_THRESHOLD_TYPE: Final = "threshold_type"
CFOF_BADGES_INPUT_DESCRIPTION: Final = "badge_description"
CFOF_BADGES_INPUT_END_DATE: Final = "end_date"
CFOF_BADGES_INPUT_ICON: Final = "icon"
CFOF_BADGES_INPUT_LABELS: Final = "badge_labels"
CFOF_BADGES_INPUT_MAINTENANCE_RULES: Final = "maintenance_rules"
CFOF_BADGES_INPUT_NAME: Final = "badge_name"
CFOF_BADGES_INPUT_OCCASION_TYPE: Final = "occasion_type"
CFOF_BADGES_INPUT_POINTS_MULTIPLIER: Final = "points_multiplier"
CFOF_BADGES_INPUT_RESET_SCHEDULE: Final = "reset_schedule"
CFOF_BADGES_INPUT_RESET_SCHEDULE_CUSTOM_INTERVAL: Final = "custom_interval"
CFOF_BADGES_INPUT_RESET_SCHEDULE_CUSTOM_INTERVAL_UNIT: Final = "custom_interval_unit"
CFOF_BADGES_INPUT_RESET_SCHEDULE_END_DATE: Final = "end_date"
CFOF_BADGES_INPUT_RESET_SCHEDULE_GRACE_PERIOD_DAYS: Final = "grace_period_days"
CFOF_BADGES_INPUT_RESET_SCHEDULE_RECURRING_FREQUENCY: Final = "recurring_frequency"
CFOF_BADGES_INPUT_RESET_SCHEDULE_START_DATE: Final = "start_date"
CFOF_BADGES_INPUT_SELECTED_CHORES: Final = "selected_chores"
CFOF_BADGES_INPUT_START_DATE: Final = "start_date"
CFOF_BADGES_INPUT_TARGET_TYPE: Final = "target_type"
CFOF_BADGES_INPUT_TARGET_THRESHOLD_VALUE: Final = "threshold_value"
CFOF_BADGES_INPUT_TYPE: Final = "badge_type"

# REWARDS
CFOF_REWARDS_INPUT_COST: Final = "reward_cost"
CFOF_REWARDS_INPUT_DESCRIPTION: Final = "reward_description"
CFOF_REWARDS_INPUT_ICON: Final = "icon"
CFOF_REWARDS_INPUT_LABELS: Final = "reward_labels"
CFOF_REWARDS_INPUT_NAME: Final = "reward_name"
CFOF_REWARDS_INPUT_REWARD_COUNT: Final = "reward_count"

# BONUSES
CFOF_BONUSES_INPUT_BONUS_COUNT: Final = "bonus_count"
CFOF_BONUSES_INPUT_DESCRIPTION: Final = "bonus_description"
CFOF_BONUSES_INPUT_ICON: Final = "icon"
CFOF_BONUSES_INPUT_LABELS: Final = "bonus_labels"
CFOF_BONUSES_INPUT_NAME: Final = "bonus_name"
CFOF_BONUSES_INPUT_POINTS: Final = "bonus_points"

# PENALTIES
CFOF_PENALTIES_INPUT_DESCRIPTION: Final = "penalty_description"
CFOF_PENALTIES_INPUT_ICON: Final = "icon"
CFOF_PENALTIES_INPUT_LABELS: Final = "penalty_labels"
CFOF_PENALTIES_INPUT_NAME: Final = "penalty_name"
CFOF_PENALTIES_INPUT_PENALTY_COUNT: Final = "penalty_count"
CFOF_PENALTIES_INPUT_POINTS: Final = "penalty_points"

# ACHIEVEMENTS
CFOF_ACHIEVEMENTS_INPUT_ACHIEVEMENT_COUNT: Final = "achievement_count"
CFOF_ACHIEVEMENTS_INPUT_ASSIGNED_KIDS: Final = "assigned_kids"
CFOF_ACHIEVEMENTS_INPUT_CRITERIA: Final = "criteria"
CFOF_ACHIEVEMENTS_INPUT_DESCRIPTION: Final = "description"
CFOF_ACHIEVEMENTS_INPUT_ICON: Final = "icon"
CFOF_ACHIEVEMENTS_INPUT_LABELS: Final = "achievement_labels"
CFOF_ACHIEVEMENTS_INPUT_NAME: Final = "name"
CFOF_ACHIEVEMENTS_INPUT_REWARD_POINTS: Final = "reward_points"
CFOF_ACHIEVEMENTS_INPUT_SELECTED_CHORE_ID: Final = "selected_chore_id"
CFOF_ACHIEVEMENTS_INPUT_TARGET_VALUE: Final = "target_value"
CFOF_ACHIEVEMENTS_INPUT_TYPE: Final = "type"

# CHALLENGES
CFOF_CHALLENGES_INPUT_ASSIGNED_KIDS: Final = "assigned_kids"
CFOF_CHALLENGES_INPUT_CHALLENGE_COUNT: Final = "challenge_count"
CFOF_CHALLENGES_INPUT_CRITERIA: Final = "criteria"
CFOF_CHALLENGES_INPUT_DESCRIPTION: Final = "description"
CFOF_CHALLENGES_INPUT_END_DATE: Final = "end_date"
CFOF_CHALLENGES_INPUT_ICON: Final = "icon"
CFOF_CHALLENGES_INPUT_LABELS: Final = "challenge_labels"
CFOF_CHALLENGES_INPUT_NAME: Final = "name"
CFOF_CHALLENGES_INPUT_REWARD_POINTS: Final = "reward_points"
CFOF_CHALLENGES_INPUT_SELECTED_CHORE_ID: Final = "selected_chore_id"
CFOF_CHALLENGES_INPUT_START_DATE: Final = "start_date"
CFOF_CHALLENGES_INPUT_TARGET_VALUE: Final = "target_value"
CFOF_CHALLENGES_INPUT_TYPE: Final = "type"

# OptionsFlow Input Fields
OPTIONS_FLOW_INPUT_ENTITY_NAME: Final = "entity_name"
OPTIONS_FLOW_INPUT_INTERNAL_ID: Final = "internal_id"
OPTIONS_FLOW_INPUT_MENU_SELECTION: Final = "menu_selection"
OPTIONS_FLOW_INPUT_MANAGE_ACTION: Final = "manage_action"

# OptionsFlow Backup Management Input Fields
CFOF_BACKUP_ACTION_SELECTION: Final = "backup_action_selection"
CFOF_BACKUP_SELECTION: Final = "backup_selection"

# OptionsFlow Data Fields
OPTIONS_FLOW_DATA_ENTITY_NAME: Final = "name"

# OptionsFlow Placeholders
OPTIONS_FLOW_PLACEHOLDER_ACTION: Final = "action"
OPTIONS_FLOW_PLACEHOLDER_ACHIEVEMENT_NAME: Final = "achievement_name"
OPTIONS_FLOW_PLACEHOLDER_BADGE_NAME: Final = "badge_name"
OPTIONS_FLOW_PLACEHOLDER_BONUS_NAME: Final = "bonus_name"
OPTIONS_FLOW_PLACEHOLDER_CHALLENGE_NAME: Final = "challenge_name"
OPTIONS_FLOW_PLACEHOLDER_CHORE_NAME: Final = "chore_name"
OPTIONS_FLOW_PLACEHOLDER_ENTITY_TYPE: Final = "entity_type"
OPTIONS_FLOW_PLACEHOLDER_KID_NAME: Final = "kid_name"
OPTIONS_FLOW_PLACEHOLDER_PARENT_NAME: Final = "parent_name"
OPTIONS_FLOW_PLACEHOLDER_PENALTY_NAME: Final = "penalty_name"
OPTIONS_FLOW_PLACEHOLDER_REWARD_NAME: Final = "reward_name"
OPTIONS_FLOW_PLACEHOLDER_SUMMARY: Final = "summary"


# OptionsFlow Helpers
OPTIONS_FLOW_ASYNC_STEP_PREFIX: Final = "async_step_"
OPTIONS_FLOW_ASYNC_STEP_ADD_PREFIX: Final = "async_step_add_"
OPTIONS_FLOW_MENU_MANAGE_PREFIX: Final = "manage_"


# Global Settings
CONF_CALENDAR_SHOW_PERIOD: Final = "calendar_show_period"
CONF_POINTS_ADJUST_VALUES: Final = "points_adjust_values"
CONF_POINTS_ICON: Final = "points_icon"
CONF_POINTS_LABEL: Final = "points_label"
CONF_RETENTION_DAILY: Final = "retention_daily"
CONF_RETENTION_MONTHLY: Final = "retention_monthly"
CONF_RETENTION_PERIODS: Final = (
    "retention_periods"  # Consolidated field (Daily|Weekly|Monthly|Yearly)
)
CONF_RETENTION_WEEKLY: Final = "retention_weekly"
CONF_RETENTION_YEARLY: Final = "retention_yearly"
CONF_UPDATE_INTERVAL: Final = "update_interval"

# Backup Management Configuration
CONF_BACKUPS_MAX_RETAINED: Final = "backups_max_retained"
DEFAULT_BACKUPS_MAX_RETAINED: Final = 5  # Keep last N backups per tag (0 = disabled)
MIN_BACKUPS_MAX_RETAINED: Final = 0  # 0 = disable automatic backups
MAX_BACKUPS_MAX_RETAINED: Final = 10  # Maximum number of backups to retain

# Backup Tags (for backup filename identification)
BACKUP_TAG_RECOVERY: Final = "recovery"  # Data recovery actions
BACKUP_TAG_REMOVAL: Final = "removal"  # Integration removal
BACKUP_TAG_RESET: Final = "reset"  # Factory reset
BACKUP_TAG_PRE_MIGRATION: Final = (
    "pre-migration"  # Before schema upgrade (never deleted)
)
BACKUP_TAG_MANUAL: Final = "manual"  # User-initiated (never deleted)

# System Settings (ConfigFlow & OptionsFlow)  Phase 3c: Consolidation
CFOF_SYSTEM_INPUT_POINTS_LABEL: Final = "points_label"
CFOF_SYSTEM_INPUT_POINTS_ICON: Final = "points_icon"
CFOF_SYSTEM_INPUT_UPDATE_INTERVAL: Final = "update_interval"
CFOF_SYSTEM_INPUT_CALENDAR_SHOW_PERIOD: Final = "calendar_show_period"
CFOF_SYSTEM_INPUT_RETENTION_DAILY: Final = "retention_daily"
CFOF_SYSTEM_INPUT_RETENTION_WEEKLY: Final = "retention_weekly"
CFOF_SYSTEM_INPUT_RETENTION_MONTHLY: Final = "retention_monthly"
CFOF_SYSTEM_INPUT_RETENTION_YEARLY: Final = "retention_yearly"
CFOF_SYSTEM_INPUT_POINTS_ADJUST_VALUES: Final = "points_adjust_values"

# Additional system settings form inputs (General Options)
CFOF_SYSTEM_INPUT_RETENTION_PERIODS: Final = "retention_periods"
CFOF_SYSTEM_INPUT_SHOW_LEGACY_ENTITIES: Final = "show_legacy_entities"
CFOF_SYSTEM_INPUT_BACKUPS_MAX_RETAINED: Final = "backups_max_retained"

# Chore Custom Interval Reset Periods
CUSTOM_INTERVAL_UNIT_OPTIONS: Final = [
    SENTINEL_EMPTY,
    TIME_UNIT_DAYS,
    TIME_UNIT_WEEKS,
    TIME_UNIT_MONTHS,
]

# Entity-Specific Configuration
# (No legacy constants - all moved to _LEGACY section at end of file)

# Notifications
NOTIFICATION_EVENT: Final = "mobile_app_notification_action"

# Legacy / Extra Entity Settings
CONF_SHOW_LEGACY_ENTITIES: Final = "show_legacy_entities"

# Badge Types
BADGE_TYPE_ACHIEVEMENT_LINKED: Final = "achievement_linked"
BADGE_TYPE_CHALLENGE_LINKED: Final = "challenge_linked"
BADGE_TYPE_CUMULATIVE: Final = "cumulative"
BADGE_TYPE_DAILY: Final = "daily"
BADGE_TYPE_PERIODIC: Final = "periodic"
BADGE_TYPE_SPECIAL_OCCASION: Final = "special_occasion"

# Achievement Types
ACHIEVEMENT_TYPE_DAILY_MIN: Final = "daily_minimum"
ACHIEVEMENT_TYPE_STREAK: Final = "chore_streak"
ACHIEVEMENT_TYPE_TOTAL: Final = "chore_total"

# Challenge Types
CHALLENGE_TYPE_DAILY_MIN: Final = "daily_minimum"
CHALLENGE_TYPE_TOTAL_WITHIN_WINDOW: Final = "total_within_window"


# ------------------------------------------------------------------------------------------------
# Data Keys
# ------------------------------------------------------------------------------------------------
# Pluralization: Use SINGULAR for single-field data (DATA_KID_NAME = "name"), PLURAL for
# collections (DATA_KIDS = "kids"). See
# ARCHITECTURE.md "Entity Plurality" (lines 926-941) for details.

# GLOBAL
DATA_ACHIEVEMENTS: Final = "achievements"
DATA_ASSIGNED_KIDS: Final = "assigned_kids"
DATA_BADGES: Final = "badges"
DATA_BONUSES: Final = "bonuses"
DATA_CHALLENGES: Final = "challenges"
DATA_CHORES: Final = "chores"
DATA_COORDINATOR: Final = "coordinator"
DATA_GLOBAL_STATE_SUFFIX: Final = "_global_state"
DATA_INTERNAL_ID: Final = "internal_id"
DATA_KIDS: Final = "kids"
DATA_LAST_CHANGE: Final = "last_change"
DATA_NAME: Final = "name"
DATA_PARENTS: Final = "parents"
DATA_PENALTIES: Final = "penalties"
DATA_PROGRESS: Final = "progress"
DATA_REWARDS: Final = "rewards"

# KIDS
DATA_KID_BADGES_EARNED_NAME: Final = "badge_name"
DATA_KID_BADGES_EARNED_LAST_AWARDED: Final = "last_awarded_date"
DATA_KID_BADGES_EARNED_AWARD_COUNT: Final = "award_count"
DATA_KID_BADGES_EARNED: Final = "badges_earned"
DATA_KID_BADGES_EARNED_PERIODS: Final = "periods"
DATA_KID_BADGES_EARNED_PERIODS_DAILY: Final = "daily"
DATA_KID_BADGES_EARNED_PERIODS_WEEKLY: Final = "weekly"
DATA_KID_BADGES_EARNED_PERIODS_MONTHLY: Final = "monthly"
DATA_KID_BADGES_EARNED_PERIODS_YEARLY: Final = "yearly"


# Badge Progress Data Structure
DATA_KID_BADGE_PROGRESS: Final = "badge_progress"

# Common Badge Progress Fields
DATA_KID_BADGE_PROGRESS_APPROVED_COUNT: Final = "approved_count"
DATA_KID_BADGE_PROGRESS_CHORES_COMPLETED: Final = "chores_completed"
DATA_KID_BADGE_PROGRESS_CHORES_CYCLE_COUNT: Final = "chores_cycle_count"
DATA_KID_BADGE_PROGRESS_CHORES_TODAY: Final = "chores_today"
DATA_KID_BADGE_PROGRESS_CRITERIA_MET: Final = "criteria_met"
DATA_KID_BADGE_PROGRESS_CYCLE_COUNT: Final = "cycle_count"
DATA_KID_BADGE_PROGRESS_DAYS_COMPLETED: Final = "days_completed"
DATA_KID_BADGE_PROGRESS_DAYS_CYCLE_COUNT: Final = "days_cycle_count"
DATA_KID_BADGE_PROGRESS_END_DATE: Final = "end_date"
DATA_KID_BADGE_PROGRESS_LAST_AWARDED: Final = "last_awarded"
DATA_KID_BADGE_PROGRESS_LAST_UPDATE_DAY: Final = "last_update_day"
DATA_KID_BADGE_PROGRESS_NAME: Final = "name"
DATA_KID_BADGE_PROGRESS_OVERALL_PROGRESS: Final = "overall_progress"
DATA_KID_BADGE_PROGRESS_PENALTY_APPLIED: Final = "penalty_applied"
DATA_KID_BADGE_PROGRESS_POINTS_CYCLE_COUNT: Final = "points_cycle_count"
DATA_KID_BADGE_PROGRESS_POINTS_TODAY: Final = "points_today"
DATA_KID_BADGE_PROGRESS_RECURRING_FREQUENCY: Final = "recurring_frequency"
DATA_KID_BADGE_PROGRESS_START_DATE: Final = "start_date"
DATA_KID_BADGE_PROGRESS_STATUS: Final = "status"
DATA_KID_BADGE_PROGRESS_TARGET_THRESHOLD_VALUE: Final = "threshold_value"
DATA_KID_BADGE_PROGRESS_TARGET_TYPE: Final = "target_type"
DATA_KID_BADGE_PROGRESS_TODAY_COMPLETED: Final = "today_completed"
DATA_KID_BADGE_PROGRESS_TOTAL_COUNT: Final = "total_count"
DATA_KID_BADGE_PROGRESS_TRACKED_CHORES: Final = "tracked_chores"
DATA_KID_BADGE_PROGRESS_TYPE: Final = "badge_type"

# Note: Shared fields already defined above in Common Badge Progress Fields section

DATA_KID_BONUS_APPLIES: Final = "bonus_applies"
DATA_KID_COMPLETED_BY_OTHER_CHORES: Final = "completed_by_other_chores"

# Kid Chore Data Structure Constants
DATA_KID_CHORE_DATA: Final = "chore_data"
DATA_KID_CHORE_DATA_STATE: Final = "state"
DATA_KID_CHORE_DATA_PENDING_CLAIM_COUNT: Final = "pending_claim_count"
DATA_KID_CHORE_DATA_NAME: Final = "name"
DATA_KID_CHORE_DATA_DUE_DATE: Final = "due_date"
DATA_KID_CHORE_DATA_LAST_APPROVED: Final = "last_approved"
DATA_KID_CHORE_DATA_LAST_CLAIMED: Final = "last_claimed"
DATA_KID_CHORE_DATA_LAST_DISAPPROVED: Final = "last_disapproved"
DATA_KID_CHORE_DATA_LAST_OVERDUE: Final = "last_overdue"
DATA_KID_CHORE_DATA_LAST_LONGEST_STREAK_ALL_TIME: Final = "last_longest_streak_all_time"
DATA_KID_CHORE_DATA_APPROVAL_PERIOD_START: Final = (
    "approval_period_start"  # INDEPENDENT: per-kid period start
)
DATA_KID_CHORE_DATA_TOTAL_COUNT: Final = "total_count"
DATA_KID_CHORE_DATA_TOTAL_POINTS: Final = "total_points"
DATA_KID_CHORE_DATA_PERIODS: Final = "periods"
DATA_KID_CHORE_DATA_PERIODS_ALL_TIME: Final = "all_time"
DATA_KID_CHORE_DATA_PERIODS_DAILY: Final = "daily"
DATA_KID_CHORE_DATA_PERIODS_WEEKLY: Final = "weekly"
DATA_KID_CHORE_DATA_PERIODS_MONTHLY: Final = "monthly"
DATA_KID_CHORE_DATA_PERIODS_YEARLY: Final = "yearly"
DATA_KID_CHORE_DATA_PERIOD_APPROVED: Final = "approved"
DATA_KID_CHORE_DATA_PERIOD_CLAIMED: Final = "claimed"
DATA_KID_CHORE_DATA_PERIOD_DISAPPROVED: Final = "disapproved"
DATA_KID_CHORE_DATA_PERIOD_LONGEST_STREAK: Final = "longest_streak"
DATA_KID_CHORE_DATA_PERIOD_OVERDUE: Final = "overdue"
DATA_KID_CHORE_DATA_PERIOD_POINTS: Final = "points"
DATA_KID_CHORE_DATA_BADGE_REFS: Final = "badge_refs"

# Chore Stats Keys
DATA_KID_CHORE_STATS: Final = "chore_stats"

# --- Approval Counts = Completion Counts ---
DATA_KID_CHORE_STATS_APPROVED_TODAY: Final = "approved_today"
DATA_KID_CHORE_STATS_APPROVED_WEEK: Final = "approved_week"
DATA_KID_CHORE_STATS_APPROVED_MONTH: Final = "approved_month"
DATA_KID_CHORE_STATS_APPROVED_YEAR: Final = "approved_year"
DATA_KID_CHORE_STATS_APPROVED_ALL_TIME: Final = "approved_all_time"

# --- Most Completed Chore ---
DATA_KID_CHORE_STATS_MOST_COMPLETED_CHORE_ALL_TIME: Final = (
    "most_completed_chore_all_time"
)
DATA_KID_CHORE_STATS_MOST_COMPLETED_CHORE_WEEK: Final = "most_completed_chore_week"
DATA_KID_CHORE_STATS_MOST_COMPLETED_CHORE_MONTH: Final = "most_completed_chore_month"
DATA_KID_CHORE_STATS_MOST_COMPLETED_CHORE_YEAR: Final = "most_completed_chore_year"

# --- Last Completion Date ---
DATA_KID_CHORE_DATA_APPROVED_LAST_DATE: Final = "approved_last_date"

# --- Total Points from Chores ---
DATA_KID_CHORE_STATS_TOTAL_POINTS_FROM_CHORES_TODAY: Final = (
    "total_points_from_chores_today"
)
DATA_KID_CHORE_STATS_TOTAL_POINTS_FROM_CHORES_WEEK: Final = (
    "total_points_from_chores_week"
)
DATA_KID_CHORE_STATS_TOTAL_POINTS_FROM_CHORES_MONTH: Final = (
    "total_points_from_chores_month"
)
DATA_KID_CHORE_STATS_TOTAL_POINTS_FROM_CHORES_YEAR: Final = (
    "total_points_from_chores_year"
)
DATA_KID_CHORE_STATS_TOTAL_POINTS_FROM_CHORES_ALL_TIME = (
    "total_points_from_chores_all_time"
)

# --- Overdue Counts ---
DATA_KID_CHORE_STATS_OVERDUE_TODAY: Final = "overdue_today"
DATA_KID_CHORE_STATS_OVERDUE_WEEK: Final = "overdue_week"
DATA_KID_CHORE_STATS_OVERDUE_MONTH: Final = "overdue_month"
DATA_KID_CHORE_STATS_OVERDUE_YEAR: Final = "overdue_year"
DATA_KID_CHORE_STATS_OVERDUE_ALL_TIME: Final = "overdue_count_all_time"

# --- Claimed Counts ---
DATA_KID_CHORE_STATS_CLAIMED_TODAY: Final = "claimed_today"
DATA_KID_CHORE_STATS_CLAIMED_WEEK: Final = "claimed_week"
DATA_KID_CHORE_STATS_CLAIMED_MONTH: Final = "claimed_month"
DATA_KID_CHORE_STATS_CLAIMED_YEAR: Final = "claimed_year"
DATA_KID_CHORE_STATS_CLAIMED_ALL_TIME: Final = "claimed_all_time"

# --- Claimed but Not Approved ---
DATA_KID_CHORE_STATS_DISAPPROVED_TODAY: Final = "disapproved_today"
DATA_KID_CHORE_STATS_DISAPPROVED_WEEK: Final = "disapproved_week"
DATA_KID_CHORE_STATS_DISAPPROVED_MONTH: Final = "disapproved_month"
DATA_KID_CHORE_STATS_DISAPPROVED_YEAR: Final = "disapproved_year"
DATA_KID_CHORE_STATS_DISAPPROVED_ALL_TIME: Final = "disapproved_all_time"

# --- Chores Current Stats ---
DATA_KID_CHORE_STATS_CURRENT_DUE_TODAY: Final = "current_due_today"
DATA_KID_CHORE_STATS_CURRENT_OVERDUE: Final = "current_overdue"
DATA_KID_CHORE_STATS_CURRENT_CLAIMED: Final = "current_claimed"
DATA_KID_CHORE_STATS_CURRENT_APPROVED: Final = "current_approved"

# --- Longest Streaks ---
DATA_KID_CHORE_STATS_LONGEST_STREAK_WEEK: Final = "longest_streak_week"
DATA_KID_CHORE_STATS_LONGEST_STREAK_MONTH: Final = "longest_streak_month"
DATA_KID_CHORE_STATS_LONGEST_STREAK_YEAR: Final = "longest_streak_year"
DATA_KID_CHORE_STATS_LONGEST_STREAK_ALL_TIME: Final = "longest_streak_all_time"

# --- Average Chores Per Day ---
DATA_KID_CHORE_STATS_AVG_PER_DAY_MONTH: Final = "avg_per_day_month"
DATA_KID_CHORE_STATS_AVG_PER_DAY_WEEK: Final = "avg_per_day_week"


# --- Badge Progress Tracking ---
DATA_KID_CUMULATIVE_BADGE_PROGRESS: Final = "cumulative_badge_progress"

# Current badge (in effect)
DATA_KID_CUMULATIVE_BADGE_PROGRESS_CURRENT_BADGE_ID: Final = "current_badge_id"
DATA_KID_CUMULATIVE_BADGE_PROGRESS_CURRENT_BADGE_NAME: Final = "current_badge_name"
DATA_KID_CUMULATIVE_BADGE_PROGRESS_CURRENT_THRESHOLD: Final = "current_threshold"

# Highest earned badge (lifetime)
DATA_KID_CUMULATIVE_BADGE_PROGRESS_HIGHEST_EARNED_BADGE_ID: Final = (
    "highest_earned_badge_id"
)
DATA_KID_CUMULATIVE_BADGE_PROGRESS_HIGHEST_EARNED_BADGE_NAME = (
    "highest_earned_badge_name"
)
DATA_KID_CUMULATIVE_BADGE_PROGRESS_HIGHEST_EARNED_THRESHOLD: Final = (
    "highest_earned_threshold"
)

# Next higher badge
DATA_KID_CUMULATIVE_BADGE_PROGRESS_NEXT_HIGHER_BADGE_ID: Final = "next_higher_badge_id"
DATA_KID_CUMULATIVE_BADGE_PROGRESS_NEXT_HIGHER_BADGE_NAME: Final = (
    "next_higher_badge_name"
)
DATA_KID_CUMULATIVE_BADGE_PROGRESS_NEXT_HIGHER_THRESHOLD: Final = (
    "next_higher_threshold"
)
DATA_KID_CUMULATIVE_BADGE_PROGRESS_NEXT_HIGHER_POINTS_NEEDED = (
    "next_higher_points_needed"
)

# Next lower badge
DATA_KID_CUMULATIVE_BADGE_PROGRESS_NEXT_LOWER_BADGE_ID: Final = "next_lower_badge_id"
DATA_KID_CUMULATIVE_BADGE_PROGRESS_NEXT_LOWER_BADGE_NAME: Final = (
    "next_lower_badge_name"
)
DATA_KID_CUMULATIVE_BADGE_PROGRESS_NEXT_LOWER_THRESHOLD: Final = "next_lower_threshold"

# Maintenance tracking
DATA_KID_CUMULATIVE_BADGE_PROGRESS_BASELINE: Final = "baseline"
DATA_KID_CUMULATIVE_BADGE_PROGRESS_CYCLE_POINTS: Final = "cycle_points"
DATA_KID_CUMULATIVE_BADGE_PROGRESS_STATUS: Final = "status"
DATA_KID_CUMULATIVE_BADGE_PROGRESS_MAINTENANCE_END_DATE: Final = "maintenance_end_date"
DATA_KID_CUMULATIVE_BADGE_PROGRESS_MAINTENANCE_GRACE_END_DATE = (
    "maintenance_grace_end_date"
)
DATA_KID_CURRENT_STREAK: Final = "current_streak"
DATA_KID_ENABLE_NOTIFICATIONS: Final = "enable_notifications"
DATA_KID_HA_USER_ID: Final = "ha_user_id"
DATA_KID_ID: Final = "kid_id"
DATA_KID_INTERNAL_ID: Final = "internal_id"
DATA_KID_LAST_BADGE_RESET: Final = "last_badge_reset"
DATA_KID_LAST_CHORE_DATE: Final = "last_chore_date"
DATA_KID_LAST_STREAK_DATE: Final = "last_date"
DATA_KID_MOBILE_NOTIFY_SERVICE: Final = "mobile_notify_service"
DATA_KID_NAME: Final = "name"
DATA_KID_OVERDUE_CHORES: Final = "overdue_chores"
DATA_KID_OVERDUE_NOTIFICATIONS: Final = "overdue_notifications"
DATA_KID_OVERALL_CHORE_STREAK: Final = "overall_chore_streak"
DATA_KID_PENALTY_APPLIES: Final = "penalty_applies"
DATA_KID_POINTS: Final = "points"
DATA_KID_POINTS_MULTIPLIER: Final = "points_multiplier"

# ——————————————————————————————————————————————
# Kid Reward Data Structure Constants (Modern - v0.5.0+)
# Supports multi-claim: kid can claim same reward multiple times before approval
# ——————————————————————————————————————————————
DATA_KID_REWARD_DATA: Final = "reward_data"
DATA_KID_REWARD_DATA_NAME: Final = "name"
DATA_KID_REWARD_DATA_PENDING_COUNT: Final = "pending_count"  # Number of pending claims
DATA_KID_REWARD_DATA_LAST_CLAIMED: Final = "last_claimed"
DATA_KID_REWARD_DATA_LAST_APPROVED: Final = "last_approved"
DATA_KID_REWARD_DATA_LAST_DISAPPROVED: Final = "last_disapproved"
DATA_KID_REWARD_DATA_TOTAL_CLAIMS: Final = "total_claims"  # All-time claim count
DATA_KID_REWARD_DATA_TOTAL_APPROVED: Final = "total_approved"  # All-time approved count
DATA_KID_REWARD_DATA_TOTAL_DISAPPROVED: Final = (
    "total_disapproved"  # All-time disapproved
)
DATA_KID_REWARD_DATA_TOTAL_POINTS_SPENT: Final = "total_points_spent"  # All-time points
DATA_KID_REWARD_DATA_NOTIFICATION_IDS: Final = (
    "notification_ids"  # Notification tracking
)

# Period-based reward tracking (aligned with chore_data and point_data patterns)
DATA_KID_REWARD_DATA_PERIODS: Final = "periods"
DATA_KID_REWARD_DATA_PERIODS_DAILY: Final = "daily"
DATA_KID_REWARD_DATA_PERIODS_WEEKLY: Final = "weekly"
DATA_KID_REWARD_DATA_PERIODS_MONTHLY: Final = "monthly"
DATA_KID_REWARD_DATA_PERIODS_YEARLY: Final = "yearly"
DATA_KID_REWARD_DATA_PERIOD_CLAIMED: Final = "claimed"
DATA_KID_REWARD_DATA_PERIOD_APPROVED: Final = "approved"
DATA_KID_REWARD_DATA_PERIOD_DISAPPROVED: Final = "disapproved"
DATA_KID_REWARD_DATA_PERIOD_POINTS: Final = "points"

DATA_KID_USE_PERSISTENT_NOTIFICATIONS: Final = "use_persistent_notifications"
DATA_KID_DASHBOARD_LANGUAGE: Final = "dashboard_language"

# ——————————————————————————————————————————————
# Custom Translation Settings (Dashboard & Notifications)
# ——————————————————————————————————————————————
CUSTOM_TRANSLATIONS_DIR: Final = "translations_custom"
DEFAULT_DASHBOARD_LANGUAGE: Final = "en"
DASHBOARD_TRANSLATIONS_SUFFIX: Final = "_dashboard"  # File naming: en_dashboard.json
NOTIFICATION_TRANSLATIONS_SUFFIX: Final = (
    "_notifications"  # File naming: en_notifications.json
)

# Legacy alias for backward compatibility
DASHBOARD_TRANSLATIONS_DIR: Final = CUSTOM_TRANSLATIONS_DIR

# ——————————————————————————————————————————————
# Kid Point History Data Structure
# ——————————————————————————————————————————————

# Top‑level key for storing period‑by‑period point history
DATA_KID_POINT_DATA: Final = "point_data"

# Sub‑section containing all period buckets
DATA_KID_POINT_DATA_PERIODS: Final = "periods"

# Individual period buckets
DATA_KID_POINT_DATA_PERIODS_DAILY: Final = "daily"
DATA_KID_POINT_DATA_PERIODS_WEEKLY: Final = "weekly"
DATA_KID_POINT_DATA_PERIODS_MONTHLY: Final = "monthly"
DATA_KID_POINT_DATA_PERIODS_YEARLY: Final = "yearly"

# Within each period entry:
#   – points_total: net delta for that period
#   – by_source: breakdown of delta by source type
DATA_KID_POINT_DATA_PERIOD_POINTS_TOTAL: Final = "points_total"
DATA_KID_POINT_DATA_PERIOD_BY_SOURCE: Final = "by_source"

# Point Sources
# --- Point Source Types (all plural) ---
POINTS_SOURCE_CHORES: Final = "chores"
POINTS_SOURCE_BONUSES: Final = "bonuses"
POINTS_SOURCE_PENALTIES: Final = "penalties"
POINTS_SOURCE_BADGES: Final = "badges"
POINTS_SOURCE_ACHIEVEMENTS: Final = "achievements"
POINTS_SOURCE_CHALLENGES: Final = "challenges"
POINTS_SOURCE_REWARDS: Final = "rewards"
POINTS_SOURCE_MANUAL: Final = "manual"
POINTS_SOURCE_OTHER: Final = "other"

# Example list of valid sources for UI/enumeration:
# Lowercase literals required by Home Assistant SelectSelector schema
POINTS_SOURCE_OPTIONS = [
    {"value": POINTS_SOURCE_CHORES, "label": "Chores"},
    {"value": POINTS_SOURCE_BONUSES, "label": "Bonuses"},
    {"value": POINTS_SOURCE_PENALTIES, "label": "Penalties"},
    {"value": POINTS_SOURCE_BADGES, "label": "Badges"},
    {"value": POINTS_SOURCE_ACHIEVEMENTS, "label": "Achievements"},
    {"value": POINTS_SOURCE_CHALLENGES, "label": "Challenges"},
    {"value": POINTS_SOURCE_REWARDS, "label": "Rewards"},
    {"value": POINTS_SOURCE_OTHER, "label": "Other"},
]

# --- Kid Point Stats (modeled after chore stats) ---
DATA_KID_POINT_STATS: Final = "point_stats"

# --- Per-period totals ---
DATA_KID_POINT_STATS_EARNED_TODAY: Final = "points_earned_today"
DATA_KID_POINT_STATS_EARNED_WEEK: Final = "points_earned_week"
DATA_KID_POINT_STATS_EARNED_MONTH: Final = "points_earned_month"
DATA_KID_POINT_STATS_EARNED_YEAR: Final = "points_earned_year"
DATA_KID_POINT_STATS_EARNED_ALL_TIME: Final = "points_earned_all_time"

# --- Per-period by-source breakdowns ---
DATA_KID_POINT_STATS_BY_SOURCE_TODAY: Final = "points_by_source_today"
DATA_KID_POINT_STATS_BY_SOURCE_WEEK: Final = "points_by_source_week"
DATA_KID_POINT_STATS_BY_SOURCE_MONTH: Final = "points_by_source_month"
DATA_KID_POINT_STATS_BY_SOURCE_YEAR: Final = "points_by_source_year"
DATA_KID_POINT_STATS_BY_SOURCE_ALL_TIME: Final = "points_by_source_all_time"

# --- Per-period spent (negative deltas) ---
DATA_KID_POINT_STATS_SPENT_TODAY: Final = "points_spent_today"
DATA_KID_POINT_STATS_SPENT_WEEK: Final = "points_spent_week"
DATA_KID_POINT_STATS_SPENT_MONTH: Final = "points_spent_month"
DATA_KID_POINT_STATS_SPENT_YEAR: Final = "points_spent_year"
DATA_KID_POINT_STATS_SPENT_ALL_TIME: Final = "points_spent_all_time"

# --- Per-period net (earned - spent) ---
DATA_KID_POINT_STATS_NET_TODAY: Final = "points_net_today"
DATA_KID_POINT_STATS_NET_WEEK: Final = "points_net_week"
DATA_KID_POINT_STATS_NET_MONTH: Final = "points_net_month"
DATA_KID_POINT_STATS_NET_YEAR: Final = "points_net_year"
DATA_KID_POINT_STATS_NET_ALL_TIME: Final = "points_net_all_time"

# --- Streaks (days with positive points) ---
DATA_KID_POINT_STATS_EARNING_STREAK_CURRENT: Final = "points_earning_streak_current"
DATA_KID_POINT_STATS_EARNING_STREAK_LONGEST: Final = "points_earning_streak_longest"

# --- Averages ---
DATA_KID_POINT_STATS_AVG_PER_DAY_WEEK: Final = "avg_points_per_day_week"
DATA_KID_POINT_STATS_AVG_PER_DAY_MONTH: Final = "avg_points_per_day_month"
DATA_KID_POINT_STATS_AVG_PER_CHORE: Final = "avg_points_per_chore"

# --- Highest balance ever (highest balance) ---
DATA_KID_POINT_STATS_HIGHEST_BALANCE: Final = "highest_balance"

# --- All time point stats ---
DATA_KID_POINTS_EARNED_ALL_TIME: Final = "points_earned_all_time"
DATA_KID_POINTS_SPENT_ALL_TIME: Final = "points_spent_all_time"
DATA_KID_POINTS_NET_ALL_TIME: Final = "points_net_all_time"
DATA_KID_POINTS_BY_SOURCE_ALL_TIME: Final = "points_by_source_all_time"

# PARENTS
DATA_PARENT_ASSOCIATED_KIDS: Final = "associated_kids"
DATA_PARENT_ENABLE_NOTIFICATIONS: Final = "enable_notifications"
DATA_PARENT_HA_USER_ID: Final = "ha_user_id"
DATA_PARENT_INTERNAL_ID: Final = "internal_id"
DATA_PARENT_MOBILE_NOTIFY_SERVICE: Final = "mobile_notify_service"
DATA_PARENT_NAME: Final = "name"
DATA_PARENT_USE_PERSISTENT_NOTIFICATIONS: Final = "use_persistent_notifications"

# CHORES
DATA_CHORE_APPROVAL_RESET_TYPE: Final = "approval_reset_type"
DATA_CHORE_APPROVAL_PERIOD_START: Final = (
    "approval_period_start"  # When current approval period started
)
DATA_CHORE_APPLICABLE_DAYS: Final = "applicable_days"
DATA_CHORE_ASSIGNED_KIDS: Final = "assigned_kids"
DATA_CHORE_CUSTOM_INTERVAL: Final = "custom_interval"
DATA_CHORE_CUSTOM_INTERVAL_UNIT: Final = "custom_interval_unit"
DATA_CHORE_DEFAULT_POINTS: Final = "default_points"
DATA_CHORE_DESCRIPTION: Final = "description"
DATA_CHORE_DUE_DATE: Final = "due_date"
DATA_CHORE_ICON: Final = "icon"
DATA_CHORE_ID: Final = "chore_id"
DATA_CHORE_INTERNAL_ID: Final = "internal_id"
DATA_CHORE_LABELS: Final = "chore_labels"
DATA_CHORE_LAST_CLAIMED: Final = "last_claimed"
DATA_CHORE_LAST_COMPLETED: Final = "last_completed"
DATA_CHORE_CLAIMED_BY: Final = "claimed_by"  # SHARED_FIRST: Who claimed this chore
DATA_CHORE_COMPLETED_BY: Final = (
    "completed_by"  # SHARED_FIRST: Who completed this chore
)
DATA_CHORE_NAME: Final = "name"
DATA_CHORE_NOTIFY_ON_APPROVAL: Final = "notify_on_approval"
DATA_CHORE_NOTIFY_ON_CLAIM: Final = "notify_on_claim"
DATA_CHORE_NOTIFY_ON_DISAPPROVAL: Final = "notify_on_disapproval"
DATA_CHORE_AUTO_APPROVE: Final = "auto_approve"
DATA_CHORE_RECURRING_FREQUENCY: Final = "recurring_frequency"
DATA_CHORE_SHOW_ON_CALENDAR: Final = "show_on_calendar"
DATA_CHORE_COMPLETION_CRITERIA: Final = "completion_criteria"
DATA_CHORE_PER_KID_DUE_DATES: Final = "per_kid_due_dates"
DATA_CHORE_OVERDUE_HANDLING_TYPE: Final = "overdue_handling_type"
DATA_CHORE_APPROVAL_RESET_PENDING_CLAIM_ACTION: Final = (
    "approval_reset_pending_claim_action"
)

# Completion Criteria Values
COMPLETION_CRITERIA_SHARED: Final = "shared_all"
COMPLETION_CRITERIA_INDEPENDENT: Final = "independent"
COMPLETION_CRITERIA_SHARED_FIRST: Final = "shared_first"
COMPLETION_CRITERIA_OPTIONS: Final = [
    {"value": COMPLETION_CRITERIA_SHARED, "label": "shared_all"},
    {"value": COMPLETION_CRITERIA_INDEPENDENT, "label": "independent"},
    {"value": COMPLETION_CRITERIA_SHARED_FIRST, "label": "shared_first"},
]

# Approval Reset Type Values (Phase 4)
# Controls when a chore can be claimed/approved again after completion
APPROVAL_RESET_AT_MIDNIGHT_ONCE: Final = "at_midnight_once"
APPROVAL_RESET_AT_MIDNIGHT_MULTI: Final = "at_midnight_multi"
APPROVAL_RESET_AT_DUE_DATE_ONCE: Final = "at_due_date_once"
APPROVAL_RESET_AT_DUE_DATE_MULTI: Final = "at_due_date_multi"
APPROVAL_RESET_UPON_COMPLETION: Final = "upon_completion"
APPROVAL_RESET_TYPE_OPTIONS: Final = [
    {"value": APPROVAL_RESET_AT_MIDNIGHT_ONCE, "label": "at_midnight_once"},
    {"value": APPROVAL_RESET_AT_MIDNIGHT_MULTI, "label": "at_midnight_multi"},
    {"value": APPROVAL_RESET_AT_DUE_DATE_ONCE, "label": "at_due_date_once"},
    {"value": APPROVAL_RESET_AT_DUE_DATE_MULTI, "label": "at_due_date_multi"},
    {"value": APPROVAL_RESET_UPON_COMPLETION, "label": "upon_completion"},
]
DEFAULT_APPROVAL_RESET_TYPE: Final = APPROVAL_RESET_AT_MIDNIGHT_ONCE

# Overdue Handling Type Values (Phase 5)
# Controls when/if a chore shows as overdue
OVERDUE_HANDLING_AT_DUE_DATE: Final = "at_due_date"
OVERDUE_HANDLING_NEVER_OVERDUE: Final = "never_overdue"
OVERDUE_HANDLING_AT_DUE_DATE_THEN_RESET: Final = "at_due_date_then_reset"
OVERDUE_HANDLING_TYPE_OPTIONS: Final = [
    {"value": OVERDUE_HANDLING_AT_DUE_DATE, "label": "at_due_date"},
    {"value": OVERDUE_HANDLING_NEVER_OVERDUE, "label": "never_overdue"},
    {
        "value": OVERDUE_HANDLING_AT_DUE_DATE_THEN_RESET,
        "label": "at_due_date_then_reset",
    },
]
DEFAULT_OVERDUE_HANDLING_TYPE: Final = OVERDUE_HANDLING_AT_DUE_DATE

# Approval Reset Pending Claim Action Values (Phase 5)
# Controls what happens to pending (unapproved) claims at approval reset
APPROVAL_RESET_PENDING_CLAIM_HOLD: Final = "hold_pending"
APPROVAL_RESET_PENDING_CLAIM_CLEAR: Final = "clear_pending"
APPROVAL_RESET_PENDING_CLAIM_AUTO_APPROVE: Final = "auto_approve_pending"
APPROVAL_RESET_PENDING_CLAIM_ACTION_OPTIONS: Final = [
    {"value": APPROVAL_RESET_PENDING_CLAIM_HOLD, "label": "hold_pending"},
    {"value": APPROVAL_RESET_PENDING_CLAIM_CLEAR, "label": "clear_pending"},
    {
        "value": APPROVAL_RESET_PENDING_CLAIM_AUTO_APPROVE,
        "label": "auto_approve_pending",
    },
]
DEFAULT_APPROVAL_RESET_PENDING_CLAIM_ACTION: Final = APPROVAL_RESET_PENDING_CLAIM_CLEAR

DATA_CHORE_STATE: Final = "state"
DATA_CHORE_TIMESTAMP: Final = "timestamp"

# BADGES
DATA_BADGE_ASSIGNED_TO: Final = "assigned_to"
DATA_BADGE_ASSOCIATED_ACHIEVEMENT: Final = "associated_achievement"
DATA_BADGE_ASSOCIATED_CHALLENGE: Final = "associated_challenge"
DATA_BADGE_AWARDS: Final = "awards"
DATA_BADGE_AWARDS_AWARD_ITEMS: Final = "award_items"
DATA_BADGE_AWARDS_AWARD_POINTS: Final = "award_points"
DATA_BADGE_AWARDS_AWARD_POINTS_REWARD: Final = "award_points_reward"
DATA_BADGE_AWARDS_AWARD_REWARD: Final = "award_reward"
DATA_BADGE_AWARDS_POINT_MULTIPLIER: Final = "points_multiplier"
DATA_BADGE_DESCRIPTION: Final = "description"
DATA_BADGE_EARNED_BY: Final = "earned_by"
DATA_BADGE_ICON: Final = "icon"
DATA_BADGE_ID: Final = "badge_id"
DATA_BADGE_INTERNAL_ID: Final = "internal_id"
DATA_BADGE_LABELS: Final = "badge_labels"
DATA_BADGE_MAINTENANCE_RULES: Final = "maintenance_rules"
DATA_BADGE_NAME: Final = "name"
DATA_BADGE_OCCASION_TYPE: Final = "occasion_type"
DATA_BADGE_RESET_SCHEDULE: Final = "reset_schedule"
DATA_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL: Final = "custom_interval"
DATA_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL_UNIT: Final = "custom_interval_unit"
DATA_BADGE_RESET_SCHEDULE_END_DATE: Final = "end_date"
DATA_BADGE_RESET_SCHEDULE_GRACE_PERIOD_DAYS: Final = "grace_period_days"
DATA_BADGE_RESET_SCHEDULE_RECURRING_FREQUENCY: Final = "recurring_frequency"
DATA_BADGE_RESET_SCHEDULE_START_DATE: Final = "start_date"
DATA_BADGE_SPECIAL_OCCASION_TYPE: Final = "occasion_type"
DATA_BADGE_TARGET: Final = "target"
DATA_BADGE_TARGET_THRESHOLD_VALUE: Final = "threshold_value"
DATA_BADGE_TARGET_TYPE: Final = "target_type"
DATA_BADGE_TRACKED_CHORES: Final = "tracked_chores"
DATA_BADGE_TRACKED_CHORES_SELECTED_CHORES: Final = "selected_chores"
DATA_BADGE_TYPE: Final = "badge_type"

# REWARDS
DATA_REWARD_COST: Final = "cost"
DATA_REWARD_DESCRIPTION: Final = "description"
DATA_REWARD_ICON: Final = "icon"
DATA_REWARD_ID: Final = "reward_id"
DATA_REWARD_INTERNAL_ID: Final = "internal_id"
DATA_REWARD_LABELS: Final = "reward_labels"
DATA_REWARD_NAME: Final = "name"
DATA_REWARD_NOTIFICATION_ID: Final = "notification_id"
DATA_REWARD_TIMESTAMP: Final = "timestamp"

# BONUSES
DATA_BONUS_DESCRIPTION: Final = "description"
DATA_BONUS_ICON: Final = "icon"
DATA_BONUS_ID: Final = "bonus_id"
DATA_BONUS_INTERNAL_ID: Final = "internal_id"
DATA_BONUS_LABELS: Final = "bonus_labels"
DATA_BONUS_NAME: Final = "name"
DATA_BONUS_POINTS: Final = "points"

# PENALTIES
DATA_PENALTY_DESCRIPTION: Final = "description"
DATA_PENALTY_ICON: Final = "icon"
DATA_PENALTY_ID: Final = "penalty_id"
DATA_PENALTY_INTERNAL_ID: Final = "internal_id"
DATA_PENALTY_LABELS: Final = "penalty_labels"
DATA_PENALTY_NAME: Final = "name"
DATA_PENALTY_POINTS: Final = "points"

# ACHIEVEMENTS
DATA_ACHIEVEMENT_ASSIGNED_KIDS: Final = "assigned_kids"
DATA_ACHIEVEMENT_AWARDED: Final = "awarded"
DATA_ACHIEVEMENT_BASELINE: Final = "baseline"
DATA_ACHIEVEMENT_CRITERIA: Final = "criteria"
DATA_ACHIEVEMENT_CURRENT_STREAK: Final = "current_streak"
DATA_ACHIEVEMENT_CURRENT_VALUE: Final = "current_value"
DATA_ACHIEVEMENT_DESCRIPTION: Final = "description"
DATA_ACHIEVEMENT_ICON: Final = "icon"
DATA_ACHIEVEMENT_ID: Final = "achievement_id"
DATA_ACHIEVEMENT_INTERNAL_ID: Final = "internal_id"
DATA_ACHIEVEMENT_LABELS: Final = "achievement_labels"
DATA_ACHIEVEMENT_LAST_AWARDED_DATE: Final = "last_awarded_date"
DATA_ACHIEVEMENT_NAME: Final = "name"
DATA_ACHIEVEMENT_PROGRESS: Final = "progress"
DATA_ACHIEVEMENT_PROGRESS_SUFFIX: Final = "_achievement_progress"
DATA_ACHIEVEMENT_REWARD_POINTS: Final = "reward_points"
DATA_ACHIEVEMENT_SELECTED_CHORE_ID: Final = "selected_chore_id"
DATA_ACHIEVEMENT_TARGET_VALUE: Final = "target_value"
DATA_ACHIEVEMENT_TYPE: Final = "type"

# CHALLENGES
DATA_CHALLENGE_ASSIGNED_KIDS: Final = "assigned_kids"
DATA_CHALLENGE_AWARDED: Final = "awarded"
DATA_CHALLENGE_COUNT: Final = "count"
DATA_CHALLENGE_CRITERIA: Final = "criteria"
DATA_CHALLENGE_DAILY_COUNTS: Final = "daily_counts"
DATA_CHALLENGE_DESCRIPTION: Final = "description"
DATA_CHALLENGE_END_DATE: Final = "end_date"
DATA_CHALLENGE_ICON: Final = "icon"
DATA_CHALLENGE_ID: Final = "challenge_id"
DATA_CHALLENGE_INTERNAL_ID: Final = "internal_id"
DATA_CHALLENGE_LABELS: Final = "challenge_labels"
DATA_CHALLENGE_NAME: Final = "name"
DATA_CHALLENGE_PROGRESS: Final = "progress"
DATA_CHALLENGE_PROGRESS_SUFFIX: Final = "_challenge_progress"
DATA_CHALLENGE_REQUIRED_DAILY: Final = "required_daily"
DATA_CHALLENGE_REWARD_POINTS: Final = "reward_points"
DATA_CHALLENGE_SELECTED_CHORE_ID: Final = "selected_chore_id"
DATA_CHALLENGE_START_DATE: Final = "start_date"
DATA_CHALLENGE_TARGET_VALUE: Final = "target_value"
DATA_CHALLENGE_TYPE: Final = "type"

# ================================================================================================
# Default Icons
# ================================================================================================
DEFAULT_ACHIEVEMENTS_ICON: Final = "mdi:trophy-award"
DEFAULT_BADGE_ICON: Final = "mdi:shield-star-outline"
DEFAULT_BONUS_ICON: Final = "mdi:seal"
DEFAULT_CALENDAR_ICON: Final = "mdi:calendar"
DEFAULT_CHALLENGES_ICON: Final = "mdi:trophy"
DEFAULT_CHORE_ICON: Final = "mdi:broom"
DEFAULT_CHORE_APPROVE_ICON: Final = "mdi:checkbox-marked-circle-outline"
DEFAULT_CHORE_CLAIM_ICON: Final = "mdi:clipboard-check-outline"
DEFAULT_CHORE_SENSOR_ICON: Final = "mdi:checkbox-blank-circle-outline"
DEFAULT_COMPLETED_CHORES_DAILY_SENSOR_ICON: Final = "mdi:clipboard-check-outline"
DEFAULT_COMPLETED_CHORES_MONTHLY_SENSOR_ICON: Final = "mdi:clipboard-list-outline"
DEFAULT_COMPLETED_CHORES_TOTAL_SENSOR_ICON: Final = "mdi:clipboard-text-clock-outline"
DEFAULT_COMPLETED_CHORES_WEEKLY_SENSOR_ICON: Final = (
    "mdi:clipboard-check-multiple-outline"
)
DEFAULT_DISAPPROVE_ICON: Final = "mdi:close-circle-outline"
DEFAULT_ICON: Final = "mdi:star-outline"
DEFAULT_PENALTY_ICON: Final = "mdi:alert-outline"
DEFAULT_PENDING_CHORE_APPROVALS_SENSOR_ICON: Final = "mdi:checkbox-blank-badge-outline"
DEFAULT_PENDING_REWARD_APPROVALS_SENSOR_ICON: Final = "mdi:gift-open-outline"
DEFAULT_POINTS_ADJUST_MINUS_ICON: Final = "mdi:minus-circle-outline"
DEFAULT_POINTS_ADJUST_MINUS_MULTIPLE_ICON: Final = "mdi:minus-circle-multiple-outline"
DEFAULT_POINTS_ADJUST_PLUS_ICON: Final = "mdi:plus-circle-outline"
DEFAULT_POINTS_ADJUST_PLUS_MULTIPLE_ICON: Final = "mdi:plus-circle-multiple-outline"
DEFAULT_POINTS_ICON: Final = "mdi:star-outline"
DEFAULT_STREAK_ICON: Final = "mdi:blur-linear"
DEFAULT_REWARD_ICON: Final = "mdi:gift-outline"
DEFAULT_TROPHY_ICON: Final = "mdi:trophy"
DEFAULT_TROPHY_OUTLINE: Final = "mdi:trophy-outline"


# ------------------------------------------------------------------------------------------------
# Default Values
# ------------------------------------------------------------------------------------------------
DEFAULT_ACHIEVEMENT_REWARD_POINTS: Final = 0
DEFAULT_ACHIEVEMENT_TARGET: Final = 1
DEFAULT_APPLICABLE_DAYS: list[str] = []
DEFAULT_BADGE_AWARD_POINTS: Final = 0
DEFAULT_BADGE_MAINTENANCE_THRESHOLD = 0  # Added
DEFAULT_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL_UNIT = SENTINEL_NONE
DEFAULT_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL = SENTINEL_NONE
DEFAULT_BADGE_RESET_SCHEDULE_END_DATE = SENTINEL_NONE
DEFAULT_BADGE_RESET_SCHEDULE_GRACE_PERIOD_DAYS: Final = 0
DEFAULT_BADGE_RESET_SCHEDULE_START_DATE = SENTINEL_NONE
DEFAULT_BADGE_RESET_SCHEDULE_RECURRING_FREQUENCY = FREQUENCY_NONE
DEFAULT_BADGE_RESET_SCHEDULE = {
    DATA_BADGE_RESET_SCHEDULE_RECURRING_FREQUENCY: (
        DEFAULT_BADGE_RESET_SCHEDULE_RECURRING_FREQUENCY
    ),
    DATA_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL: (
        DEFAULT_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL
    ),
    DATA_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL_UNIT: (
        DEFAULT_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL_UNIT
    ),
    DATA_BADGE_RESET_SCHEDULE_START_DATE: DEFAULT_BADGE_RESET_SCHEDULE_START_DATE,
    DATA_BADGE_RESET_SCHEDULE_END_DATE: DEFAULT_BADGE_RESET_SCHEDULE_END_DATE,
    DATA_BADGE_RESET_SCHEDULE_GRACE_PERIOD_DAYS: (
        DEFAULT_BADGE_RESET_SCHEDULE_GRACE_PERIOD_DAYS
    ),
}
DEFAULT_BADGE_TARGET_TYPE: Final = "points"
DEFAULT_BADGE_TARGET_THRESHOLD_VALUE: Final = 50
DEFAULT_BADGE_TARGET = {
    "type": DEFAULT_BADGE_TARGET_TYPE,
    "value": DEFAULT_BADGE_TARGET_THRESHOLD_VALUE,
}
DEFAULT_BONUS_POINTS: Final = 1
DEFAULT_CALENDAR_SHOW_PERIOD: Final = 90
DEFAULT_CHORE_AUTO_APPROVE: Final = False
DEFAULT_CHORE_SHOW_ON_CALENDAR: Final = True
DEFAULT_CHALLENGE_REWARD_POINTS: Final = 0
DEFAULT_RETENTION_DAILY: Final = 7
DEFAULT_RETENTION_WEEKLY: Final = 5
DEFAULT_RETENTION_MONTHLY: Final = 3
DEFAULT_RETENTION_YEARLY: Final = 3
DEFAULT_CHALLENGE_TARGET: Final = 1
DEFAULT_CHORES_UNIT: Final = "Chores"
DEFAULT_DAILY_RESET_TIME = {"hour": 0, "minute": 0, "second": 0}
DEFAULT_DUE_TIME = {"hour": 23, "minute": 59, "second": 0}
DEFAULT_HOUR: Final = 0
DEFAULT_KID_POINTS_MULTIPLIER: Final = 1
DEFAULT_SHOW_LEGACY_ENTITIES: Final = False
DEFAULT_MONTHLY_RESET_DAY: Final = 1
DEFAULT_MULTIPLE_CLAIMS_PER_DAY = False
DEFAULT_NOTIFY_DELAY_REMINDER: Final = 24
DEFAULT_NOTIFY_ON_APPROVAL = True
DEFAULT_NOTIFY_ON_CLAIM = True
DEFAULT_NOTIFY_ON_DISAPPROVAL = True
DEFAULT_PENALTY_POINTS: Final = 1
DEFAULT_PENDING_CHORES_UNIT: Final = "Pending Chores"
DEFAULT_PENDING_REWARDS_UNIT: Final = "Pending Rewards"
DEFAULT_POINTS: Final = 5
DEFAULT_POINTS_ADJUST_VALUES: list[float] = [+1.0, -1.0, +2.0, -2.0, +10.0, -10.0]
DEFAULT_POINTS_LABEL: Final = "Points"
DEFAULT_POINTS_MULTIPLIER = 1.0
DEFAULT_REWARD_COST: Final = 10
DEFAULT_REMINDER_DELAY: Final = 30
DEFAULT_WEEKLY_RESET_DAY: Final = 0
DEFAULT_YEAR_END_DAY: Final = 31
DEFAULT_YEAR_END_HOUR: Final = 23
DEFAULT_YEAR_END_MINUTE: Final = 59
DEFAULT_YEAR_END_MONTH: Final = 12
DEFAULT_YEAR_END_SECOND: Final = 0
DEFAULT_ZERO: Final = 0


# ------------------------------------------------------------------------------------------------
# Badge Threshold Types
# ------------------------------------------------------------------------------------------------
# Badge Target Types for all supported badge logic

BADGE_TARGET_THRESHOLD_TYPE_POINTS: Final = "points"
BADGE_TARGET_THRESHOLD_TYPE_POINTS_CHORES: Final = "points_chores"
BADGE_TARGET_THRESHOLD_TYPE_CHORE_COUNT: Final = "chore_count"
BADGE_TARGET_THRESHOLD_TYPE_DAYS_SELECTED_CHORES: Final = "days_all_chores"
BADGE_TARGET_THRESHOLD_TYPE_DAYS_80PCT_CHORES = "days_80pct_chores"
BADGE_TARGET_THRESHOLD_TYPE_DAYS_SELECTED_CHORES_NO_OVERDUE = (
    "days_all_chores_no_overdue"
)
BADGE_TARGET_THRESHOLD_TYPE_DAYS_SELECTED_DUE_CHORES: Final = "days_all_due_chores"
BADGE_TARGET_THRESHOLD_TYPE_DAYS_80PCT_DUE_CHORES = "days_80pct_due_chores"
BADGE_TARGET_THRESHOLD_TYPE_DAYS_SELECTED_DUE_CHORES_NO_OVERDUE = (
    "days_all_due_chores_no_overdue"
)
BADGE_TARGET_THRESHOLD_TYPE_DAYS_MIN_3_CHORES = "days_min_3_chores"
BADGE_TARGET_THRESHOLD_TYPE_DAYS_MIN_5_CHORES = "days_min_5_chores"
BADGE_TARGET_THRESHOLD_TYPE_DAYS_MIN_7_CHORES = "days_min_7_chores"
BADGE_TARGET_THRESHOLD_TYPE_STREAK_SELECTED_CHORES: Final = "streak_all_chores"
BADGE_TARGET_THRESHOLD_TYPE_STREAK_80PCT_CHORES = "streak_80pct_chores"
BADGE_TARGET_THRESHOLD_TYPE_STREAK_SELECTED_CHORES_NO_OVERDUE = (
    "streak_all_chores_no_overdue"
)
BADGE_TARGET_THRESHOLD_TYPE_STREAK_80PCT_DUE_CHORES = "streak_80pct_due_chores"
BADGE_TARGET_THRESHOLD_TYPE_STREAK_SELECTED_DUE_CHORES_NO_OVERDUE = (
    "streak_all_due_chores_no_overdue"
)

# Legacy
BADGE_THRESHOLD_TYPE_CHORE_COUNT: Final = "chore_count"
BADGE_THRESHOLD_TYPE_POINTS: Final = "points"


# ------------------------------------------------------------------------------------------------
# States
# ------------------------------------------------------------------------------------------------

# Chore States
CHORE_STATE_APPROVED = "approved"
CHORE_STATE_APPROVED_IN_PART = "approved_in_part"
CHORE_STATE_CLAIMED = "claimed"
CHORE_STATE_CLAIMED_IN_PART = "claimed_in_part"
CHORE_STATE_COMPLETED_BY_OTHER = "completed_by_other"
CHORE_STATE_INDEPENDENT = "independent"
CHORE_STATE_OVERDUE = "overdue"
CHORE_STATE_PENDING = "pending"
CHORE_STATE_UNKNOWN = "unknown"

# Reward States
REWARD_STATE_APPROVED = "approved"
REWARD_STATE_CLAIMED = "claimed"
REWARD_STATE_NOT_CLAIMED = "not_claimed"

# Badge States
BADGE_STATE_IN_PROGRESS: Final = "in_progress"
BADGE_STATE_EARNED: Final = "earned"
BADGE_STATE_ACTIVE_CYCLE: Final = "active_cycle"
CUMULATIVE_BADGE_STATE_ACTIVE = "active"
CUMULATIVE_BADGE_STATE_GRACE = "grace"
CUMULATIVE_BADGE_STATE_DEMOTED = "demoted"

# ------------------------------------------------------------------------------------------------
# Actions
# ------------------------------------------------------------------------------------------------

# Action titles for notifications (translation keys)
TRANS_KEY_NOTIF_ACTION_APPROVE: Final = "notif_action_approve"
TRANS_KEY_NOTIF_ACTION_DISAPPROVE: Final = "notif_action_disapprove"
TRANS_KEY_NOTIF_ACTION_REMIND_30: Final = "notif_action_remind_30"

# Notification Title Translation Keys
TRANS_KEY_NOTIF_TITLE_CHORE_ASSIGNED: Final = "notification_title_chore_assigned"
TRANS_KEY_NOTIF_TITLE_CHORE_CLAIMED: Final = "notification_title_chore_claimed"
TRANS_KEY_NOTIF_TITLE_CHORE_APPROVED: Final = "notification_title_chore_approved"
TRANS_KEY_NOTIF_TITLE_CHORE_DISAPPROVED: Final = "notification_title_chore_disapproved"
TRANS_KEY_NOTIF_TITLE_CHORE_OVERDUE: Final = "notification_title_chore_overdue"
TRANS_KEY_NOTIF_TITLE_CHORE_REMINDER: Final = "notification_title_chore_reminder"

TRANS_KEY_NOTIF_TITLE_REWARD_CLAIMED: Final = "notification_title_reward_claimed"
TRANS_KEY_NOTIF_TITLE_REWARD_APPROVED: Final = "notification_title_reward_approved"
TRANS_KEY_NOTIF_TITLE_REWARD_DISAPPROVED: Final = (
    "notification_title_reward_disapproved"
)
TRANS_KEY_NOTIF_TITLE_REWARD_REMINDER: Final = "notification_title_reward_reminder"

TRANS_KEY_NOTIF_TITLE_BADGE_EARNED: Final = "notification_title_badge_earned"
TRANS_KEY_NOTIF_TITLE_ACHIEVEMENT_EARNED: Final = (
    "notification_title_achievement_earned"
)
TRANS_KEY_NOTIF_TITLE_CHALLENGE_COMPLETED: Final = (
    "notification_title_challenge_completed"
)

TRANS_KEY_NOTIF_TITLE_PENALTY_APPLIED: Final = "notification_title_penalty_applied"
TRANS_KEY_NOTIF_TITLE_BONUS_APPLIED: Final = "notification_title_bonus_applied"

# Notification Message Translation Keys
TRANS_KEY_NOTIF_MESSAGE_CHORE_ASSIGNED: Final = "notification_message_chore_assigned"
TRANS_KEY_NOTIF_MESSAGE_CHORE_CLAIMED: Final = "notification_message_chore_claimed"
TRANS_KEY_NOTIF_MESSAGE_CHORE_APPROVED: Final = "notification_message_chore_approved"
TRANS_KEY_NOTIF_MESSAGE_CHORE_DISAPPROVED: Final = (
    "notification_message_chore_disapproved"
)
TRANS_KEY_NOTIF_MESSAGE_CHORE_OVERDUE: Final = "notification_message_chore_overdue"
TRANS_KEY_NOTIF_MESSAGE_CHORE_REMINDER: Final = "notification_message_chore_reminder"

TRANS_KEY_NOTIF_MESSAGE_REWARD_CLAIMED_KID: Final = (
    "notification_message_reward_claimed_kid"
)
TRANS_KEY_NOTIF_MESSAGE_REWARD_CLAIMED_PARENT: Final = (
    "notification_message_reward_claimed_parent"
)
TRANS_KEY_NOTIF_MESSAGE_REWARD_APPROVED: Final = "notification_message_reward_approved"
TRANS_KEY_NOTIF_MESSAGE_REWARD_DISAPPROVED: Final = (
    "notification_message_reward_disapproved"
)
TRANS_KEY_NOTIF_MESSAGE_REWARD_REMINDER: Final = "notification_message_reward_reminder"

TRANS_KEY_NOTIF_MESSAGE_BADGE_EARNED_KID: Final = (
    "notification_message_badge_earned_kid"
)
TRANS_KEY_NOTIF_MESSAGE_BADGE_EARNED_PARENT: Final = (
    "notification_message_badge_earned_parent"
)
TRANS_KEY_NOTIF_MESSAGE_ACHIEVEMENT_EARNED_KID: Final = (
    "notification_message_achievement_earned_kid"
)
TRANS_KEY_NOTIF_MESSAGE_ACHIEVEMENT_EARNED_PARENT: Final = (
    "notification_message_achievement_earned_parent"
)
TRANS_KEY_NOTIF_MESSAGE_CHALLENGE_COMPLETED_KID: Final = (
    "notification_message_challenge_completed_kid"
)
TRANS_KEY_NOTIF_MESSAGE_CHALLENGE_COMPLETED_PARENT: Final = (
    "notification_message_challenge_completed_parent"
)

TRANS_KEY_NOTIF_MESSAGE_PENALTY_APPLIED: Final = "notification_message_penalty_applied"
TRANS_KEY_NOTIF_MESSAGE_BONUS_APPLIED: Final = "notification_message_bonus_applied"

# Action identifiers
ACTION_APPROVE_CHORE = "APPROVE_CHORE"
ACTION_APPROVE_REWARD = "APPROVE_REWARD"
ACTION_DISAPPROVE_CHORE = "DISAPPROVE_CHORE"
ACTION_DISAPPROVE_REWARD = "DISAPPROVE_REWARD"
ACTION_REMIND_30 = "REMIND_30"


# ------------------------------------------------------------------------------------------------
# Translation Keys - Entity State Attributes
# ------------------------------------------------------------------------------------------------

# Translation keys for PURPOSE attribute values (sensor.py)
TRANS_KEY_PURPOSE_CHORE_STATUS: Final = "purpose_chore_status"
TRANS_KEY_PURPOSE_POINTS: Final = "purpose_points"
TRANS_KEY_PURPOSE_CHORES: Final = "purpose_chores"
TRANS_KEY_PURPOSE_KID_BADGES: Final = "purpose_kid_badges"
TRANS_KEY_PURPOSE_BADGE_PROGRESS: Final = "purpose_badge_progress"
TRANS_KEY_PURPOSE_BADGE: Final = "purpose_badge"
TRANS_KEY_PURPOSE_SHARED_CHORE: Final = "purpose_shared_chore"
TRANS_KEY_PURPOSE_REWARD_STATUS: Final = "purpose_reward_status"
TRANS_KEY_PURPOSE_PENALTY_APPLIED: Final = "purpose_penalty_applied"
TRANS_KEY_PURPOSE_ACHIEVEMENT: Final = "purpose_achievement"
TRANS_KEY_PURPOSE_CHALLENGE: Final = "purpose_challenge"
TRANS_KEY_PURPOSE_ACHIEVEMENT_PROGRESS: Final = "purpose_achievement_progress"
TRANS_KEY_PURPOSE_CHALLENGE_PROGRESS: Final = "purpose_challenge_progress"
TRANS_KEY_PURPOSE_BONUS_APPLIED: Final = "purpose_bonus_applied"
TRANS_KEY_PURPOSE_DASHBOARD_HELPER: Final = "purpose_dashboard_helper"
# Legacy sensor purposes (sensor_legacy.py)
TRANS_KEY_PURPOSE_CHORE_APPROVALS_ALL_TIME_EXTRA: Final = (
    "purpose_chore_approvals_all_time_extra"
)
TRANS_KEY_PURPOSE_CHORE_APPROVALS_TODAY_EXTRA: Final = (
    "purpose_chore_approvals_today_extra"
)
TRANS_KEY_PURPOSE_CHORE_APPROVALS_WEEK_EXTRA: Final = (
    "purpose_chore_approvals_week_extra"
)
TRANS_KEY_PURPOSE_CHORE_APPROVALS_MONTH_EXTRA: Final = (
    "purpose_chore_approvals_month_extra"
)
TRANS_KEY_PURPOSE_CHORES_PENDING_APPROVAL_EXTRA: Final = (
    "purpose_chores_pending_approval_extra"
)
TRANS_KEY_PURPOSE_REWARDS_PENDING_APPROVAL_EXTRA: Final = (
    "purpose_rewards_pending_approval_extra"
)
TRANS_KEY_PURPOSE_POINTS_EARNED_TODAY_EXTRA: Final = "purpose_points_earned_today_extra"
TRANS_KEY_PURPOSE_POINTS_EARNED_WEEK_EXTRA: Final = "purpose_points_earned_week_extra"
TRANS_KEY_PURPOSE_POINTS_EARNED_MONTH_EXTRA: Final = "purpose_points_earned_month_extra"
TRANS_KEY_PURPOSE_POINTS_MAX_EVER_EXTRA: Final = "purpose_points_max_ever_extra"
TRANS_KEY_PURPOSE_CHORE_STREAK_EXTRA: Final = "purpose_chore_streak_extra"

# Button purpose translation keys (button.py)
TRANS_KEY_PURPOSE_BUTTON_CHORE_CLAIM: Final = "purpose_button_chore_claim"
TRANS_KEY_PURPOSE_BUTTON_CHORE_APPROVE: Final = "purpose_button_chore_approve"
TRANS_KEY_PURPOSE_BUTTON_CHORE_DISAPPROVE: Final = "purpose_button_chore_disapprove"
TRANS_KEY_PURPOSE_BUTTON_REWARD_REDEEM: Final = "purpose_button_reward_redeem"
TRANS_KEY_PURPOSE_BUTTON_REWARD_APPROVE: Final = "purpose_button_reward_approve"
TRANS_KEY_PURPOSE_BUTTON_REWARD_DISAPPROVE: Final = "purpose_button_reward_disapprove"
TRANS_KEY_PURPOSE_BUTTON_PENALTY_APPLY: Final = "purpose_button_penalty_apply"
TRANS_KEY_PURPOSE_BUTTON_POINTS_ADJUST: Final = "purpose_button_points_adjust"
TRANS_KEY_PURPOSE_BUTTON_BONUS_APPLY: Final = "purpose_button_bonus_apply"

# Select purpose translation keys (select.py)
TRANS_KEY_PURPOSE_SELECT_KID_CHORES: Final = "purpose_select_kid_chores"

# Calendar purpose translation keys (calendar.py)
TRANS_KEY_PURPOSE_CALENDAR_SCHEDULE: Final = "purpose_calendar_schedule"

# Datetime purpose translation keys (datetime.py)
TRANS_KEY_PURPOSE_DATETIME_DASHBOARD_HELPER: Final = "purpose_datetime_dashboard_helper"

# Translation keys for entity state attributes (all sensor classes)
TRANS_KEY_ATTR_PURPOSE: Final = "purpose"
TRANS_KEY_ATTR_KID_NAME: Final = "kid_name"
TRANS_KEY_ATTR_CHORE_NAME: Final = "chore_name"
TRANS_KEY_ATTR_BADGE_NAME: Final = "badge_name"
TRANS_KEY_ATTR_REWARD_NAME: Final = "reward_name"
TRANS_KEY_ATTR_ACHIEVEMENT_NAME: Final = "achievement_name"
TRANS_KEY_ATTR_CHALLENGE_NAME: Final = "challenge_name"
TRANS_KEY_ATTR_BONUS_NAME: Final = "bonus_name"
TRANS_KEY_ATTR_PENALTY_NAME: Final = "penalty_name"
TRANS_KEY_ATTR_DESCRIPTION: Final = "description"

# Dashboard Helper Sensor attributes (KidDashboardHelperSensor)
TRANS_KEY_ATTR_CHORES: Final = "chores"
TRANS_KEY_ATTR_CHORES_BY_LABEL: Final = "chores_by_label"
TRANS_KEY_ATTR_REWARDS: Final = "rewards"
TRANS_KEY_ATTR_BADGES: Final = "badges"
TRANS_KEY_ATTR_BONUSES: Final = "bonuses"
TRANS_KEY_ATTR_PENALTIES: Final = "penalties"
TRANS_KEY_ATTR_ACHIEVEMENTS: Final = "achievements"
TRANS_KEY_ATTR_CHALLENGES: Final = "challenges"
TRANS_KEY_ATTR_POINTS_BUTTONS: Final = "points_buttons"
TRANS_KEY_ATTR_PENDING_APPROVALS: Final = "pending_approvals"
TRANS_KEY_ATTR_CORE_SENSORS: Final = "core_sensors"
TRANS_KEY_ATTR_DASHBOARD_HELPERS: Final = "dashboard_helpers"
TRANS_KEY_ATTR_UI_TRANSLATIONS: Final = "ui_translations"
TRANS_KEY_ATTR_LANGUAGE: Final = "language"

# Shared attributes across multiple sensors
TRANS_KEY_ATTR_STATUS: Final = "status"
TRANS_KEY_ATTR_LABELS: Final = "labels"
TRANS_KEY_ATTR_COST: Final = "cost"
TRANS_KEY_ATTR_POINTS: Final = "points"
TRANS_KEY_ATTR_APPLIED: Final = "applied"
TRANS_KEY_ATTR_CLAIMS: Final = "claims"
TRANS_KEY_ATTR_APPROVALS: Final = "approvals"
TRANS_KEY_ATTR_EID: Final = "eid"
TRANS_KEY_ATTR_NAME: Final = "name"
TRANS_KEY_ATTR_BADGE_TYPE: Final = "badge_type"
TRANS_KEY_ATTR_BADGE_EARNED: Final = "badge_earned"

# Chore-specific attributes (ChoreStatusSensor, dashboard helper chores array)
TRANS_KEY_ATTR_CHORE_LABELS: Final = "chore_labels"
TRANS_KEY_ATTR_CHORE_DUE_DATE: Final = "chore_due_date"
TRANS_KEY_ATTR_CHORE_IS_TODAY_AM: Final = "chore_is_today_am"
TRANS_KEY_ATTR_CHORE_PRIMARY_GROUP: Final = "chore_primary_group"
TRANS_KEY_ATTR_CHORE_CLAIMED_BY: Final = "chore_claimed_by"
TRANS_KEY_ATTR_CHORE_COMPLETED_BY: Final = "chore_completed_by"
TRANS_KEY_ATTR_CAN_CLAIM: Final = "can_claim"
TRANS_KEY_ATTR_CAN_APPROVE: Final = "can_approve"
TRANS_KEY_ATTR_COMPLETION_CRITERIA: Final = "completion_criteria"
TRANS_KEY_ATTR_LAST_APPROVED: Final = "last_approved"
TRANS_KEY_ATTR_LAST_CLAIMED: Final = "last_claimed"
TRANS_KEY_ATTR_APPROVAL_PERIOD_START: Final = "approval_period_start"


# ------------------------------------------------------------------------------------------------
# Entities Attributes
# ------------------------------------------------------------------------------------------------
ATTR_ACHIEVEMENT_NAME: Final = "achievement_name"
ATTR_ALL_EARNED_BADGES: Final = "all_earned_badges"
ATTR_APPROVAL_RESET_TYPE: Final = "approval_reset_type"
ATTR_APPROVAL_PERIOD_START: Final = "approval_period_start"
ATTR_APPLICABLE_DAYS: Final = "applicable_days"
ATTR_AWARDED: Final = "awarded"
ATTR_BADGE_AWARDS: Final = "awards"
ATTR_BONUS_BUTTON_EID: Final = "bonus_button_eid"
ATTR_CAN_APPROVE: Final = "can_approve"
ATTR_CAN_CLAIM: Final = "can_claim"
ATTR_ASSIGNED_KIDS: Final = "assigned_kids"
ATTR_ASSOCIATED_ACHIEVEMENT: Final = "associated_achievement"
ATTR_ASSOCIATED_CHALLENGE: Final = "associated_challenge"
ATTR_ASSOCIATED_CHORE: Final = "associated_chore"
ATTR_AWARD_POINTS: Final = "award_points"
ATTR_AWARD_REWARD: Final = "award_reward"
ATTR_BADGE_AWARD_MODE: Final = "award_mode"
ATTR_BADGE_NAME: Final = "badge_name"
ATTR_BADGE_STATUS: Final = "badge_status"
ATTR_BADGE_TYPE: Final = "badge_type"
ATTR_BONUS_NAME: Final = "bonus_name"
ATTR_BONUS_POINTS: Final = "bonus_points"
ATTR_CHALLENGE_NAME: Final = "challenge_name"
ATTR_CHALLENGE_TYPE: Final = "challenge_type"
ATTR_CHORE_APPROVALS_COUNT: Final = "chore_approvals_count"
ATTR_CHORE_APPROVALS_TODAY: Final = "chore_approvals_today"
ATTR_CHORE_CLAIMS_COUNT: Final = "chore_claims_count"
ATTR_CHORE_CURRENT_STREAK: Final = "chore_current_streak"
ATTR_CHORE_HIGHEST_STREAK: Final = "chore_highest_streak"
ATTR_CHORE_POINTS_EARNED: Final = "chore_points_earned"
ATTR_CHORE_OVERDUE_COUNT: Final = "chore_overdue_count"
ATTR_CHORE_DISAPPROVED_COUNT: Final = "chore_disapproved_count"
ATTR_CHORE_LAST_LONGEST_STREAK_DATE: Final = "chore_last_longest_streak_date"
ATTR_CHORE_APPROVE_BUTTON_ENTITY_ID: Final = "approve_button_eid"
ATTR_CHORE_CLAIM_BUTTON_ENTITY_ID: Final = "claim_button_eid"
ATTR_CHORE_DISAPPROVE_BUTTON_ENTITY_ID: Final = "disapprove_button_eid"
ATTR_CHORE_ICON: Final = "chore_icon"
ATTR_CHORE_NAME: Final = "chore_name"
ATTR_CLAIMED_ON: Final = "Claimed on"
ATTR_COST: Final = "cost"
ATTR_CRITERIA: Final = "criteria"
ATTR_BADGE_CUMULATIVE_BASELINE_POINTS: Final = "baseline_points"
ATTR_BADGE_CUMULATIVE_CYCLE_POINTS: Final = "cycle_points"
ATTR_BADGE_CUMULATIVE_GRACE_END_DATE: Final = "maintenance_grace_end_date"
ATTR_BADGE_CUMULATIVE_MAINTENANCE_POINTS_REQUIRED: Final = "maintenance_points_required"
ATTR_BADGE_CUMULATIVE_MAINTENANCE_END_DATE: Final = "maintenance_end_date"
ATTR_BADGE_CUMULATIVE_POINTS_TO_MAINTENANCE: Final = "maintenance_points_remaining"
ATTR_CURRENT_BADGE_NAME: Final = "current_badge_name"
ATTR_CURRENT_BADGE_EID: Final = "current_badge_eid"
ATTR_CUSTOM_FREQUENCY_INTERVAL: Final = "custom_frequency_interval"
ATTR_CUSTOM_FREQUENCY_UNIT: Final = "custom_frequency_unit"
ATTR_DAILY_THRESHOLD: Final = "daily_threshold"
ATTR_DEFAULT_POINTS: Final = "default_points"
ATTR_DESCRIPTION: Final = "description"
ATTR_PREFIX_CHORE_STAT: Final = "chore_stat_"
ATTR_PREFIX_POINT_STAT: Final = "point_stat_"
ATTR_PURPOSE: Final = "purpose"

# PURPOSE values for sensor attributes (for translation support)
# Main sensors (sensor.py)
PURPOSE_SENSOR_CHORE_STATUS: Final = "Status of chore claim/approval for kid"
PURPOSE_SENSOR_POINTS: Final = "Current point balance and point stats"
PURPOSE_SENSOR_CHORES: Final = (
    "All time completed chores and chore stats (total, approved, claimed, pending)"
)
PURPOSE_SENSOR_BADGE_HIGHEST: Final = (
    "Highest badge earned by kid, cumulative badge cycle and other badge info"
)
PURPOSE_SENSOR_BADGE_PROGRESS: Final = "Percent progress toward earning badge"
PURPOSE_SENSOR_BADGE: Final = (
    "Count of kids who have earned this badge and badge information"
)
PURPOSE_SENSOR_SHARED_CHORE: Final = "Global state of shared chore"
PURPOSE_SENSOR_REWARD_STATUS: Final = "Count of times reward claimed by kid"
PURPOSE_SENSOR_PENALTY_APPLIED: Final = "Count of times penalty applied to kid"
PURPOSE_SENSOR_ACHIEVEMENT: Final = (
    "Overall percent progress of achievement across all assigned kids"
)
PURPOSE_SENSOR_CHALLENGE: Final = (
    "Overall percent progress of challenge across all assigned kids"
)
PURPOSE_SENSOR_ACHIEVEMENT_PROGRESS: Final = (
    "Percent progress toward earning achievement"
)
PURPOSE_SENSOR_CHALLENGE_PROGRESS: Final = (
    "Percent progress toward completing challenge"
)
PURPOSE_SENSOR_BONUS_APPLIED: Final = "Count of times bonus applied to kid"
PURPOSE_SENSOR_DASHBOARD_HELPER: Final = "Aggregated kid data for dashboard"
# Legacy sensors (sensor_legacy.py)
PURPOSE_SENSOR_CHORE_APPROVALS_ALL_TIME_EXTRA: Final = (
    "Count of chore approvals all time (extra)"
)
PURPOSE_SENSOR_CHORE_APPROVALS_TODAY_EXTRA: Final = (
    "Count of chore approvals today (extra)"
)
PURPOSE_SENSOR_CHORE_APPROVALS_WEEK_EXTRA: Final = (
    "Count of chore approvals this week (extra)"
)
PURPOSE_SENSOR_CHORE_APPROVALS_MONTH_EXTRA: Final = (
    "Count of chore approvals this month (extra)"
)
PURPOSE_SENSOR_CHORES_PENDING_APPROVAL_EXTRA: Final = (
    "Count of chores pending approval across all kids (extra)"
)
PURPOSE_SENSOR_REWARDS_PENDING_APPROVAL_EXTRA: Final = (
    "Count of rewards pending approval across all kids (extra)"
)
PURPOSE_SENSOR_POINTS_EARNED_TODAY_EXTRA: Final = "Points earned today by kid (extra)"
PURPOSE_SENSOR_POINTS_EARNED_WEEK_EXTRA: Final = (
    "Points earned this week by kid (extra)"
)
PURPOSE_SENSOR_POINTS_EARNED_MONTH_EXTRA: Final = (
    "Points earned this month by kid (extra)"
)
PURPOSE_SENSOR_POINTS_MAX_EVER_EXTRA: Final = (
    "Highest point balance ever reached (extra)"
)
PURPOSE_SENSOR_CHORE_STREAK_EXTRA: Final = (
    "Highest chore completion streak for kid (extra)"
)

# PURPOSE values for button attributes (button.py)
PURPOSE_BUTTON_CHORE_CLAIM: Final = "Kid claims completion of assigned chore"
PURPOSE_BUTTON_CHORE_APPROVE: Final = "Parent approves claimed chore"
PURPOSE_BUTTON_CHORE_DISAPPROVE: Final = "Parent disapproves claimed chore"
PURPOSE_BUTTON_REWARD_REDEEM: Final = "Kid redeems reward using points"
PURPOSE_BUTTON_REWARD_APPROVE: Final = "Parent approves redeemed reward"
PURPOSE_BUTTON_REWARD_DISAPPROVE: Final = "Parent disapproves redeemed reward"
PURPOSE_BUTTON_PENALTY_APPLY: Final = "Parent applies penalty (deducts points)"
PURPOSE_BUTTON_POINTS_ADJUST: Final = "Parent manually adjusts kid's points"
PURPOSE_BUTTON_BONUS_APPLY: Final = "Parent applies bonus (adds points)"

# PURPOSE values for select attributes (select.py)
PURPOSE_SELECT_CHORES: Final = "Dropdown to select chore from all available chores"
PURPOSE_SELECT_REWARDS: Final = "Dropdown to select reward from all available rewards"
PURPOSE_SELECT_PENALTIES: Final = (
    "Dropdown to select penalty from all available penalties"
)
PURPOSE_SELECT_BONUSES: Final = "Dropdown to select bonus from all available bonuses"
PURPOSE_SELECT_KID_CHORES: Final = "Kid's chore selection for dashboard filtering"

# PURPOSE values for calendar attributes (calendar.py)
PURPOSE_CALENDAR_SCHEDULE: Final = "Calendar showing kid's chore schedule and due dates"

# PURPOSE values for datetime attributes (datetime.py)
PURPOSE_DATETIME_DASHBOARD_HELPER: Final = (
    "Date/time picker for dashboard date range filtering"
)

ATTR_DUE_DATE: Final = "due_date"
ATTR_END_DATE: Final = "end_date"
ATTR_FRIENDLY_NAME: Final = "friendly_name"
ATTR_GLOBAL_STATE: Final = "global_state"
ATTR_HIGHEST_BADGE_THRESHOLD_VALUE: Final = "highest_badge_threshold_value"
ATTR_HIGHEST_EARNED_BADGE_NAME: Final = "highest_earned_badge_name"
ATTR_KID_NAME: Final = "kid_name"
ATTR_KIDS_ASSIGNED: Final = "kids_assigned"
ATTR_KIDS_EARNED: Final = "kids_earned"
ATTR_LABELS: Final = "labels"
ATTR_LAST_APPROVED: Final = "last_approved"
ATTR_LAST_CLAIMED: Final = "last_claimed"
ATTR_LAST_DISAPPROVED: Final = "last_disapproved"
ATTR_LAST_OVERDUE: Final = "last_overdue"
ATTR_NEXT_HIGHER_BADGE_NAME: Final = "next_higher_badge_name"
ATTR_NEXT_HIGHER_BADGE_EID: Final = "next_higher_badge_eid"
ATTR_NEXT_LOWER_BADGE_NAME: Final = "next_lower_badge_name"
ATTR_NEXT_LOWER_BADGE_EID: Final = "next_lower_badge_eid"
ATTR_OCCASION_DATE: Final = "occasion_date"
ATTR_OCCASION_TYPE: Final = "occasion_type"
ATTR_PENALTY_BUTTON_EID: Final = "penalty_button_eid"
ATTR_PENALTY_NAME: Final = "penalty_name"
ATTR_PENALTY_POINTS: Final = "penalty_points"
ATTR_PERIODIC_RECURRENT: Final = "recurrent"
ATTR_POINTS_MULTIPLIER: Final = "points_multiplier"
ATTR_POINTS_TO_NEXT_BADGE: Final = "points_to_next_badge"
ATTR_RAW_PROGRESS: Final = "raw_progress"
ATTR_RECURRING_FREQUENCY: Final = "recurring_frequency"
ATTR_REQUIRED_CHORES: Final = "required_chores"
ATTR_RESET_SCHEDULE: Final = "reset_schedule"
ATTR_REWARD_APPROVALS_COUNT: Final = "reward_approvals_count"
ATTR_REWARD_CLAIMS_COUNT: Final = "reward_claims_count"
ATTR_REWARD_NAME: Final = "reward_name"
ATTR_REDEEMED_ON: Final = "Redeemed on"
ATTR_REWARD_POINTS: Final = "reward_points"
ATTR_REWARD_APPROVE_BUTTON_ENTITY_ID: Final = "approve_button_eid"
ATTR_REWARD_CLAIM_BUTTON_ENTITY_ID: Final = "claim_button_eid"
ATTR_REWARD_DISAPPROVE_BUTTON_ENTITY_ID: Final = "disapprove_button_eid"
ATTR_SIGN_LABEL: Final = "sign_label"
ATTR_START_DATE: Final = "start_date"
ATTR_STREAKS_BY_ACHIEVEMENT: Final = "streaks_by_achievement"
ATTR_COMPLETION_CRITERIA: Final = "completion_criteria"
ATTR_TARGET: Final = "target"
ATTR_TARGET_VALUE: Final = "target_value"
ATTR_THRESHOLD_TYPE: Final = "threshold_type"
ATTR_THRESHOLD_VALUE: Final = "threshold_value"

ATTR_TRIGGER_INFO: Final = "trigger_info"
ATTR_TYPE: Final = "type"

# Dashboard Helper Sensor Attributes
ATTR_CHORES_BY_LABEL: Final = "chores_by_label"
ATTR_CHORE_CLAIMED_BY: Final = "claimed_by"
ATTR_CHORE_COMPLETED_BY: Final = "completed_by"
ATTR_CHORE_DUE_DATE: Final = "due_date"
ATTR_CHORE_IS_TODAY_AM: Final = "is_today_am"
ATTR_CHORE_LABELS: Final = "labels"
ATTR_CHORE_PRIMARY_GROUP: Final = "primary_group"

# Common attributes for chores and rewards in dashboard helper
ATTR_EID: Final = "eid"
ATTR_NAME: Final = "name"
ATTR_STATUS: Final = "status"
ATTR_CLAIMS: Final = "claims"
ATTR_APPROVALS: Final = "approvals"
ATTR_POINTS: Final = "points"
ATTR_APPLIED: Final = "applied"
ATTR_BADGE_EARNED: Final = "earned"

# Primary Group Values
PRIMARY_GROUP_TODAY = "today"
PRIMARY_GROUP_THIS_WEEK = "this_week"
PRIMARY_GROUP_OTHER = "other"


# ================================================================================================
# Entity ID Constants (SUFFIX and MIDFIX patterns)
# ================================================================================================
#
# See docs/ARCHITECTURE.md "Entity ID Construction Patterns" for detailed explanation of:
# - SUFFIX pattern: Appended identifiers ("_points", "_badge")
# - MIDFIX pattern: Embedded between parts ("_chore_claim_", "_bonus_")
# - UNIQUE_ID construction: entry_id + [_ids] + SUFFIX
# - ENTITY_ID construction: prefix + [names] + [MIDFIX] + [names] + [SUFFIX]
#
# ================================================================================================

# ------------------------------------------------------------------------------------------------
# Sensors
# ------------------------------------------------------------------------------------------------

# Sensor Prefixes
SENSOR_KC_PREFIX: Final = "sensor.kc_"

# ------------------------------------------------------------------------------------------------
# DateTime
# ------------------------------------------------------------------------------------------------

# DateTime Prefix
DATETIME_KC_PREFIX: Final = "datetime.kc_"

# DateTime Entity ID Midfix and Suffix
DATETIME_KC_EID_MIDFIX_UI_DASHBOARD: Final = "_ui_dashboard_"
DATETIME_KC_EID_SUFFIX_DATE_HELPER: Final = "date_helper"

# DateTime Unique ID Suffix
DATETIME_KC_UID_SUFFIX_DATE_HELPER: Final = "_date_helper"

# Sensor Unique ID Suffixes
SENSOR_KC_UID_SUFFIX_ACHIEVEMENT_SENSOR: Final = "_achievement"
SENSOR_KC_UID_SUFFIX_ACHIEVEMENT_PROGRESS_SENSOR: Final = "_achievement_progress"
SENSOR_KC_UID_SUFFIX_BADGE_PROGRESS_SENSOR: Final = "_badge_progress"
SENSOR_KC_UID_SUFFIX_BADGE_SENSOR: Final = "_badge_sensor"
SENSOR_KC_UID_SUFFIX_BONUS_APPLIES_SENSOR: Final = "_bonus_applies"
SENSOR_KC_UID_SUFFIX_CHALLENGE_SENSOR: Final = "_challenge"
SENSOR_KC_UID_SUFFIX_CHALLENGE_PROGRESS_SENSOR: Final = "_challenge_progress"
SENSOR_KC_UID_SUFFIX_CHORES_SENSOR: Final = "_chores"
SENSOR_KC_UID_SUFFIX_COMPLETED_DAILY_SENSOR: Final = "_completed_daily"
SENSOR_KC_UID_SUFFIX_COMPLETED_MONTHLY_SENSOR: Final = "_completed_monthly"
SENSOR_KC_UID_SUFFIX_COMPLETED_TOTAL_SENSOR: Final = "_completed_total"
SENSOR_KC_UID_SUFFIX_COMPLETED_WEEKLY_SENSOR: Final = "_completed_weekly"
SENSOR_KC_UID_SUFFIX_CHORE_STATUS_SENSOR: Final = "_status"
SENSOR_KC_UID_SUFFIX_KID_BADGES_SENSOR: Final = "_badges"
SENSOR_KC_UID_SUFFIX_KID_HIGHEST_STREAK_SENSOR: Final = "_chores_highest_streak"
SENSOR_KC_UID_SUFFIX_KID_MAX_POINTS_EVER_SENSOR: Final = "_max_points_ever"
SENSOR_KC_UID_SUFFIX_KID_POINTS_EARNED_DAILY_SENSOR: Final = "_points_earned_daily"
SENSOR_KC_UID_SUFFIX_KID_POINTS_EARNED_MONTHLY_SENSOR: Final = "_points_earned_monthly"
SENSOR_KC_UID_SUFFIX_KID_POINTS_EARNED_WEEKLY_SENSOR: Final = "_points_earned_weekly"
SENSOR_KC_UID_SUFFIX_KID_POINTS_SENSOR: Final = "_points"
SENSOR_KC_UID_SUFFIX_PENALTY_APPLIES_SENSOR: Final = "_penalty_applies"
SENSOR_KC_UID_SUFFIX_PENDING_CHORE_APPROVALS_SENSOR: Final = "_pending_chore_approvals"
SENSOR_KC_UID_SUFFIX_PENDING_REWARD_APPROVALS_SENSOR: Final = (
    "_pending_reward_approvals"
)
SENSOR_KC_UID_SUFFIX_REWARD_STATUS_SENSOR: Final = "_reward_status"
SENSOR_KC_UID_SUFFIX_SHARED_CHORE_GLOBAL_STATE_SENSOR: Final = "_global_state"

# Sensor Entity ID Mid & Suffixes
SENSOR_KC_EID_MIDFIX_ACHIEVEMENT_PROGRESS_SENSOR: Final = "_achievement_status_"
SENSOR_KC_EID_MIDFIX_ACHIEVEMENT_SENSOR: Final = "achievement_status_"
SENSOR_KC_EID_MIDFIX_BADGE_PROGRESS_SENSOR: Final = "_badge_status_"
SENSOR_KC_EID_MIDFIX_BONUS_APPLIES_SENSOR: Final = "_bonuses_applied_"
SENSOR_KC_EID_MIDFIX_CHALLENGE_PROGRESS_SENSOR: Final = "_challenge_status_"
SENSOR_KC_EID_MIDFIX_CHALLENGE_SENSOR: Final = "challenge_status_"
SENSOR_KC_EID_MIDFIX_CHORE_STATUS_SENSOR: Final = "_chore_status_"
SENSOR_KC_EID_SUFFIX_CHORES_COMPLETED_DAILY_SENSOR: Final = "_chores_completed_daily"
SENSOR_KC_EID_SUFFIX_CHORES_COMPLETED_MONTHLY_SENSOR: Final = (
    "_chores_completed_monthly"
)
SENSOR_KC_EID_SUFFIX_CHORES_COMPLETED_TOTAL_SENSOR: Final = "_chores_completed_total"
SENSOR_KC_EID_SUFFIX_CHORES_COMPLETED_WEEKLY_SENSOR: Final = "_chores_completed_weekly"
SENSOR_KC_EID_SUFFIX_KID_CHORES_SENSOR: Final = "_chores"
SENSOR_KC_EID_SUFFIX_KID_BADGES_SENSOR: Final = "_badges"
SENSOR_KC_EID_SUFFIX_KID_HIGHEST_STREAK_SENSOR: Final = "_chores_highest_streak"
SENSOR_KC_EID_MIDFIX_PENALTY_APPLIES_SENSOR: Final = "_penalties_applied_"
SENSOR_KC_EID_MIDFIX_REWARD_STATUS_SENSOR: Final = "_reward_status_"
SENSOR_KC_EID_MIDFIX_SHARED_CHORE_GLOBAL_STATUS_SENSOR: Final = "global_chore_status_"
SENSOR_KC_EID_SUFFIX_BADGE_SENSOR: Final = "_badge"
SENSOR_KC_EID_SUFFIX_KID_MAX_POINTS_EARNED_SENSOR: Final = "_points_max_ever"
SENSOR_KC_EID_SUFFIX_KID_POINTS_EARNED_DAILY_SENSOR: Final = "_points_earned_daily"
SENSOR_KC_EID_SUFFIX_KID_POINTS_EARNED_MONTHLY_SENSOR: Final = "_points_earned_monthly"
SENSOR_KC_EID_SUFFIX_KID_POINTS_EARNED_WEEKLY_SENSOR: Final = "_points_earned_weekly"
SENSOR_KC_EID_SUFFIX_KID_POINTS_SENSOR: Final = "_points"
SENSOR_KC_EID_SUFFIX_PENDING_CHORE_APPROVALS_SENSOR: Final = (
    "global_chore_pending_approvals"
)
SENSOR_KC_EID_SUFFIX_PENDING_REWARD_APPROVALS_SENSOR: Final = (
    "global_reward_pending_approvals"
)
# Sensor Entity ID Midfix and Suffix for UI Dashboard Helper
SENSOR_KC_EID_MIDFIX_UI_DASHBOARD: Final = "_ui_dashboard_"
SENSOR_KC_EID_SUFFIX_UI_DASHBOARD_HELPER: Final = "helper"

# ------------------------------------------------------------------------------------------------
# Selects
# ------------------------------------------------------------------------------------------------

# Select Prefixes
SELECT_KC_PREFIX: Final = "select.kc_"

# Select Unique ID Mid & Suffixes
SELECT_KC_UID_MIDFIX_CHORES_SELECT: Final = "_chores_select_"
SELECT_KC_UID_SUFFIX_BONUSES_SELECT: Final = "_bonuses_select"
SELECT_KC_UID_SUFFIX_CHORES_SELECT: Final = "_chores_select"
SELECT_KC_UID_SUFFIX_PENALTIES_SELECT: Final = "_penalties_select"
SELECT_KC_UID_SUFFIX_REWARDS_SELECT: Final = "_rewards_select"

# Select Entity ID Mid & Suffixes
SELECT_KC_EID_SUFFIX_ALL_BONUSES: Final = "all_bonuses"
SELECT_KC_EID_SUFFIX_ALL_CHORES: Final = "all_chores"
SELECT_KC_EID_SUFFIX_ALL_PENALTIES: Final = "all_penalties"
SELECT_KC_EID_SUFFIX_ALL_REWARDS: Final = "all_rewards"
SELECT_KC_EID_SUFFIX_CHORE_LIST: Final = "_ui_dashboard_chore_list_helper"

# ------------------------------------------------------------------------------------------------
# Buttons
# ------------------------------------------------------------------------------------------------

# Button Prefixes
BUTTON_KC_PREFIX: Final = "button.kc_"

# Button Unique ID Mid & Suffixes
BUTTON_KC_UID_MIDFIX_ADJUST_POINTS: Final = "_adjust_points_"
BUTTON_KC_UID_SUFFIX_APPROVE: Final = "_approve"
BUTTON_KC_UID_SUFFIX_APPROVE_REWARD: Final = "_approve_reward"
BUTTON_KC_UID_SUFFIX_CLAIM: Final = "_claim"
BUTTON_KC_UID_SUFFIX_DISAPPROVE: Final = "_disapprove"
BUTTON_KC_UID_SUFFIX_DISAPPROVE_REWARD: Final = "_disapprove_reward"

# Button Entity ID Mid & Suffixes
BUTTON_KC_EID_MIDFIX_BONUS: Final = "_bonus_"
BUTTON_KC_EID_MIDFIX_CHORE_APPROVAL: Final = "_chore_approval_"
BUTTON_KC_EID_MIDFIX_CHORE_CLAIM: Final = "_chore_claim_"
BUTTON_KC_EID_MIDFIX_CHORE_DISAPPROVAL: Final = "_chore_disapproval_"
BUTTON_KC_EID_MIDFIX_PENALTY: Final = "_penalty_"
BUTTON_KC_EID_MIDFIX_REWARD_APPROVAL: Final = "_reward_approval_"
BUTTON_KC_EID_MIDFIX_REWARD_CLAIM: Final = "_reward_claim_"
BUTTON_KC_EID_MIDFIX_REWARD_DISAPPROVAL: Final = "_reward_disapproval_"
BUTTON_KC_EID_SUFFIX_POINTS: Final = "_points"

# ------------------------------------------------------------------------------------------------
# Calendars
# ------------------------------------------------------------------------------------------------

# Calendar Prefixes
CALENDAR_KC_PREFIX: Final = "calendar.kc_"

# Calendar Unique ID Mid & Suffixes
CALENDAR_KC_UID_SUFFIX_CALENDAR: Final = "_calendar"

# ------------------------------------------------------------------------------------------------
# Helper Return Types
# ------------------------------------------------------------------------------------------------
HELPER_RETURN_DATE = "date"
HELPER_RETURN_DATETIME = "datetime"
HELPER_RETURN_DATETIME_LOCAL = "datetime_local"
HELPER_RETURN_DATETIME_UTC = "datetime_utc"
HELPER_RETURN_ISO_DATE = "iso_date"
HELPER_RETURN_ISO_DATETIME = "iso_datetime"
# For HA DateTimeSelector - local timezone, format: "%Y-%m-%d %H:%M:%S"
HELPER_RETURN_SELECTOR_DATETIME = "selector_datetime"

# ------------------------------------------------------------------------------------------------
# DateTime Helper Safety Limits
# ------------------------------------------------------------------------------------------------
# Maximum number of iterations allowed in date calculation loops to prevent infinite loops
# Used in get_next_scheduled_datetime() and add_interval_to_datetime() when require_future=True
MAX_DATE_CALCULATION_ITERATIONS: Final = 1000

# ------------------------------------------------------------------------------------------------
# DateTime Constants (End-of-Period Values)
# ------------------------------------------------------------------------------------------------
# Time values for end-of-day calculations (23:59:00)
END_OF_DAY_HOUR: Final = 23
END_OF_DAY_MINUTE: Final = 59
END_OF_DAY_SECOND: Final = 0

# Calendar calculations
MONTHS_PER_QUARTER: Final = 3
MONTHS_PER_YEAR: Final = 12
LAST_DAY_OF_DECEMBER: Final = 31
LAST_MONTH_OF_YEAR: Final = 12

# Weekday index for Sunday in Python's datetime.weekday() (Monday=0, Sunday=6)
SUNDAY_WEEKDAY_INDEX: Final = 6

# ISO date string slice length (YYYY-MM-DD = 10 characters)
ISO_DATE_STRING_LENGTH: Final = 10

# Month multiplier for interval calculations
MONTH_INTERVAL_MULTIPLIER: Final = 1

# ------------------------------------------------------------------------------------------------
# Services
# ------------------------------------------------------------------------------------------------
SERVICE_ADJUST_POINTS: Final = "adjust_points"
SERVICE_APPLY_BONUS: Final = "apply_bonus"
SERVICE_APPLY_PENALTY: Final = "apply_penalty"
SERVICE_APPROVE_CHORE: Final = "approve_chore"
SERVICE_APPROVE_REWARD: Final = "approve_reward"
SERVICE_CLAIM_CHORE: Final = "claim_chore"
SERVICE_DISAPPROVE_CHORE: Final = "disapprove_chore"
SERVICE_DISAPPROVE_REWARD: Final = "disapprove_reward"
SERVICE_REDEEM_REWARD: Final = "redeem_reward"
SERVICE_REMOVE_AWARDED_BADGES: Final = "remove_awarded_badges"
SERVICE_RESET_ALL_CHORES: Final = "reset_all_chores"
SERVICE_RESET_ALL_DATA: Final = "reset_all_data"
SERVICE_RESET_BONUSES: Final = "reset_bonuses"
SERVICE_RESET_OVERDUE_CHORES: Final = "reset_overdue_chores"
SERVICE_RESET_PENALTIES: Final = "reset_penalties"
SERVICE_RESET_REWARDS: Final = "reset_rewards"
SERVICE_SET_CHORE_DUE_DATE: Final = "set_chore_due_date"
SERVICE_SKIP_CHORE_DUE_DATE: Final = "skip_chore_due_date"


# ------------------------------------------------------------------------------------------------
# Field Names (for service calls)
# ------------------------------------------------------------------------------------------------
FIELD_BADGE_NAME = "badge_name"
FIELD_BONUS_NAME = "bonus_name"
FIELD_CHORE_ID = "chore_id"
FIELD_CHORE_NAME = "chore_name"
FIELD_DUE_DATE = "due_date"
FIELD_KID_ID = "kid_id"
FIELD_KID_NAME = "kid_name"
FIELD_PARENT_NAME = "parent_name"
FIELD_PENALTY_NAME = "penalty_name"
FIELD_POINTS_AWARDED = "points_awarded"
FIELD_REWARD_NAME = "reward_name"


# ------------------------------------------------------------------------------------------------
# Labels
# ------------------------------------------------------------------------------------------------
LABEL_BADGES: Final = "Badges"
LABEL_COMPLETED_DAILY: Final = "Daily Completed Chores"
LABEL_COMPLETED_MONTHLY: Final = "Monthly Completed Chores"
LABEL_COMPLETED_WEEKLY: Final = "Weekly Completed Chores"
LABEL_NONE: Final = ""
LABEL_POINTS: Final = "Points"

# Entity Type Labels (for error messages and translation placeholders)
LABEL_KID: Final = "Kid"
LABEL_CHORE: Final = "Chore"
LABEL_REWARD: Final = "Reward"
LABEL_BADGE: Final = "Badge"
LABEL_PENALTY: Final = "Penalty"
LABEL_BONUS: Final = "Bonus"
LABEL_PARENT: Final = "Parent"
LABEL_ACHIEVEMENT: Final = "Achievement"
LABEL_CHALLENGE: Final = "Challenge"

# Backup/Restore Labels
# (backup label constants removed - now using emoji prefixes directly)

# Deprecated entity unique_id suffixes (for cleanup/migration - KC 3.x compatibility)
DEPRECATED_SUFFIX_BADGES: Final = "_badges"
DEPRECATED_SUFFIX_REWARD_CLAIMS: Final = "_reward_claims"
DEPRECATED_SUFFIX_REWARD_APPROVALS: Final = "_reward_approvals"
DEPRECATED_SUFFIX_CHORE_CLAIMS: Final = "_chore_claims"
DEPRECATED_SUFFIX_CHORE_APPROVALS: Final = "_chore_approvals"
DEPRECATED_SUFFIX_STREAK: Final = "_streak"

DEPRECATED_SUFFIXES: Final = [
    DEPRECATED_SUFFIX_BADGES,
    DEPRECATED_SUFFIX_REWARD_CLAIMS,
    DEPRECATED_SUFFIX_REWARD_APPROVALS,
    DEPRECATED_SUFFIX_CHORE_CLAIMS,
    DEPRECATED_SUFFIX_CHORE_APPROVALS,
    DEPRECATED_SUFFIX_STREAK,
]

# Migration identifiers (for schema version tracking in DATA_META_MIGRATIONS_APPLIED)
MIGRATION_DATETIME_UTC: Final = "datetime_utc"
MIGRATION_CHORE_DATA_STRUCTURE: Final = "chore_data_structure"
MIGRATION_KID_DATA_STRUCTURE: Final = "kid_data_structure"
MIGRATION_BADGE_RESTRUCTURE: Final = "badge_restructure"
MIGRATION_CUMULATIVE_BADGE_PROGRESS: Final = "cumulative_badge_progress"
MIGRATION_BADGES_EARNED_DICT: Final = "badges_earned_dict"
MIGRATION_POINT_STATS: Final = "point_stats"
MIGRATION_CHORE_DATA_AND_STREAKS: Final = "chore_data_and_streaks"

DEFAULT_MIGRATIONS_APPLIED: Final = [
    MIGRATION_DATETIME_UTC,
    MIGRATION_CHORE_DATA_STRUCTURE,
    MIGRATION_KID_DATA_STRUCTURE,
    MIGRATION_BADGE_RESTRUCTURE,
    MIGRATION_CUMULATIVE_BADGE_PROGRESS,
    MIGRATION_BADGES_EARNED_DICT,
    MIGRATION_POINT_STATS,
    MIGRATION_CHORE_DATA_AND_STREAKS,
]


# ------------------------------------------------------------------------------------------------
# Button Prefixes
# ------------------------------------------------------------------------------------------------
BUTTON_BONUS_PREFIX: Final = "bonus_button_"
BUTTON_PENALTY_PREFIX: Final = "penalty_button_"
BUTTON_REWARD_PREFIX: Final = "reward_button_"


# ------------------------------------------------------------------------------------------------
# Errors and Warnings
# ------------------------------------------------------------------------------------------------

# Translation Keys for Phase 2b: Generic Error Templates (coordinator.py remediation)
# These 12 templates replace 41 hardcoded f-strings in coordinator.py using placeholders
# Format: TRANS_KEY_ERROR_{CATEGORY} with translation_placeholders for dynamic values
TRANS_KEY_ERROR_NOT_FOUND: Final = "not_found"  # {entity_type} '{name}' not found
TRANS_KEY_ERROR_NOT_ASSIGNED: Final = "not_assigned"  # {entity} not assigned to {kid}
TRANS_KEY_ERROR_INSUFFICIENT_POINTS: Final = (
    "insufficient_points"  # {kid} has {current}, needs {required}
)
TRANS_KEY_ERROR_ALREADY_CLAIMED: Final = "already_claimed"  # {entity} already claimed
TRANS_KEY_ERROR_INVALID_STATUS: Final = (
    "invalid_status"  # {entity} status is {status}, expected {expected}
)
TRANS_KEY_ERROR_ENTITY_MISMATCH: Final = (
    "entity_mismatch"  # {provided} does not match {expected}
)
TRANS_KEY_ERROR_INVALID_FREQUENCY: Final = (
    "invalid_frequency"  # Recurring frequency '{frequency}' is not valid
)
TRANS_KEY_ERROR_MISSING_FIELD: Final = (
    "missing_field"  # Required field '{field}' is missing from {entity}
)
TRANS_KEY_ERROR_INVALID_DATE: Final = "invalid_date"  # {field} date '{date}' is invalid
TRANS_KEY_ERROR_DATE_CONSTRAINT: Final = (
    "date_constraint"  # {constraint} violation: {detail}
)
TRANS_KEY_ERROR_OPERATION_FAILED: Final = (
    "operation_failed"  # {operation} failed: {reason}
)
TRANS_KEY_ERROR_CONFIGURATION: Final = (
    "configuration_error"  # Configuration error: {detail}
)
TRANS_KEY_ERROR_SHARED_CHORE_KID: Final = (
    "shared_chore_cannot_have_kid"  # Cannot specify kid for SHARED chore
)
TRANS_KEY_ERROR_REQUIRED_FIELD: Final = "required_field"  # Must provide {field}
TRANS_KEY_ERROR_INVALID_DATE_FORMAT: Final = (
    "invalid_date_format"  # Invalid date format
)
TRANS_KEY_ERROR_DATE_IN_PAST: Final = "date_in_past"  # Due date cannot be in the past
TRANS_KEY_ERROR_MISSING_CHORE: Final = "missing_chore"  # Must provide chore ID or name
TRANS_KEY_ERROR_CHORE_CLAIMED_BY_OTHER: Final = (
    "chore_claimed_by_other"  # Chore already claimed by another kid
)
TRANS_KEY_ERROR_CHORE_ALREADY_APPROVED: Final = (
    "chore_already_approved"  # Chore already approved, try again after reset period
)
TRANS_KEY_ERROR_CHORE_PENDING_CLAIM: Final = (
    "chore_pending_claim"  # Chore has a pending claim awaiting approval
)
TRANS_KEY_ERROR_CHORE_COMPLETED_BY_OTHER: Final = (
    "chore_completed_by_other"  # SHARED_FIRST chore already completed by another kid
)

# Translation Keys for Phase 2-4 Error Migration (Action Templating)
# These map to templated exceptions in translations/en.json using action labels
TRANS_KEY_ERROR_NOT_AUTHORIZED_ACTION: Final = "not_authorized_action"
TRANS_KEY_ERROR_NOT_AUTHORIZED_ACTION_GLOBAL: Final = "not_authorized_action_global"
TRANS_KEY_ERROR_CALENDAR_CREATE_NOT_SUPPORTED: Final = "calendar_create_not_supported"
TRANS_KEY_ERROR_CALENDAR_DELETE_NOT_SUPPORTED: Final = "calendar_delete_not_supported"
TRANS_KEY_ERROR_CALENDAR_UPDATE_NOT_SUPPORTED: Final = "calendar_update_not_supported"

# Action identifiers for use with TRANS_KEY_ERROR_NOT_AUTHORIZED_ACTION template
# These values are passed directly as {action} placeholder in exception messages
ERROR_ACTION_CLAIM_CHORES: Final = "claim_chores"
ERROR_ACTION_APPROVE_CHORES: Final = "approve_chores"
ERROR_ACTION_DISAPPROVE_CHORES: Final = "disapprove_chores"
ERROR_ACTION_REDEEM_REWARDS: Final = "redeem_rewards"
ERROR_ACTION_APPROVE_REWARDS: Final = "approve_rewards"
ERROR_ACTION_DISAPPROVE_REWARDS: Final = "disapprove_rewards"
ERROR_ACTION_APPLY_PENALTIES: Final = "apply_penalties"
ERROR_ACTION_APPLY_BONUSES: Final = "apply_bonuses"
ERROR_ACTION_ADJUST_POINTS: Final = "adjust_points"
ERROR_ACTION_RESET_PENALTIES: Final = "reset_penalties"
ERROR_ACTION_RESET_BONUSES: Final = "reset_bonuses"
ERROR_ACTION_RESET_REWARDS: Final = "reset_rewards"
ERROR_ACTION_REMOVE_BADGES: Final = "remove_badges"

TRANS_KEY_ERROR_MSG_NO_ENTRY_FOUND: Final = "error_msg_no_entry_found"

# Config Flow & Options Flow Translation Keys (Phase 2b)
# Generic templates for validation errors across config/options flows
TRANS_KEY_CFOF_INVALID_INPUT: Final = "invalid_input"  # General validation failure
TRANS_KEY_CFOF_DUPLICATE_NAME: Final = "duplicate_name"  # Name already exists
TRANS_KEY_CFOF_INVALID_DATE_RANGE: Final = "invalid_date_range"  # Start/end date issues
TRANS_KEY_CFOF_MISSING_REQUIRED: Final = "missing_required"  # Required field missing
TRANS_KEY_CFOF_INVALID_FORMAT: Final = "invalid_format"  # Format validation failure


# Unknown States (Display Translation Keys)
TRANS_KEY_DISPLAY_UNKNOWN_CHALLENGE: Final = "display_unknown_challenge"
TRANS_KEY_DISPLAY_UNKNOWN_CHORE: Final = "display_unknown_chore"
TRANS_KEY_DISPLAY_UNKNOWN_KID: Final = "display_unknown_kid"
TRANS_KEY_DISPLAY_UNKNOWN_REWARD: Final = "display_unknown_reward"
TRANS_KEY_DISPLAY_UNKNOWN_ENTITY: Final = "display_unknown_entity"

# Config Flow & Options Flow Error Keys
CFOP_ERROR_ACHIEVEMENT_NAME: Final = "name"
CFOP_ERROR_BADGE_NAME: Final = "badge_name"
CFOP_ERROR_ASSIGNED_KIDS: Final = "assigned_kids"
CFOP_ERROR_BASE: Final = "base"
CFOP_ERROR_CORRUPT_FILE: Final = "corrupt_file"
CFOP_ERROR_FILE_NOT_FOUND: Final = "file_not_found"
CFOP_ERROR_INVALID_JSON: Final = "invalid_json"
CFOP_ERROR_NO_BACKUPS_FOUND: Final = "no_backups_found"
CFOP_ERROR_RESTORE_FAILED: Final = "restore_failed"
CFOP_ERROR_BONUS_NAME: Final = "bonus_name"
CFOP_ERROR_CHALLENGE_NAME: Final = "name"
CFOP_ERROR_CHORE_NAME: Final = "chore_name"
CFOP_ERROR_DUE_DATE: Final = "due_date"
CFOP_ERROR_END_DATE: Final = "end_date"
CFOP_ERROR_KID_NAME: Final = "kid_name"
CFOP_ERROR_PARENT_NAME: Final = "parent_name"
CFOP_ERROR_PENALTY_NAME: Final = "penalty_name"
CFOP_ERROR_REWARD_NAME: Final = "reward_name"
CFOP_ERROR_SELECT_CHORE_ID: Final = "selected_chore_id"
CFOP_ERROR_START_DATE: Final = "start_date"
# Additional error keys used by config_flow.py abort() calls
CFOP_ERROR_INVALID_STRUCTURE: Final = "invalid_structure"
CFOP_ERROR_UNKNOWN: Final = "unknown"
# Phase 3 additions for config_flow remediation
CFOP_ERROR_EMPTY_JSON: Final = "empty_json"  # Empty JSON data provided
CFOP_ERROR_INVALID_SELECTION: Final = "invalid_selection"  # Invalid menu selection
CFOP_ERROR_OVERDUE_RESET_COMBO: Final = "overdue_handling_type"  # Invalid combination
# Phase 3c: System Settings Consolidation
CFOP_ERROR_UPDATE_INTERVAL: Final = "update_interval"
CFOP_ERROR_CALENDAR_SHOW_PERIOD: Final = "calendar_show_period"
CFOP_ERROR_RETENTION_DAILY: Final = "retention_daily"
CFOP_ERROR_RETENTION_WEEKLY: Final = "retention_weekly"
CFOP_ERROR_RETENTION_MONTHLY: Final = "retention_monthly"
CFOP_ERROR_RETENTION_YEARLY: Final = "retention_yearly"
CFOP_ERROR_POINTS_ADJUST_VALUES: Final = "points_adjust_values"


# ------------------------------------------------------------------------------------------------
# Parent Approval Workflow
# ------------------------------------------------------------------------------------------------
DEFAULT_PARENT_APPROVAL_REQUIRED: Final = (
    True  # Enable parent approval for certain actions
)
DEFAULT_HA_USERNAME_LINK_ENABLED: Final = True  # Enable linking kids to HA usernames


# ------------------------------------------------------------------------------------------------
# Calendar Attributes
# ------------------------------------------------------------------------------------------------
ATTR_CAL_ALL_DAY: Final = "all_day"
ATTR_CAL_DESCRIPTION: Final = "description"
ATTR_CAL_END: Final = "end"
ATTR_CAL_MANUFACTURER: Final = "manufacturer"
ATTR_CAL_START: Final = "start"
ATTR_CAL_SUMMARY: Final = "summary"


# ------------------------------------------------------------------------------------------------
# Dashboard Helper Sensor Attributes (Phase 2b)
# JSON keys exposed in sensor.kc_<kid>_ui_dashboard_helper attributes for dashboard consumption
# ------------------------------------------------------------------------------------------------
ATTR_DASHBOARD_CHORES: Final = "chores"
ATTR_DASHBOARD_REWARDS: Final = "rewards"
ATTR_DASHBOARD_BONUSES: Final = "bonuses"
ATTR_DASHBOARD_PENALTIES: Final = "penalties"
ATTR_DASHBOARD_ACHIEVEMENTS: Final = "achievements"
ATTR_DASHBOARD_CHALLENGES: Final = "challenges"
ATTR_DASHBOARD_BADGES: Final = "badges"
ATTR_DASHBOARD_CHORES_BY_LABEL: Final = "chores_by_label"
ATTR_DASHBOARD_PENDING_APPROVALS: Final = "pending_approvals"
ATTR_DASHBOARD_POINTS_BUTTONS: Final = "points_buttons"
ATTR_DASHBOARD_KID_NAME: Final = "kid_name"
ATTR_DASHBOARD_UI_TRANSLATIONS: Final = "ui_translations"


# ------------------------------------------------------------------------------------------------
# Translation Keys
# ------------------------------------------------------------------------------------------------
# Global
TRANS_KEY_LABEL_ACHIEVEMENT: Final = "label_achievement"
TRANS_KEY_LABEL_BADGE: Final = "label_badge"
TRANS_KEY_LABEL_BONUS: Final = "label_bonus"
TRANS_KEY_LABEL_CHALLENGE: Final = "label_challenge"
TRANS_KEY_LABEL_CHORE: Final = "label_chore"
TRANS_KEY_LABEL_KID: Final = "label_kid"
TRANS_KEY_LABEL_PENALTY: Final = "label_penalty"
TRANS_KEY_LABEL_REWARD: Final = "label_reward"
TRANS_KEY_NO_DUE_DATE: Final = "no_due_date"

# ConfigFlow & OptionsFlow Translation Keys
# Data Recovery
TRANS_KEY_CFOF_DATA_RECOVERY_TITLE: Final = "data_recovery_title"
TRANS_KEY_CFOF_DATA_RECOVERY_DESCRIPTION: Final = "data_recovery_description"
TRANS_KEY_CFOF_BACKUP_CURRENT_ACTIVE: Final = "backup_current_active"
TRANS_KEY_CFOF_BACKUP_AGE: Final = "backup_age"
TRANS_KEY_CFOF_RESTORE_WARNING: Final = "restore_warning"

# Backup Management
TRANS_KEY_CFOF_BACKUP_ACTIONS_MENU: Final = "backup_actions_menu"
TRANS_KEY_CFOF_SELECT_BACKUP_TO_DELETE: Final = "select_backup_to_delete"
TRANS_KEY_CFOF_SELECT_BACKUP_TO_RESTORE: Final = "select_backup_to_restore"

# Badge Fields
TRANS_KEY_CFOF_BADGE_ASSIGNED_TO: Final = "assigned_to"
TRANS_KEY_CFOF_BADGE_ASSOCIATED_ACHIEVEMENT: Final = "associated_achievement"
TRANS_KEY_CFOF_BADGE_AWARD_ITEMS: Final = "award_items"
TRANS_KEY_CFOF_BADGE_ASSOCIATED_CHALLENGE: Final = "associated_challenge"
TRANS_KEY_CFOF_BADGE_LABELS: Final = "badge_labels"
TRANS_KEY_CFOF_BADGE_OCCASION_TYPE: Final = "occasion_type"
TRANS_KEY_CFOF_BADGE_RESET_SCHEDULE_END_DATE_REQUIRED: Final = "end_date_required"
TRANS_KEY_CFOF_BADGE_RESET_SCHEDULE: Final = "reset_schedule"
TRANS_KEY_CFOF_BADGE_RESET_SCHEDULE_RECURRING_FREQUENCY: Final = "recurring_frequency"
TRANS_KEY_CFOF_BADGE_RESET_SCHEDULE_START_DATE_REQUIRED: Final = "start_date_required"
TRANS_KEY_CFOF_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL_UNIT: Final = "custom_interval_unit"
TRANS_KEY_CFOF_BADGE_RESET_SCHEDULE_CUSTOM_INTERVAL: Final = "custom_interval"
TRANS_KEY_CFOF_BADGE_SELECTED_CHORES: Final = "selected_chores"
TRANS_KEY_CFOF_BADGE_TARGET_TYPE: Final = "target_type"
TRANS_KEY_CFOF_BADGE_TYPE: Final = "badge_type"
TRANS_KEY_CFOF_CHORE_AUTO_APPROVE: Final = "auto_approve"
TRANS_KEY_CFOF_CHORE_MUST_BE_SELECTED: Final = "a_chore_must_be_selected"
TRANS_KEY_CFOF_CHORE_SHOW_ON_CALENDAR: Final = "show_on_calendar"
TRANS_KEY_CFOF_DUE_DATE_IN_PAST: Final = "due_date_in_past"
TRANS_KEY_CFOF_DUPLICATE_ACHIEVEMENT: Final = "duplicate_achievement"
TRANS_KEY_CFOF_DUPLICATE_BADGE: Final = "duplicate_badge"
TRANS_KEY_CFOF_DUPLICATE_BONUS: Final = "duplicate_bonus"
TRANS_KEY_CFOF_DUPLICATE_CHALLENGE: Final = "duplicate_challenge"
TRANS_KEY_CFOF_DUPLICATE_CHORE: Final = "duplicate_chore"
TRANS_KEY_CFOF_DUPLICATE_KID: Final = "duplicate_kid"
TRANS_KEY_CFOF_DUPLICATE_PARENT: Final = "duplicate_parent"
TRANS_KEY_CFOF_DUPLICATE_PENALTY: Final = "duplicate_penalty"
TRANS_KEY_CFOF_DUPLICATE_REWARD: Final = "duplicate_reward"
TRANS_KEY_CFOF_END_DATE_IN_PAST: Final = "end_date_in_past"
TRANS_KEY_CFOF_END_DATE_NOT_AFTER_START_DATE: Final = "end_date_not_after_start_date"
TRANS_KEY_CFOF_ERROR_ASSIGNED_KIDS: Final = "error_assigned_kids"
# Config Flow abort reason translation keys (for async_abort calls)
TRANS_KEY_CFOP_ERROR_FILE_NOT_FOUND: Final = "file_not_found"
TRANS_KEY_CFOP_ERROR_CORRUPT_FILE: Final = "corrupt_file"
TRANS_KEY_CFOP_ERROR_INVALID_STRUCTURE: Final = "invalid_structure"
TRANS_KEY_CFOP_ERROR_UNKNOWN: Final = "unknown"
TRANS_KEY_ERROR_SINGLE_INSTANCE: Final = "single_instance_allowed"
TRANS_KEY_CFOF_ERROR_AWARD_POINTS_MINIMUM: Final = "error_award_points_minimum"
TRANS_KEY_CFOF_ERROR_AWARD_INVALID_MULTIPLIER: Final = "error_award_invalid_multiplier"
TRANS_KEY_CFOF_ERROR_AWARD_INVALID_AWARD_ITEM: Final = "invalid_award_item_selected"
TRANS_KEY_CFOF_ERROR_AWARD_AT_LEAST_ONE_REQUIRED: Final = (
    "error_award_at_least_one_required"
)
TRANS_KEY_CFOF_ERROR_BADGE_ACHIEVEMENT_REQUIRED: Final = (
    "error_badge_achievement_required"
)
TRANS_KEY_CFOF_ERROR_BADGE_CHALLENGE_REQUIRED: Final = "error_badge_challenge_required"
TRANS_KEY_CFOF_ERROR_BADGE_OCCASION_TYPE_REQUIRED: Final = (
    "error_badge_occasion_type_required"
)
TRANS_KEY_CFOF_ERROR_BADGE_CUSTOM_RESET_DATE_REQUIRED: Final = (
    "error_badge_custom_reset_date_required"
)
TRANS_KEY_CFOF_BADGE_REQUIRES_ASSIGNMENT: Final = "badge_requires_assignment"
TRANS_KEY_CFOF_ERROR_BADGE_END_DATE_REQUIRED: Final = "error_badge_end_date_required"
TRANS_KEY_CFOF_ERROR_BADGE_RESET_TYPE_REQUIRED: Final = (
    "error_badge_reset_type_required"
)
TRANS_KEY_CFOF_ERROR_BADGE_START_DATE_REQUIRED: Final = (
    "error_badge_start_date_required"
)
TRANS_KEY_CFOF_ERROR_REWARD_SELECTION: Final = "error_reward_selection"
TRANS_KEY_CFOF_ERROR_POINTS_MULTIPLIER_REQUIRED: Final = (
    "error_points_multiplier_required"
)
TRANS_KEY_CFOF_ERROR_THRESHOLD_REQUIRED: Final = "error_threshold_required"
TRANS_KEY_CFOF_INVALID_ACHIEVEMENT: Final = "invalid_achievement"
TRANS_KEY_CFOF_INVALID_ACHIEVEMENT_COUNT: Final = "invalid_achievement_count"
TRANS_KEY_CFOF_INVALID_ACHIEVEMENT_NAME: Final = "invalid_achievement_name"
TRANS_KEY_CFOF_INVALID_ACTION: Final = "invalid_action"
TRANS_KEY_CFOF_INVALID_BADGE: Final = "invalid_badge"
TRANS_KEY_CFOF_INVALID_BADGE_COUNT: Final = "invalid_badge_count"
TRANS_KEY_CFOF_INVALID_BADGE_NAME: Final = "invalid_badge_name"
TRANS_KEY_CFOF_INVALID_BADGE_TARGET_THRESHOLD_VALUE = (
    "invalid_badge_target_threshold_value"
)
TRANS_KEY_CFOF_INVALID_BADGE_TYPE: Final = "invalid_badge_type"
TRANS_KEY_CFOF_INVALID_MAINTENANCE_RULES: Final = "invalid_maintenance_rules"
TRANS_KEY_CFOF_TARGET_THRESHOLD_REQUIRED: Final = "target_threshold_required"
TRANS_KEY_CFOF_INVALID_FORMAT_LIST: Final = "invalid_format_list_expected"
TRANS_KEY_CFOF_END_DATE_BEFORE_START: Final = "end_date_before_start_date"
TRANS_KEY_CFOF_INVALID_GRACE_PERIOD: Final = "invalid_grace_period_days"
TRANS_KEY_CFOF_INVALID_BONUS: Final = "invalid_bonus"
TRANS_KEY_CFOF_INVALID_BONUS_COUNT: Final = "invalid_bonus_count"
TRANS_KEY_CFOF_INVALID_BONUS_NAME: Final = "invalid_bonus_name"
TRANS_KEY_CFOF_INVALID_CHALLENGE: Final = "invalid_challenge"
TRANS_KEY_CFOF_INVALID_CHALLENGE_COUNT: Final = "invalid_challenge_count"
TRANS_KEY_CFOF_INVALID_CHALLENGE_NAME: Final = "invalid_challenge_name"
TRANS_KEY_CFOF_CHALLENGE_NAME_REQUIRED: Final = "err_name_required"
TRANS_KEY_CFOF_CHALLENGE_NAME_DUPLICATE: Final = "err_name_duplicate"
TRANS_KEY_CFOF_CHALLENGE_DATES_REQUIRED: Final = "err_dates_required"
TRANS_KEY_CFOF_CHALLENGE_END_BEFORE_START: Final = "err_end_before_start"
TRANS_KEY_CFOF_CHALLENGE_INVALID_DATE: Final = "err_invalid_date"
TRANS_KEY_CFOF_CHALLENGE_TARGET_INVALID: Final = "err_target_invalid"
TRANS_KEY_CFOF_CHALLENGE_POINTS_NEGATIVE: Final = "err_points_negative"
TRANS_KEY_CFOF_CHALLENGE_POINTS_INVALID: Final = "err_points_invalid"
TRANS_KEY_CFOF_INVALID_CHORE: Final = "invalid_chore"
TRANS_KEY_CFOF_INVALID_CHORE_COUNT: Final = "invalid_chore_count"
TRANS_KEY_CFOF_INVALID_CHORE_NAME: Final = "invalid_chore_name"
TRANS_KEY_CFOF_INVALID_OVERDUE_RESET_COMBINATION: Final = (
    "invalid_overdue_reset_combination"
)
TRANS_KEY_CFOF_NO_KIDS_ASSIGNED: Final = "no_kids_assigned"
TRANS_KEY_CFOF_INVALID_DUE_DATE: Final = "invalid_due_date"
TRANS_KEY_CFOF_DATE_REQUIRED_FOR_FREQUENCY: Final = "date_required_for_frequency"
TRANS_KEY_CFOF_INVALID_END_DATE: Final = "invalid_end_date"
TRANS_KEY_CFOF_INVALID_ENTITY: Final = "invalid_entity"
TRANS_KEY_CFOF_INVALID_KID: Final = "invalid_kid"
TRANS_KEY_CFOF_INVALID_KID_COUNT: Final = "invalid_kid_count"
TRANS_KEY_CFOF_INVALID_KID_NAME: Final = "invalid_kid_name"
TRANS_KEY_CFOF_INVALID_PARENT: Final = "invalid_parent"
TRANS_KEY_CFOF_INVALID_PARENT_COUNT: Final = "invalid_parent_count"
TRANS_KEY_CFOF_INVALID_PARENT_NAME: Final = "invalid_parent_name"
TRANS_KEY_CFOF_INVALID_PENALTY: Final = "invalid_penalty"
TRANS_KEY_CFOF_INVALID_PENALTY_COUNT: Final = "invalid_penalty_count"
TRANS_KEY_CFOF_INVALID_PENALTY_NAME: Final = "invalid_penalty_name"
TRANS_KEY_CFOF_INVALID_REWARD: Final = "invalid_reward"
TRANS_KEY_CFOF_INVALID_REWARD_COUNT: Final = "invalid_reward_count"
TRANS_KEY_CFOF_INVALID_REWARD_NAME: Final = "invalird_reward_name"
TRANS_KEY_CFOF_INVALID_SELECTION: Final = "invalid_selection"
TRANS_KEY_CFOF_INVALID_START_DATE: Final = "invalid_start_date"
TRANS_KEY_CFOF_POINTS_LABEL_REQUIRED: Final = "points_label_required"
TRANS_KEY_CFOF_MAIN_MENU: Final = "main_menu"
TRANS_KEY_CFOF_MANAGE_ACTIONS: Final = "manage_actions"
TRANS_KEY_CFOF_NO_ENTITY_TYPE: Final = "no_{}s"
TRANS_KEY_CFOF_POINTS_ADJUST: Final = "points_adjust_options"
TRANS_KEY_CFOF_REQUIRED_CHORES: Final = "required_chores"
TRANS_KEY_CFOP_RESET_SCHEDULE: Final = "reset_schedule"
TRANS_KEY_CFOF_START_DATE_IN_PAST: Final = "start_date_in_past"
TRANS_KEY_CFOF_SETUP_COMPLETE: Final = "setup_complete"
TRANS_KEY_CFOF_SUMMARY_ACHIEVEMENTS: Final = "Achievements: "
TRANS_KEY_CFOF_SUMMARY_BADGES: Final = "Badges: "
TRANS_KEY_CFOF_SUMMARY_BONUSES: Final = "Bonuses: "
TRANS_KEY_CFOF_SUMMARY_CHALLENGES: Final = "Challenges: "
TRANS_KEY_CFOF_SUMMARY_CHORES: Final = "Chores: "
TRANS_KEY_CFOF_SUMMARY_KIDS: Final = "Kids: "
TRANS_KEY_CFOF_SUMMARY_PARENTS: Final = "Parents: "
TRANS_KEY_CFOF_SUMMARY_PENALTIES: Final = "Penalties: "
TRANS_KEY_CFOF_SUMMARY_REWARDS: Final = "Rewards: "

# Phase 3c: System Settings Translation Keys
TRANS_KEY_CFOF_INVALID_UPDATE_INTERVAL: Final = "invalid_update_interval"
TRANS_KEY_CFOF_INVALID_CALENDAR_SHOW_PERIOD: Final = "invalid_calendar_show_period"
TRANS_KEY_CFOF_INVALID_RETENTION_PERIOD: Final = "invalid_retention_period"
TRANS_KEY_CFOF_INVALID_POINTS_ADJUST_VALUES: Final = "invalid_points_adjust_values"

# Flow Helpers Translation Keys
TRANS_KEY_FLOW_HELPERS_APPLICABLE_DAYS: Final = "applicable_days"
TRANS_KEY_FLOW_HELPERS_APPROVAL_RESET_PENDING_CLAIM_ACTION: Final = (
    "approval_reset_pending_claim_action"
)
TRANS_KEY_FLOW_HELPERS_APPROVAL_RESET_TYPE: Final = "approval_reset_type"
TRANS_KEY_FLOW_HELPERS_ASSIGNED_KIDS: Final = "assigned_kids"
TRANS_KEY_FLOW_HELPERS_CHORE_NOTIFICATIONS: Final = "chore_notifications"
TRANS_KEY_FLOW_HELPERS_COMPLETION_CRITERIA: Final = "completion_criteria"
TRANS_KEY_FLOW_HELPERS_ASSOCIATED_ACHIEVEMENT: Final = "associated_achievement"
TRANS_KEY_FLOW_HELPERS_ASSOCIATED_CHALLENGE: Final = "associated_challenge"
TRANS_KEY_FLOW_HELPERS_ASSOCIATED_KIDS: Final = "associated_kids"
TRANS_KEY_FLOW_HELPERS_AWARD_MODE: Final = "award_mode"
TRANS_KEY_FLOW_HELPERS_AWARD_REWARD: Final = "award_reward"
TRANS_KEY_FLOW_HELPERS_CUSTOM_INTERVAL_UNIT: Final = "custom_interval_unit"
TRANS_KEY_FLOW_HELPERS_DAILY_THRESHOLD_TYPE: Final = "daily_threshold_type"
TRANS_KEY_FLOW_HELPERS_MAIN_MENU: Final = "main_menu"
TRANS_KEY_FLOW_HELPERS_MANAGE_ACTIONS: Final = "manage_actions"
TRANS_KEY_FLOW_HELPERS_OCCASION_TYPE: Final = "occasion_type"
TRANS_KEY_FLOW_HELPERS_ONE_TIME_REWARD: Final = "one_time_reward"
TRANS_KEY_FLOW_HELPERS_OVERDUE_HANDLING_TYPE: Final = "overdue_handling_type"
TRANS_KEY_FLOW_HELPERS_PERIOD: Final = "period"
TRANS_KEY_FLOW_HELPERS_RECURRING_FREQUENCY: Final = "recurring_frequency"
TRANS_KEY_FLOW_HELPERS_RESET_CRITERIA: Final = "reset_criteria"
TRANS_KEY_FLOW_HELPERS_RESET_TYPE: Final = "reset_type"
TRANS_KEY_FLOW_HELPERS_SELECTED_CHORE_ID: Final = "selected_chore_id"
TRANS_KEY_FLOW_HELPERS_THRESHOLD_TYPE: Final = "threshold_type"

# Sensor Translation Keys
TRANS_KEY_SENSOR_ACHIEVEMENT_PROGRESS_SENSOR: Final = "kid_achievement_progress_sensor"
TRANS_KEY_SENSOR_ACHIEVEMENT_STATE_SENSOR: Final = "system_achievement_sensor"
TRANS_KEY_SENSOR_BADGE_SENSOR: Final = "system_badge_sensor"
TRANS_KEY_SENSOR_BONUS_APPLIES_SENSOR: Final = "kid_bonus_applied_sensor"
TRANS_KEY_SENSOR_CHALLENGE_PROGRESS_SENSOR: Final = "kid_challenge_progress_sensor"
TRANS_KEY_SENSOR_CHALLENGE_STATE_SENSOR: Final = "system_challenge_sensor"
TRANS_KEY_SENSOR_CHORES_COMPLETED_DAILY_SENSOR: Final = (
    "system_chore_approvals_daily_sensor"
)
TRANS_KEY_SENSOR_CHORES_COMPLETED_MONTHLY_SENSOR: Final = (
    "system_chore_approvals_monthly_sensor"
)
TRANS_KEY_SENSOR_CHORES_COMPLETED_TOTAL_SENSOR: Final = "system_chore_approvals_sensor"
TRANS_KEY_SENSOR_CHORES_COMPLETED_WEEKLY_SENSOR: Final = (
    "system_chore_approvals_weekly_sensor"
)
TRANS_KEY_SENSOR_CHORES_SENSOR: Final = "kid_chores_sensor"
TRANS_KEY_SENSOR_CHORE_STATUS_SENSOR: Final = "kid_chore_status_sensor"
TRANS_KEY_SENSOR_KID_HIGHEST_STREAK_SENSOR: Final = "kid_chore_streak_sensor"
TRANS_KEY_SENSOR_KID_MAX_POINTS_EVER_SENSOR: Final = "kid_points_max_ever_sensor"
TRANS_KEY_SENSOR_KID_POINTS_EARNED_DAILY_SENSOR: Final = (
    "kid_points_earned_daily_sensor"
)
TRANS_KEY_SENSOR_KID_POINTS_EARNED_MONTHLY_SENSOR: Final = (
    "kid_points_earned_monthly_sensor"
)
TRANS_KEY_SENSOR_KID_POINTS_EARNED_WEEKLY_SENSOR: Final = (
    "kid_points_earned_weekly_sensor"
)
TRANS_KEY_SENSOR_KID_POINTS_SENSOR: Final = "kid_points_sensor"
TRANS_KEY_SENSOR_KID_BADGES_SENSOR: Final = "kid_badges_sensor"
TRANS_KEY_SENSOR_PENALTY_APPLIES_SENSOR: Final = "kid_penalty_applied_sensor"
TRANS_KEY_SENSOR_PENDING_CHORES_APPROVALS_SENSOR: Final = (
    "system_chores_pending_approval_sensor"
)
TRANS_KEY_SENSOR_PENDING_REWARDS_APPROVALS_SENSOR: Final = (
    "system_rewards_pending_approval_sensor"
)
TRANS_KEY_SENSOR_REWARD_STATUS_SENSOR: Final = "kid_reward_status_sensor"
TRANS_KEY_SENSOR_SHARED_CHORE_GLOBAL_STATUS_SENSOR: Final = (
    "system_chore_shared_state_sensor"
)


# Sensor Attributes Translation Keys
TRANS_KEY_SENSOR_ATTR_ACHIEVEMENT_NAME: Final = "achievement_name"
TRANS_KEY_SENSOR_ATTR_BADGE_NAME: Final = "badge_name"
TRANS_KEY_SENSOR_ATTR_BONUS_NAME: Final = "bonus_name"
TRANS_KEY_SENSOR_ATTR_CHALLENGE_NAME: Final = "challenge_name"
TRANS_KEY_SENSOR_ATTR_CHORE_NAME: Final = "chore_name"
TRANS_KEY_SENSOR_ATTR_KID_NAME: Final = "kid_name"
TRANS_KEY_SENSOR_ATTR_PENALTY_NAME: Final = "penalty_name"
TRANS_KEY_SENSOR_ATTR_POINTS: Final = "points"
TRANS_KEY_SENSOR_ATTR_REWARD_NAME: Final = "reward_name"

# DateTime Translation Keys
TRANS_KEY_DATETIME_DATE_HELPER: Final = "kid_dashboard_helper_datetime_picker"

# Select Translation Keys
TRANS_KEY_SELECT_BASE: Final = "kc_select_base"
TRANS_KEY_SELECT_BONUSES: Final = "system_bonuses_select"
TRANS_KEY_SELECT_CHORES: Final = "system_chores_select"
TRANS_KEY_SELECT_CHORES_KID: Final = "kid_dashboard_helper_chores_select"
TRANS_KEY_SELECT_PENALTIES: Final = "system_penalties_select"
TRANS_KEY_SELECT_REWARDS: Final = "system_rewards_select"

# Select Labels
TRANS_KEY_SELECT_LABEL_ALL_BONUSES: Final = "select_label_all_bonuses"
TRANS_KEY_SELECT_LABEL_ALL_CHORES: Final = "select_label_all_chores"
TRANS_KEY_SELECT_LABEL_ALL_PENALTIES: Final = "select_label_all_penalties"
TRANS_KEY_SELECT_LABEL_ALL_REWARDS: Final = "select_label_all_rewards"
TRANS_KEY_SELECT_LABEL_CHORES_FOR: Final = "select_label_chores_for"

# Button Translation Keys
TRANS_KEY_BUTTON_APPROVE_CHORE_BUTTON: Final = "parent_chore_approve_button"
TRANS_KEY_BUTTON_APPROVE_REWARD_BUTTON: Final = "parent_reward_approve_button"
TRANS_KEY_BUTTON_BONUS_BUTTON: Final = "parent_bonus_apply_button"
TRANS_KEY_BUTTON_CLAIM_CHORE_BUTTON: Final = "kid_chore_claim_button"
TRANS_KEY_BUTTON_CLAIM_REWARD_BUTTON: Final = "kid_reward_redeem_button"
TRANS_KEY_BUTTON_DELTA_PLUS_LABEL: Final = "+"
TRANS_KEY_BUTTON_DELTA_MINUS_TEXT: Final = "minus_"
TRANS_KEY_BUTTON_DELTA_PLUS_TEXT: Final = "plus_"
TRANS_KEY_BUTTON_DISAPPROVE_CHORE_BUTTON: Final = "parent_chore_disapprove_button"
TRANS_KEY_BUTTON_DISAPPROVE_REWARD_BUTTON: Final = "parent_reward_disapprove_button"
TRANS_KEY_BUTTON_MANUAL_ADJUSTMENT_BUTTON: Final = "parent_points_adjust_button"
TRANS_KEY_BUTTON_PENALTY_BUTTON: Final = "parent_penalty_apply_button"


# Button Attributes Translation Keys
TRANS_KEY_BUTTON_ATTR_BONUS_NAME: Final = "bonus_name"
TRANS_KEY_BUTTON_ATTR_CHORE_NAME: Final = "chore_name"
TRANS_KEY_BUTTON_ATTR_KID_NAME: Final = "kid_name"
TRANS_KEY_BUTTON_ATTR_PENALTY_NAME: Final = "penalty_name"
TRANS_KEY_BUTTON_ATTR_POINTS_LABEL: Final = "points_label"
TRANS_KEY_BUTTON_ATTR_REWARD_NAME: Final = "reward_name"
TRANS_KEY_BUTTON_ATTR_SIGN_LABEL: Final = "sign_label"

# Calendar Attributes Translation Keys
TRANS_KEY_CALENDAR_NAME: Final = "kid_schedule_calendar"

# FMT Errors Translation Keys
TRANS_KEY_FMT_ERROR_ADJUST_POINTS: Final = "adjust_points"
TRANS_KEY_FMT_ERROR_APPLY_BONUS: Final = "apply_bonus"
TRANS_KEY_FMT_ERROR_APPLY_PENALTIES: Final = "apply_penalties"
TRANS_KEY_FMT_ERROR_APPROVE_CHORES: Final = "approve_chores"
TRANS_KEY_FMT_ERROR_APPROVE_REWARDS: Final = "approve_rewards"
TRANS_KEY_FMT_ERROR_CLAIM_CHORES: Final = "claim_chores"
TRANS_KEY_FMT_ERROR_DISAPPROVE_CHORES: Final = "disapprove_chores"
TRANS_KEY_FMT_ERROR_DISAPPROVE_REWARDS: Final = "disapprove_rewards"
TRANS_KEY_FMT_ERROR_REDEEM_REWARDS: Final = "redeem_rewards"

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

# Badge Type to Options Flow Add Step Name Mapping
OPTIONS_FLOW_ADD_STEP: Final = {
    BADGE_TYPE_ACHIEVEMENT_LINKED: OPTIONS_FLOW_STEP_ADD_BADGE_ACHIEVEMENT,
    BADGE_TYPE_CHALLENGE_LINKED: OPTIONS_FLOW_STEP_ADD_BADGE_CHALLENGE,
    BADGE_TYPE_CUMULATIVE: OPTIONS_FLOW_STEP_ADD_BADGE_CUMULATIVE,
    BADGE_TYPE_DAILY: OPTIONS_FLOW_STEP_ADD_BADGE_DAILY,
    BADGE_TYPE_PERIODIC: OPTIONS_FLOW_STEP_ADD_BADGE_PERIODIC,
    BADGE_TYPE_SPECIAL_OCCASION: OPTIONS_FLOW_STEP_ADD_BADGE_SPECIAL,
}

# Badge Type to Options Flow Edit Step Name Mapping
OPTIONS_FLOW_EDIT_STEP: Final = {
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
    {"value": FREQUENCY_CUSTOM, "label": "Custom (define period below)"},
]

# Badge target handler constants for handler mapping keys
BADGE_HANDLER_PARAM_PERCENT_REQUIRED: Final = "percent_required"
BADGE_HANDLER_PARAM_ONLY_DUE_TODAY: Final = "only_due_today"
BADGE_HANDLER_PARAM_REQUIRE_NO_OVERDUE: Final = "require_no_overdue"
BADGE_HANDLER_PARAM_MIN_COUNT: Final = "min_count"
BADGE_HANDLER_PARAM_FROM_CHORES_ONLY: Final = "from_chores_only"

# Badge Special Occasion Types
OCCASION_TYPE_OPTIONS = [OCCASION_BIRTHDAY, OCCASION_HOLIDAY, FREQUENCY_CUSTOM]

# Lowercase literals required by Home Assistant SelectSelector schema
TARGET_TYPE_OPTIONS = [
    {"value": BADGE_TARGET_THRESHOLD_TYPE_POINTS, "label": "Points Earned"},
    {
        "value": BADGE_TARGET_THRESHOLD_TYPE_POINTS_CHORES,
        "label": "Points Earned (From Chores)",
    },
    {
        "value": BADGE_TARGET_THRESHOLD_TYPE_CHORE_COUNT,
        "label": "Chores Completed",
    },
    {
        "value": BADGE_TARGET_THRESHOLD_TYPE_DAYS_SELECTED_CHORES,
        "label": "Days Selected Chores Completed",
    },
    {
        "value": BADGE_TARGET_THRESHOLD_TYPE_DAYS_80PCT_CHORES,
        "label": "Days 80% of Selected Chores Completed",
    },
    {
        "value": BADGE_TARGET_THRESHOLD_TYPE_DAYS_SELECTED_CHORES_NO_OVERDUE,
        "label": "Days Selected Chores Completed (No Overdue)",
    },
    {
        "value": BADGE_TARGET_THRESHOLD_TYPE_DAYS_SELECTED_DUE_CHORES,
        "label": "Days Selected Due Chores Completed",
    },
    {
        "value": BADGE_TARGET_THRESHOLD_TYPE_DAYS_80PCT_DUE_CHORES,
        "label": "Days 80% of Selected Due Chores Completed",
    },
    {
        "value": BADGE_TARGET_THRESHOLD_TYPE_DAYS_SELECTED_DUE_CHORES_NO_OVERDUE,
        "label": "Days Selected Due Chores Completed (No Overdue)",
    },
    {
        "value": BADGE_TARGET_THRESHOLD_TYPE_DAYS_MIN_3_CHORES,
        "label": "Days Minimum 3 Chores Completed",
    },
    {
        "value": BADGE_TARGET_THRESHOLD_TYPE_DAYS_MIN_5_CHORES,
        "label": "Days Minimum 5 Chores Completed",
    },
    {
        "value": BADGE_TARGET_THRESHOLD_TYPE_DAYS_MIN_7_CHORES,
        "label": "Days Minimum 7 Chores Completed",
    },
    {
        "value": BADGE_TARGET_THRESHOLD_TYPE_STREAK_SELECTED_CHORES,
        "label": "Streak: Selected Chores Completed",
    },
    {
        "value": BADGE_TARGET_THRESHOLD_TYPE_STREAK_80PCT_CHORES,
        "label": "Streak: 80% of Selected Chores Completed",
    },
    {
        "value": BADGE_TARGET_THRESHOLD_TYPE_STREAK_SELECTED_CHORES_NO_OVERDUE,
        "label": "Streak: Selected Chores Completed (No Overdue)",
    },
    {
        "value": BADGE_TARGET_THRESHOLD_TYPE_STREAK_80PCT_DUE_CHORES,
        "label": "Streak: 80% of Selected Due Chores Completed",
    },
    {
        "value": BADGE_TARGET_THRESHOLD_TYPE_STREAK_SELECTED_DUE_CHORES_NO_OVERDUE,
        "label": "Streak: Selected Due Chores Completed (No Overdue)",
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
        "value": SENTINEL_EMPTY,
        "label": LABEL_NONE,
    }
]


# ================================================================================================
# DEPRECATED CONSTANTS (Currently active in existing version, planned for future refactoring)
# These reference CONSTANTS that are actively used in production code.
# They are marked for eventual replacement when underlying features are refactored.
# Must be named as _DEPRECATED and organized in the dedicates section at the bottom of const.py.
# DO NOT DELETE - would break installations without migration.
# ================================================================================================

# Not in use at this time

# ================================================================================================
# LEGACY CONSTANTS for one-time data conversion only (migration support)
# These reference constants that are replaced during migration.
# After migration completes, these keys NO LONGER EXIST in storage.
# Remove in KC-vNext after migration support is dropped.
# Must be named as _LEGACY and organized in the dedicates section at the bottom of const.py.
# DO NOT DELETE - would break migrations for upgrading users.
# ================================================================================================

# Top-level schema version field (KC 3.x→4.x migration)
CONF_SCHEMA_VERSION_LEGACY: Final = "schema_version"

# Config entry entity keys (KC 3.x stored entity data in config_entry.options)
# These are read ONCE during migration, then entity data lives in .storage/kidschores_data
CONF_ACHIEVEMENTS_LEGACY: Final = "achievements"
CONF_BADGES_LEGACY: Final = "badges"
CONF_BONUSES_LEGACY: Final = "bonuses"
CONF_CHALLENGES_LEGACY: Final = "challenges"
CONF_CHORES_LEGACY: Final = "chores"
CONF_KIDS_LEGACY: Final = "kids"
CONF_PARENTS_LEGACY: Final = "parents"
CONF_PENALTIES_LEGACY: Final = "penalties"
CONF_REWARDS_LEGACY: Final = "rewards"

# Individual entity field keys (used during KC 3.x→4.x migration)
CONF_COST_LEGACY: Final = "cost"
CONF_DASHBOARD_LANGUAGE_LEGACY: Final = "dashboard_language"
CONF_HA_USER_LEGACY: Final = "ha_user"
CONF_INTERNAL_ID_LEGACY: Final = "internal_id"
CONF_POINTS_LEGACY: Final = "points"
CONF_SHARED_CHORE_LEGACY: Final = "shared_chore"
CONF_COMPLETION_CRITERIA_LEGACY: Final = "completion_criteria"

# Achievement entity fields (KC 3.x migration)
CONF_ACHIEVEMENT_ASSIGNED_KIDS_LEGACY: Final = "assigned_kids"
CONF_ACHIEVEMENT_CRITERIA_LEGACY: Final = "criteria"
CONF_ACHIEVEMENT_LABELS_LEGACY: Final = "achievement_labels"
CONF_ACHIEVEMENT_REWARD_POINTS_LEGACY: Final = "reward_points"
CONF_ACHIEVEMENT_SELECTED_CHORE_ID_LEGACY: Final = "selected_chore_id"
CONF_ACHIEVEMENT_TARGET_VALUE_LEGACY: Final = "target_value"
CONF_ACHIEVEMENT_TYPE_LEGACY: Final = "type"

# Bonus entity fields (KC 3.x migration)
CONF_BONUS_DESCRIPTION_LEGACY: Final = "bonus_description"
CONF_BONUS_LABELS_LEGACY: Final = "bonus_labels"
CONF_BONUS_NAME_LEGACY: Final = "bonus_name"
CONF_BONUS_POINTS_LEGACY: Final = "bonus_points"

# Challenge entity fields (KC 3.x migration)
CONF_CHALLENGE_ASSIGNED_KIDS_LEGACY: Final = "assigned_kids"
CONF_CHALLENGE_CRITERIA_LEGACY: Final = "criteria"
CONF_CHALLENGE_END_DATE_LEGACY: Final = "end_date"
CONF_CHALLENGE_LABELS_LEGACY: Final = "challenge_labels"
CONF_CHALLENGE_REWARD_POINTS_LEGACY: Final = "reward_points"
CONF_CHALLENGE_SELECTED_CHORE_ID_LEGACY: Final = "selected_chore_id"
CONF_CHALLENGE_START_DATE_LEGACY: Final = "start_date"
CONF_CHALLENGE_TARGET_VALUE_LEGACY: Final = "target_value"
CONF_CHALLENGE_TYPE_LEGACY: Final = "type"

# Chore entity fields (KC 3.x migration)
CONF_ALLOW_MULTIPLE_CLAIMS_PER_DAY_LEGACY: Final = "allow_multiple_claims_per_day"
CONF_APPLICABLE_DAYS_LEGACY: Final = "applicable_days"
CONF_APPROVAL_RESET_PENDING_CLAIM_ACTION_LEGACY: Final = (
    "approval_reset_pending_claim_action"
)
CONF_APPROVAL_RESET_TYPE_LEGACY: Final = "approval_reset_type"
CONF_ASSIGNED_KIDS_LEGACY: Final = "assigned_kids"
CONF_CHORE_AUTO_APPROVE_LEGACY: Final = "auto_approve"
CONF_CHORE_DESCRIPTION_LEGACY: Final = "chore_description"
CONF_CHORE_LABELS_LEGACY: Final = "chore_labels"
CONF_CHORE_NAME_LEGACY: Final = "chore_name"
CONF_CUSTOM_INTERVAL_LEGACY: Final = "custom_interval"
CONF_CUSTOM_INTERVAL_UNIT_LEGACY: Final = "custom_interval_unit"
CONF_DEFAULT_POINTS_LEGACY: Final = "default_points"
CONF_DUE_DATE_LEGACY: Final = "due_date"
CONF_OVERDUE_HANDLING_TYPE_LEGACY: Final = "overdue_handling_type"
CONF_RECURRING_FREQUENCY_LEGACY: Final = "recurring_frequency"
CONF_CHORE_SHOW_ON_CALENDAR_LEGACY: Final = "show_on_calendar"

# Notification entity fields (KC 3.x migration)
CONF_ENABLE_MOBILE_NOTIFICATIONS_LEGACY: Final = "enable_mobile_notifications"
CONF_ENABLE_PERSISTENT_NOTIFICATIONS_LEGACY: Final = "enable_persistent_notifications"
CONF_MOBILE_NOTIFY_SERVICE_LEGACY: Final = "mobile_notify_service"
CONF_CHORE_NOTIFICATIONS_LEGACY: Final = "chore_notifications"

# Parent entity fields (KC 3.x migration)
CONF_ASSOCIATED_KIDS_LEGACY: Final = "associated_kids"
CONF_HA_USER_ID_LEGACY: Final = "ha_user_id"
CONF_PARENT_NAME_LEGACY: Final = "parent_name"

# Penalty entity fields (KC 3.x migration)
CONF_PENALTY_DESCRIPTION_LEGACY: Final = "penalty_description"
CONF_PENALTY_LABELS_LEGACY: Final = "penalty_labels"
CONF_PENALTY_NAME_LEGACY: Final = "penalty_name"
CONF_PENALTY_POINTS_LEGACY: Final = "penalty_points"

# Reward entity fields (KC 3.x migration)
CONF_REWARD_COST_LEGACY: Final = "reward_cost"
CONF_REWARD_DESCRIPTION_LEGACY: Final = "reward_description"
CONF_REWARD_LABELS_LEGACY: Final = "reward_labels"
CONF_REWARD_NAME_LEGACY: Final = "reward_name"

CFOF_CHORES_INPUT_PARTIAL_ALLOWED_LEGACY: Final = "partial_allowed"
CONF_PARTIAL_ALLOWED_LEGACY: Final = "partial_allowed"
# Legacy/Deprecated (Development-Only: Removed before v4.0+ production release)
# Replaced by nested periods structure (DATA_KID_CHORE_DATA_PERIODS)
DATA_KID_TODAY_CHORE_APPROVALS_LEGACY: Final = (
    "today_chore_approvals"  # Use periods structure instead. [DELETE BEFORE PROD]
)
DATA_CHORE_PARTIAL_ALLOWED_LEGACY: Final = "partial_allowed"
# Runtime Data Keys
# LEGACY (v0.4.0): Chore/reward queues removed, computed from timestamps instead
# Keep constants for backward-compat migration code in migration_pre_v42.py
DATA_PENDING_CHORE_APPROVALS_LEGACY: Final = "pending_chore_approvals"
DATA_PENDING_REWARD_APPROVALS_LEGACY: Final = "pending_reward_approvals"

# Runtime flag keys (stored in hass.data, not persisted)
RUNTIME_KEY_STARTUP_BACKUP_CREATED: Final = "_startup_backup_created_"

DEFAULT_BADGE_THRESHOLD_VALUE_LEGACY: Final = 50
DEFAULT_PARTIAL_ALLOWED_LEGACY = False
ATTR_PARTIAL_ALLOWED_LEGACY: Final = "partial_allowed"


# Kid Badge Data (used in migration functions)
DATA_KID_BADGES_LEGACY: Final = (
    "badges"  # Used in _migrate_kid_badges(), remove when migration dropped
)

# Kid Chore Tracking (LEGACY: Migration only)
DATA_KID_CHORE_APPROVALS_LEGACY: Final = "chore_approvals"  # LEGACY: Migration only - use kid_chore_data[chore_id]["periods"][period]["approved"]
DATA_KID_CHORE_CLAIMS_LEGACY: Final = (
    "chore_claims"  # LEGACY: Migration only - use chore_data structure
)
DATA_KID_CHORE_STREAKS_LEGACY: Final = (
    "chore_streaks"  # LEGACY: Migration only - use chore_data structure
)

# Kid Completed Chores Counters (LEGACY - migration only, use chore_stats)
DATA_KID_COMPLETED_CHORES_MONTHLY_LEGACY = (
    "completed_chores_monthly"  # LEGACY: Migration only
)
DATA_KID_COMPLETED_CHORES_TOTAL_LEGACY = (
    "completed_chores_total"  # LEGACY: Migration only
)
DATA_KID_COMPLETED_CHORES_TODAY_LEGACY = (
    "completed_chores_today"  # LEGACY: Migration only
)
DATA_KID_COMPLETED_CHORES_WEEKLY_LEGACY = (
    "completed_chores_weekly"  # LEGACY: Migration only
)
DATA_KID_COMPLETED_CHORES_YEARLY_LEGACY = (
    "completed_chores_yearly"  # LEGACY: Migration only
)

# Kid Points Earned Tracking (LEGACY: Migration only)
DATA_KID_POINTS_EARNED_MONTHLY_LEGACY: Final = "points_earned_monthly"  # LEGACY: Migration only - use point_stats["periods"]["monthly"]["earned"]
DATA_KID_POINTS_EARNED_TODAY_LEGACY: Final = "points_earned_today"  # LEGACY: Migration only - use point_stats["periods"]["daily"]["earned"]
DATA_KID_POINTS_EARNED_WEEKLY_LEGACY: Final = "points_earned_weekly"  # LEGACY: Migration only - use point_stats["periods"]["weekly"]["earned"]
DATA_KID_POINTS_EARNED_YEARLY_LEGACY: Final = "points_earned_yearly"  # LEGACY: Migration only - use point_stats["periods"]["yearly"]["earned"]

# Additional Kid Legacy Fields (scattered throughout v0.4.0)
DATA_KID_APPROVED_CHORES_LEGACY: Final = "approved_chores"  # LEGACY: Migration only
DATA_KID_CLAIMED_CHORES_LEGACY: Final = (
    "claimed_chores"  # LEGACY: Migration only - use chore_data structure
)
DATA_KID_MAX_POINTS_EVER_LEGACY: Final = (
    "max_points_ever"  # Legacy field - use POINT_STATS_EARNED_ALL_TIME instead
)
DATA_KID_MAX_STREAK_LEGACY: Final = (
    "max_streak"  # Legacy field - use CHORE_STATS_LONGEST_STREAK_ALL_TIME instead
)

# Legacy Reward Fields (v0.4.0): Replaced by reward_data structure
# Keep constants for backward-compat migration code in migration_pre_v42.py
DATA_KID_PENDING_REWARDS_LEGACY: Final = "pending_rewards"
DATA_KID_REDEEMED_REWARDS_LEGACY: Final = "redeemed_rewards"
DATA_KID_REWARD_APPROVALS_LEGACY: Final = "reward_approvals"
DATA_KID_REWARD_CLAIMS_LEGACY: Final = "reward_claims"

# Legacy Chore Fields (v0.4.0): Replaced by new structures
DATA_CHORE_ALLOW_MULTIPLE_CLAIMS_PER_DAY_LEGACY: Final = "allow_multiple_claims_per_day"  # Migration only - replaced by DATA_CHORE_APPROVAL_RESET_TYPE
DATA_CHORE_SHARED_CHORE_LEGACY: Final = (
    "shared_chore"  # LEGACY: Use completion_criteria
)


# KC 4.x Beta Cleanup (removed in schema v42)
# Used in coordinator._migrate_*() functions to clean up deprecated keys from KC 4.x beta
# TODO(KC 5.0): Remove after KC 4.x beta support dropped (all users on v42+)
MIGRATION_PERFORMED = (
    "migration_performed"  # Cleanup key, redundant with schema_version
)
MIGRATION_KEY_VERSION = (
    "migration_key_version"  # Cleanup key, redundant with schema_version
)
MIGRATION_KEY_VERSION_NUMBER = 41  # Old target version for KC 3.x→4.x migration
MIGRATION_DATA_LEGACY_ORPHAN = "legacy_orphan"  # Cleanup data key from beta

# KC 3.x→4.x Badge Migration
DATA_BADGE_CHORE_COUNT_TYPE_LEGACY = (
    "chore_count_type"  # Read in _migrate_badge_schema()
)
DATA_BADGE_POINTS_MULTIPLIER_LEGACY = (
    "points_multiplier"  # Read in _migrate_badge_schema()
)
DATA_BADGE_THRESHOLD_TYPE_LEGACY = (
    "threshold_type"  # Read in _migrate_badge_schema(), deleted after
)
DATA_BADGE_THRESHOLD_VALUE_LEGACY = (
    "threshold_value"  # Read in _migrate_badge_schema(), deleted after
)
