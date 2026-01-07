# KidsChores Testing Suite

Welcome to the KidsChores Home Assistant integration testing suite! This comprehensive test framework validates the integration's functionality, including dashboard templates, business logic, and user workflows.

## 🌟 The Stårblüm Family

Our tests follow the adventures of the magical **Stårblüm Family**, who use the KidsChores integration to manage their household chores and earn rewards!

### Meet the Family

**Parents**:

- **Môm Astrid Stårblüm** (@Astrid) - The family organizer who approves chores and rewards
- **Dad Leo Stårblüm** (@Leo) - The fun parent who creates bonus opportunities

**Kids**:

- **Zoë Stårblüm** (Age 8, avatar: mdi:star-face) - The responsible oldest, loves earning badges
- **Max! Stårblüm** (Age 6, avatar: mdi:rocket) - The energetic middle child, always claiming chores
- **Lila Stårblüm** (Age 8, avatar: mdi:flower) - The creative twin, motivated by rewards

### Why Special Characters?

All names include special characters (å, ï, ë, ø, @, !) to ensure robust Unicode handling throughout the integration. This validates that the system works for international families with diverse naming conventions.

---

## 📚 Testing Philosophy

Our testing approach follows three key principles:

### 1. **User-Centric Testing**

Tests mirror real-world user workflows:

- Setup integration → Config flow
- Add entities → Options flow
- Interact with system → Services & UI
- View data → Dashboard templates

### 2. **Comprehensive Coverage**

Tests cover all entity types and workflows:

- **Entities**: Parents, kids, chores, badges, bonuses, penalties, rewards
- **Workflows**: Claim, approve, disapprove, reset, redeem, award
- **Features**: Recurring chores, shared chores, badge maintenance, reward approval

### 3. **Scenario-Based Data**

Tests use pre-built scenarios that tell a story:

- **Minimal**: Zoë's first week with simple chores
- **Medium**: Zoë and Max! learning to share chores
- **Full**: Complete family with badges, streaks, and advanced features

---

## 🎯 What We Test

### Config & Setup (8 tests)

- Initial integration setup via UI
- YAML configuration import
- Input validation and error handling
- Duplicate detection

### Coordinator Logic (12 tests)

- Chore lifecycle: claim → approve → reset
- Points calculation: base + bonuses - penalties
- Badge awards and maintenance
- Recurring chore scheduling
- Shared chore coordination

### Options Flow (9 tests)

- Adding entities: kids, chores, badges, etc.
- Editing entity properties
- Deleting entities with dependency checks
- Validation: unique names, point limits, required fields

### Services (5 tests)

- Chore services: `claim_chore`, `approve_chore`, etc.
- Points services: `adjust_points`, `apply_bonus`, `apply_penalty`
- Reward services: `redeem_reward`, `approve_reward`, etc.
- Badge services: `award_badge`, `remove_badge`
- Bulk operations: `reset_all_chores`, `reset_penalties`

### Dashboard Templates (17 tests)

- Jinja2 template rendering without errors
- Entity filtering and grouping
- Translation loading from backend
- State color mapping (green/orange/red/blue)
- Date handling with timezone awareness
- Empty state handling
- Complex multi-kid scenarios

### Workflow Tests (32 tests)

- Kid chore workflow: claim → approve → complete (11 tests)
- Parent penalty/bonus application (11 tests)
- Kid reward redemption: claim → approval (10 tests)

**Total: 78 tests (71 passing, 7 intentionally skipped) ✅**

**Test Success Rate**: 100% of non-skipped tests passing

---

## 🚀 Quick Start

### Run All Tests

```bash
cd /workspaces/kidschores-ha
python -m pytest tests/ -v
```

### Run Specific Category

```bash
# Dashboard tests only
python -m pytest tests/test_dashboard_templates.py -v

# Coordinator tests only
python -m pytest tests/test_coordinator.py -v
```

### Run Single Test

```bash
python -m pytest tests/test_dashboard_templates.py::TestDashboardWelcomeCard::test_welcome_card_renders -v
```

### Run with Coverage

```bash
python -m pytest tests/ --cov=custom_components.kidschores --cov-report=term-missing
```

---

## 📖 Documentation Structure

Our testing documentation is organized into focused guides:

### 1. [README.md](README.md) (This File)

**Purpose**: Quick overview and getting started guide

### 2. [TESTING_GUIDE.md](TESTING_GUIDE.md)

**Purpose**: Comprehensive technical guide for writing and debugging tests
**Topics**: Data loading methods, test patterns, fixtures, debugging, best practices

### 3. [TESTING_AGENT_INSTRUCTIONS.md](TESTING_AGENT_INSTRUCTIONS.md)

**Purpose**: Quick reference for AI agents
**Topics**: Decision trees, essential patterns, code quality checklist

### 4. [TEST_SCENARIOS.md](TEST_SCENARIOS.md)

**Purpose**: Test scenario descriptions and YAML structure
**Topics**: Stårblüm family storyline, scenario data, usage examples

---

## 🛠️ For Test Developers

- **Writing new tests?** → Read [TESTING_GUIDE.md](TESTING_GUIDE.md)
- **AI agent?** → Use [TESTING_AGENT_INSTRUCTIONS.md](TESTING_AGENT_INSTRUCTIONS.md)
- **Understanding test data?** → See [TEST_SCENARIOS.md](TEST_SCENARIOS.md)

---

## 🧪 Test Scenarios

We provide three pre-built test scenarios with the Stårblüm Family:

### Minimal Scenario

**File**: `testdata_scenario_minimal.yaml`

**Purpose**: Entry-level testing, basic workflows

**Contents**:

- 1 parent (Môm Astrid)
- 1 kid (Zoë)
- 2 chores (Feed the cåts, Pick up Lëgo!)
- 1 badge (Brønze Står)
- 1 bonus (Stär Sprïnkle Bonus)
- 1 penalty (Førget Chöre)
- 1 reward (Ice Créam!)

**Best For**: Config flow tests, basic service tests, simple coordinator logic

### Medium Scenario

**File**: `testdata_scenario_medium.yaml`

**Purpose**: Multi-kid coordination, shared chores

**Contents**:

- 2 parents (Môm Astrid, Dad Leo)
- 2 kids (Zoë, Max!)
- 4 chores (1 shared: Clëan Living Room)
- 2 badges (Brønze Står, Dåily Dëlight)
- 2 bonuses
- 2 penalties
- 2 rewards

**Best For**: Shared chore tests, multi-kid filtering, parent approval tests

### Full Scenario

**File**: `testdata_scenario_full.yaml`

**Purpose**: Complete feature set validation

**Contents**:

- 2 parents (Môm Astrid, Dad Leo)
- 3 kids (Zoë, Max!, Lila)
- 7 chores (3 recurring, 1 shared)
- 5 badges (3 cumulative with maintenance, 1 periodic, 1 daily)
- 2 bonuses
- 3 penalties
- 5 rewards
- Detailed progress tracking (streaks, badge progress, reward claims)

**Best For**: Badge maintenance tests, recurring chore tests, comprehensive dashboard tests

See [TEST_SCENARIOS.md](TEST_SCENARIOS.md) for full details.

---

## 🎓 Learning Path

1. **Run tests**: `python -m pytest tests/ -v` (150 tests in 7 seconds!)
2. **Read**: [TESTING_GUIDE.md](TESTING_GUIDE.md) for comprehensive guide
3. **Study**: Start with `test_dashboard_templates.py` (simplest examples)
4. **Write**: Follow patterns from existing tests
5. **AI Agents**: Use [TESTING_AGENT_INSTRUCTIONS.md](TESTING_AGENT_INSTRUCTIONS.md) for quick patterns

---

## 🔍 Key Testing Concepts

### Data Loading Methods (CRITICAL)

**Two methods for loading test data - use the right one!**

#### Options Flow (UI Simulation)

**When**: Testing user interactions, input validation, UI workflows

**Example**: `test_options_flow.py`, `test_config_flow.py`

```python
# Add kid via options flow
result = await hass.config_entries.options.async_init(config_entry.entry_id)
result = await hass.config_entries.options.async_configure(
    result["flow_id"], user_input={"next_step": "add_kid"}
)
result = await hass.config_entries.options.async_configure(
    result["flow_id"], user_input={"name": "Zoë Stårblüm", "age": 8}
)
```

#### Direct Coordinator Loading (Business Logic)

**When**: Testing workflows, state transitions, business logic

**Example**: `test_workflow_*.py`, `test_coordinator.py`, `test_services.py`

```python
# Load scenario data directly into coordinator
async def test_workflow(hass, scenario_minimal):
    config_entry, name_to_id_map = scenario_minimal
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]

    # Entities already loaded from YAML scenario
    kid_id = name_to_id_map["kid:Zoë"]
    chore_id = name_to_id_map["chore:Feed the cåts"]
```

**Critical**: After direct loading, entity platforms must be reloaded (done automatically by `scenario_minimal` fixture).

See [TESTING_TECHNICAL_GUIDE.md](TESTING_TECHNICAL_GUIDE.md) "Data Loading Methods" for complete comparison.

### Dashboard Templates

Dashboard templates use Jinja2 to render kid-specific cards. Tests validate:

- Template syntax (no errors)
- Entity filtering (correct kid's data)
- Translation loading (from backend helper sensor)
- State colors (green/orange/red/blue)
- Empty state handling (graceful fallbacks)

See [TESTING_TECHNICAL_GUIDE.md](TESTING_TECHNICAL_GUIDE.md) "Dashboard Template Testing" for complete guide.

---

## 🛠️ Common Commands

### Development

See [TESTING_GUIDE.md](TESTING_GUIDE.md) for full details on:

- **Data Loading Methods**: Options flow vs direct coordinator loading
- **Dashboard Templates**: Jinja2 template validation
- **Test Patterns**: Platform reload, entity access, notification mocking
  # Arrange: Set up data via options flow
  # Act: Execute service or call coordinator method
  # Assert: Verify expected state changes

````

### Running Your Tests

```bash
# Run your new test
python -m pytest tests/test_your_file.py::test_your_function -v

# Run all tests to ensure no regressions
python -m pytest tests/ -v
````

### Documentation

If your test introduces new patterns:

1. Update [TESTING_INSTRUCTIONS.md](TESTING_INSTRUCTIONS.md) with pattern
2. Add example to relevant section
3. Update test count in this README

---

## 📊 Test Statistics

- **Total Tests**: 150 (139 passing, 11 skipped)
- **Execution Time**: ~7 seconds
- **Test Files**: 22 active files
- **Code Coverage**: ~95% of integration code

**Test Distribution**:

- Config/Setup: 8 tests
- Coordinator Logic: 12 tests
- Options Flow: 18 tests
- Workflows: 23 tests
- Dashboard: 35 tests
- Helpers: 31 tests
- Other: 23 tests
  - Options flow tests (9)
  - Service tests (5)
  - Dashboard template tests (17)
  - Stårblüm Family scenarios (3)
  - Comprehensive documentation

---

See [TESTING_GUIDE.md](TESTING_GUIDE.md) "Debugging" section for:

- Test failure troubleshooting
- Dashboard template debugging
- Coordinator state inspection
- Logging and isolation techniques

**Q: Why "Stårblüm Family"?**
A: Special characters ensure robust Unicode handling. The magical theme makes tests fun!

**Q: Do I need to use options flow?**
A: Yes! It's critical for realistic tests that mirror user workflows.

**Q: Can I skip dashboard tests?**
A: No - dashboard tests catch template syntax errors before runtime.

**Q: How do I add a new scenario?**
A: Copy `testdata_scenario_minimal.yaml`, modify, document in `TEST_SCENARIOS.md`.

**Q: Tests are slow - how to speed up?**
A: Use minimal scenario, run specific test file, use `-x` flag to stop on first failure.

**Q: Test passes locally but fails in CI?**
A: Check timezone handling (use UTC), async contexts, file paths.

---

**Happy Testing! 🎉**

The Stårblüm Family thanks you for keeping the KidsChores integration bug-free and reliable!

```sh
python -m pytest tests/test_services.py -k test_service_apply_bonus_and_penalty
```

## More Information

- See the main repository README for integration details.
- For Home Assistant test best practices, see the [Home Assistant developer docs](https://developers.home-assistant.io/docs/development_testing/).
