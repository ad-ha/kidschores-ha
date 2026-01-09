# KidsChores Testing Fixture Guide

**Purpose**: Comprehensive reference for all pytest fixtures in `conftest.py` with dependency graphs, usage examples, selection criteria, and troubleshooting.

**Audience**: AI agents, developers creating/maintaining tests

**Related Documentation**:

- [TESTDATA_CATALOG.md](./TESTDATA_CATALOG.md) - Scenario data reference
- [TESTING_AGENT_INSTRUCTIONS.md](./TESTING_AGENT_INSTRUCTIONS.md) - Quick-start guide
- [TESTING_GUIDE.md](./TESTING_GUIDE.md) - Comprehensive testing documentation

---

## Quick Start

**Creating a new test? Follow this decision tree:**

```
Do you need entities to exist?
├─ NO → Use mock_config_entry + mock_coordinator (unit tests)
└─ YES → Need real coordinator?
    ├─ NO → Use mock_coordinator with create_mock_*_data() helpers
    └─ YES → Use init_integration, then:
        ├─ Empty data? → Use as-is (config flow tests)
        ├─ Simple data? → Use init_integration_with_data()
        └─ Realistic scenario? → Use scenario_minimal/medium/full
```

---

## Table of Contents

1. [Core Setup Fixtures](#core-setup-fixtures)
2. [Data Creation Helpers](#data-creation-helpers)
3. [Scenario Fixtures](#scenario-fixtures)
4. [Testing Helpers (Phase 1)](#testing-helpers-phase-1)
5. [Fixture Dependency Graph](#fixture-dependency-graph)
6. [Common Patterns](#common-patterns)
7. [Troubleshooting](#troubleshooting)

---

## Core Setup Fixtures

### `auto_enable_custom_integrations`

**Scope**: Function (autouse=True)
**Dependencies**: `enable_custom_integrations` (from pytest-homeassistant)
**Returns**: Pass-through of enable_custom_integrations

**Purpose**: Automatically enables custom integrations for all tests

**Usage**: No action required - applied automatically to every test

```python
# No explicit usage needed - autouse=True
async def test_something(hass):
    # Custom integrations already enabled
    pass
```

**Notes**:

- Applied to every test function automatically
- Enables loading of custom_components during tests
- Required for KidsChores integration to load

---

### `mock_hass_users`

**Scope**: Function
**Dependencies**: `hass` (Home Assistant instance)
**Returns**: `dict[str, Any]` - Dictionary mapping user IDs to user objects

**Purpose**: Creates mock Home Assistant users for parent authentication testing

**Structure**:

```python
{
    "parent1": User(id="parent1_id", name="Parent One"),
    "parent2": User(id="parent2_id", name="Parent Two"),
}
```

**Usage**:

```python
async def test_parent_authorization(hass, mock_hass_users):
    """Test that only authorized parents can approve chores."""
    parent1 = mock_hass_users["parent1"]

    # Use parent1.id in authorization checks
    context = Context(user_id=parent1.id)
    await hass.services.async_call(
        DOMAIN, "approve_chore",
        {"chore_id": "some_id"},
        context=context
    )
```

**When to Use**:

- ✅ Testing service calls with authorization
- ✅ Testing parent-only actions (approve, modify points)
- ✅ Scenario fixtures (automatically passed to apply_scenario_direct)
- ❌ Tests that don't check user permissions

**Notes**:

- User objects are created with Home Assistant's auth system
- User IDs are consistent: "parent1_id", "parent2_id"
- Scenarios link parents to these IDs via `ha_userid` in YAML

---

### `mock_config_entry`

**Scope**: Function
**Dependencies**: None
**Returns**: `MockConfigEntry`

**Purpose**: Creates a minimal config entry for KidsChores integration

**Structure**:

```python
MockConfigEntry(
    domain=DOMAIN,
    title="KidsChores",
    data={},  # Empty - data lives in .storage
    entry_id="test_entry_id",
    unique_id=None,
)
```

**Usage**:

```python
async def test_config_flow(hass, mock_config_entry):
    """Test configuration flow initialization."""
    mock_config_entry.add_to_hass(hass)

    # Now available via hass.config_entries
    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
```

**When to Use**:

- ✅ Config flow tests (before setup)
- ✅ Options flow tests
- ✅ Testing setup error handling
- ❌ Tests needing populated data (use init_integration instead)

**Notes**:

- Does NOT call async_setup_entry - integration not loaded
- Empty data dict - KidsChores v4.2+ stores data in .storage only
- Entry not added to hass automatically - call `.add_to_hass(hass)` first

---

### `mock_storage_data`

**Scope**: Function
**Dependencies**: None
**Returns**: `dict[str, dict]` - Empty storage structure

**Purpose**: Provides empty storage structure for testing initialization

**Structure**:

```python
{
    "kids": {},
    "parents": {},
    "chores": {},
    "rewards": {},
    "achievements": {},
    "challenges": {},
    "badges": {},
    "bonuses": {},
    "penalties": {},
}
```

**Usage**:

```python
def test_empty_storage_initialization(mock_storage_data):
    """Test that empty storage has correct structure."""
    assert "kids" in mock_storage_data
    assert "chores" in mock_storage_data
    assert len(mock_storage_data["kids"]) == 0
```

**When to Use**:

- ✅ Testing storage initialization logic
- ✅ Verifying empty state behavior
- ✅ Unit tests for storage manager
- ❌ Integration tests (use scenarios instead)

---

### `mock_storage_manager`

**Scope**: Function
**Dependencies**: `mock_storage_data`
**Returns**: `MagicMock` - Mocked KCStorageManager

**Purpose**: Provides a mocked storage manager for unit testing without real file I/O

**Methods Mocked**:

- `async_load()` → Returns mock_storage_data
- `async_save()` → No-op (doesn't write files)
- `get_data()` → Returns mock_storage_data
- `async_clear_kid_data()` → No-op

**Usage**:

```python
async def test_coordinator_load(hass, mock_storage_manager):
    """Test coordinator loads data from storage."""
    coordinator = KCDataCoordinator(hass, mock_storage_manager, mock_config_entry)

    await coordinator.async_load()

    # Verify load was called
    mock_storage_manager.async_load.assert_called_once()
```

**When to Use**:

- ✅ Unit testing coordinator logic
- ✅ Testing without filesystem access
- ✅ Fast tests that don't need persistence
- ❌ Integration tests verifying actual storage (use init_integration)

---

### `mock_coordinator`

**Scope**: Function
**Dependencies**: `mock_config_entry`, `mock_storage_manager`
**Returns**: `KCDataCoordinator` - Initialized coordinator with empty data

**Purpose**: Provides a real coordinator instance with mocked storage (no file I/O)

**Usage**:

```python
async def test_add_kid(mock_coordinator):
    """Test adding a kid to empty coordinator."""
    kid_id = await mock_coordinator.async_add_kid(
        name="Test Kid",
        age=8,
        interests=["testing"]
    )

    assert kid_id in mock_coordinator.kids_data
    assert mock_coordinator.kids_data[kid_id]["name"] == "Test Kid"
```

**When to Use**:

- ✅ Unit testing coordinator methods (add_kid, add_chore, etc.)
- ✅ Testing business logic without integration setup
- ✅ Fast isolated tests
- ❌ Tests needing entity platforms (use init_integration)

**Notes**:

- Real KCDataCoordinator instance, but storage is mocked
- No entities created (button, sensor platforms not loaded)
- No config entry setup in Home Assistant

---

### `init_integration`

**Scope**: Function (async)
**Dependencies**: `hass`, `mock_config_entry`
**Returns**: `MockConfigEntry` - Config entry after successful setup

**Purpose**: Fully sets up KidsChores integration with empty data - coordinator + all entity platforms loaded

**What It Does**:

1. Adds mock_config_entry to Home Assistant
2. Calls `async_setup_entry()` - loads integration
3. Waits for setup to complete
4. All entity platforms registered (button, sensor)
5. Coordinator initialized with empty storage

**Usage**:

```python
async def test_entity_platforms_loaded(hass, init_integration):
    """Test that all entity platforms are available."""
    # integration is fully loaded, but data is empty
    assert hass.states.async_entity_ids("button") == []
    assert hass.states.async_entity_ids("sensor") == []

    # Coordinator is accessible via hass.data
    from custom_components.kidschores.const import DATA_COORDINATOR
    coordinator = hass.data[DOMAIN][init_integration.entry_id][DATA_COORDINATOR]
    assert len(coordinator.kids_data) == 0  # Empty
```

**When to Use**:

- ✅ Config flow tests
- ✅ Options flow tests
- ✅ Testing integration initialization
- ✅ Base for scenario fixtures (scenario_minimal uses this)
- ❌ Tests needing populated data (add scenario fixture)

**Notes**:

- Integration fully loaded but coordinator has NO data
- Entity platforms registered but no entities created (empty data)
- Use with `apply_scenario_direct()` or scenario fixtures to add data

---

### `init_integration_with_data`

**Scope**: Function (async)
**Dependencies**: `hass`, `init_integration`
**Returns**: `tuple[MockConfigEntry, dict[str, str]]` - (config_entry, name_to_id_map)

**Purpose**: Sets up integration with 1 kid, 2 chores, 1 reward for simple tests

**Data Created**:

- 1 kid: "Test Kid" (age 8, 50 initial points)
- 2 chores: "Test Chore 1" (10pts), "Test Chore 2" (15pts)
- 1 reward: "Test Reward" (30pt cost)

**Usage**:

```python
async def test_claim_chore_workflow(hass, init_integration_with_data):
    """Test basic claim/approve workflow."""
    entry, name_map = init_integration_with_data

    # Entities exist with test data
    kid_id = name_map["Test Kid"]
    chore_id = name_map["Test Chore 1"]

    # Test claiming
    claim_button = f"button.kc_test_kid_claim_chore_test_chore_1"
    await hass.services.async_call("button", "press", {"entity_id": claim_button})
```

**When to Use**:

- ✅ Simple workflow tests (claim, approve, earn)
- ✅ Tests needing minimal realistic data
- ✅ Quick smoke tests
- ❌ Tests needing multiple kids (use scenario_medium)
- ❌ Tests needing badges/achievements (use scenario fixtures)

**Notes**:

- Reloads entity platforms to create button/sensor entities
- Returns name_to_id_map for easy lookups
- Good balance: more data than init_integration, simpler than scenarios

---

## Data Creation Helpers

### `create_mock_kid_data()`

**Type**: Function (not fixture)
**Dependencies**: None
**Returns**: `dict[str, Any]` - Kid data structure

**Purpose**: Creates a single kid's data dictionary for testing

**Signature**:

```python
def create_mock_kid_data(
    kid_id: str,
    name: str,
    age: int = 8,
    points: int = 0,
    lifetime_points: int = 0,
) -> dict[str, Any]:
```

**Usage**:

```python
def test_kid_data_structure(mock_coordinator):
    """Test coordinator handles kid data correctly."""
    kid_data = create_mock_kid_data(
        kid_id="kid123",
        name="Alex",
        age=10,
        points=100,
        lifetime_points=500
    )

    mock_coordinator.kids_data["kid123"] = kid_data

    assert mock_coordinator.kids_data["kid123"]["name"] == "Alex"
    assert mock_coordinator.kids_data["kid123"]["points"] == 100
```

**When to Use**:

- ✅ Unit tests needing custom kid data
- ✅ Testing coordinator methods with specific values
- ✅ Building custom test scenarios
- ❌ Integration tests (use scenarios)

**Structure Created**:

```python
{
    "internal_id": kid_id,
    "name": name,
    "age": age,
    "interests": [],
    "avatar": None,
    "points": points,
    "lifetime_points": lifetime_points,
    "chores_completed": [],
    "badges_earned": {},
    "rewards_claimed": [],
}
```

---

### `create_mock_chore_data()`

**Type**: Function (not fixture)
**Dependencies**: None
**Returns**: `dict[str, Any]` - Chore data structure

**Signature**:

```python
def create_mock_chore_data(
    chore_id: str,
    name: str,
    assigned_to: list[str],
    points: int = 10,
    chore_type: str = "daily",
) -> dict[str, Any]:
```

**Usage**:

```python
def test_chore_assignment(mock_coordinator):
    """Test chore assignment to multiple kids."""
    kid1_id = "kid1"
    kid2_id = "kid2"

    chore_data = create_mock_chore_data(
        chore_id="chore123",
        name="Shared Cleanup",
        assigned_to=[kid1_id, kid2_id],
        points=20,
        chore_type="daily"
    )

    mock_coordinator.chores_data["chore123"] = chore_data

    assert len(chore_data["assigned_to"]) == 2
    assert chore_type == "daily"
```

**When to Use**:

- ✅ Testing chore logic with specific types
- ✅ Shared chore tests
- ✅ Custom claim/approve scenarios
- ❌ Realistic workflow tests (use scenarios)

**Structure Created**:

```python
{
    "internal_id": chore_id,
    "name": name,
    "description": "",
    "points": points,
    "chore_type": chore_type,  # "daily", "weekly", "periodic"
    "assigned_to": assigned_to,
    "icon": "mdi:clipboard-check",
    "claims": {},
    "completion_history": [],
}
```

---

### `create_mock_reward_data()`

**Type**: Function (not fixture)
**Dependencies**: None
**Returns**: `dict[str, Any]` - Reward data structure

**Signature**:

```python
def create_mock_reward_data(
    reward_id: str,
    name: str,
    cost: int = 50,
) -> dict[str, Any]:
```

**Usage**:

```python
def test_reward_claiming(mock_coordinator):
    """Test reward claim validation."""
    reward_data = create_mock_reward_data(
        reward_id="reward123",
        name="Movie Night",
        cost=100
    )

    mock_coordinator.rewards_data["reward123"] = reward_data

    # Test insufficient points
    kid_data = create_mock_kid_data("kid1", "Alex", points=50)
    assert kid_data["points"] < reward_data["cost"]
```

**When to Use**:

- ✅ Testing reward purchase logic
- ✅ Points validation tests
- ✅ Custom reward scenarios
- ❌ Multi-reward tests (use scenarios)

**Structure Created**:

```python
{
    "internal_id": reward_id,
    "name": name,
    "description": "",
    "cost": cost,
    "icon": "mdi:star",
    "claims": {},
}
```

---

## Scenario Fixtures

**See [TESTDATA_CATALOG.md](./TESTDATA_CATALOG.md) for complete entity listings**

### `scenario_minimal`

**Scope**: Function (async)
**Dependencies**: `hass`, `init_integration`, `mock_hass_users`
**Returns**: `tuple[MockConfigEntry, dict[str, str]]`

**Purpose**: Simplest realistic scenario - 1 kid, 2 chores, basic features

**Scenario Contents**:

- 1 parent: Môm Astrid (linked to parent1 mock user)
- 1 kid: Zoë (10 points, 10 lifetime)
- 2 chores: "Feed the cåts", "Wåter the plänts"
- 1 badge: "Brønze Står"
- 1 bonus: "Stär Sprïnkle Bonus"
- 1 penalty: "Førget Chöre"
- 1 reward: "Ice Créam!"

**Usage**:

```python
async def test_basic_claim_approve(hass, scenario_minimal):
    """Test claim and approve workflow with realistic data."""
    entry, name_map = scenario_minimal

    # Get kid and chore IDs from scenario
    zoe_id = name_map["Zoë"]
    feed_cats_id = name_map["Feed the cåts"]

    # Claim chore
    claim_button = f"button.kc_zoe_claim_chore_feed_the_cats"
    await hass.services.async_call("button", "press", {"entity_id": claim_button})

    # Verify claim registered
    coordinator = get_coordinator(hass, entry)
    assert feed_cats_id in coordinator.chores_data[feed_cats_id]["claims"]
```

**When to Use**:

- ✅ Basic workflow tests (claim, approve, complete)
- ✅ Single-kid dashboard tests
- ✅ Simple point tracking
- ✅ Config flow with data tests
- ❌ Multi-kid coordination (use scenario_medium)
- ❌ Badge maintenance (use scenario_full)

**Files Using This**: `test_calendar_scenarios.py` (6 tests)

---

### `scenario_medium`

**Scope**: Function (async)
**Dependencies**: `hass`, `init_integration`
**Returns**: `tuple[MockConfigEntry, dict[str, str]]`

**Purpose**: Multi-kid scenario with shared chores and badge progression

**Scenario Contents**:

- 2 parents: Môm Astrid, Dad Leo
- 2 kids: Zoë (35 points, 350 lifetime), Max! (15 points, 180 lifetime)
- 4 chores: Including shared "Stär sweep"
- 6 badges: Bronze/Silver/Gold, Weekly Wizard, Daily Delight, Special Occasion
- 2 bonuses, 2 penalties, 2 rewards

**Usage**:

```python
async def test_shared_chore_multi_claim(hass, scenario_medium):
    """Test that shared chores allow multiple claims."""
    entry, name_map = scenario_medium

    # Both kids can claim "Stär sweep"
    zoe_id = name_map["Zoë"]
    max_id = name_map["Max!"]
    sweep_id = name_map["Stär sweep"]

    # Zoë claims
    await hass.services.async_call(
        "button", "press",
        {"entity_id": "button.kc_zoe_claim_chore_star_sweep"}
    )

    # Max claims (should succeed - shared chore)
    await hass.services.async_call(
        "button", "press",
        {"entity_id": "button.kc_max_claim_chore_star_sweep"}
    )

    # Verify both claims exist
    coordinator = get_coordinator(hass, entry)
    claims = coordinator.chores_data[sweep_id]["claims"]
    assert zoe_id in claims
    assert max_id in claims
```

**When to Use**:

- ✅ Multi-kid coordination tests
- ✅ Shared chore workflows
- ✅ Badge assignment and maintenance
- ✅ Special occasion badge testing (Dec 21 badge)
- ❌ Single-kid tests (use scenario_minimal)
- ✅ Stress testing (use `scenario_stress` fixture)

**Files Using This**: `test_badge_assignment_baseline.py`, `test_badge_creation.py`

---

### `scenario_full`

**Scope**: Function (async)
**Dependencies**: `hass`, `init_integration`
**Returns**: `tuple[MockConfigEntry, dict[str, str]]`

**Purpose**: Complete feature coverage - 3 kids, all entity types, badge maintenance

**Scenario Contents**:

- 2 parents: Môm Astrid, Dad Leo
- 3 kids: Zoë (520 lifetime), Max! (280 lifetime), Lila (310 lifetime)
- 7 chores: Mix of daily, weekly, periodic, shared
- 5 badges: Multiple cumulative badges with multipliers
- 2 bonuses, 3 penalties, 5 rewards (40-300pt range)

**Usage**:

```python
async def test_badge_maintenance_tracking(hass, scenario_full):
    """Test badge maintenance period tracking."""
    entry, name_map = scenario_full

    # Zoë has earned Bronze Står - check maintenance
    zoe_id = name_map["Zoë"]
    bronze_badge_id = name_map["Brønze Står"]

    coordinator = get_coordinator(hass, entry)
    badges_earned = coordinator.kids_data[zoe_id]["badges_earned"]

    assert bronze_badge_id in badges_earned
    assert "last_awarded_date" in badges_earned[bronze_badge_id]
    assert "periods" in badges_earned[bronze_badge_id]
```

**When to Use**:

- ✅ Badge maintenance testing
- ✅ Complex workflow tests
- ✅ Performance testing (3 kids is moderate load)
- ✅ Complete feature coverage
- ❌ Simple tests (use scenario_minimal)
- ✅ Extreme stress testing (use `scenario_stress` fixture)

**Notes**:

- Identical to `scenario_full` fixture (canonical baseline)
- Use `scenario_full` when semantic name is clearer
- Use `scenario_full` fixture when needing "The Stârblüm Family" theme

---

## Testing Helpers (Phase 1)

**Added**: 2025-01-20 (Testing Standards Maturity Initiative)
**Purpose**: Reduce boilerplate, eliminate hardcoded values, standardize patterns

### `construct_entity_id()`

**Type**: Function
**Returns**: `str` - Formatted entity ID

**Purpose**: Construct entity IDs matching integration's slugification logic

**Signature**:

```python
def construct_entity_id(domain: str, kid_name: str, entity_type: str) -> str
```

**Usage**:

```python
# BEFORE (hardcoded, error-prone)
points_sensor = "sensor.kc_zoe_points"  # Wrong if Zoë's name changes!

# AFTER (helper - adapts to data)
points_sensor = construct_entity_id("sensor", "Zoë", "points")
# Returns: "sensor.kc_zoe_points"

# Works with spaces and special characters
entity_id = construct_entity_id("sensor", "Sarah Jane", "lifetime_points")
# Returns: "sensor.kc_sarah_jane_lifetime_points"
```

**When to Use**:

- ✅ All entity ID construction in tests
- ✅ Button entity lookups
- ✅ Sensor entity lookups
- ❌ Never hardcode entity IDs

---

### `assert_entity_state()`

**Type**: Async function
**Returns**: Entity state object

**Purpose**: One-line entity state and attribute verification

**Signature**:

```python
async def assert_entity_state(
    hass: HomeAssistant,
    entity_id: str,
    expected_state: str,
    expected_attrs: dict[str, Any] | None = None,
) -> Any
```

**Usage**:

```python
# BEFORE (verbose, multi-line)
state = hass.states.get(entity_id)
assert state is not None
assert state.state == "50"
assert state.attributes.get("lifetime_points") == 100

# AFTER (helper - concise, clear intent)
await assert_entity_state(
    hass,
    "sensor.kc_zoe_points",
    expected_state="50",
    expected_attrs={"lifetime_points": 100}
)
```

**When to Use**:

- ✅ Verifying sensor states
- ✅ Checking entity attributes
- ✅ Post-action state validation
- ❌ When you need the full state object for further processing

**Raises**: `AssertionError` with descriptive message if verification fails

---

### `get_kid_by_name()`

**Type**: Function
**Returns**: `dict[str, Any]` - Kid data dictionary

**Purpose**: Name-based kid lookup from coordinator data

**Signature**:

```python
def get_kid_by_name(data: dict[str, Any], name: str) -> dict[str, Any]
```

**Usage**:

```python
# BEFORE (manual search, name_to_id_map dependency)
kid_id = name_to_id_map["Zoë"]
kid_data = coordinator.kids_data[kid_id]

# AFTER (helper - direct name lookup)
kid_data = get_kid_by_name(coordinator.kids_data, "Zoë")
kid_id = kid_data["internal_id"]
assert kid_data["name"] == "Zoë"
```

**When to Use**:

- ✅ Looking up kids by display name
- ✅ Tests using scenario data
- ✅ When name_to_id_map isn't available
- ❌ When you already have the kid_id

**Raises**: `KeyError` if kid name not found

---

### `get_chore_by_name()`

**Type**: Function
**Returns**: `dict[str, Any]` - Chore data dictionary

**Purpose**: Name-based chore lookup, optionally scoped to specific kid

**Signature**:

```python
def get_chore_by_name(
    data: dict[str, Any],
    chore_name: str,
    kid_name: str | None = None,
) -> dict[str, Any]
```

**Usage**:

```python
# Find any chore by name
chore_data = get_chore_by_name(coordinator.chores_data, "Feed the cåts")

# Find chore assigned to specific kid (disambiguation)
chore_data = get_chore_by_name(
    coordinator.chores_data,
    "Clean room",  # Multiple kids might have this
    kid_name="Zoë"  # Get Zoë's version
)

chore_id = chore_data["internal_id"]
```

**When to Use**:

- ✅ Looking up chores by display name
- ✅ Verifying chore assignment
- ✅ Tests with multiple similar chore names
- ❌ When you already have the chore_id

**Raises**: `KeyError` if chore not found

---

### `get_reward_by_name()`

**Type**: Function
**Returns**: `dict[str, Any]` - Reward data dictionary

**Purpose**: Name-based reward lookup

**Signature**:

```python
def get_reward_by_name(
    data: dict[str, Any],
    reward_name: str,
    kid_name: str | None = None,
) -> dict[str, Any]
```

**Usage**:

```python
# Find reward by name
reward_data = get_reward_by_name(coordinator.rewards_data, "Ice Créam!")
reward_id = reward_data["internal_id"]
cost = reward_data["cost"]

assert cost == 60
```

**When to Use**:

- ✅ Looking up rewards by display name
- ✅ Verifying reward costs
- ✅ Testing claim validation
- ❌ When you already have the reward_id

**Raises**: `KeyError` if reward not found

---

### `create_test_datetime()`

**Type**: Function
**Returns**: `str` - UTC ISO datetime string

**Purpose**: Clean datetime creation with offset support

**Signature**:

```python
def create_test_datetime(days_offset: int = 0, hours_offset: int = 0) -> str
```

**Usage**:

```python
# BEFORE (verbose datetime manipulation)
from datetime import datetime, timedelta, timezone
now = datetime.now(timezone.utc)
future = now + timedelta(days=7, hours=3)
future_str = future.isoformat()

# AFTER (helper - clean and clear)
future_datetime = create_test_datetime(days_offset=7, hours_offset=3)

# Common patterns
now = create_test_datetime()  # Current time UTC
yesterday = create_test_datetime(days_offset=-1)
next_week = create_test_datetime(days_offset=7)
```

**When to Use**:

- ✅ Creating test timestamps
- ✅ Future/past date calculations
- ✅ Chore due date testing
- ❌ When you need complex datetime manipulation

**Returns**: Always UTC-aware ISO format string

---

### `make_overdue()`

**Type**: Function
**Returns**: `str` - UTC ISO datetime string in the past

**Purpose**: Calculate overdue dates for testing

**Signature**:

```python
def make_overdue(base_date: str | None = None, days: int = 7) -> str
```

**Usage**:

```python
# Make chore overdue by 7 days (default)
overdue_date = make_overdue()

# Make overdue by specific number of days
overdue_date = make_overdue(days=3)

# Make specific date overdue
base = create_test_datetime()
overdue_date = make_overdue(base_date=base, days=5)

# Use in chore data
chore_data["due_date"] = make_overdue(days=2)  # 2 days overdue
```

**When to Use**:

- ✅ Testing overdue chore logic
- ✅ Calendar event testing
- ✅ Notification testing
- ❌ Future dates (use create_test_datetime instead)

---

## Fixture Dependency Graph

```
Foundational Layer (No dependencies):
├── auto_enable_custom_integrations
├── mock_storage_data
└── mock_config_entry

↓

Storage/Mock Layer:
├── mock_storage_manager ──→ mock_storage_data
└── mock_coordinator ──→ mock_config_entry, mock_storage_manager

↓

Integration Setup Layer:
├── mock_hass_users ──→ hass
└── init_integration ──→ hass, mock_config_entry

↓

Data Population Layer:
├── init_integration_with_data ──→ hass, init_integration
├── scenario_minimal ──→ hass, init_integration, mock_hass_users
├── scenario_medium ──→ hass, init_integration
└── scenario_full ──→ hass, init_integration

Helper Functions (used by all layers):
├── create_mock_kid_data()
├── create_mock_chore_data()
├── create_mock_reward_data()
├── load_scenario_yaml()
├── apply_scenario_direct()
├── reload_entity_platforms()
├── get_button_entity_id()
│
└── Phase 1 Helpers (Testing Standards Maturity Initiative):
    ├── construct_entity_id()
    ├── assert_entity_state()
    ├── get_kid_by_name()
    ├── get_chore_by_name()
    ├── get_reward_by_name()
    ├── create_test_datetime()
    └── make_overdue()
```

---

## Common Patterns

### Pattern 1: Config Flow Test (Empty Data)

```python
async def test_config_flow_init(hass, mock_config_entry):
    """Test config flow initialization."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
```

**Uses**: `mock_config_entry`
**Why**: Config flow needs entry before setup, no data needed

---

### Pattern 2: Simple Workflow Test (Minimal Data)

```python
async def test_claim_approve_workflow(hass, init_integration_with_data):
    """Test basic claim and approve flow."""
    entry, name_map = init_integration_with_data

    kid_id = name_map["Test Kid"]
    chore_id = name_map["Test Chore 1"]

    # Claim chore
    claim_button = construct_entity_id("button", "Test Kid", "claim_chore_test_chore_1")
    await hass.services.async_call("button", "press", {"entity_id": claim_button})

    # Verify claim
    coordinator = get_coordinator(hass, entry)
    chore_data = coordinator.chores_data[chore_id]
    assert kid_id in chore_data["claims"]
```

**Uses**: `init_integration_with_data`, `construct_entity_id()`
**Why**: Need working entities but simple data sufficient

---

### Pattern 3: Multi-Kid Test (Realistic Scenario)

```python
async def test_shared_chore_coordination(hass, scenario_medium):
    """Test shared chores with multiple kids."""
    entry, name_map = scenario_medium

    # Use helper to get kid data by name
    coordinator = get_coordinator(hass, entry)
    zoe_data = get_kid_by_name(coordinator.kids_data, "Zoë")
    max_data = get_kid_by_name(coordinator.kids_data, "Max!")

    # Get shared chore
    sweep_data = get_chore_by_name(coordinator.chores_data, "Stär sweep")

    # Both kids should be assigned
    assert zoe_data["internal_id"] in sweep_data["assigned_to"]
    assert max_data["internal_id"] in sweep_data["assigned_to"]
```

**Uses**: `scenario_medium`, `get_kid_by_name()`, `get_chore_by_name()`
**Why**: Testing multi-kid coordination needs realistic scenario

---

### Pattern 4: Badge Maintenance Test (Complete Data)

```python
async def test_badge_maintenance_tracking(hass, scenario_full):
    """Test badge maintenance period tracking."""
    entry, name_map = scenario_full

    # Use helpers for lookups
    coordinator = get_coordinator(hass, entry)
    zoe_data = get_kid_by_name(coordinator.kids_data, "Zoë")
    badge_data = coordinator.badges_data[name_map["Brønze Står"]]

    # Check maintenance rules
    assert badge_data.get("maintenance_daily") is not None

    # Verify Zoë has earned it
    assert name_map["Brønze Står"] in zoe_data["badges_earned"]
```

**Uses**: `scenario_full`, Phase 1 helpers
**Why**: Badge maintenance needs complete feature coverage

---

### Pattern 5: Unit Test (Mocked Storage)

```python
async def test_add_kid_logic(mock_coordinator):
    """Test coordinator kid addition logic."""
    kid_id = await mock_coordinator.async_add_kid(
        name="Test Kid",
        age=10,
        interests=["reading"]
    )

    assert kid_id in mock_coordinator.kids_data
    assert mock_coordinator.kids_data[kid_id]["name"] == "Test Kid"
    assert mock_coordinator.kids_data[kid_id]["points"] == 0
```

**Uses**: `mock_coordinator`
**Why**: Unit test doesn't need full integration, just coordinator logic

---

### Pattern 6: Custom Data Test (Data Builders)

```python
def test_chore_points_calculation(mock_coordinator):
    """Test points calculation with custom data."""
    kid_data = create_mock_kid_data("kid1", "Alex", points=50)
    chore_data = create_mock_chore_data(
        "chore1", "Test Chore",
        assigned_to=["kid1"],
        points=25
    )

    mock_coordinator.kids_data["kid1"] = kid_data
    mock_coordinator.chores_data["chore1"] = chore_data

    # Test points logic
    expected_new_points = kid_data["points"] + chore_data["points"]
    assert expected_new_points == 75
```

**Uses**: `mock_coordinator`, `create_mock_kid_data()`, `create_mock_chore_data()`
**Why**: Need specific data values not in scenarios

---

## Troubleshooting

### Issue: "Config entry not found"

**Symptoms**:

```python
KeyError: 'test_entry_id' in hass.data[DOMAIN]
```

**Cause**: Using fixture that doesn't call `async_setup_entry()`

**Solution**: Use `init_integration` or higher, not `mock_config_entry` alone

```python
# ❌ WRONG - entry not set up
async def test_something(hass, mock_config_entry):
    coordinator = hass.data[DOMAIN][mock_config_entry.entry_id]  # KeyError!

# ✅ CORRECT - entry fully set up
async def test_something(hass, init_integration):
    coordinator = hass.data[DOMAIN][init_integration.entry_id]  # Works!
```

---

### Issue: "Entity not found"

**Symptoms**:

```python
assert hass.states.get("button.kc_zoe_claim_chore_feed_cats") is None
```

**Cause**: Using fixture with empty data or not reloading platforms

**Solution**: Use scenario fixture or call `reload_entity_platforms()`

```python
# ❌ WRONG - init_integration has no data, no entities created
async def test_entities(hass, init_integration):
    state = hass.states.get("button.kc_zoe_claim_chore_feed_cats")
    assert state is not None  # Fails! No data = no entities

# ✅ CORRECT - scenario has data and reloads platforms
async def test_entities(hass, scenario_minimal):
    state = hass.states.get("button.kc_zoe_claim_chore_feed_the_cats")
    assert state is not None  # Works! Entities exist
```

---

### Issue: "Name not found in name_to_id_map"

**Symptoms**:

```python
KeyError: 'Zoë' in name_to_id_map
```

**Cause**: Scenario doesn't have that kid, or using wrong fixture

**Solution**: Check scenario contents in [TESTDATA_CATALOG.md](./TESTDATA_CATALOG.md)

```python
# ❌ WRONG - scenario_minimal only has Zoë
async def test_max(hass, scenario_minimal):
    entry, name_map = scenario_minimal
    max_id = name_map["Max!"]  # KeyError! Max not in minimal

# ✅ CORRECT - scenario_medium has Max!
async def test_max(hass, scenario_medium):
    entry, name_map = scenario_medium
    max_id = name_map["Max!"]  # Works! Max exists in medium
```

---

### Issue: "Data structure is dict, not list"

**Symptoms**:

```python
TypeError: 'dict' object is not subscriptable
```

**Cause**: Trying to iterate dict without `.values()`

**Solution**: All storage dicts use UUID keys - iterate with `.values()`

```python
# ❌ WRONG - can't iterate dict keys directly
for kid in coordinator.kids_data:
    print(kid["name"])  # kid is UUID string, not dict!

# ✅ CORRECT - iterate dict values
for kid_data in coordinator.kids_data.values():
    print(kid_data["name"])  # kid_data is the dict

# ✅ ALSO CORRECT - use Phase 1 helpers
kid_data = get_kid_by_name(coordinator.kids_data, "Zoë")
```

---

### Issue: "Fixture not found"

**Symptoms**:

```python
fixture 'scenario_full' provides identical data
```

**Cause**: Using wrong scenario name

**Solution**: Only 3 scenario fixtures exist: `scenario_minimal`, `scenario_medium`, `scenario_full`

```python
# ❌ WRONG - storyline is a YAML file reference, not a fixture
async def test_something(hass, scenario_storyline):
    pass

# ✅ CORRECT - use scenario_full fixture (provides identical Stârblüm family data)
async def test_something(hass, scenario_full):
    pass
```

**Available Scenario Fixtures**:

- `scenario_minimal` - 1 kid, 2 chores
- `scenario_medium` - 2 kids, 4 chores, shared chores
- `scenario_full` - 3 kids, 7 chores, all features

**YAML Files** (use with `load_scenario_yaml()`, not as fixtures):

- `testdata_scenario_minimal.yaml`
- `testdata_scenario_medium.yaml`
- `testdata_scenario_full.yaml`
- `testdata_scenario_minimal.yaml` → `scenario_minimal` fixture
- `testdata_scenario_medium.yaml` → `scenario_medium` fixture
- `testdata_scenario_full.yaml` → `scenario_full` fixture (Stârblüm family reference)
- `testdata_scenario_performance_stress.yaml` → `scenario_stress` fixture (100 kids, 500+ chores)

---

### Issue: "Storage not persisted"

**Symptoms**: Changes disappear after coordinator reload

**Cause**: Using `mock_storage_manager` which doesn't persist

**Solution**: Use `init_integration` for real storage, or accept mock behavior

```python
# ❌ Mock storage - changes not persisted
async def test_persistence(hass, mock_coordinator):
    await mock_coordinator.async_add_kid("Test", 8, [])
    # Changes won't survive reload - mock storage!

# ✅ Real storage - changes persisted
async def test_persistence(hass, init_integration):
    coordinator = get_coordinator(hass, init_integration)
    await coordinator.async_add_kid("Test", 8, [])
    # Changes persisted to .storage/kidschores_data
```

---

### Issue: "Helper function returns wrong data"

**Symptoms**: `get_kid_by_name()` raises KeyError for existing kid

**Cause**: Kid name doesn't match exactly (case, spacing, special chars)

**Solution**: Use exact name from scenario YAML

```python
# ❌ WRONG - name doesn't match YAML exactly
kid_data = get_kid_by_name(coordinator.kids_data, "Zoe")  # KeyError!
# Scenario has "Zoë" with umlaut, not "Zoe"

# ✅ CORRECT - exact match including special chars
kid_data = get_kid_by_name(coordinator.kids_data, "Zoë")  # Works!

# ✅ ALSO CORRECT - use name_to_id_map from fixture
entry, name_map = scenario_minimal
zoe_id = name_map["Zoë"]  # Guaranteed correct
```

---

## Quick Reference: Fixture Selection Matrix

| Test Type                     | Need Entities? | Data Complexity | Recommended Fixture               |
| ----------------------------- | -------------- | --------------- | --------------------------------- |
| Config flow                   | No             | None            | `mock_config_entry`               |
| Options flow                  | No             | None            | `mock_config_entry`               |
| Unit test (coordinator logic) | No             | Custom          | `mock_coordinator` + data helpers |
| Simple workflow               | Yes            | Minimal         | `init_integration_with_data`      |
| Single-kid tests              | Yes            | Realistic       | `scenario_minimal`                |
| Multi-kid coordination        | Yes            | Realistic       | `scenario_medium`                 |
| Badge maintenance             | Yes            | Complete        | `scenario_full`                   |
| Shared chores                 | Yes            | Realistic       | `scenario_medium`                 |
| Performance testing           | Yes            | Realistic       | `scenario_full`                   |
| Stress testing                | Yes            | Extreme         | Use `scenario_stress` fixture     |

---

## Related Documentation

- [TESTDATA_CATALOG.md](./TESTDATA_CATALOG.md) - Complete scenario entity listings
- [TESTING_AGENT_INSTRUCTIONS.md](./TESTING_AGENT_INSTRUCTIONS.md) - Quick-start guide
- [TESTING_GUIDE.md](./TESTING_GUIDE.md) - Comprehensive testing documentation
- [TEST_CREATION_TEMPLATE.md](./TEST_CREATION_TEMPLATE.md) - Step-by-step templates (Phase 3)

---

**Last Updated**: 2025-01-20
**Testing Standards Maturity Initiative**: Phase 2 Complete
**Next Phase**: TEST_CREATION_TEMPLATE.md (step-by-step templates for all test types)
