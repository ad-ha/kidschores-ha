# KidsChores Test Creation Template

**Purpose**: Step-by-step templates for creating high-quality tests following KidsChores standards.

**Audience**: AI agents, developers creating new tests

**Related Documentation**:

- [TESTDATA_CATALOG.md](./TESTDATA_CATALOG.md) - Scenario selection guide
- [FIXTURE_GUIDE.md](./FIXTURE_GUIDE.md) - Fixture usage reference
- [TESTING_AGENT_INSTRUCTIONS.md](./TESTING_AGENT_INSTRUCTIONS.md) - Quick-start guide
- [TESTING_GUIDE.md](./TESTING_GUIDE.md) - Comprehensive testing documentation

---

## Quick Start Checklist

**Before writing any test:**

- [ ] **Identify test type** - Config flow, service, entity state, coordinator, workflow, or integration?
- [ ] **Select scenario** - Check [TESTDATA_CATALOG.md](./TESTDATA_CATALOG.md) for appropriate scenario
- [ ] **Choose fixtures** - Review [FIXTURE_GUIDE.md](./FIXTURE_GUIDE.md) fixture selection matrix
- [ ] **Plan assertions** - What specific behavior are you verifying?
- [ ] **Check existing tests** - Similar tests in the file? Reuse patterns!

---

## Table of Contents

1. [Test Type Decision Tree](#test-type-decision-tree)
2. [Template: Config Flow Test](#template-config-flow-test)
3. [Template: Service Test](#template-service-test)
4. [Template: Entity State Test](#template-entity-state-test)
5. [Template: Coordinator Test](#template-coordinator-test)
6. [Template: Workflow Test](#template-workflow-test)
7. [Template: Integration Test](#template-integration-test)
8. [Naming Conventions](#naming-conventions)
9. [AAA Pattern Guidelines](#aaa-pattern-guidelines)
10. [Common Assertion Patterns](#common-assertion-patterns)
11. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
12. [Parametrization Guide](#parametrization-guide)
13. [Test Quality Checklist](#test-quality-checklist)

---

## Test Type Decision Tree

```
What are you testing?
├─ User flow through UI forms?
│  └─ Use: Config Flow Test
├─ Service call behavior?
│  └─ Use: Service Test
├─ Entity state/attributes after action?
│  └─ Use: Entity State Test
├─ Coordinator business logic?
│  └─ Use: Coordinator Test
├─ Complete user workflow (multiple steps)?
│  └─ Use: Workflow Test
└─ End-to-end integration (setup → action → verify)?
   └─ Use: Integration Test
```

---

## Template: Config Flow Test

**Use when**: Testing configuration/options flows, form validation, flow navigation

**File location**: `tests/test_config_flow.py` or `tests/test_options_flow.py`

### Basic Structure

```python
"""Tests for KidsChores config flow."""

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.kidschores.const import DOMAIN


async def test_form_<flow_name>_<scenario>(hass: HomeAssistant) -> None:
    """Test <describe what scenario you're testing>."""
    # ARRANGE: Initialize flow
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # ASSERT: Verify initial form
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "expected_first_step"

    # ACT: Submit form with valid data
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"field_name": "value"},
    )

    # ASSERT: Verify flow progressed
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "next_step"
    # Or for completion:
    # assert result["type"] == FlowResultType.CREATE_ENTRY
```

### Example: Testing Form Validation

```python
async def test_form_points_label_validation_empty(hass: HomeAssistant) -> None:
    """Test points label validation rejects empty input."""
    # ARRANGE: Navigate to points_label step
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"backup_selection": "start_fresh"},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={}
    )

    # ACT: Submit empty points label
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_POINTS_LABEL: ""},
    )

    # ASSERT: Verify validation error
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "points_label"
    assert result["errors"] == {"points_label": "cannot_be_empty"}
```

### Key Points

- **Fixtures needed**: `hass` only (no integration setup required)
- **Navigation**: Each `async_configure()` call submits current form
- **Flow ID**: Carry forward `result["flow_id"]` through all steps
- **Validation**: Submit invalid data, verify `FlowResultType.FORM` with `errors`
- **Completion**: Final step returns `FlowResultType.CREATE_ENTRY`

---

## Template: Service Test

**Use when**: Testing service call behavior, parameter validation, state changes

**File location**: `tests/test_services.py`

### Basic Structure

```python
"""Tests for KidsChores services."""

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kidschores.const import (
    ATTR_KID_NAME,
    ATTR_CHORE_NAME,
    DOMAIN,
    SERVICE_CLAIM_CHORE,
)
from .conftest import get_kid_by_name, get_chore_by_name, construct_entity_id


async def test_service_<service_name>_<scenario>(
    hass: HomeAssistant,
    scenario_minimal: tuple[MockConfigEntry, dict[str, str]],
) -> None:
    """Test <service> with <scenario description>."""
    # ARRANGE: Get scenario data
    entry, name_map = scenario_minimal

    kid_name = "Zoë"
    chore_name = "Feed the cåts"

    # Get IDs using helpers
    kid_id = name_map[kid_name]
    chore_id = name_map[chore_name]

    # Get coordinator
    from custom_components.kidschores.const import COORDINATOR
    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]

    # ACT: Call service
    await hass.services.async_call(
        DOMAIN,
        SERVICE_CLAIM_CHORE,
        {ATTR_KID_NAME: kid_name, ATTR_CHORE_NAME: chore_name},
        blocking=True,
    )

    # ASSERT: Verify state changes
    chore_data = coordinator.chores_data[chore_id]
    assert chore_data["state"] == CHORE_STATE_CLAIMED
    assert chore_id in coordinator.kids_data[kid_id]["claimed_chores"]
```

### Example: Testing Service Validation

```python
async def test_service_claim_chore_invalid_kid_name(
    hass: HomeAssistant,
    scenario_minimal: tuple[MockConfigEntry, dict[str, str]],
) -> None:
    """Test claim_chore service rejects invalid kid name."""
    entry, name_map = scenario_minimal

    # ACT & ASSERT: Service call should raise validation error
    with pytest.raises(ServiceValidationError, match="Kid not found"):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_CLAIM_CHORE,
            {ATTR_KID_NAME: "Nonexistent Kid", ATTR_CHORE_NAME: "Feed the cåts"},
            blocking=True,
        )
```

### Example: Testing Entity State After Service

```python
async def test_service_approve_chore_updates_points_sensor(
    hass: HomeAssistant,
    scenario_minimal: tuple[MockConfigEntry, dict[str, str]],
) -> None:
    """Test approve_chore service updates kid's points sensor."""
    entry, name_map = scenario_minimal

    kid_name = "Zoë"
    chore_name = "Feed the cåts"

    # Get initial points
    points_sensor = construct_entity_id("sensor", kid_name, "points")
    initial_points = float(hass.states.get(points_sensor).state)

    # Claim and approve chore
    await hass.services.async_call(
        DOMAIN, SERVICE_CLAIM_CHORE,
        {ATTR_KID_NAME: kid_name, ATTR_CHORE_NAME: chore_name},
        blocking=True,
    )
    await hass.services.async_call(
        DOMAIN, SERVICE_APPROVE_CHORE,
        {ATTR_CHORE_NAME: chore_name},
        blocking=True,
    )

    # Verify points increased
    final_points = float(hass.states.get(points_sensor).state)
    assert final_points == initial_points + 10.0  # chore is worth 10 points
```

### Key Points

- **Fixtures needed**: Scenario fixture (e.g., `scenario_minimal`)
- **Coordinator access**: `hass.data[DOMAIN][entry.entry_id][COORDINATOR]`
- **Use helpers**: `get_kid_by_name()`, `get_chore_by_name()`, `construct_entity_id()`
- **Blocking calls**: Always use `blocking=True` to wait for completion
- **Validation errors**: Use `pytest.raises(ServiceValidationError)` for expected failures

---

## Template: Entity State Test

**Use when**: Testing entity state values, attributes, availability after setup or actions

**File location**: `tests/test_sensor.py`, `tests/test_button.py`, etc.

### Basic Structure

```python
"""Tests for KidsChores sensor entities."""

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .conftest import construct_entity_id, assert_entity_state


async def test_<entity_type>_<attribute>_<scenario>(
    hass: HomeAssistant,
    scenario_minimal: tuple[MockConfigEntry, dict[str, str]],
) -> None:
    """Test <entity> <attribute> with <scenario>."""
    # ARRANGE
    entry, name_map = scenario_minimal
    kid_name = "Zoë"

    # Construct entity ID using helper
    entity_id = construct_entity_id("sensor", kid_name, "points")

    # ACT: (if testing after action)
    # await hass.services.async_call(...)

    # ASSERT: Verify state and attributes
    await assert_entity_state(
        hass,
        entity_id,
        expected_state="10",
        expected_attrs={
            "lifetime_points": 10,
            "friendly_name": "Zoë Points",
        },
    )
```

### Example: Testing Attribute Updates

```python
async def test_sensor_points_updates_after_chore_approval(
    hass: HomeAssistant,
    scenario_minimal: tuple[MockConfigEntry, dict[str, str]],
) -> None:
    """Test points sensor updates when chore is approved."""
    entry, name_map = scenario_minimal
    kid_name = "Zoë"
    chore_name = "Feed the cåts"

    # Get initial state
    points_sensor = construct_entity_id("sensor", kid_name, "points")
    initial_state = hass.states.get(points_sensor)
    initial_points = float(initial_state.state)

    # Claim and approve chore
    await hass.services.async_call(
        DOMAIN, SERVICE_CLAIM_CHORE,
        {ATTR_KID_NAME: kid_name, ATTR_CHORE_NAME: chore_name},
        blocking=True,
    )
    await hass.services.async_call(
        DOMAIN, SERVICE_APPROVE_CHORE,
        {ATTR_CHORE_NAME: chore_name},
        blocking=True,
    )

    # Verify state updated
    await assert_entity_state(
        hass,
        points_sensor,
        expected_state=str(initial_points + 10.0),
        expected_attrs={"lifetime_points": initial_points + 10.0},
    )
```

### Example: Testing Entity Availability

```python
async def test_sensor_unavailable_when_kid_removed(
    hass: HomeAssistant,
    scenario_minimal: tuple[MockConfigEntry, dict[str, str]],
) -> None:
    """Test sensor becomes unavailable when kid is removed."""
    entry, name_map = scenario_minimal
    kid_name = "Zoë"
    kid_id = name_map[kid_name]

    points_sensor = construct_entity_id("sensor", kid_name, "points")

    # Verify initially available
    state = hass.states.get(points_sensor)
    assert state.state != "unavailable"

    # Remove kid
    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    await coordinator.async_remove_kid(kid_id)
    await hass.async_block_till_done()

    # Verify sensor unavailable
    state = hass.states.get(points_sensor)
    assert state.state == "unavailable"
```

### Key Points

- **Fixtures needed**: Scenario fixture for realistic data
- **Use helpers**: `construct_entity_id()`, `assert_entity_state()`
- **State access**: `hass.states.get(entity_id)`
- **Attributes**: Access via `state.attributes.get("key")`
- **Async wait**: Use `await hass.async_block_till_done()` after actions

---

## Template: Coordinator Test

**Use when**: Testing coordinator business logic, data manipulation, storage operations

**File location**: `tests/test_coordinator.py`

### Basic Structure

```python
"""Tests for KidsChores coordinator."""

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kidschores.const import COORDINATOR, DOMAIN
from .conftest import create_mock_kid_data, get_kid_by_name


async def test_coordinator_<operation>_<scenario>(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test coordinator <operation> with <scenario>."""
    # ARRANGE: Get coordinator
    coordinator = hass.data[DOMAIN][init_integration.entry_id][COORDINATOR]

    # Create test data
    kid_name = "Test Kid"
    kid_age = 10

    # ACT: Perform coordinator operation
    kid_id = await coordinator.async_add_kid(
        name=kid_name,
        age=kid_age,
        interests=["testing"],
    )

    # ASSERT: Verify data structure
    assert kid_id in coordinator.kids_data
    kid_data = coordinator.kids_data[kid_id]
    assert kid_data["name"] == kid_name
    assert kid_data["age"] == kid_age
    assert kid_data["points"] == 0
```

### Example: Testing Data Validation

```python
async def test_coordinator_add_kid_validates_name(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test coordinator rejects empty kid name."""
    coordinator = hass.data[DOMAIN][init_integration.entry_id][COORDINATOR]

    # ACT & ASSERT: Should raise validation error
    with pytest.raises(ValueError, match="Name cannot be empty"):
        await coordinator.async_add_kid(name="", age=8, interests=[])
```

### Example: Testing Business Logic

```python
async def test_coordinator_approve_chore_applies_points(
    hass: HomeAssistant,
    scenario_minimal: tuple[MockConfigEntry, dict[str, str]],
) -> None:
    """Test coordinator applies points when chore approved."""
    entry, name_map = scenario_minimal
    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]

    kid_name = "Zoë"
    chore_name = "Feed the cåts"

    # Get initial points
    kid_data = get_kid_by_name(coordinator.kids_data, kid_name)
    initial_points = kid_data["points"]

    # Get chore points
    chore_data = get_chore_by_name(coordinator.chores_data, chore_name)
    chore_points = chore_data["default_points"]

    # Claim and approve
    await coordinator.async_claim_chore(kid_data["internal_id"], chore_data["internal_id"])
    await coordinator.async_approve_chore(chore_data["internal_id"])

    # Verify points added
    kid_data = get_kid_by_name(coordinator.kids_data, kid_name)
    assert kid_data["points"] == initial_points + chore_points
```

### Key Points

- **Fixtures needed**: `init_integration` for empty setup, or scenario for data
- **Direct coordinator access**: Test business logic without services/entities
- **Use helpers**: `get_kid_by_name()`, `get_chore_by_name()`, data builders
- **Async methods**: Most coordinator methods are async - use `await`
- **No entity verification**: This tests coordinator only, not entity states

---

## Template: Workflow Test

**Use when**: Testing complete multi-step user workflows (claim → approve → reward)

**File location**: `tests/test_workflow_*.py`

### Basic Structure

```python
"""Tests for KidsChores chore claim workflow."""

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kidschores.const import (
    CHORE_STATE_CLAIMED,
    CHORE_STATE_APPROVED,
    COORDINATOR,
    DOMAIN,
)
from .conftest import construct_entity_id, get_kid_by_name, get_chore_by_name


async def test_workflow_<name>_<scenario>(
    hass: HomeAssistant,
    scenario_minimal: tuple[MockConfigEntry, dict[str, str]],
) -> None:
    """Test complete <workflow name> workflow."""
    # ARRANGE: Get scenario data
    entry, name_map = scenario_minimal
    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]

    kid_name = "Zoë"
    chore_name = "Feed the cåts"

    kid_data = get_kid_by_name(coordinator.kids_data, kid_name)
    chore_data = get_chore_by_name(coordinator.chores_data, chore_name)

    initial_points = kid_data["points"]
    chore_points = chore_data["default_points"]

    # ACT: Step 1 - Claim chore
    claim_button = construct_entity_id("button", kid_name, f"claim_chore_{chore_name}")
    await hass.services.async_call("button", "press", {"entity_id": claim_button}, blocking=True)

    # ASSERT: Verify claim state
    chore_data = get_chore_by_name(coordinator.chores_data, chore_name)
    assert chore_data["state"] == CHORE_STATE_CLAIMED

    # ACT: Step 2 - Approve chore
    approve_button = construct_entity_id("button", kid_name, f"approve_chore_{chore_name}")
    await hass.services.async_call("button", "press", {"entity_id": approve_button}, blocking=True)

    # ASSERT: Verify approval and points
    chore_data = get_chore_by_name(coordinator.chores_data, chore_name)
    assert chore_data["state"] == CHORE_STATE_APPROVED

    kid_data = get_kid_by_name(coordinator.kids_data, kid_name)
    assert kid_data["points"] == initial_points + chore_points

    # ASSERT: Verify entity states
    points_sensor = construct_entity_id("sensor", kid_name, "points")
    await assert_entity_state(
        hass,
        points_sensor,
        expected_state=str(initial_points + chore_points),
    )
```

### Example: Multi-Kid Workflow

```python
async def test_workflow_shared_chore_both_kids(
    hass: HomeAssistant,
    scenario_medium: tuple[MockConfigEntry, dict[str, str]],
) -> None:
    """Test shared chore workflow with both kids claiming."""
    entry, name_map = scenario_medium
    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]

    # Both kids claim shared chore
    shared_chore = "Stär sweep"
    zoe_id = name_map["Zoë"]
    max_id = name_map["Max!"]

    # Zoë claims
    await hass.services.async_call(
        DOMAIN, SERVICE_CLAIM_CHORE,
        {ATTR_KID_NAME: "Zoë", ATTR_CHORE_NAME: shared_chore},
        blocking=True,
    )

    # Max claims (should succeed - shared chore)
    await hass.services.async_call(
        DOMAIN, SERVICE_CLAIM_CHORE,
        {ATTR_KID_NAME: "Max!", ATTR_CHORE_NAME: shared_chore},
        blocking=True,
    )

    # Verify both claims exist
    chore_data = get_chore_by_name(coordinator.chores_data, shared_chore)
    assert zoe_id in chore_data["claims"]
    assert max_id in chore_data["claims"]

    # Approve both
    await hass.services.async_call(
        DOMAIN, SERVICE_APPROVE_CHORE,
        {ATTR_CHORE_NAME: shared_chore, ATTR_KID_NAME: "Zoë"},
        blocking=True,
    )
    await hass.services.async_call(
        DOMAIN, SERVICE_APPROVE_CHORE,
        {ATTR_CHORE_NAME: shared_chore, ATTR_KID_NAME: "Max!"},
        blocking=True,
    )

    # Verify both got points
    zoe_data = coordinator.kids_data[zoe_id]
    max_data = coordinator.kids_data[max_id]
    assert zoe_data["points"] > 0
    assert max_data["points"] > 0
```

### Key Points

- **Fixtures needed**: Scenario fixture with realistic data
- **Multi-step**: Each step should have ACT + ASSERT
- **Complete flow**: Test entire user journey, not isolated pieces
- **State verification**: Check intermediate states, not just final
- **Use helpers**: Avoid hardcoded entity IDs and data lookups

---

## Template: Integration Test

**Use when**: Testing complete integration behavior, setup → data → entities → services

**File location**: `tests/test_init.py`, `tests/test_integration_*.py`

### Basic Structure

```python
"""Tests for KidsChores integration setup."""

from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kidschores.const import DOMAIN


async def test_integration_<scenario>(hass: HomeAssistant, init_integration: MockConfigEntry) -> None:
    """Test integration <scenario description>."""
    # ARRANGE: Integration already set up by fixture

    # ASSERT: Verify integration loaded
    assert init_integration.entry_id in hass.data[DOMAIN]

    # ASSERT: Verify platforms loaded
    assert hass.states.async_entity_ids(Platform.SENSOR)
    assert hass.states.async_entity_ids(Platform.BUTTON)

    # ASSERT: Verify coordinator exists
    from custom_components.kidschores.const import COORDINATOR
    coordinator = hass.data[DOMAIN][init_integration.entry_id][COORDINATOR]
    assert coordinator is not None
```

### Example: Testing Setup with Data

```python
async def test_integration_loads_scenario_data(
    hass: HomeAssistant,
    scenario_minimal: tuple[MockConfigEntry, dict[str, str]],
) -> None:
    """Test integration creates entities from scenario data."""
    entry, name_map = scenario_minimal

    # Verify kid entities created
    kid_name = "Zoë"
    points_sensor = construct_entity_id("sensor", kid_name, "points")
    lifetime_sensor = construct_entity_id("sensor", kid_name, "lifetime_points")

    assert hass.states.get(points_sensor) is not None
    assert hass.states.get(lifetime_sensor) is not None

    # Verify chore buttons created
    chore_name = "Feed the cåts"
    claim_button = construct_entity_id("button", kid_name, f"claim_chore_feed_the_cats")

    assert hass.states.get(claim_button) is not None
```

### Example: Testing Unload

```python
async def test_integration_unload(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test integration unloads cleanly."""
    # Verify loaded
    assert init_integration.entry_id in hass.data[DOMAIN]

    # Unload
    await hass.config_entries.async_unload(init_integration.entry_id)
    await hass.async_block_till_done()

    # Verify unloaded
    assert init_integration.entry_id not in hass.data[DOMAIN]
```

### Key Points

- **Fixtures needed**: `init_integration` or scenario fixtures
- **Setup verification**: Check platforms loaded, coordinator exists
- **Entity creation**: Verify entities exist after setup
- **Cleanup testing**: Test unload/reload behavior
- **End-to-end**: Test from setup through usage to teardown

---

## Naming Conventions

### Test Function Names

**Pattern**: `test_<component>_<action>_<scenario>`

**Examples**:

```python
# Good - descriptive, clear hierarchy
test_service_claim_chore_success()
test_service_claim_chore_invalid_kid()
test_sensor_points_updates_after_approval()
test_coordinator_add_kid_validates_name()
test_workflow_claim_approve_reward_complete()

# Bad - vague, no context
test_claim()
test_service()
test_it_works()
```

### Test File Names

**Pattern**: `test_<module>_<focus>.py`

**Examples**:

```python
# Good - specific focus
test_config_flow.py
test_options_flow.py
test_services.py
test_sensor.py
test_workflow_chore_claim.py
test_badge_assignment_baseline.py

# Bad - too broad
test_kidschores.py
test_everything.py
test_misc.py
```

### Naming Rules

1. **Start with `test_`** - Required by pytest
2. **Use snake_case** - Not camelCase or PascalCase
3. **Be specific** - Describe what's being tested and expected outcome
4. **Include scenario** - `_success`, `_failure`, `_invalid_input`, `_edge_case`
5. **Group related** - Similar tests should have similar prefix
6. **No abbreviations** - Write out full words for clarity

---

## AAA Pattern Guidelines

**AAA = Arrange, Act, Assert**

Every test should follow this structure with clear sections:

```python
async def test_example(hass, scenario_minimal):
    """Test description."""
    # ARRANGE: Set up test data and get references
    entry, name_map = scenario_minimal
    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]

    kid_name = "Zoë"
    initial_points = get_kid_by_name(coordinator.kids_data, kid_name)["points"]

    # ACT: Perform the action being tested
    await hass.services.async_call(
        DOMAIN, SERVICE_CLAIM_CHORE,
        {ATTR_KID_NAME: kid_name, ATTR_CHORE_NAME: "Feed the cåts"},
        blocking=True,
    )

    # ASSERT: Verify expected outcomes
    kid_data = get_kid_by_name(coordinator.kids_data, kid_name)
    assert "feed_the_cats" in kid_data["claimed_chores"]
```

### Arrange Guidelines

**Purpose**: Set up test preconditions

**Good practices**:

- Get all data references at start
- Create test data using helpers
- Set up mocks/patches
- Document what state you're starting from

```python
# Good - clear setup
entry, name_map = scenario_minimal
coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
kid_data = get_kid_by_name(coordinator.kids_data, "Zoë")
initial_points = kid_data["points"]

# Bad - setup mixed with actions
result = await service_call()  # Too early!
kid_data = get_kid_by_name(...)  # Should be in ARRANGE
```

### Act Guidelines

**Purpose**: Execute ONE action being tested

**Good practices**:

- One primary action per test
- Use `blocking=True` for service calls
- Add `await hass.async_block_till_done()` after non-blocking operations
- Keep this section minimal

```python
# Good - single clear action
await hass.services.async_call(
    DOMAIN, SERVICE_CLAIM_CHORE,
    {ATTR_KID_NAME: "Zoë", ATTR_CHORE_NAME: "Feed the cåts"},
    blocking=True,
)

# Bad - multiple unrelated actions
await service_call_1()
await service_call_2()  # Should be separate test
await service_call_3()  # Should be separate test
```

### Assert Guidelines

**Purpose**: Verify expected outcomes

**Good practices**:

- Multiple related assertions OK
- Check both positive and negative conditions
- Use helper functions for complex checks
- Add descriptive assertion messages

```python
# Good - comprehensive verification
kid_data = get_kid_by_name(coordinator.kids_data, "Zoë")
assert kid_data["points"] == initial_points + 10
assert chore_id in kid_data["claimed_chores"]

state = hass.states.get(points_sensor)
assert state.state == "20"

# Bad - no assertions!
await service_call()
# Test ends with no verification - useless test
```

---

## Common Assertion Patterns

### State Equality

```python
# Basic state check
state = hass.states.get(entity_id)
assert state.state == "expected_value"

# Using helper
await assert_entity_state(hass, entity_id, expected_state="10")
```

### Attribute Verification

```python
# Check single attribute
state = hass.states.get(entity_id)
assert state.attributes.get("lifetime_points") == 100

# Check multiple attributes with helper
await assert_entity_state(
    hass,
    entity_id,
    expected_state="50",
    expected_attrs={
        "lifetime_points": 100,
        "badges_count": 3,
    },
)
```

### Dictionary Membership

```python
# Check key exists
assert kid_id in coordinator.kids_data

# Check value in dictionary
kid_data = coordinator.kids_data[kid_id]
assert kid_data["name"] == "Zoë"

# Check nested value
assert chore_id in kid_data["claimed_chores"]
```

### List Containment

```python
# Check item in list
assert "reading" in kid_data["interests"]

# Check list length
assert len(coordinator.kids_data) == 3

# Check empty
assert kid_data["claimed_chores"] == []
```

### Exception Assertions

```python
# Assert exception raised
with pytest.raises(ValueError, match="Name cannot be empty"):
    await coordinator.async_add_kid(name="", age=8, interests=[])

# Assert specific exception type
with pytest.raises(ServiceValidationError):
    await hass.services.async_call(...)
```

### Numeric Comparisons

```python
# Exact match
assert kid_data["points"] == 50.0

# Greater/less than
assert kid_data["points"] > 0
assert kid_data["age"] >= 6

# Tolerance for floats
assert abs(calculated_value - expected_value) < 0.01
```

### Boolean Assertions

```python
# True/False
assert chore_data["is_shared"] is True
assert kid_data["avatar"] is None

# Truthy/Falsy (use with caution)
assert coordinator.kids_data  # Non-empty dict
assert not kid_data["claimed_chores"]  # Empty list
```

---

## Anti-Patterns to Avoid

### ❌ Hardcoded Entity IDs

```python
# Bad - breaks if kid name changes
state = hass.states.get("sensor.kc_zoe_points")

# Good - constructed from data
points_sensor = construct_entity_id("sensor", kid_name, "points")
state = hass.states.get(points_sensor)
```

### ❌ Direct Data Access Without Helpers

```python
# Bad - relies on internal structure
kid_id = None
for k_id, k_data in coordinator.kids_data.items():
    if k_data["name"] == "Zoë":
        kid_id = k_id
        break

# Good - use helper
kid_data = get_kid_by_name(coordinator.kids_data, "Zoë")
kid_id = kid_data["internal_id"]
```

### ❌ Testing Multiple Things at Once

```python
# Bad - one test for multiple scenarios
async def test_all_services():
    await test_claim()  # Should be separate test
    await test_approve()  # Should be separate test
    await test_reward()  # Should be separate test

# Good - separate focused tests
async def test_service_claim_chore_success():
    ...

async def test_service_approve_chore_success():
    ...

async def test_service_redeem_reward_success():
    ...
```

### ❌ No Assertions

```python
# Bad - test does nothing
async def test_claim_chore(hass, scenario_minimal):
    await hass.services.async_call(
        DOMAIN, SERVICE_CLAIM_CHORE, {...}, blocking=True
    )
    # No assertions! Test is useless

# Good - verify behavior
async def test_claim_chore(hass, scenario_minimal):
    await hass.services.async_call(...)

    chore_data = get_chore_by_name(coordinator.chores_data, "Feed the cåts")
    assert chore_data["state"] == CHORE_STATE_CLAIMED
```

### ❌ Sleep/Wait Instead of Async Done

```python
# Bad - unreliable timing
await hass.services.async_call(...)
await asyncio.sleep(1)  # Don't do this!
assert state == "expected"

# Good - proper synchronization
await hass.services.async_call(..., blocking=True)
# Or:
await hass.async_block_till_done()
assert state == "expected"
```

### ❌ Over-Mocking

```python
# Bad - mocking too much, not testing real behavior
with patch("custom_components.kidschores.coordinator.KCDataCoordinator"):
    with patch("custom_components.kidschores.storage.KCStorageManager"):
        with patch("custom_components.kidschores.helpers.kc_helpers"):
            # You're not testing anything real anymore!
            ...

# Good - use fixtures, mock only external calls
async def test_service(hass, scenario_minimal):
    # Test real coordinator with real storage helpers
    # Only mock external services (notifications, etc.)
    with patch.object(coordinator, "_notify_kid", new=AsyncMock()):
        ...
```

### ❌ Unclear Test Names

```python
# Bad - what does this test?
async def test_chore_1():
    ...

async def test_service():
    ...

# Good - descriptive names
async def test_chore_claim_updates_state_to_claimed():
    ...

async def test_service_claim_chore_rejects_nonexistent_kid():
    ...
```

### ❌ Making Up Data

```python
# Bad - data doesn't exist in scenario
kid_name = "NonexistentKid"  # Not in scenario!
await service_call(ATTR_KID_NAME: kid_name)

# Good - use data from catalog/scenario
# Check TESTDATA_CATALOG.md first!
kid_name = "Zoë"  # Exists in scenario_minimal
await service_call(ATTR_KID_NAME: kid_name)
```

---

## Parametrization Guide

**Use when**: Testing same logic with multiple inputs

### Basic Parametrization

```python
import pytest

@pytest.mark.parametrize(
    "kid_name,expected_slug",
    [
        ("Zoë", "zoe"),
        ("Max!", "max"),
        ("Sarah Jane", "sarah_jane"),
    ],
)
def test_kid_name_slugification(kid_name, expected_slug):
    """Test kid names are slugified correctly."""
    from homeassistant.util import slugify

    result = slugify(kid_name)
    assert result == expected_slug
```

### Parametrize with IDs

```python
@pytest.mark.parametrize(
    "points,cost,should_succeed",
    [
        (100, 50, True),
        (50, 50, True),
        (49, 50, False),
        (0, 50, False),
    ],
    ids=["enough_points", "exact_points", "one_short", "no_points"],
)
async def test_reward_claim_point_validation(
    hass, init_integration, points, cost, should_succeed
):
    """Test reward claim validates sufficient points."""
    coordinator = hass.data[DOMAIN][init_integration.entry_id][COORDINATOR]

    kid_data = create_mock_kid_data("kid1", "Test", points=points)
    reward_data = create_mock_reward_data("reward1", "Reward", cost=cost)

    coordinator.kids_data["kid1"] = kid_data
    coordinator.rewards_data["reward1"] = reward_data

    if should_succeed:
        await coordinator.async_claim_reward("kid1", "reward1")
        assert True  # No exception
    else:
        with pytest.raises(ValueError):
            await coordinator.async_claim_reward("kid1", "reward1")
```

### Parametrize with Fixtures

```python
@pytest.mark.parametrize(
    "scenario_fixture",
    ["scenario_minimal", "scenario_medium", "scenario_full"],
)
async def test_points_sensor_exists_all_scenarios(
    hass, scenario_fixture, request
):
    """Test points sensor exists in all scenarios."""
    # Use request.getfixturevalue to get fixture dynamically
    entry, name_map = request.getfixturevalue(scenario_fixture)

    # All scenarios have Zoë
    points_sensor = construct_entity_id("sensor", "Zoë", "points")
    state = hass.states.get(points_sensor)

    assert state is not None
    assert state.state != "unavailable"
```

### When to Parametrize

✅ **Use parametrization when**:

- Testing same logic with different inputs
- Validating boundary conditions (0, 1, max values)
- Testing multiple similar error cases
- Verifying behavior across scenarios

❌ **Don't parametrize when**:

- Tests have different logic
- Tests need different fixtures
- Tests verify completely different things
- It makes test harder to understand

---

## Test Quality Checklist

Before submitting/completing a test, verify:

### ✅ Structure & Organization

- [ ] Test has clear, descriptive name following convention
- [ ] Test function has docstring explaining purpose
- [ ] Test follows AAA pattern (Arrange, Act, Assert)
- [ ] Test is in correct file for its type
- [ ] Related tests are grouped together

### ✅ Test Data

- [ ] Using scenario from TESTDATA_CATALOG.md (not made-up data)
- [ ] Using correct fixture for test type (see FIXTURE_GUIDE.md)
- [ ] Using Phase 1 helpers (construct*entity_id, get*\*\_by_name, etc.)
- [ ] No hardcoded entity IDs or data values
- [ ] Test data is realistic and meaningful

### ✅ Test Behavior

- [ ] Test has clear assertions (doesn't just run code)
- [ ] Test verifies expected behavior, not implementation
- [ ] Test is focused (one thing per test)
- [ ] Test handles async properly (await, blocking=True)
- [ ] Test cleans up after itself (fixtures handle this usually)

### ✅ Error Handling

- [ ] Negative cases tested (invalid input, missing data)
- [ ] Uses pytest.raises for expected exceptions
- [ ] Error messages are checked (match="expected message")
- [ ] Validation errors use ServiceValidationError

### ✅ Maintainability

- [ ] Test will fail if behavior changes (not brittle)
- [ ] Test is independent (no reliance on other test order)
- [ ] Test is fast (uses minimal fixtures needed)
- [ ] Test is readable (another developer can understand)
- [ ] Comments explain "why", not "what"

### ✅ Documentation

- [ ] Test name clearly indicates what's being tested
- [ ] Docstring explains test purpose and scenario
- [ ] Complex logic has comments explaining approach
- [ ] References related tests if applicable

---

## Quick Reference: Test Type Selection

| I need to test...         | Test Type    | Fixture            | File                                |
| ------------------------- | ------------ | ------------------ | ----------------------------------- |
| UI flow navigation        | Config Flow  | `hass`             | `test_config_flow.py`               |
| Form validation           | Config Flow  | `hass`             | `test_config_flow.py`               |
| Service call behavior     | Service      | Scenario           | `test_services.py`                  |
| Service validation        | Service      | Scenario           | `test_services.py`                  |
| Entity state after action | Entity State | Scenario           | `test_sensor.py` / `test_button.py` |
| Entity attributes         | Entity State | Scenario           | `test_sensor.py`                    |
| Coordinator logic         | Coordinator  | `init_integration` | `test_coordinator.py`               |
| Data validation           | Coordinator  | `mock_coordinator` | `test_coordinator.py`               |
| Multi-step workflow       | Workflow     | Scenario           | `test_workflow_*.py`                |
| Complete user journey     | Workflow     | Scenario           | `test_workflow_*.py`                |
| Integration setup         | Integration  | `init_integration` | `test_init.py`                      |
| Platform loading          | Integration  | `init_integration` | `test_init.py`                      |

---

## Related Documentation

- **[TESTDATA_CATALOG.md](./TESTDATA_CATALOG.md)** - Find the right scenario for your test
- **[FIXTURE_GUIDE.md](./FIXTURE_GUIDE.md)** - Choose the right fixtures
- **[TESTING_AGENT_INSTRUCTIONS.md](./TESTING_AGENT_INSTRUCTIONS.md)** - Quick commands and setup
- **[TESTING_GUIDE.md](./TESTING_GUIDE.md)** - Comprehensive testing documentation

---

**Last Updated**: 2025-01-20
**Testing Standards Maturity Initiative**: Phase 3 Complete
**Next Phase**: Implementation and adoption across test suite
