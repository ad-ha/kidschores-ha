# KidsChores Testing - Technical Guide

Comprehensive technical documentation for testing the KidsChores Home Assistant integration.

## Table of Contents

- [Quick Start](#quick-start)
- [Test Organization](#test-organization)
- [Data Loading Methods](#data-loading-methods)
- [Test Categories](#test-categories)
- [Migration Testing](#migration-testing)
- [Dashboard Template Testing](#dashboard-template-testing)
- [Test Fixtures](#test-fixtures)
- [Testing Patterns](#testing-patterns)
- [Debugging](#debugging)
- [Best Practices](#best-practices)

---

## Quick Start

```bash
# Run all tests
cd /workspaces/kidschores-ha
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_workflow_parent_actions.py -v

# Run with coverage
python -m pytest tests/ --cov=custom_components.kidschores --cov-report=term-missing

# Run single test
python -m pytest tests/test_config_flow.py::test_form_user_flow -v
```

---

## Test Organization

### File Structure

```
tests/
├── conftest.py                          # pytest fixtures and configuration
├── test_config_flow.py                 # Initial setup tests (8 tests)
├── test_coordinator.py                 # Business logic tests (12 tests)
├── test_options_flow.py                # Entity management tests (9 tests)
├── test_options_flow_comprehensive.py  # Detailed options tests
├── test_services.py                    # Service call tests (5 tests)
├── test_dashboard_templates.py         # Jinja template tests (17 tests)
├── test_workflow_kid_chores.py         # Kid chore workflow tests (11 tests)
├── test_workflow_parent_actions.py     # Parent penalty/bonus tests (11 tests)
├── test_workflow_kid_rewards.py        # Kid reward workflow tests (10 tests)
├── test_migration_generic.py           # Generic v40→v42 migration tests (9 tests)
├── test_migration_samples_validation.py # Multi-version migration validation (30 tests)
├── testdata_scenario_minimal.yaml      # Minimal test scenario
├── testdata_scenario_medium.yaml       # Medium test scenario
├── testdata_scenario_full.yaml         # Full test scenario
├── migration_samples/                  # Production data samples
│   └── kidschores_data_ad-ha           # Real-world v40 production data
├── README.md                           # High-level overview
├── TESTING_TECHNICAL_GUIDE.md          # This file
└── TESTING_AGENT_INSTRUCTIONS.md       # AI agent guidance
```

### Test Count Summary

**Total: 117 tests (109 passing, 17 intentionally skipped)**

| Category              | Tests  | Status                   |
| --------------------- | ------ | ------------------------ |
| Config Flow           | 8      | ✅ All passing           |
| Coordinator           | 12     | ✅ All passing           |
| Options Flow          | 9      | ✅ All passing           |
| Services              | 5      | ✅ All passing           |
| Dashboard Templates   | 17     | ✅ All passing           |
| Kid Chore Workflow    | 11     | ✅ All passing           |
| Parent Actions        | 11     | ✅ All passing           |
| Kid Reward Workflow   | 10     | ✅ All passing           |
| **Migration Testing** | **39** | ✅ **All passing** (NEW) |
| **Skipped**           | **17** | ⏭️ Intentionally skipped |

**Skipped tests** require live Home Assistant instance or external dependencies (notification services, etc.)

**New in v4.2**: Migration testing validates v40→v42 schema upgrades. See [Migration Testing](#migration-testing) section below.

---

## Data Loading Methods

### CRITICAL DISTINCTION

The integration supports two methods for loading test data:

### Method 1: Options Flow (User Workflow)

**When to use**: Testing user interactions, UI workflows, validation logic

**How it works**: Simulates user adding/editing entities through Home Assistant UI

**Pattern**:

```python
async def test_via_options_flow(hass, config_entry):
    """Add entity via options flow (simulates user UI interaction)."""
    # Initialize options flow
    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    # Navigate to add kid step
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"next_step": "add_kid"}
    )

    # Submit kid data
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "name": "Zoë Stårblüm",
            "age": 8,
            "avatar": "mdi:star-face"
        }
    )

    # Data now in coordinator
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
    assert len(coordinator.kids_data) == 1
```

**What gets tested**:

- Input validation (age limits, name uniqueness, etc.)
- Schema compliance
- Error handling
- Storage persistence
- Entity registry updates

**Use for**:

- `test_options_flow.py` tests
- `test_config_flow.py` tests
- Tests validating user input handling

### Method 2: Direct Coordinator Loading (Scenario Data)

**When to use**: Testing business logic, workflows, state transitions

**How it works**: Directly loads pre-built scenario data into coordinator, bypassing UI

**Pattern**:

```python
async def test_via_coordinator(hass, scenario_minimal):
    """Load entities via coordinator (simulates pre-configured system)."""
    config_entry, name_to_id_map = scenario_minimal
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Entities already loaded from YAML scenario
    zoe_id = name_to_id_map["kid:Zoë"]
    chore_id = name_to_id_map["chore:Feed the cåts"]

    # Test business logic
    coordinator.claim_chore("Zoë", chore_id)
    assert coordinator.kids_data[zoe_id]["chores_claimed"][chore_id] is not None
```

**How scenario loading works**:

```python
# conftest.py
async def apply_scenario_direct(hass, config_entry, scenario_data, mock_users=None):
    """Load scenario data directly into coordinator storage."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Parse YAML scenario
    family = scenario_data.get("family", {})

    # Add parents directly to coordinator.parents_data
    for parent in family.get("parents", []):
        parent_id = str(uuid.uuid4())
        coordinator.parents_data[parent_id] = {
            "name": parent["name"],
            "ha_user_id": parent.get("ha_user_id", ""),
            # ... other fields
        }

    # Add kids directly to coordinator.kids_data
    for kid in family.get("kids", []):
        kid_id = str(uuid.uuid4())
        coordinator.kids_data[kid_id] = {
            "name": kid["name"],
            "age": kid["age"],
            "points": kid.get("points", 0),
            # ... other fields
        }

    # Add chores, badges, rewards, etc. to their respective coordinator dicts

    # Save to storage
    await coordinator.storage_manager.save_data()

    # Reload entity platforms to create entities from new data
    await reload_entity_platforms(hass, config_entry)
```

**What gets tested**:

- State transitions (pending → claimed → approved)
- Point calculations
- Badge awards
- Recurring chore resets
- Notification triggers
- Workflow completions

**Use for**:

- `test_workflow_*.py` tests
- `test_coordinator.py` tests
- `test_services.py` tests
- Tests validating business logic

### Comparison Table

| Aspect              | Options Flow                   | Direct Coordinator Loading              |
| ------------------- | ------------------------------ | --------------------------------------- |
| **Simulates**       | User UI interaction            | Pre-configured system                   |
| **Speed**           | Slower (async flow navigation) | Faster (direct data insertion)          |
| **Validates**       | Input validation, UI flows     | Business logic, state transitions       |
| **Entity Creation** | Automatic via options flow     | Manual via platform reload              |
| **Storage**         | Saved via flow completion      | Saved via `storage_manager.save_data()` |
| **Use Case**        | Testing user experience        | Testing integration functionality       |

### When to Use Each Method

**Use Options Flow when**:

- Testing config/options flow UI
- Validating user input
- Testing error handling in forms
- Verifying entity registry updates
- Testing duplicate detection

**Use Direct Loading when**:

- Testing chore claim/approve workflows
- Testing penalty/bonus application
- Testing reward redemption flows
- Testing recurring chore resets
- Testing badge maintenance
- Testing bulk operations

---

## Test Categories

### 1. Config Flow Tests (`test_config_flow.py`)

**Purpose**: Test initial integration setup

**Data Loading**: Options flow (simulates first-time setup)

**Key Tests**:

- `test_form_user_flow`: Complete setup wizard
- `test_form_duplicate`: Prevent duplicate integrations
- `test_form_import`: YAML configuration import

**Pattern**:

```python
async def test_form_user_flow(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={"integration_name": "KidsChores"}
    )
    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
```

### 2. Options Flow Tests (`test_options_flow.py`)

**Purpose**: Test entity management through UI

**Data Loading**: Options flow (simulates user adding/editing entities)

**Key Tests**:

- `test_options_add_kid`: Add kid via UI form
- `test_options_edit_chore`: Edit chore properties
- `test_options_delete_reward`: Delete reward with validation

**Pattern**:

```python
async def test_options_add_kid(hass, config_entry):
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"next_step": "add_kid"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"name": "Zoë", "age": 8}
    )
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
    assert len(coordinator.kids_data) == 1
```

### 3. Coordinator Tests (`test_coordinator.py`)

**Purpose**: Test business logic and state management

**Data Loading**: Direct coordinator loading (scenario data)

**Key Tests**:

- `test_claim_chore`: Chore claim logic
- `test_approve_chore`: Point calculation and award
- `test_badge_maintenance`: Badge threshold tracking

**Pattern**:

```python
async def test_claim_chore(hass, scenario_minimal):
    config_entry, name_to_id_map = scenario_minimal
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    kid_id = name_to_id_map["kid:Zoë"]
    chore_id = name_to_id_map["chore:Feed the cåts"]

    coordinator.claim_chore("Zoë", chore_id)

    assert chore_id in coordinator.kids_data[kid_id]["chores_claimed"]
```

### 4. Service Tests (`test_services.py`)

**Purpose**: Test service call interfaces

**Data Loading**: Direct coordinator loading (scenario data)

**Key Tests**:

- `test_service_claim_chore`: Call `kidschores.claim_chore` service
- `test_service_adjust_points`: Call `kidschores.adjust_points` service

**Pattern**:

```python
async def test_service_claim_chore(hass, scenario_minimal):
    config_entry, name_to_id_map = scenario_minimal

    await hass.services.async_call(
        DOMAIN,
        "claim_chore",
        {"kid_name": "Zoë", "chore_name": "Feed the cåts"},
        blocking=True
    )

    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
    kid_id = name_to_id_map["kid:Zoë"]
    chore_id = name_to_id_map["chore:Feed the cåts"]

    assert chore_id in coordinator.kids_data[kid_id]["chores_claimed"]
```

### 5. Workflow Tests (Kid Chores)

**Purpose**: Test complete kid chore workflows

**Data Loading**: Direct coordinator loading + entity platform reload

**Key Tests**:

- `test_kid_claim_chore_button`: Kid presses claim button
- `test_parent_approve_chore_button`: Parent presses approve button
- `test_chore_points_awarded`: Points added after approval

**Pattern**:

```python
async def test_kid_claim_chore_button(hass, scenario_minimal, mock_hass_users):
    config_entry, name_to_id_map = scenario_minimal
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Get claim button entity
    claim_button_id = get_button_entity_id(hass, "Zoë", "chore_claim", "Feed the cåts")

    # Get button entity directly
    button_entity = None
    for entity in hass.data.get("entity_components", {}).get("button", {}).entities:
        if entity.entity_id == claim_button_id:
            button_entity = entity
            break

    # Set kid context and press button
    button_entity._context = Context(user_id=mock_hass_users["kid1"].id)

    with patch.object(coordinator, "_notify_parent", new=AsyncMock()):
        await button_entity.async_press()
        await hass.async_block_till_done()

    # Verify chore claimed
    kid_id = name_to_id_map["kid:Zoë"]
    chore_id = name_to_id_map["chore:Feed the cåts"]
    assert chore_id in coordinator.kids_data[kid_id]["chores_claimed"]
```

### 6. Workflow Tests (Parent Actions)

**Purpose**: Test parent penalty/bonus application workflows

**Data Loading**: Direct coordinator loading + entity platform reload

**Key Tests**:

- `test_parent_apply_penalty_button`: Parent applies penalty
- `test_penalty_decrements_points`: Points deducted correctly
- `test_penalty_recorded_in_history`: Penalty tracked in `penalty_applies`

**Pattern**:

```python
async def test_parent_apply_penalty_button(hass, scenario_minimal, mock_hass_users):
    config_entry, name_to_id_map = scenario_minimal
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Get penalty button entity
    penalty_button_id = get_button_entity_id(hass, "Zoë", "penalty", "Førget Chöre")

    # Get button entity directly
    button_entity = None
    for entity in hass.data.get("entity_components", {}).get("button", {}).entities:
        if entity.entity_id == penalty_button_id:
            button_entity = entity
            break

    # Set parent context and press button
    button_entity._context = Context(user_id=mock_hass_users["parent1"].id)

    with patch.object(coordinator, "_notify_kid", new=AsyncMock()):
        await button_entity.async_press()
        await hass.async_block_till_done()

    # Verify points deducted
    kid_id = name_to_id_map["kid:Zoë"]
    initial_points = 10.0
    assert coordinator.kids_data[kid_id]["points"] == initial_points - 5.0
```

### 7. Dashboard Template Tests

**Purpose**: Validate Jinja2 dashboard templates

**Data Loading**: Mock entity states (no coordinator needed)

**See [Dashboard Template Testing](#dashboard-template-testing) section below for full details**

---

## Migration Testing

Migration tests validate that v40 data structures are correctly upgraded to v42 schema during integration startup, ensuring no data loss and proper schema transformation.

### What Gets Tested

✅ **Migration Framework Tests** (`test_migration_generic.py`):

- Schema version detection and upgrade
- All entity types preserved (kids, chores, rewards, badges, etc.)
- Modern data structures created (chore_data, point_stats, etc.)
- Legacy fields removed after migration
- Entity counts preserved
- Data integrity across migration

✅ **Multi-Version Validation** (`test_migration_samples_validation.py`):

- v30, v31, v40-beta1 → v42 migration paths
- Required fields present in v42 structure
- Datetime format conversion to UTC ISO strings
- Badge list-to-dict transformation
- Chore assignment preservation
- Kid points preserved
- Badge cumulative progress initialization

### Why Test Migrations?

1. **Backward compatibility** - Existing installations upgrade without data loss
2. **Schema evolution** - Complex transformations (list→dict, datetime formats) work correctly
3. **One-time cleanup** - Legacy fields removed, not orphaned
4. **Production validation** - Real data from production instances tested
5. **Version diversity** - Multiple legacy versions (v30, v31, v40) supported

### How to Use Migration Tests

#### Test with Production Data

Test any v40 KidsChores data file (from users, production backups, etc.):

```bash
# Test your v40 data file
pytest tests/test_migration_generic.py --migration-file=path/to/your/kidschores_data -v

# Example with ad-ha production data
pytest tests/test_migration_generic.py \
    --migration-file=tests/migration_samples/kidschores_data_ad-ha -v
```

#### Expected Output

```
test_migration_generic.py::test_multiple_files_example[tests/migration_samples/kidschores_data_ad-ha] PASSED
```

The test will:

1. Load your v40 data file
2. Run all pre-v42 migrations
3. Validate schema version is now 42
4. Verify all entities present
5. Check modern structures exist
6. Ensure legacy fields removed
7. Verify data integrity

#### Add New Test Data

To add your own production data for testing:

```bash
# Copy data to migration_samples directory
cp /path/to/your/.storage/kidschores_data tests/migration_samples/kidschores_data_myname

# Run migration test
pytest tests/test_migration_generic.py --migration-file=tests/migration_samples/kidschores_data_myname -v
```

### Generic Framework Architecture

The migration framework is **reusable and extensible**:

**Files**:

- `utils/validate_migration.py` (658 lines) - Core validation logic, entity-agnostic
- `test_migration_generic.py` (276 lines) - Generic test fixtures and parametrization
- `test_migration_samples_validation.py` (445 lines) - Multi-version validation suite

**How it works**:

1. Load v40 data file into memory
2. Run `migration_pre_v42._run_pre_v42_migrations()`
3. Validate result with `MigrationValidator` class:
   - Schema version check
   - Required fields verification
   - Data structure validation
   - Legacy field cleanup verification
   - Entity count preservation
   - Data integrity checks

**Auto-discovers** all entities without hardcoding names or IDs

### Test All Migration Paths

```bash
# Run all migration tests (generic + multi-version)
pytest tests/test_migration_generic.py tests/test_migration_samples_validation.py -v

# Run only generic tests (for your data files)
pytest tests/test_migration_generic.py -v

# Run only multi-version validation (v30, v31, v40)
pytest tests/test_migration_samples_validation.py -v

# With coverage report
pytest tests/test_migration*.py --cov=custom_components.kidschores --cov-report=term-missing
```

### Key Validation Points

**Schema Version**: Confirms data was migrated to v42

```python
assert meta_section.get("schema_version") == 42
```

**Entity Preservation**: All entity types present with correct counts

```python
assert len(kids) > 0
assert len(chores) > 0
assert len(rewards) > 0
# ... etc
```

**Modern Structures**: New v42 structures created

```python
assert const.DATA_CHORE_DATA in chore  # New structure
assert const.DATA_POINT_STATS in kid   # New structure
```

**Legacy Cleanup**: Old fields removed

```python
assert const.DATA_KID_CHORE_CLAIMS_LEGACY not in kid
assert const.DATA_KID_POINTS_EARNED_TODAY_LEGACY not in kid
```

**Data Integrity**: Data accessible and valid

```python
assert isinstance(kid[const.DATA_POINTS], (int, float))
assert all(isinstance(timestamp, str) for timestamp in chore_timestamps)
```

---

## Dashboard Template Testing

Dashboard template tests validate that Jinja2 templates used in the KidsChores dashboard render correctly without requiring a live Home Assistant instance.

### Why Test Templates?

1. **Catch syntax errors early** - Invalid Jinja2 breaks dashboards
2. **Validate data access** - Ensure entity states and attributes are accessible
3. **Prevent integration regressions** - Changes to coordinator data structures won't break dashboards
4. **Verify translations** - Translation keys load from dashboard helper sensor
5. **Test filtering logic** - Entity filtering by assigned kids works correctly

### What Can Be Tested

✅ **Can test**:

- Jinja2 template syntax and rendering
- Entity state access (`states()`, `state_attr()`)
- Template filters (`slugify`, `int`, `datetime`)
- Translation key loading from `ui_translations` attribute
- Data structure navigation (loops, conditionals)
- Entity filtering by attributes
- Default value handling for missing data

❌ **Cannot test** (requires browser):

- Visual appearance and layout
- CSS styling and colors
- Mushroom card rendering
- Auto-entities card behavior
- User interactions (clicks, taps)
- Card animations and transitions

### Test Structure

```python
async def test_dashboard_template(hass, dashboard_entities):
    """Test dashboard template renders without errors."""
    # Arrange: Set up entity states
    # (done by dashboard_entities fixture)

    # Act: Render template
    template_str = """
    {%- set Kid_name = 'Alice' -%}
    {%- set dashboard_helper = 'sensor.kc_' ~ Kid_name | slugify() ~ '_ui_dashboard_helper' -%}
    {%- set ui = state_attr(dashboard_helper, 'ui_translations') or {} -%}
    {{ ui.get('welcome', 'err-welcome') }}
    """
    template = Template(template_str, hass)
    result = template.async_render()

    # Assert: Verify output
    assert "Welcome" in result
    assert "err-" not in result  # No missing translations
```

### Key Test Fixtures

**`dashboard_entities` fixture**: Sets up complete dashboard data

```python
@pytest.fixture
async def dashboard_entities(hass, kid_name, kid_slug):
    """Set up dashboard entity states for testing."""
    # Dashboard helper sensor with translations and entity lists
    hass.states.async_set(
        f"sensor.kc_{kid_slug}_ui_dashboard_helper",
        "active",
        {
            "ui_translations": {
                "welcome": "Welcome",
                "your_points": "Your Points",
                # ... 40+ translation keys
            },
            "chores": [
                {"eid": "sensor.kc_chore_make_bed", "name": "Make Bed", "status": "pending"}
            ],
            "rewards": [
                {"eid": "sensor.kc_reward_ice_cream", "name": "Ice Cream", "cost": 60}
            ],
            "badges": [],
            "chores_by_label": {"Kitchen": ["sensor.kc_chore_dishes"]}
        }
    )

    # Points sensor
    hass.states.async_set(f"sensor.kc_{kid_slug}_points", "50.0", {})

    # Other sensors...

    return hass
```

### Test Categories

#### 1. Welcome Card Tests

Tests the greeting card with kid's name, points, and stats

```python
async def test_welcome_card_renders(hass, dashboard_entities):
    """Test welcome card renders with kid name and points."""
    template = Template(WELCOME_CARD_TEMPLATE, hass)
    result = template.async_render()

    assert "Alice" in result
    assert "50.0" in result  # Points
```

#### 2. Chores Card Tests

Tests chore list rendering with state-based coloring

```python
async def test_chores_card_state_colors(hass, dashboard_entities):
    """Test chore state determines icon color."""
    template = Template(CHORES_CARD_TEMPLATE, hass)
    result = template.async_render()

    # Pending = orange, Approved = green, Claimed = blue, Overdue = red
    assert "color: orange" in result or "icon_color: orange" in result
```

#### 3. Translation Tests

Tests translation loading from dashboard helper sensor

```python
async def test_translations_from_helper(hass, dashboard_entities):
    """Test translations load from ui_translations attribute."""
    template = Template("{{ ui.get('welcome', 'err-welcome') }}", hass)
    result = template.async_render()

    assert result == "Welcome"
    assert "err-" not in result
```

#### 4. Filter Tests

Tests custom Jinja filters (slugify, int, datetime)

```python
async def test_slugify_filter(hass, dashboard_entities):
    """Test slugify filter converts names to entity IDs."""
    template = Template("{{ 'Zoë Stårblüm' | slugify }}", hass)
    result = template.async_render()

    assert result == "zoe_starblum"
```

#### 5. Empty State Tests

Tests graceful handling of missing data

```python
async def test_empty_chore_list(hass, dashboard_entities):
    """Test dashboard handles empty chore list gracefully."""
    # Set empty chores list
    hass.states.async_set(
        "sensor.kc_alice_ui_dashboard_helper",
        "active",
        {"ui_translations": {...}, "chores": []}
    )

    template = Template(CHORES_CARD_TEMPLATE, hass)
    result = template.async_render()

    assert "No chores" in result or "no chores" in result
```

### Integration Data Flow

```
Integration Coordinator
    ↓
Dashboard Helper Sensor (sensor.kc_<kid>_ui_dashboard_helper)
    ├── ui_translations: {} (40+ keys)
    ├── chores: [] (sorted, filtered)
    ├── rewards: []
    ├── badges: []
    ├── bonuses: []
    ├── penalties: []
    └── chores_by_label: {}
    ↓
Jinja2 Templates in Dashboard YAML
    ↓
Rendered Cards in Home Assistant UI
```

### Dashboard Helper Sensor Structure

```yaml
sensor.kc_zoe_ui_dashboard_helper:
  state: "chores:2 rewards:1 badges:1 bonuses:1 penalties:1"
  attributes:
    ui_translations:
      welcome: "Welcome"
      your_points: "Your Points"
      chores: "Chores"
      rewards: "Rewards"
      # ... 40+ keys
    chores:
      - eid: "sensor.kc_zoe_chore_status_feed_cats"
        name: "Feed the cåts"
        status: "approved"
        labels: []
        due_date: null
        primary_group: "today"
    rewards:
      - eid: "sensor.kc_zoe_reward_status_ice_cream"
        name: "Ice Créam!"
        cost: 60
        claims: 0
        approvals: 0
    badges:
      - eid: "sensor.kc_bronze_star_badge"
        name: "Brønze Står"
        threshold: 400
        current_progress: 390
    chores_by_label:
      Kitchen:
        - "sensor.kc_zoe_chore_status_dishes"
        - "sensor.kc_zoe_chore_status_wipe_counters"
```

### Running Dashboard Tests

```bash
# Run all dashboard tests
pytest tests/test_dashboard_templates.py -v

# Run specific test
pytest tests/test_dashboard_templates.py::TestDashboardWelcomeCard::test_welcome_card_renders -v

# Run with coverage
pytest tests/test_dashboard_templates.py --cov=custom_components.kidschores --cov-report=term-missing
```

### Dashboard Testing Best Practices

1. **Use dashboard_entities fixture** - Provides complete entity setup
2. **Test rendering, not appearance** - Focus on data access, not CSS
3. **Verify translations load** - Check `ui_translations` attribute access
4. **Test empty states** - Ensure graceful handling of missing data
5. **Test filtering logic** - Verify entity filtering by assigned kids
6. **Mock all entities** - Don't rely on coordinator; use hass.states.async_set()

---

## Test Fixtures

### Common Fixtures (conftest.py)

#### `hass`

Provides mock Home Assistant instance

```python
@pytest.fixture
async def hass():
    """Fixture to provide a test instance of Home Assistant."""
    # Returns mock hass instance
    yield hass
```

#### `config_entry`

Provides initialized config entry

```python
@pytest.fixture
async def config_entry(hass):
    """Fixture to provide a config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"integration_name": "KidsChores"},
        entry_id="test_entry_id"
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    return entry
```

#### `mock_hass_users`

Provides mock Home Assistant users for authorization testing

```python
@pytest.fixture
def mock_hass_users(hass):
    """Fixture to provide mock HA users (parent1, kid1, kid2, admin)."""
    users = {
        "parent1": MockUser(
            id="parent1_user_id",
            name="Parent 1",
            is_admin=False
        ),
        "kid1": MockUser(
            id="kid1_user_id",
            name="Kid 1",
            is_admin=False
        ),
        "admin": MockUser(
            id="admin_user_id",
            name="Admin",
            is_admin=True
        )
    }
    return users
```

#### `scenario_minimal`

Loads minimal test scenario with 1 kid, 2 chores, 1 badge, etc.

```python
@pytest.fixture
async def scenario_minimal(hass, init_integration, mock_hass_users):
    """Fixture to load minimal scenario and return (config_entry, name_to_id_map)."""
    scenario_data = yaml.safe_load(Path("tests/testdata_scenario_minimal.yaml").read_text())

    name_to_id_map = await apply_scenario_direct(
        hass, init_integration, scenario_data, mock_hass_users
    )

    # Reload entity platforms to create entities from scenario data
    await reload_entity_platforms(hass, init_integration)

    return init_integration, name_to_id_map
```

#### `reload_entity_platforms`

Reloads entity platforms after data changes

```python
async def reload_entity_platforms(hass, config_entry):
    """Reload entity platforms to recreate entities from new data."""
    # Unload platforms
    await hass.config_entries.async_unload_platforms(
        config_entry,
        [Platform.SENSOR, Platform.BUTTON, Platform.SELECT, Platform.CALENDAR]
    )
    await hass.async_block_till_done()

    # Reload platforms
    await hass.config_entries.async_forward_entry_setups(
        config_entry,
        [Platform.SENSOR, Platform.BUTTON, Platform.SELECT, Platform.CALENDAR]
    )
    await hass.async_block_till_done()
```

---

## Testing Patterns

### Pattern 1: Direct Entity Method Call (Bypass Service Dispatcher)

**When to use**: Workflow tests where service dispatcher fails after platform reload

**Why**: After reloading platforms, service dispatcher may lose entity references. Accessing entities directly ensures button presses reach the correct entity.

```python
async def test_with_direct_entity_call(hass, scenario_minimal, mock_hass_users):
    """Test button press by calling entity method directly."""
    config_entry, name_to_id_map = scenario_minimal
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Get button entity ID
    button_id = get_button_entity_id(hass, "Zoë", "chore_claim", "Feed the cåts")

    # Find button entity in entity registry
    button_entity = None
    for entity in hass.data.get("entity_components", {}).get("button", {}).entities:
        if entity.entity_id == button_id:
            button_entity = entity
            break

    assert button_entity is not None, f"Button entity {button_id} not found"

    # Set user context
    button_entity._context = Context(user_id=mock_hass_users["kid1"].id)

    # Call async_press directly (bypasses service dispatcher)
    with patch.object(coordinator, "_notify_parent", new=AsyncMock()):
        await button_entity.async_press()
        await hass.async_block_till_done()

    # Verify action completed
    kid_id = name_to_id_map["kid:Zoë"]
    chore_id = name_to_id_map["chore:Feed the cåts"]
    assert chore_id in coordinator.kids_data[kid_id]["chores_claimed"]
```

### Pattern 2: Mock Notifications

**When to use**: All workflow tests that trigger notifications

**Why**: Prevents teardown errors when coordinator tries to call notify service that doesn't exist in test environment

```python
from unittest.mock import AsyncMock, patch

async def test_with_mocked_notifications(hass, scenario_minimal):
    """Test action that would trigger notifications."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Mock notification methods
    with patch.object(coordinator, "_notify_parent", new=AsyncMock()):
        with patch.object(coordinator, "_notify_kid", new=AsyncMock()):
            # Execute action that would send notifications
            coordinator.claim_chore("Zoë", chore_id)

            # Verify action completed without errors
            assert chore_claimed
```

### Pattern 3: Authorization Testing

**When to use**: Testing that actions respect user roles (kid vs parent vs admin)

**Why**: Integration has built-in access control that checks user IDs against parent/kid entities

**Setup**: Link mock users to coordinator entities

```python
# In conftest.py - apply_scenario_direct()
for idx, parent in enumerate(family.get("parents", [])):
    parent_id = str(uuid.uuid4())

    # Link first parent to parent1 mock user for authorization tests
    parent_ha_user_id = ""
    if mock_users and idx == 0 and "parent1" in mock_users:
        parent_ha_user_id = mock_users["parent1"].id

    coordinator.parents_data[parent_id] = {
        "name": parent["name"],
        "ha_user_id": parent_ha_user_id,  # Links mock user to parent entity
        # ... other fields
    }
```

**Test**:

```python
async def test_authorization(hass, scenario_minimal, mock_hass_users):
    """Test that only authorized users can perform actions."""
    button_entity._context = Context(user_id=mock_hass_users["parent1"].id)

    # Parent1 is linked to first parent entity in scenario
    # This action should succeed
    await button_entity.async_press()

    # Change to kid user (not authorized for parent action)
    button_entity._context = Context(user_id=mock_hass_users["kid1"].id)

    # This action should fail authorization check
    with pytest.raises(HomeAssistantError):
        await button_entity.async_press()
```

### Pattern 4: Test Data Structures

**When to use**: Verifying coordinator internal data after actions

**Common structures**:

```python
# Penalty tracking
coordinator.kids_data[kid_id]["penalty_applies"] = {
    penalty_id: count  # Number of times penalty applied
}

# Bonus tracking
coordinator.kids_data[kid_id]["bonus_applies"] = {
    bonus_id: count  # Number of times bonus applied
}

# Point stats (aggregated by source and time period)
coordinator.kids_data[kid_id]["point_stats"] = {
    "points_by_source_today": {
        "chores": 50.0,
        "bonuses": 15.0,
        "penalties": -10.0,
        "adjustments": 5.0
    },
    "points_by_source_week": {...},
    "points_by_source_month": {...},
    # ... other time periods
}

# Badge progress (for cumulative badges)
coordinator.kids_data[kid_id]["cumulative_badge_progress"] = {
    "baseline": 405.0,  # Points when last badge awarded
    "cycle_points": 0,  # Points since last badge (resets on award)
    "current_badge_id": "badge_uuid",
    "highest_earned_badge_id": "badge_uuid",
    "status": "active"
}

# Badges earned
coordinator.kids_data[kid_id]["badges_earned"] = {
    badge_id: {
        "badge_name": "Brønze Står",
        "last_awarded_date": "2024-01-15T10:30:00Z",
        "award_count": 3,
        "periods": {
            "daily": {"2024-01-15": 1},
            "weekly": {"2024-W03": 1},
            "monthly": {"2024-01": 1},
            "yearly": {"2024": 1}
        }
    }
}
```

**Test examples**:

```python
# Test penalty counter increments
penalty_applies = coordinator.kids_data[kid_id].get("penalty_applies", {})
assert penalty_id in penalty_applies
assert penalty_applies[penalty_id] == initial_count + 1

# Test point stats updated
point_stats = coordinator.kids_data[kid_id].get("point_stats", {})
penalties_today = point_stats.get("points_by_source_today", {}).get("penalties", 0)
assert penalties_today == -5.0

# Test badge awarded and cycle reset
badges_earned = coordinator.kids_data[kid_id]["badges_earned"]
assert bronze_star_badge in badges_earned

progress = coordinator.kids_data[kid_id].get("cumulative_badge_progress", {})
assert progress["baseline"] >= 400.0  # Baseline moved forward
assert progress["cycle_points"] == 0  # Cycle reset after award
```

---

## Debugging

### Enable Debug Logging

```python
# In test file
import logging
logging.basicConfig(level=logging.DEBUG)

# Or in conftest.py
@pytest.fixture
def caplog_debug(caplog):
    """Enable debug logging for tests."""
    caplog.set_level(logging.DEBUG, logger="custom_components.kidschores")
    return caplog
```

### Print Coordinator State

```python
import json

async def test_with_debug_output(hass, scenario_minimal):
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Print coordinator data
    print("\n=== COORDINATOR DATA ===")
    print(json.dumps(coordinator.kids_data, indent=2, default=str))
    print(json.dumps(coordinator.chores_data, indent=2, default=str))
```

### Run Single Test with Full Output

```bash
# Run with print statements visible
pytest tests/test_workflow_parent_actions.py::test_penalty_decrements_points -v -s

# Run with full traceback
pytest tests/test_workflow_parent_actions.py::test_penalty_decrements_points -vv --tb=long

# Run with debug logging
pytest tests/test_workflow_parent_actions.py::test_penalty_decrements_points -v --log-cli-level=DEBUG
```

### Check Entity Registry

```python
from homeassistant.helpers import entity_registry as er

async def test_check_entity_registry(hass, config_entry):
    registry = er.async_get(hass)

    # Check if entity registered
    entity_entry = registry.async_get("button.kc_zoe_chore_claim_feed_cats")

    print(f"Entity entry: {entity_entry}")
    print(f"Platform: {entity_entry.platform if entity_entry else 'NOT IN REGISTRY'}")
    print(f"Unique ID: {entity_entry.unique_id if entity_entry else 'N/A'}")
```

### Verify Entity Exists

```python
async def test_verify_entity_exists(hass):
    # Check state exists
    state = hass.states.get("sensor.kc_zoe_points")
    assert state is not None, "Entity not found in state machine"

    # Check entity in platform
    entities = hass.data.get("entity_components", {}).get("sensor", {}).entities
    sensor_ids = [e.entity_id for e in entities]
    print(f"Sensor entities: {sensor_ids}")

    assert "sensor.kc_zoe_points" in sensor_ids
```

---

## Best Practices

### 1. Use Appropriate Data Loading Method

- **Options Flow**: UI workflow tests, validation tests
- **Direct Loading**: Business logic tests, workflow tests

### 2. Always Mock Notifications

```python
with patch.object(coordinator, "_notify_parent", new=AsyncMock()):
    with patch.object(coordinator, "_notify_kid", new=AsyncMock()):
        # Execute action
```

### 3. Set User Context for Authorization

```python
button_entity._context = Context(user_id=mock_hass_users["parent1"].id)
```

### 4. Reload Platforms After Data Changes

```python
await reload_entity_platforms(hass, config_entry)
```

### 5. Use Direct Entity Access for Workflow Tests

```python
# Good: Direct entity access
button_entity = None
for entity in hass.data.get("entity_components", {}).get("button", {}).entities:
    if entity.entity_id == button_id:
        button_entity = entity
        break

await button_entity.async_press()

# Avoid: Service dispatcher after platform reload
await hass.services.async_call(BUTTON_DOMAIN, SERVICE_PRESS, {...})  # May fail
```

### 6. Test Actual Data Structures

```python
# Good: Test actual data structure
penalty_applies = coordinator.kids_data[kid_id].get("penalty_applies", {})
assert penalty_id in penalty_applies

# Avoid: Test non-existent structure
penalties_history = coordinator.kids_data[kid_id].get("penalties_history", [])  # Doesn't exist!
```

### 7. Use Scenarios for Workflow Tests

```python
# Good: Load scenario data
async def test_workflow(hass, scenario_minimal):
    config_entry, name_to_id_map = scenario_minimal
    # Data already loaded, entities created

# Avoid: Manually creating data in test
async def test_workflow(hass, config_entry):
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
    coordinator.kids_data["kid_id"] = {...}  # Tedious and error-prone
```

### 8. Check Badge Award Logic

```python
# After bonus that crosses badge threshold:

# ✅ Check badge awarded
badges_earned = coordinator.kids_data[kid_id]["badges_earned"]
assert bronze_star_badge in badges_earned

# ✅ Check baseline moved forward
progress = coordinator.kids_data[kid_id].get("cumulative_badge_progress", {})
assert progress["baseline"] >= 400.0

# ❌ Don't check cycle_points (resets to 0 after award)
cycle_points = progress.get("cycle_points", 0)
assert cycle_points >= 400.0  # WRONG! This will fail because cycle resets
```

### 9. Clean Up Debug Code

Remove debug print statements before committing:

```python
# Remove before commit:
print(f"DEBUG: kid_id = {kid_id}")
print(f"DEBUG: penalty_data = {penalty_data}")
```

### 10. Follow Naming Conventions

```python
# Good test names
async def test_kid_claim_chore_button()
async def test_parent_apply_penalty_button()
async def test_bonus_triggers_badge_threshold()

# Descriptive fixture names
@pytest.fixture
async def scenario_minimal()
@pytest.fixture
def mock_hass_users()
```

---

## Common Pitfalls

### ❌ Using Service Dispatcher After Platform Reload

```python
# WRONG: Service dispatcher may not find entities after reload
await hass.services.async_call(
    BUTTON_DOMAIN,
    SERVICE_PRESS,
    {ATTR_ENTITY_ID: button_id},
    blocking=True
)

# RIGHT: Access entity directly
button_entity = None
for entity in hass.data.get("entity_components", {}).get("button", {}).entities:
    if entity.entity_id == button_id:
        button_entity = entity
        break
await button_entity.async_press()
```

### ❌ Forgetting to Mock Notifications

```python
# WRONG: Notifications will cause teardown errors
await button_entity.async_press()

# RIGHT: Mock notification methods
with patch.object(coordinator, "_notify_kid", new=AsyncMock()):
    await button_entity.async_press()
```

### ❌ Not Setting User Context

```python
# WRONG: No user context means authorization fails
await button_entity.async_press()

# RIGHT: Set user context for authorization
button_entity._context = Context(user_id=mock_hass_users["parent1"].id)
await button_entity.async_press()
```

### ❌ Testing Non-Existent Data Structures

```python
# WRONG: penalties_history doesn't exist
penalties_history = coordinator.kids_data[kid_id].get("penalties_history", [])

# RIGHT: Test actual structure
penalty_applies = coordinator.kids_data[kid_id].get("penalty_applies", {})
assert penalty_id in penalty_applies
```

### ❌ Checking cycle_points After Badge Award

```python
# WRONG: cycle_points resets to 0 after badge award
cycle_points = coordinator.kids_data[kid_id].get("cumulative_badge_progress", {}).get("cycle_points", 0)
assert cycle_points >= 400.0  # This fails!

# RIGHT: Check badge awarded or baseline moved
badges_earned = coordinator.kids_data[kid_id]["badges_earned"]
assert bronze_star_badge in badges_earned

# OR check baseline
progress = coordinator.kids_data[kid_id].get("cumulative_badge_progress", {})
assert progress["baseline"] >= 400.0
```

---

## Lessons Learned

### Lesson 1: Entity Platforms Must Be Reloaded

After loading scenario data directly into coordinator, entity platforms must be reloaded to create entities. The `scenario_minimal` fixture does this automatically.

```python
await reload_entity_platforms(hass, config_entry)
```

### Lesson 2: Service Dispatcher Unreliable After Reload

After platform reload, the service dispatcher may lose entity references. Use direct entity access instead.

```python
# ✅ Direct entity access
button_entity = None
for entity in hass.data.get("entity_components", {}).get("button", {}).entities:
    if entity.entity_id == button_id:
        button_entity = entity
        break
await button_entity.async_press()
```

### Lesson 3: Authorization Requires User Context Linkage

Link mock Home Assistant users to coordinator parent/kid entities via `ha_user_id` field. First parent gets `parent1` user ID, first kid gets `kid1` user ID.

```python
button_entity._context = Context(user_id=mock_hass_users["parent1"].id)
```

### Lesson 4: Penalty Points Must Be Negative

Penalties deduct points, so store as negative values in `points` calculation.

```python
new_points = current_points + penalty_points  # penalty_points is negative (e.g., -5.0)
```

### Lesson 5: Notification Mocks Required

Mock `_notify_kid` and `_notify_parent` methods to prevent teardown errors when coordinator tries to call notify service.

```python
with patch.object(coordinator, "_notify_kid", new=AsyncMock()):
    with patch.object(coordinator, "_notify_parent", new=AsyncMock()):
        await button_entity.async_press()
```

### Lesson 6: Know Your Data Structures

Test actual coordinator data structures, not assumed ones. Key structures: `penalty_applies`, `bonus_applies`, `point_stats`, `badges_earned`, `cumulative_badge_progress`.

### Lesson 7: Badge Cycle Resets After Award

When a badge is awarded, `cycle_points` resets to 0 and `baseline` moves forward. Check `badges_earned` or `baseline`, not `cycle_points`.

```python
# ✅ Check badge awarded
assert badge_id in coordinator.kids_data[kid_id]["badges_earned"]

# ✅ Check baseline moved
assert progress["baseline"] >= threshold

# ❌ Don't check cycle_points (resets to 0)
assert progress["cycle_points"] >= threshold  # WRONG!
```

### Lesson 8: Context API Import Required

Import `Context` from `homeassistant.core`, not `homeassistant.const`.

```python
from homeassistant.core import Context
```

### Lesson 9: Entity Naming Uses Slugify

Entity IDs are slugified (lowercase, no special characters, underscores replace spaces). Use `get_button_entity_id()` helper.

```python
button_id = get_button_entity_id(hass, "Zoë", "chore_claim", "Feed the cåts")
# Returns: button.kc_zoe_chore_claim_feed_the_cats
```

### Lesson 10: Test One Thing at a Time

Break complex workflows into focused tests. Each test should validate one specific behavior.

---

## Resources

- **pytest Documentation**: https://docs.pytest.org/
- **Home Assistant Testing**: https://developers.home-assistant.io/docs/development_testing
- **Jinja2 Templates**: https://jinja.palletsprojects.com/

---

**Last Updated**: December 13, 2024
**Test Suite Version**: 1.0 (78 tests)
