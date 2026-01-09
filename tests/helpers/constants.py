"""Test constants for KidsChores integration tests.

This module re-exports all constants from the integration for use in tests.
Import from here, not directly from custom_components.kidschores.const.

=============================================================================
QUICK REFERENCE
=============================================================================

CHORE STATUS SENSOR STATE VALUES (sensor.kc_<kid>_chore_status_<chore>):
    - CHORE_STATE_PENDING: Initial state, chore not yet claimed
    - CHORE_STATE_CLAIMED: Kid has claimed, awaiting approval
    - CHORE_STATE_APPROVED: Chore completed and approved
    - CHORE_STATE_OVERDUE: Past due date without completion
    - CHORE_STATE_COMPLETED_BY_OTHER: Another kid completed shared_first chore
    - CHORE_STATE_CLAIMED_IN_PART: Partial claim (shared chores)
    - CHORE_STATE_APPROVED_IN_PART: Partial approval (shared chores)

GLOBAL STATE ATTRIBUTE (ATTR_GLOBAL_STATE on chore status sensor):
    The global_state attribute shows the aggregated chore state across all
    assigned kids. See test_constants.py for full documentation.

=============================================================================
"""

# ruff: noqa: F401
# pylint: disable=unused-import

from custom_components.kidschores.const import (
    APPROVAL_RESET_AT_DUE_DATE_MULTI,
    APPROVAL_RESET_AT_DUE_DATE_ONCE,
    APPROVAL_RESET_AT_MIDNIGHT_MULTI,
    # =========================================================================
    # APPROVAL RESET TYPES
    # =========================================================================
    APPROVAL_RESET_AT_MIDNIGHT_ONCE,
    APPROVAL_RESET_PENDING_CLAIM_AUTO_APPROVE,
    APPROVAL_RESET_PENDING_CLAIM_CLEAR,
    # =========================================================================
    # PENDING CLAIM ACTIONS
    # =========================================================================
    APPROVAL_RESET_PENDING_CLAIM_HOLD,
    APPROVAL_RESET_UPON_COMPLETION,
    # =========================================================================
    # SENSOR ATTRIBUTES - Chore Status Sensor
    # =========================================================================
    ATTR_APPROVAL_RESET_TYPE,
    ATTR_CAN_APPROVE,
    ATTR_CAN_CLAIM,
    ATTR_CHORE_APPROVALS_COUNT,
    ATTR_CHORE_APPROVE_BUTTON_ENTITY_ID,
    ATTR_CHORE_CLAIM_BUTTON_ENTITY_ID,
    ATTR_CHORE_CLAIMS_COUNT,
    ATTR_CHORE_CURRENT_STREAK,
    ATTR_CHORE_DISAPPROVE_BUTTON_ENTITY_ID,
    ATTR_CHORE_HIGHEST_STREAK,
    ATTR_CHORE_POINTS_EARNED,
    ATTR_COMPLETION_CRITERIA,
    ATTR_COST,
    # =========================================================================
    # DASHBOARD HELPER SENSOR ATTRIBUTES
    # =========================================================================
    ATTR_DASHBOARD_ACHIEVEMENTS,
    ATTR_DASHBOARD_BADGES,
    ATTR_DASHBOARD_BONUSES,
    ATTR_DASHBOARD_CHALLENGES,
    ATTR_DASHBOARD_CHORES,
    ATTR_DASHBOARD_KID_NAME,
    ATTR_DASHBOARD_PENALTIES,
    ATTR_DASHBOARD_PENDING_APPROVALS,
    ATTR_DASHBOARD_POINTS_BUTTONS,
    ATTR_DASHBOARD_REWARDS,
    ATTR_DASHBOARD_UI_TRANSLATIONS,
    ATTR_DEFAULT_POINTS,
    ATTR_DUE_DATE,
    ATTR_GLOBAL_STATE,
    ATTR_LAST_APPROVED,
    ATTR_LAST_CLAIMED,
    ATTR_RECURRING_FREQUENCY,
    # =========================================================================
    # SENSOR ATTRIBUTES - Reward Status Sensor
    # =========================================================================
    ATTR_REWARD_APPROVALS_COUNT,
    ATTR_REWARD_APPROVE_BUTTON_ENTITY_ID,
    ATTR_REWARD_CLAIM_BUTTON_ENTITY_ID,
    ATTR_REWARD_CLAIMS_COUNT,
    ATTR_REWARD_DISAPPROVE_BUTTON_ENTITY_ID,
    # =========================================================================
    # ENTITY ID COMPONENTS
    # =========================================================================
    BUTTON_KC_UID_SUFFIX_APPROVE,
    BUTTON_KC_UID_SUFFIX_CLAIM,
    BUTTON_KC_UID_SUFFIX_DISAPPROVE,
    CFOF_CHORES_INPUT_ASSIGNED_KIDS,
    CFOF_CHORES_INPUT_COMPLETION_CRITERIA,
    CFOF_CHORES_INPUT_DEFAULT_POINTS,
    # =========================================================================
    # CONFIG FLOW FIELD NAMES
    # =========================================================================
    CFOF_CHORES_INPUT_NAME,
    CFOF_KIDS_INPUT_KID_NAME,
    CFOF_PARENTS_INPUT_NAME,
    # =========================================================================
    # CHORE STATES
    # =========================================================================
    CHORE_STATE_APPROVED,
    CHORE_STATE_APPROVED_IN_PART,
    CHORE_STATE_CLAIMED,
    CHORE_STATE_CLAIMED_IN_PART,
    CHORE_STATE_COMPLETED_BY_OTHER,
    CHORE_STATE_INDEPENDENT,
    CHORE_STATE_OVERDUE,
    CHORE_STATE_PENDING,
    CHORE_STATE_UNKNOWN,
    # =========================================================================
    # COMPLETION CRITERIA
    # =========================================================================
    COMPLETION_CRITERIA_INDEPENDENT,
    COMPLETION_CRITERIA_SHARED,
    COMPLETION_CRITERIA_SHARED_FIRST,
    # =========================================================================
    # DOMAIN & COORDINATOR
    # =========================================================================
    COORDINATOR,
    # =========================================================================
    # DATA KEYS - TOP LEVEL
    # =========================================================================
    DATA_ACHIEVEMENTS,
    DATA_BADGES,
    DATA_BONUSES,
    DATA_CHALLENGES,
    # =========================================================================
    # DATA KEYS - CHORE FIELDS
    # =========================================================================
    DATA_CHORE_APPLICABLE_DAYS,
    DATA_CHORE_APPROVAL_PERIOD_START,
    DATA_CHORE_APPROVAL_RESET_PENDING_CLAIM_ACTION,
    DATA_CHORE_APPROVAL_RESET_TYPE,
    DATA_CHORE_ASSIGNED_KIDS,
    DATA_CHORE_COMPLETION_CRITERIA,
    DATA_CHORE_CUSTOM_INTERVAL,
    DATA_CHORE_CUSTOM_INTERVAL_UNIT,
    DATA_CHORE_DEFAULT_POINTS,
    DATA_CHORE_DESCRIPTION,
    DATA_CHORE_DUE_DATE,
    DATA_CHORE_ICON,
    DATA_CHORE_INTERNAL_ID,
    DATA_CHORE_LABELS,
    DATA_CHORE_NAME,
    DATA_CHORE_OVERDUE_HANDLING_TYPE,
    DATA_CHORE_PER_KID_DUE_DATES,
    DATA_CHORE_RECURRING_FREQUENCY,
    DATA_CHORE_STATE,
    DATA_CHORE_TIMESTAMP,
    DATA_CHORES,
    # =========================================================================
    # DATA KEYS - KID FIELDS
    # =========================================================================
    DATA_KID_BADGES_EARNED,
    DATA_KID_CHORE_DATA,
    # =========================================================================
    # DATA KEYS - KID CHORE DATA
    # =========================================================================
    DATA_KID_CHORE_DATA_APPROVAL_PERIOD_START,
    DATA_KID_CHORE_DATA_DUE_DATE,
    DATA_KID_CHORE_DATA_LAST_APPROVED,
    DATA_KID_CHORE_DATA_LAST_CLAIMED,
    DATA_KID_CHORE_DATA_LAST_DISAPPROVED,
    DATA_KID_CHORE_DATA_STATE,
    DATA_KID_CHORE_DATA_TOTAL_COUNT,
    DATA_KID_CHORE_DATA_TOTAL_POINTS,
    DATA_KID_COMPLETED_BY_OTHER_CHORES,
    DATA_KID_HA_USER_ID,
    DATA_KID_INTERNAL_ID,
    DATA_KID_NAME,
    DATA_KID_OVERDUE_CHORES,
    DATA_KID_POINT_STATS,
    DATA_KID_POINTS,
    DATA_KID_REWARD_DATA,
    DATA_KIDS,
    DATA_PARENTS,
    DATA_PENALTIES,
    # =========================================================================
    # DATA KEYS - REWARD FIELDS
    # =========================================================================
    DATA_REWARD_COST,
    DATA_REWARD_DESCRIPTION,
    DATA_REWARD_ICON,
    DATA_REWARD_INTERNAL_ID,
    DATA_REWARD_LABELS,
    DATA_REWARD_NAME,
    DATA_REWARDS,
    # =========================================================================
    # DEFAULTS
    # =========================================================================
    DEFAULT_APPROVAL_RESET_PENDING_CLAIM_ACTION,
    DEFAULT_APPROVAL_RESET_TYPE,
    DEFAULT_OVERDUE_HANDLING_TYPE,
    DEFAULT_REWARD_COST,
    DEFAULT_ZERO,
    DOMAIN,
    # =========================================================================
    # FREQUENCIES
    # =========================================================================
    FREQUENCY_DAILY,
    FREQUENCY_MONTHLY,
    FREQUENCY_NONE,
    FREQUENCY_WEEKLY,
    # =========================================================================
    # OVERDUE HANDLING TYPES
    # =========================================================================
    OVERDUE_HANDLING_AT_DUE_DATE,
    OVERDUE_HANDLING_AT_DUE_DATE_THEN_RESET,
    OVERDUE_HANDLING_NEVER_OVERDUE,
    # =========================================================================
    # REWARD STATES
    # =========================================================================
    REWARD_STATE_APPROVED,
    REWARD_STATE_CLAIMED,
    REWARD_STATE_NOT_CLAIMED,
    SENSOR_KC_EID_MIDFIX_CHORE_STATUS_SENSOR,
    SENSOR_KC_EID_SUFFIX_UI_DASHBOARD_HELPER,
    SENSOR_KC_PREFIX,
    SENSOR_KC_UID_SUFFIX_CHORE_STATUS_SENSOR,
    SENSOR_KC_UID_SUFFIX_KID_POINTS_SENSOR,
    # =========================================================================
    # TRANSLATION KEYS (for error assertions)
    # =========================================================================
    TRANS_KEY_ERROR_CHORE_ALREADY_APPROVED,
)

# =============================================================================
# CONVENIENCE LISTS
# =============================================================================

CHORE_STATE_VALUES: list[str] = [
    CHORE_STATE_PENDING,
    CHORE_STATE_CLAIMED,
    CHORE_STATE_APPROVED,
    CHORE_STATE_APPROVED_IN_PART,
    CHORE_STATE_CLAIMED_IN_PART,
    CHORE_STATE_OVERDUE,
    CHORE_STATE_COMPLETED_BY_OTHER,
]

REWARD_STATE_VALUES: list[str] = [
    REWARD_STATE_NOT_CLAIMED,
    REWARD_STATE_CLAIMED,
    REWARD_STATE_APPROVED,
]

COMPLETION_CRITERIA_VALUES: list[str] = [
    COMPLETION_CRITERIA_INDEPENDENT,
    COMPLETION_CRITERIA_SHARED,
    COMPLETION_CRITERIA_SHARED_FIRST,
]
