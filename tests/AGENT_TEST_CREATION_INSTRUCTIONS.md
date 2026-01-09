# Agent Test Creation Instructions

**Purpose**: Guide for creating modern KidsChores tests using YAML scenarios, the setup helper, and the dashboard helper sensor as single source of truth.

---

## Overview: Modern Test Architecture

```
tests/
├── conftest.py              # Core fixtures (mock_hass_users, auto_enable_custom_integrations)
├── helpers/
│   ├── __init__.py          # Re-exports everything for convenient imports
│   ├── constants.py         # All KidsChores constants (from const.py)
│   ├── setup.py             # setup_from_yaml(), SetupResult dataclass
│   ├── workflows.py         # Chore/reward workflow helpers
│   └── validation.py        # Entity state validation helpers
├── scenarios/
│   ├── scenario_minimal.yaml    # 1 kid, 5 chores
│   ├── scenario_shared.yaml     # 3 kids, 8 shared chores
│   ├── scenario_full.yaml       # 3 kids, everything
│   └── scenario_notifications.yaml  # Notification testing
├── test_workflow_chores.py      # Chore workflow tests
├── test_workflow_notifications.py  # Notification workflow tests
├── test_translations_custom.py  # Translation file tests
└── legacy/                      # Old tests (direct coordinator manipulation)
```

---

## Rule 0: Import from tests.helpers, NOT const.py

✅ **CORRECT** - Import from tests.helpers:

```python
from tests.helpers import (
    # Setup
    setup_from_yaml, SetupResult,

    # Constants - Chore states
    CHORE_STATE_PENDING, CHORE_STATE_CLAIMED, CHORE_STATE_APPROVED,
    CHORE_STATE_COMPLETED_BY_OTHER, CHORE_STATE_OVERDUE,

    # Constants - Sensor attributes
    ATTR_CHORE_CLAIM_BUTTON_ENTITY_ID, ATTR_CHORE_APPROVE_BUTTON_ENTITY_ID,
    ATTR_GLOBAL_STATE, ATTR_CAN_CLAIM, ATTR_CAN_APPROVE, ATTR_DUE_DATE,

    # Constants - Completion criteria
    COMPLETION_CRITERIA_INDEPENDENT, COMPLETION_CRITERIA_SHARED,
    COMPLETION_CRITERIA_SHARED_FIRST,

    # Constants - Data keys
    DATA_KID_CHORE_DATA, DATA_KID_CHORE_DATA_STATE, DATA_KID_POINTS,

    # Workflows
    get_dashboard_helper, find_chore, get_chore_buttons,
)
```

❌ **WRONG** - Direct import from const.py:

```python
from custom_components.kidschores.const import CHORE_STATE_PENDING  # Don't do this
```

**Why**: `tests/helpers/constants.py` provides organized imports with quick-reference documentation.

---

## Rule 1: Use YAML Scenarios + setup_from_yaml()

Modern tests load scenarios from YAML files and run through the full config flow:

```python
from tests.helpers.setup import setup_from_yaml, SetupResult

@pytest.fixture
async def scenario_minimal(
    hass: HomeAssistant,
    mock_hass_users: dict[str, Any],
) -> SetupResult:
    """Load minimal scenario: 1 kid, 1 parent, 5 chores."""
    return await setup_from_yaml(
        hass,
        mock_hass_users,
        "tests/scenarios/scenario_minimal.yaml",
    )
```

### SetupResult provides:

```python
result = await setup_from_yaml(hass, mock_hass_users, "tests/scenarios/scenario_minimal.yaml")

# Access coordinator directly
coordinator = result.coordinator

# Get internal IDs by name
kid_id = result.kid_ids["Zoë"]           # UUID for Zoë
chore_id = result.chore_ids["Make bed"]  # UUID for Make bed chore
parent_id = result.parent_ids["Mom"]     # UUID for Mom

# Config entry
config_entry = result.config_entry
```

---

## Rule 2: Two Testing Approaches

### Approach A: Direct Coordinator API (Simpler, Faster)

Use for testing business logic without UI interaction:

```python
async def test_claim_changes_state(hass, scenario_minimal):
    coordinator = scenario_minimal.coordinator
    kid_id = scenario_minimal.kid_ids["Zoë"]
    chore_id = scenario_minimal.chore_ids["Make bed"]

    # Use coordinator API directly
    coordinator.claim_chore(kid_id, chore_id, "Zoë")

    # Read state from coordinator data
    kid_data = coordinator.kids_data.get(kid_id, {})
    chore_data = kid_data.get(DATA_KID_CHORE_DATA, {}).get(chore_id, {})
    state = chore_data.get(DATA_KID_CHORE_DATA_STATE)

    assert state == CHORE_STATE_CLAIMED
```

### Approach B: Service Calls via Dashboard Helper (Full Integration)

Use for testing complete end-to-end flows through HA entities:

```python
from homeassistant.core import Context

async def test_claim_via_button(hass, scenario_minimal, mock_hass_users):
    # Get dashboard helper
    helper_state = hass.states.get("sensor.kc_zoe_ui_dashboard_helper")
    helper_attrs = helper_state.attributes

    # Find chore in helper
    chore = next(c for c in helper_attrs["chores"] if c["name"] == "Make bed")
    chore_sensor_eid = chore["eid"]

    # Get button ID from chore sensor
    chore_state = hass.states.get(chore_sensor_eid)
    claim_button_eid = chore_state.attributes[ATTR_CHORE_CLAIM_BUTTON_ENTITY_ID]

    # Press button with user context
    kid_context = Context(user_id=mock_hass_users["kid1"].id)
    await hass.services.async_call(
        "button", "press",
        {"entity_id": claim_button_eid},
        blocking=True, context=kid_context,
    )
    await hass.async_block_till_done()

    # Verify via sensor state
    chore_state = hass.states.get(chore_sensor_eid)
    assert chore_state.state == CHORE_STATE_CLAIMED
```

---

## Rule 3: Dashboard Helper Is Single Source of Truth for Entity IDs

The dashboard helper sensor (`sensor.kc_{kid}_ui_dashboard_helper`) contains ALL entity IDs:

```python
helper_state = hass.states.get("sensor.kc_zoe_ui_dashboard_helper")
helper_attrs = helper_state.attributes

# Chores (sensor entity IDs)
chores_list = helper_attrs.get("chores", [])
for chore in chores_list:
    chore_eid = chore["eid"]        # sensor.kc_zoe_chore_status_make_bed
    chore_name = chore["name"]      # "Make bed"
    chore_status = chore["status"]  # "pending", "claimed", "approved"
    can_claim = chore["can_claim"]  # True/False
    can_approve = chore["can_approve"]

# Rewards (sensor entity IDs)
rewards_list = helper_attrs.get("rewards", [])

# Bonuses & Penalties (BUTTON entity IDs - not sensors!)
bonuses_list = helper_attrs.get("bonuses", [])
penalties_list = helper_attrs.get("penalties", [])

# Core sensors
core_sensors = helper_attrs.get("core_sensors", {})
points_sensor = core_sensors["points_eid"]  # sensor.kc_zoe_points
```

**Never manually construct entity IDs. Always extract from dashboard helper.**

---

## Rule 4: Getting Button IDs from Chore Sensors

Chore-specific buttons are in the chore sensor's attributes:

```python
from tests.helpers import (
    ATTR_CHORE_CLAIM_BUTTON_ENTITY_ID,
    ATTR_CHORE_APPROVE_BUTTON_ENTITY_ID,
    ATTR_CHORE_DISAPPROVE_BUTTON_ENTITY_ID,
)

# Get chore sensor from dashboard helper
chore_info = next(c for c in helper_attrs["chores"] if c["name"] == "Make bed")
chore_sensor_eid = chore_info["eid"]

# Read button IDs from sensor attributes
chore_state = hass.states.get(chore_sensor_eid)
claim_button = chore_state.attributes.get(ATTR_CHORE_CLAIM_BUTTON_ENTITY_ID)
approve_button = chore_state.attributes.get(ATTR_CHORE_APPROVE_BUTTON_ENTITY_ID)
disapprove_button = chore_state.attributes.get(ATTR_CHORE_DISAPPROVE_BUTTON_ENTITY_ID)
```

---

## Rule 5: Service Calls With User Context

Always pass `context=` with the appropriate user for authorization:

```python
from homeassistant.core import Context

# Kid claims chore
kid_context = Context(user_id=mock_hass_users["kid1"].id)
await hass.services.async_call(
    "button", "press",
    {"entity_id": claim_button_eid},
    blocking=True, context=kid_context,
)

# Parent approves chore
parent_context = Context(user_id=mock_hass_users["parent1"].id)
await hass.services.async_call(
    "button", "press",
    {"entity_id": approve_button_eid},
    blocking=True, context=parent_context,
)
```

### Available mock_hass_users Keys

- `mock_hass_users["kid1"]` - First kid (Zoë in most scenarios)
- `mock_hass_users["kid2"]` - Second kid (Max)
- `mock_hass_users["kid3"]` - Third kid (Lila)
- `mock_hass_users["parent1"]` - First parent (Mom)
- `mock_hass_users["admin"]` - Admin user

---

## Rule 6: Reading Coordinator Data

For direct data access, use coordinator properties:

```python
coordinator = scenario_minimal.coordinator

# Kid data
kid_data = coordinator.kids_data.get(kid_id, {})
points = kid_data.get(DATA_KID_POINTS, 0.0)
name = kid_data.get(DATA_KID_NAME, "")

# Per-kid chore state
chore_data = kid_data.get(DATA_KID_CHORE_DATA, {})
per_chore = chore_data.get(chore_id, {})
state = per_chore.get(DATA_KID_CHORE_DATA_STATE, CHORE_STATE_PENDING)
due_date = per_chore.get(DATA_KID_CHORE_DATA_DUE_DATE)

# Global chore data
chore_info = coordinator.chores_data.get(chore_id, {})
completion_criteria = chore_info.get(DATA_CHORE_COMPLETION_CRITERIA)
recurring_frequency = chore_info.get(DATA_CHORE_RECURRING_FREQUENCY)
```

---

## YAML Scenario Format

Create scenarios in `tests/scenarios/`:

```yaml
# tests/scenarios/scenario_example.yaml

system:
  points_label: "Points"
  points_icon: "mdi:star-outline"

kids:
  - name: "Zoë"
    ha_user: "kid1" # Maps to mock_hass_users["kid1"]
    dashboard_language: "en"
    enable_mobile_notifications: false
    mobile_notify_service: ""

parents:
  - name: "Mom"
    ha_user: "parent1" # Maps to mock_hass_users["parent1"]
    kids: ["Zoë"] # Associate with kids by name
    enable_mobile_notifications: false
    mobile_notify_service: ""

chores:
  - name: "Make bed"
    assigned_to: ["Zoë"] # Assign by kid name
    points: 5.0
    icon: "mdi:bed"
    completion_criteria: "independent" # or "shared_all", "shared_first"
    recurring_frequency: "daily" # or "weekly", "monthly", "once"
    auto_approve: false
    # Advanced options:
    # approval_reset_type: "at_midnight_once"
    # overdue_handling_type: "at_due_date"
    # due_date: "2026-01-15T08:00:00"
```

---

## Complete Test Example

```python
"""Chore workflow tests."""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant

from tests.helpers import (
    CHORE_STATE_PENDING, CHORE_STATE_CLAIMED, CHORE_STATE_APPROVED,
    DATA_KID_CHORE_DATA, DATA_KID_CHORE_DATA_STATE, DATA_KID_POINTS,
)
from tests.helpers.setup import setup_from_yaml, SetupResult


@pytest.fixture
async def scenario_minimal(
    hass: HomeAssistant,
    mock_hass_users: dict[str, Any],
) -> SetupResult:
    """Load minimal scenario."""
    return await setup_from_yaml(
        hass, mock_hass_users,
        "tests/scenarios/scenario_minimal.yaml",
    )


def get_kid_chore_state(coordinator, kid_id: str, chore_id: str) -> str:
    """Get chore state for a kid."""
    kid_data = coordinator.kids_data.get(kid_id, {})
    chore_data = kid_data.get(DATA_KID_CHORE_DATA, {})
    per_chore = chore_data.get(chore_id, {})
    return per_chore.get(DATA_KID_CHORE_DATA_STATE, CHORE_STATE_PENDING)


class TestChoreWorkflow:
    """Chore workflow tests."""

    @pytest.mark.asyncio
    async def test_claim_approve_grants_points(
        self,
        hass: HomeAssistant,
        scenario_minimal: SetupResult,
    ) -> None:
        """Claiming and approving a chore grants points."""
        coordinator = scenario_minimal.coordinator
        kid_id = scenario_minimal.kid_ids["Zoë"]
        chore_id = scenario_minimal.chore_ids["Make bed"]  # 5 points

        initial_points = coordinator.kids_data[kid_id].get(DATA_KID_POINTS, 0.0)

        with patch.object(coordinator, "_notify_kid", new=AsyncMock()):
            # Claim
            coordinator.claim_chore(kid_id, chore_id, "Zoë")
            assert get_kid_chore_state(coordinator, kid_id, chore_id) == CHORE_STATE_CLAIMED

            # Approve
            coordinator.approve_chore("Mom", kid_id, chore_id)
            assert get_kid_chore_state(coordinator, kid_id, chore_id) == CHORE_STATE_APPROVED

        # Verify points
        final_points = coordinator.kids_data[kid_id].get(DATA_KID_POINTS, 0.0)
        assert final_points == initial_points + 5.0
```

---

## Quick Reference: Key Constants

### Chore States

| Constant                         | Value                | Meaning                           |
| -------------------------------- | -------------------- | --------------------------------- |
| `CHORE_STATE_PENDING`            | "pending"            | Not yet claimed                   |
| `CHORE_STATE_CLAIMED`            | "claimed"            | Claimed, awaiting approval        |
| `CHORE_STATE_APPROVED`           | "approved"           | Completed and approved            |
| `CHORE_STATE_OVERDUE`            | "overdue"            | Past due date                     |
| `CHORE_STATE_COMPLETED_BY_OTHER` | "completed_by_other" | Another kid did it (shared_first) |
| `CHORE_STATE_CLAIMED_IN_PART`    | "claimed_in_part"    | Some kids claimed (shared_all)    |
| `CHORE_STATE_APPROVED_IN_PART`   | "approved_in_part"   | Some kids approved (shared_all)   |

### Completion Criteria

| Constant                           | Behavior                              |
| ---------------------------------- | ------------------------------------- |
| `COMPLETION_CRITERIA_INDEPENDENT`  | Each kid has their own chore instance |
| `COMPLETION_CRITERIA_SHARED_FIRST` | First to claim wins, others blocked   |
| `COMPLETION_CRITERIA_SHARED`       | All assigned kids must complete       |

### Sensor Attributes

| Constant                                 | Description                      |
| ---------------------------------------- | -------------------------------- |
| `ATTR_CHORE_CLAIM_BUTTON_ENTITY_ID`      | Button to claim chore            |
| `ATTR_CHORE_APPROVE_BUTTON_ENTITY_ID`    | Button to approve chore          |
| `ATTR_CHORE_DISAPPROVE_BUTTON_ENTITY_ID` | Button to disapprove chore       |
| `ATTR_GLOBAL_STATE`                      | Aggregated state across all kids |
| `ATTR_CAN_CLAIM`                         | Whether chore can be claimed     |
| `ATTR_CAN_APPROVE`                       | Whether chore can be approved    |
| `ATTR_DUE_DATE`                          | Chore due date                   |
| `ATTR_DEFAULT_POINTS`                    | Points awarded on approval       |

---

## Golden Rules

1. **Import from `tests.helpers`** - never from `const.py` directly
2. **Use YAML scenarios** - create reusable test data via `setup_from_yaml()`
3. **Get entity IDs from dashboard helper** - never construct them manually
4. **Use SetupResult** - access `coordinator`, `kid_ids`, `chore_ids` by name
5. **Mock notifications** - `patch.object(coordinator, "_notify_kid", new=AsyncMock())`
6. **Pass user context** - service calls need `context=Context(user_id=...)`
