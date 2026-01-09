"""Test helpers for KidsChores integration tests.

This module re-exports all helpers for convenient imports:

    from tests.helpers import (
        # Setup
        setup_scenario, setup_minimal_scenario, SetupResult,

        # Constants
        CHORE_STATE_PENDING, CHORE_STATE_CLAIMED, CHORE_STATE_APPROVED,
        ATTR_CHORE_CLAIM_BUTTON_ENTITY_ID,

        # Workflows
        claim_chore, approve_chore, WorkflowResult,
        get_dashboard_helper, find_chore,

        # Validation
        verify_entity_state, count_entities_by_platform,
    )

See individual modules for full documentation:
- setup.py: Declarative test setup via config flow
- constants.py: All KidsChores constants for test assertions
- workflows.py: Chore/reward/bonus workflow helpers
- validation.py: Entity state and count validation
"""

# Re-export from setup
# Re-export from constants
from tests.helpers.constants import (
    APPROVAL_RESET_AT_DUE_DATE_MULTI,
    APPROVAL_RESET_AT_DUE_DATE_ONCE,
    APPROVAL_RESET_AT_MIDNIGHT_MULTI,
    # Approval reset types
    APPROVAL_RESET_AT_MIDNIGHT_ONCE,
    APPROVAL_RESET_PENDING_CLAIM_AUTO_APPROVE,
    APPROVAL_RESET_PENDING_CLAIM_CLEAR,
    # Pending claim actions
    APPROVAL_RESET_PENDING_CLAIM_HOLD,
    APPROVAL_RESET_UPON_COMPLETION,
    ATTR_CAN_APPROVE,
    ATTR_CAN_CLAIM,
    # Sensor attributes
    ATTR_CHORE_APPROVE_BUTTON_ENTITY_ID,
    ATTR_CHORE_CLAIM_BUTTON_ENTITY_ID,
    ATTR_CHORE_DISAPPROVE_BUTTON_ENTITY_ID,
    ATTR_DASHBOARD_BONUSES,
    # Dashboard helper attributes
    ATTR_DASHBOARD_CHORES,
    ATTR_DASHBOARD_PENALTIES,
    ATTR_DASHBOARD_REWARDS,
    ATTR_DEFAULT_POINTS,
    ATTR_DUE_DATE,
    ATTR_GLOBAL_STATE,
    # Reward attributes
    ATTR_REWARD_APPROVE_BUTTON_ENTITY_ID,
    ATTR_REWARD_CLAIM_BUTTON_ENTITY_ID,
    ATTR_REWARD_DISAPPROVE_BUTTON_ENTITY_ID,
    # Chore states
    CHORE_STATE_APPROVED,
    CHORE_STATE_APPROVED_IN_PART,
    CHORE_STATE_CLAIMED,
    CHORE_STATE_CLAIMED_IN_PART,
    CHORE_STATE_COMPLETED_BY_OTHER,
    CHORE_STATE_INDEPENDENT,
    CHORE_STATE_OVERDUE,
    CHORE_STATE_PENDING,
    CHORE_STATE_UNKNOWN,
    CHORE_STATE_VALUES,
    # Completion criteria
    COMPLETION_CRITERIA_INDEPENDENT,
    COMPLETION_CRITERIA_SHARED,
    COMPLETION_CRITERIA_SHARED_FIRST,
    COMPLETION_CRITERIA_VALUES,
    # Domain
    COORDINATOR,
    DATA_CHORE_APPROVAL_RESET_PENDING_CLAIM_ACTION,
    DATA_CHORE_APPROVAL_RESET_TYPE,
    DATA_CHORE_ASSIGNED_KIDS,
    DATA_CHORE_DEFAULT_POINTS,
    DATA_CHORE_DUE_DATE,
    # Data keys - chore fields
    DATA_CHORE_NAME,
    DATA_CHORE_OVERDUE_HANDLING_TYPE,
    DATA_CHORE_PER_KID_DUE_DATES,
    DATA_CHORE_RECURRING_FREQUENCY,
    DATA_CHORE_STATE,
    DATA_CHORES,
    # Data keys - kid chore data
    DATA_KID_CHORE_DATA,
    DATA_KID_CHORE_DATA_STATE,
    DATA_KID_COMPLETED_BY_OTHER_CHORES,
    DATA_KID_NAME,
    DATA_KID_POINTS,
    # Data keys - top level
    DATA_KIDS,
    DATA_REWARDS,
    DOMAIN,
    # Frequencies
    FREQUENCY_DAILY,
    FREQUENCY_MONTHLY,
    FREQUENCY_NONE,
    FREQUENCY_WEEKLY,
    # Overdue handling types
    OVERDUE_HANDLING_AT_DUE_DATE,
    OVERDUE_HANDLING_AT_DUE_DATE_THEN_RESET,
    OVERDUE_HANDLING_NEVER_OVERDUE,
    # Reward states
    REWARD_STATE_APPROVED,
    REWARD_STATE_CLAIMED,
    REWARD_STATE_NOT_CLAIMED,
    REWARD_STATE_VALUES,
    # Translation keys (for error assertions)
    TRANS_KEY_ERROR_CHORE_ALREADY_APPROVED,
)
from tests.helpers.setup import (
    SetupResult,
    setup_minimal_scenario,
    setup_multi_kid_scenario,
    setup_scenario,
)

# Re-export from validation
from tests.helpers.validation import (
    assert_all_entities_exist,
    assert_all_states_equal,
    assert_attribute_equals,
    assert_due_date_advanced,
    # Basic entity assertions
    assert_entity_exists,
    assert_entity_not_exists,
    assert_points_changed,
    assert_points_unchanged,
    assert_state_equals,
    assert_state_in,
    assert_state_not_equals,
    assert_state_transition,
    assert_workflow_failed,
    # Workflow result assertions
    assert_workflow_success,
    count_entities_by_kid,
    # Entity counting
    count_entities_by_platform,
    # Batch operations
    get_all_entity_states,
    get_kid_entity_ids,
    verify_entity_state,
    # Entity verification
    verify_kid_entities,
)

# Re-export from workflows
from tests.helpers.workflows import (
    WorkflowResult,
    apply_bonus,
    apply_penalty,
    approve_chore,
    approve_reward,
    claim_chore,
    claim_reward,
    disapprove_chore,
    find_bonus,
    find_chore,
    find_penalty,
    find_reward,
    get_chore_buttons,
    get_chore_states_all_kids,
    get_dashboard_helper,
    get_kid_points,
    get_reward_buttons,
    press_button,
)

__all__ = [
    # Setup
    "SetupResult",
    "setup_scenario",
    "setup_minimal_scenario",
    "setup_multi_kid_scenario",
    # Constants - States
    "CHORE_STATE_APPROVED",
    "CHORE_STATE_APPROVED_IN_PART",
    "CHORE_STATE_CLAIMED",
    "CHORE_STATE_CLAIMED_IN_PART",
    "CHORE_STATE_COMPLETED_BY_OTHER",
    "CHORE_STATE_INDEPENDENT",
    "CHORE_STATE_OVERDUE",
    "CHORE_STATE_PENDING",
    "CHORE_STATE_UNKNOWN",
    "CHORE_STATE_VALUES",
    "REWARD_STATE_APPROVED",
    "REWARD_STATE_CLAIMED",
    "REWARD_STATE_NOT_CLAIMED",
    "REWARD_STATE_VALUES",
    # Constants - Attributes
    "ATTR_CHORE_APPROVE_BUTTON_ENTITY_ID",
    "ATTR_CHORE_CLAIM_BUTTON_ENTITY_ID",
    "ATTR_CHORE_DISAPPROVE_BUTTON_ENTITY_ID",
    "ATTR_GLOBAL_STATE",
    "ATTR_CAN_APPROVE",
    "ATTR_CAN_CLAIM",
    "ATTR_DEFAULT_POINTS",
    "ATTR_DUE_DATE",
    "ATTR_REWARD_APPROVE_BUTTON_ENTITY_ID",
    "ATTR_REWARD_CLAIM_BUTTON_ENTITY_ID",
    "ATTR_REWARD_DISAPPROVE_BUTTON_ENTITY_ID",
    "ATTR_DASHBOARD_CHORES",
    "ATTR_DASHBOARD_REWARDS",
    "ATTR_DASHBOARD_BONUSES",
    "ATTR_DASHBOARD_PENALTIES",
    # Constants - Completion criteria
    "COMPLETION_CRITERIA_INDEPENDENT",
    "COMPLETION_CRITERIA_SHARED",
    "COMPLETION_CRITERIA_SHARED_FIRST",
    "COMPLETION_CRITERIA_VALUES",
    # Constants - Data keys
    "COORDINATOR",
    "DOMAIN",
    "DATA_KIDS",
    "DATA_CHORES",
    "DATA_REWARDS",
    "DATA_KID_POINTS",
    "DATA_KID_NAME",
    # Constants - Kid chore data keys
    "DATA_KID_CHORE_DATA",
    "DATA_KID_CHORE_DATA_STATE",
    "DATA_KID_COMPLETED_BY_OTHER_CHORES",
    # Constants - Chore field keys
    "DATA_CHORE_NAME",
    "DATA_CHORE_STATE",
    "DATA_CHORE_DUE_DATE",
    "DATA_CHORE_PER_KID_DUE_DATES",
    "DATA_CHORE_DEFAULT_POINTS",
    "DATA_CHORE_RECURRING_FREQUENCY",
    "DATA_CHORE_APPROVAL_RESET_TYPE",
    "DATA_CHORE_OVERDUE_HANDLING_TYPE",
    "DATA_CHORE_APPROVAL_RESET_PENDING_CLAIM_ACTION",
    "DATA_CHORE_ASSIGNED_KIDS",
    # Constants - Frequencies
    "FREQUENCY_DAILY",
    "FREQUENCY_WEEKLY",
    "FREQUENCY_MONTHLY",
    "FREQUENCY_NONE",
    # Constants - Approval reset types
    "APPROVAL_RESET_AT_MIDNIGHT_ONCE",
    "APPROVAL_RESET_AT_MIDNIGHT_MULTI",
    "APPROVAL_RESET_AT_DUE_DATE_ONCE",
    "APPROVAL_RESET_AT_DUE_DATE_MULTI",
    "APPROVAL_RESET_UPON_COMPLETION",
    # Constants - Pending claim actions
    "APPROVAL_RESET_PENDING_CLAIM_HOLD",
    "APPROVAL_RESET_PENDING_CLAIM_CLEAR",
    "APPROVAL_RESET_PENDING_CLAIM_AUTO_APPROVE",
    # Constants - Overdue handling types
    "OVERDUE_HANDLING_AT_DUE_DATE",
    "OVERDUE_HANDLING_NEVER_OVERDUE",
    "OVERDUE_HANDLING_AT_DUE_DATE_THEN_RESET",
    # Constants - Translation keys
    "TRANS_KEY_ERROR_CHORE_ALREADY_APPROVED",
    # Workflows
    "WorkflowResult",
    "get_dashboard_helper",
    "get_kid_points",
    "find_chore",
    "find_reward",
    "find_bonus",
    "find_penalty",
    "get_chore_buttons",
    "get_reward_buttons",
    "press_button",
    "claim_chore",
    "approve_chore",
    "disapprove_chore",
    "claim_reward",
    "approve_reward",
    "apply_bonus",
    "apply_penalty",
    "get_chore_states_all_kids",
    # Validation - Basic assertions
    "assert_entity_exists",
    "assert_entity_not_exists",
    "assert_state_equals",
    "assert_state_not_equals",
    "assert_attribute_equals",
    "assert_state_in",
    # Validation - Workflow assertions
    "assert_workflow_success",
    "assert_workflow_failed",
    "assert_points_changed",
    "assert_points_unchanged",
    "assert_state_transition",
    "assert_due_date_advanced",
    # Validation - Counting
    "count_entities_by_platform",
    "count_entities_by_kid",
    "get_kid_entity_ids",
    # Validation - Verification
    "verify_kid_entities",
    "verify_entity_state",
    # Validation - Batch
    "get_all_entity_states",
    "assert_all_entities_exist",
    "assert_all_states_equal",
]
