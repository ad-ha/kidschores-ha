# File: const.py
"""Constants for the KidsChores integration.

This file centralizes configuration keys, defaults, labels, domain names,
event names, and platform identifiers for consistency across the integration.
It also supports localization by defining all labels and UI texts used in sensors,
services, and options flow.
"""

import logging

from homeassistant.const import Platform

# -------------------- General --------------------
# Integration Domain and Logging
DOMAIN = "kidschores"
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

# -------------------- Configuration --------------------
# Configuration Keys
CONF_ACHIEVEMENTS = "achievements"
CONF_APPLICABLE_DAYS = "applicable_days"
CONF_BADGES = "badges"  # Key for badges configuration
CONF_CHALLENGES = "challenges"
CONF_CHORES = "chores"  # Key for chores configuration
CONF_GLOBAL = "global"
CONF_KIDS = "kids"  # Key for kids configuration
CONF_PARENTS = "parents"  # Key for parents configuration
CONF_PENALTIES = "penalties"  # Key for penalties configuration
CONF_POINTS_ICON = "points_icon"
CONF_POINTS_LABEL = "points_label"  # Custom label for points
CONF_REWARDS = "rewards"  # Key for rewards configuration
CONF_BONUSES = "bonuses"

# Options Flow Management
OPTIONS_FLOW_ACHIEVEMENTS = "manage_achievements"  # Edit achivements step
OPTIONS_FLOW_BADGES = "manage_badges"  # Edit badges step
OPTIONS_FLOW_CHALLENGES = "manage_challenges"  # Edit challenges step
OPTIONS_FLOW_CHORES = "manage_chores"  # Edit chores step
OPTIONS_FLOW_KIDS = "manage_kids"  # Edit kids step
OPTIONS_FLOW_PARENTS = "manage_parents"  # Edit parents step
OPTIONS_FLOW_PENALTIES = "manage_penalties"  # Edit penalties step
OPTIONS_FLOW_REWARDS = "manage_rewards"  # Edit rewards step
OPTIONS_FLOW_BONUSES = "manage_bonuses"  # Edit bonuses step

# Validation Keys
VALIDATION_DUE_DATE = "due_date"  # Optional due date for chores
VALIDATION_PARTIAL_ALLOWED = "partial_allowed"  # Allow partial points in chores
VALIDATION_THRESHOLD_TYPE = "threshold_type"  # Badge criteria type
VALIDATION_THRESHOLD_VALUE = "threshold_value"  # Badge criteria value

# Notification configuration keys
CONF_ENABLE_MOBILE_NOTIFICATIONS = "enable_mobile_notifications"
CONF_MOBILE_NOTIFY_SERVICE = "mobile_notify_service"
CONF_ENABLE_PERSISTENT_NOTIFICATIONS = "enable_persistent_notifications"
CONF_NOTIFY_ON_CLAIM = "notify_on_claim"
CONF_NOTIFY_ON_APPROVAL = "notify_on_approval"
CONF_NOTIFY_ON_DISAPPROVAL = "notify_on_disapproval"
CONF_CHORE_NOTIFY_SERVICE = "chore_notify_service"

NOTIFICATION_EVENT = "mobile_app_notification_action"

# Achievement types
ACHIEVEMENT_TYPE_STREAK = "chore_streak"  # e.g., "Make bed 20 days in a row"
ACHIEVEMENT_TYPE_TOTAL = "chore_total"  # e.g., "Complete 100 chores overall"
ACHIEVEMENT_TYPE_DAILY_MIN = (
    "daily_minimum"  # e.g., "Complete minimum 5 chores in one day"
)

# Challenge types
CHALLENGE_TYPE_TOTAL_WITHIN_WINDOW = (
    "total_within_window"  # e.g., "Complete 50 chores in 30 days"
)
CHALLENGE_TYPE_DAILY_MIN = "daily_minimum"  # e.g., "Do 2 chores each day for 14 days"


# -------------------- Defaults --------------------
# Default Icons
DEFAULT_ACHIEVEMENTS_ICON = "mdi:trophy-award"  # Default icon for achievements
DEFAULT_BADGE_ICON = "mdi:shield-star-outline"  # Default icon for badges
DEFAULT_CALENDAR_ICON = "mdi:calendar"  # Default icon for calendar sensors
DEFAULT_CHALLENGES_ICON = "mdi:trophy"  # Default icon for achievements
DEFAULT_CHORE_APPROVE_ICON = "mdi:checkbox-marked-circle-outline"
DEFAULT_CHORE_BINARY_ICON = (
    "mdi:checkbox-blank-circle-outline"  # For chore status binary sensor
)
DEFAULT_CHORE_CLAIM_ICON = "mdi:clipboard-check-outline"
DEFAULT_CHORE_SENSOR_ICON = (
    "mdi:checkbox-blank-circle-outline"  # For chore status sensor
)
DEFAULT_DISAPPROVE_ICON = (
    "mdi:close-circle-outline"  # Default icon for disapprove buttons
)
DEFAULT_ICON = "mdi:star-outline"  # Default icon for general points display
DEFAULT_PENALTY_ICON = "mdi:alert-outline"  # Default icon for penalties
DEFAULT_POINTS_ADJUST_MINUS_ICON = "mdi:minus-circle-outline"
DEFAULT_POINTS_ADJUST_PLUS_ICON = "mdi:plus-circle-outline"
DEFAULT_POINTS_ADJUST_MINUS_MULTIPLE_ICON = "mdi:minus-circle-multiple-outline"
DEFAULT_POINTS_ADJUST_PLUS_MULTIPLE_ICON = "mdi:plus-circle-multiple-outline"
DEFAULT_POINTS_ICON = "mdi:star-outline"  # Default icon for points
DEFAULT_STREAK_ICON = "mdi:blur-linear"  # Default icon for streaks
DEFAULT_BONUS_ICON = "mdi:seal"  # Default icon for bonuses
DEFAULT_REWARD_ICON = "mdi:gift-outline"  # Default icon for rewards
DEFAULT_TROPHY_ICON = "mdi:trophy"  # For highest-badge sensor fallback
DEFAULT_TROPHY_OUTLINE = "mdi:trophy-outline"

# Default Values
DEFAULT_APPLICABLE_DAYS = []  # Empty means the chore applies every day.
DEFAULT_BADGE_THRESHOLD = 50  # Default points threshold for badges
DEFAULT_MULTIPLE_CLAIMS_PER_DAY = False  # Allow only one chore claim per day
DEFAULT_PARTIAL_ALLOWED = False  # Partial points not allowed by default
DEFAULT_POINTS = 5  # Default points awarded for each chore
DEFAULT_POINTS_MULTIPLIER = 1  # Default points multiplier for badges
DEFAULT_POINTS_LABEL = "Points"  # Default label for points displayed in UI
DEFAULT_PENALTY_POINTS = 2  # Default points deducted for each penalty
DEFAULT_BONUS_POINTS = 2  # Default points added for each bonus
DEFAULT_REMINDER_DELAY = 30  # Default reminder delay in minutes
DEFAULT_REWARD_COST = 10  # Default cost for each reward
DEFAULT_DAILY_RESET_TIME = {
    "hour": 0,
    "minute": 0,
    "second": 0,
}  # Daily reset at midnight
DEFAULT_MONTHLY_RESET_DAY = 1  # Monthly reset on the 1st day
DEFAULT_WEEKLY_RESET_DAY = 0  # Weekly reset on Monday (0 = Monday, 6 = Sunday)
DEFAULT_NOTIFY_ON_CLAIM = True
DEFAULT_NOTIFY_ON_APPROVAL = True
DEFAULT_NOTIFY_ON_DISAPPROVAL = True

# -------------------- Recurring Frequencies --------------------
FREQUENCY_BIWEEKLY = "biweekly"
FREQUENCY_CUSTOM = "custom"
FREQUENCY_DAILY = "daily"
FREQUENCY_MONTHLY = "monthly"
FREQUENCY_NONE = "none"
FREQUENCY_WEEKLY = "weekly"

# -------------------- Data Keys --------------------
# Data Keys for Coordinator and Storage
DATA_ACHIEVEMENTS = "achievements"  # Key for storing achievements data
DATA_BADGES = "badges"  # Key for storing badges data
DATA_CHALLENGES = "challenges"  # Key for storing challenges data
DATA_CHORES = "chores"  # Key for storing chores data
DATA_KIDS = "kids"  # Key for storing kids data in storage
DATA_PARENTS = "parents"  # Key for storing parent data
DATA_PENDING_CHORE_APPROVALS = "pending_chore_approvals"  # Pending chore approvals
DATA_PENDING_REWARD_APPROVALS = "pending_reward_approvals"  # Pending reward approvals
DATA_PENALTIES = "penalties"  # Key for storing penalties data
DATA_REWARDS = "rewards"  # Key for storing rewards data
DATA_BONUSES = "bonuses"  # Key for storing bonuses data

# -------------------- States --------------------
# Badge Threshold Types
BADGE_THRESHOLD_TYPE_CHORE_COUNT = (
    "chore_count"  # Badges for completing a number of chores
)
BADGE_THRESHOLD_TYPE_POINTS = "points"  # Badges awarded for reaching points

# Chore States
CHORE_STATE_APPROVED = "approved"  # Chore fully approved
CHORE_STATE_APPROVED_IN_PART = "approved_in_part"  # Chore approved for some kids
CHORE_STATE_CLAIMED = "claimed"  # Chore claimed by a kid
CHORE_STATE_CLAIMED_IN_PART = "claimed_in_part"  # Chore claimed by some kids
CHORE_STATE_INDEPENDENT = "independent"  # Chore is not shared
CHORE_STATE_OVERDUE = "overdue"  # Chore not completed before the due date
CHORE_STATE_PARTIAL = "partial"  # Chore approved with partial points
CHORE_STATE_PENDING = "pending"  # Default state: chore pending approval
CHORE_STATE_UNKNOWN = "unknown"  # Unknown chore state


# Reward States
REWARD_STATE_APPROVED = "approved"  # Reward fully approved
REWARD_STATE_CLAIMED = "claimed"  # Reward claimed by a kid
REWARD_STATE_NOT_CLAIMED = "not_claimed"  # Default state: reward not claimed
REWARD_STATE_UNKNOWN = "unknown"  # Unknown reward state

# -------------------- Events --------------------
# Event Names
EVENT_CHORE_COMPLETED = "kidschores_chore_completed"  # Event for chore completion
EVENT_REWARD_REDEEMED = "kidschores_reward_redeemed"  # Event for redeeming a reward

# -------------------- Actions --------------------
# Action titles for notifications
ACTION_TITLE_APPROVE = "Approve"
ACTION_TITLE_DISAPPROVE = "Disapprove"
ACTION_TITLE_REMIND_30 = "Remind in 30 mins"

# Action identifiers
ACTION_APPROVE_CHORE = "APPROVE_CHORE"
ACTION_DISAPPROVE_CHORE = "DISAPPROVE_CHORE"
ACTION_APPROVE_REWARD = "APPROVE_REWARD"
ACTION_DISAPPROVE_REWARD = "DISAPPROVE_REWARD"
ACTION_REMIND_30 = "REMIND_30"

# -------------------- Sensors --------------------
# Sensor Attributes
ATTR_ACHIEVEMENT_NAME = "achievement_name"
ATTR_ALL_EARNED_BADGES = "all_earned_badges"
ATTR_ALLOW_MULTIPLE_CLAIMS_PER_DAY = "allow_multiple_claims_per_day"
ATTR_APPLICABLE_DAYS = "applicable_days"
ATTR_AWARDED = "awarded"
ATTR_ASSIGNED_KIDS = "assigned_kids"
ATTR_ASSOCIATED_CHORE = "associated_chore"
ATTR_BADGES = "badges"
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
ATTR_BONUS_NAME = "bonus_name"
ATTR_BONUS_POINTS = "bonus_points"
ATTR_START_DATE = "start_date"
ATTR_SHARED_CHORE = "shared_chore"
ATTR_TARGET_VALUE = "target_value"
ATTR_THRESHOLD_TYPE = "threshold_type"
ATTR_TYPE = "type"

# Calendar Attributes
ATTR_CAL_SUMMARY = "summary"
ATTR_CAL_START = "start"
ATTR_CAL_END = "end"
ATTR_CAL_ALL_DAY = "all_day"
ATTR_CAL_DESCRIPTION = "description"
ATTR_CAL_MANUFACTURER = "manufacturer"

# Sensor Types
SENSOR_TYPE_BADGES = "badges"  # Sensor tracking earned badges
SENSOR_TYPE_CHORE_APPROVALS = "chore_approvals"  # Chore approvals sensor
SENSOR_TYPE_CHORE_CLAIMS = "chore_claims"  # Chore claims sensor
SENSOR_TYPE_COMPLETED_DAILY = (
    "completed_daily"  # Sensor tracking daily chores completed
)
SENSOR_TYPE_COMPLETED_MONTHLY = (
    "completed_monthly"  # Sensor tracking monthly chores completed
)
SENSOR_TYPE_COMPLETED_WEEKLY = (
    "completed_weekly"  # Sensor tracking weekly chores completed
)
SENSOR_TYPE_PENALTY_APPLIES = "penalty_applies"  # Penalty applies sensor
SENSOR_TYPE_POINTS = "points"  # Sensor tracking total points
SENSOR_TYPE_PENDING_CHORE_APPROVALS = (
    "pending_chore_approvals"  # Pending chore approvals
)
SENSOR_TYPE_PENDING_REWARD_APPROVALS = (
    "pending_reward_approvals"  # Pending reward approvals
)
SENSOR_TYPE_REWARD_APPROVALS = "reward_approvals"  # Reward approvals sensor
SENSOR_TYPE_REWARD_CLAIMS = "reward_claims"  # Reward claims sensor
SENSOR_TYPE_BONUS_APPLIES = "bonus_applies"  # Bonus applies sensor


# -------------------- Services --------------------
# Custom Services
SERVICE_APPLY_PENALTY = "apply_penalty"  # Apply penalty service
SERVICE_APPROVE_CHORE = "approve_chore"  # Approve chore service
SERVICE_APPROVE_REWARD = "approve_reward"  # Approve reward service
SERVICE_CLAIM_CHORE = "claim_chore"  # Claim chore service
SERVICE_DISAPPROVE_CHORE = "disapprove_chore"  # Disapprove chore service
SERVICE_DISAPPROVE_REWARD = "disapprove_reward"  # Disapprove reward service
SERVICE_REDEEM_REWARD = "redeem_reward"  # Redeem reward service
SERVICE_RESET_ALL_CHORES = "reset_all_chores"  # Reset all chores service
SERVICE_RESET_ALL_DATA = "reset_all_data"  # Reset all data service
SERVICE_RESET_OVERDUE_CHORES = "reset_overdue_chores"  # Reset overdue chores
SERVICE_SET_CHORE_DUE_DATE = "set_chore_due_date"  # Set or reset chores due date
SERVICE_SKIP_CHORE_DUE_DATE = (
    "skip_chore_due_date"  # Skip chores due date and reschedule
)
SERVICE_APPLY_BONUS = "apply_bonus"  # Apply bonus service
SERVICE_RESET_PENALTIES = "reset_penalties"  # Reset penalties service
SERVICE_RESET_BONUSES = "reset_bonuses"  # Reset bonuses service

# Field Names (for consistency across services)
FIELD_CHORE_ID = "chore_id"
FIELD_CHORE_NAME = "chore_name"
FIELD_KID_NAME = "kid_name"
FIELD_PARENT_NAME = "parent_name"
FIELD_PENALTY_NAME = "penalty_name"
FIELD_POINTS_AWARDED = "points_awarded"
FIELD_REWARD_NAME = "reward_name"
FIELD_BONUS_NAME = "bonus_name"

# -------------------- Labels --------------------
# Labels for Sensors and UI
LABEL_BADGES = "Badges"
LABEL_COMPLETED_DAILY = "Daily Completed Chores"
LABEL_COMPLETED_MONTHLY = "Monthly Completed Chores"
LABEL_COMPLETED_WEEKLY = "Weekly Completed Chores"
LABEL_POINTS = "Points"

# -------------------- Buttons --------------------
# Button Prefixes for Dynamic Creation
BUTTON_DISAPPROVE_CHORE_PREFIX = "disapprove_chore_button_"  # Disapprove chore button
BUTTON_DISAPPROVE_REWARD_PREFIX = (
    "disapprove_reward_button_"  # Disapprove reward button
)
BUTTON_PENALTY_PREFIX = (
    "penalty_button_"  # Prefix for dynamically created penalty buttons
)
BUTTON_REWARD_PREFIX = "reward_button_"  # Prefix for dynamically created reward buttons
BUTTON_BONUS_PREFIX = "bonus_button_"  # Prefix for dynamically created bonus buttons

# -------------------- Errors and Warnings --------------------
DUE_DATE_NOT_SET = "Not Set"
ERROR_CHORE_NOT_FOUND = "Chore not found."  # Error for missing chore
ERROR_CHORE_NOT_FOUND_FMT = "Chore '{}' not found"  # Error format for missing chore
ERROR_INVALID_POINTS = "Invalid points."  # Error for invalid points input
ERROR_KID_NOT_FOUND = "Kid not found."  # Error for non-existent kid
ERROR_KID_NOT_FOUND_FMT = "Kid '{}' not found"  # Error format for missing kid
ERROR_NOT_AUTHORIZED_ACTION_FMT = "Not authorized to {}."  # Auth error format
ERROR_NOT_AUTHORIZED_FMT = (
    "User not authorized to {} for this kid."  # Auth error format
)
ERROR_PENALTY_NOT_FOUND = "Penalty not found."  # Error for missing penalty
ERROR_PENALTY_NOT_FOUND_FMT = (
    "Penalty '{}' not found"  # Error format for missing penalty
)
ERROR_REWARD_NOT_FOUND = "Reward not found."  # Error for missing reward
ERROR_REWARD_NOT_FOUND_FMT = "Reward '{}' not found"  # Error format for missing reward
ERROR_BONUS_NOT_FOUND = "Bonus not found."  # Error for missing bonus
ERROR_BONUS_NOT_FOUND_FMT = "Bonus '{}' not found"  # Error format for missing bonus
ERROR_USER_NOT_AUTHORIZED = (
    "User is not authorized to perform this action."  # Auth error
)
MSG_NO_ENTRY_FOUND = "No KidsChores entry found"

# Unknown States
UNKNOWN_CHORE = "Unknown Chore"  # Error for unknown chore
UNKNOWN_KID = "Unknown Kid"  # Error for unknown kid
UNKNOWN_REWARD = "Unknown Reward"  # Error for unknown reward

# -------------------- Parent Approval Workflow --------------------
PARENT_APPROVAL_REQUIRED = True  # Enable parent approval for certain actions
HA_USERNAME_LINK_ENABLED = True  # Enable linking kids to HA usernames


# ---------------------------- Weekdays -----------------------------
WEEKDAY_OPTIONS = {
    "mon": "Monday",
    "tue": "Tuesday",
    "wed": "Wednesday",
    "thu": "Thursday",
    "fri": "Friday",
    "sat": "Saturday",
    "sun": "Sunday",
}
