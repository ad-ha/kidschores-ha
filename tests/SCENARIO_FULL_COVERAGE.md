# Test Scenario Full - Comprehensive Chore Coverage Matrix

**Last Updated**: December 28, 2025
**Scenario Version**: 2.0 (18 chores)
**Purpose**: Comprehensive testing of all chore type combinations and workflows

---

## Overview

The `scenario_full` fixture provides complete coverage of KidsChores v0.4.0+ functionality with all chore types, completion criteria, and assignment patterns represented.

### Family Structure

- **3 Kids**: Zoë (age 8), Max! (age 6), Lila (age 8)
- **2 Parents**: Môm Astrid Stârblüm, Dad Leo
- **18 Chores**: 9 independent, 3 shared_all, 3 shared_first, 3 custom frequency
- **6 Badges**: Cumulative (Bronze, Silver, Gold), Periodic (Weekly Wizard), Daily (Daily Delight), Special Occasion
- **5 Rewards**: Ice Cream (60), Movie Night (120), Extra Playtime (40), Star Adventure Pack (200), Garden Picnic (300)
- **3 Penalties**: Forgot Chore (-5), Messy Room (-10), Late for Dinner (-3)
- **2 Bonuses**: Star Sprinkle (15), Magic Minute (10)

---

## Chore Coverage Matrix (18 Total)

### INDEPENDENT Chores (9 chores)

Each kid completes separately, tracks individual progress.

#### Single-Kid Independent (6 chores)

1. **Feed the cåts** (Zoë)

   - **Frequency**: Daily
   - **Points**: 10
   - **Tests**: Basic daily independent workflow
   - **Completion Criteria**: `independent` (explicit)
   - **Icon**: mdi:cat

2. **Wåter the plänts** (Zoë)

   - **Frequency**: Daily
   - **Points**: 10
   - **Tests**: Daily independent with **auto-approve**
   - **Completion Criteria**: `independent` (explicit)
   - **Auto-approve**: `true` (no parent approval needed)
   - **Icon**: mdi:watering-can

3. **Pick up Lëgo!** (Max!)

   - **Frequency**: Weekly
   - **Points**: 15
   - **Tests**: Weekly independent chore
   - **Completion Criteria**: `independent` (explicit)
   - **Icon**: mdi:lego

4. **Charge Røbot** (Max!)

   - **Frequency**: Daily (explicit recurring_frequency)
   - **Points**: 10
   - **Tests**: Daily independent with explicit recurring setting
   - **Completion Criteria**: `independent` (explicit)
   - **Icon**: mdi:robot

5. **Paint the rãinbow** (Lila)

   - **Frequency**: Weekly
   - **Points**: 15
   - **Tests**: Weekly independent chore
   - **Completion Criteria**: `independent` (explicit)
   - **Icon**: mdi:palette

6. **Sweep the p@tio** (Lila)
   - **Frequency**: Daily
   - **Points**: 10
   - **Tests**: Daily independent chore
   - **Completion Criteria**: `independent` (explicit)
   - **Icon**: mdi:broom

#### Multi-Kid Independent (3 chores)

Multiple kids assigned, but each completes independently.

7. **Stär sweep** (Zoë, Max!, Lila)

   - **Frequency**: Daily
   - **Points**: 20
   - **Tests**: 3-kid independent (each completes separately)
   - **Completion Criteria**: `independent` (explicit)
   - **Icon**: mdi:star

8. **Ørgänize Bookshelf** (Zoë, Lila)

   - **Frequency**: Weekly (explicit recurring_frequency)
   - **Points**: 18
   - **Tests**: 2-kid independent with higher points
   - **Completion Criteria**: `independent` (explicit)
   - **Icon**: mdi:bookshelf

9. **Deep Clean Tøy Chest** (Max!)
   - **Frequency**: Monthly
   - **Points**: 30
   - **Tests**: Monthly independent (less frequent recurrence)
   - **Completion Criteria**: `independent` (explicit)
   - **Icon**: mdi:treasure-chest

---

### SHARED_ALL Chores (3 chores)

All assigned kids must claim/approve before chore completes.

10. **Family Dinner Prep** (Zoë, Max!, Lila)

    - **Frequency**: Daily (explicit recurring_frequency)
    - **Points**: 15
    - **Tests**: Daily shared_all, 3 kids, chore-level due date
    - **Completion Criteria**: `shared_all` (explicit)
    - **Icon**: mdi:food
    - **Workflow**: All kids must claim → All kids must approve → Chore completes

11. **Weekend Yärd Work** (Zoë, Max!, Lila)

    - **Frequency**: Weekly (explicit recurring_frequency)
    - **Points**: 25
    - **Tests**: Weekly shared_all, 3 kids
    - **Completion Criteria**: `shared_all` (explicit)
    - **Icon**: mdi:tree
    - **Workflow**: All kids claim → All kids approve → Chore completes

12. **Sibling Rööm Cleanup** (Max!, Lila)
    - **Frequency**: Weekly (explicit recurring_frequency)
    - **Points**: 20
    - **Tests**: Weekly shared_all, 2 kids (subset)
    - **Completion Criteria**: `shared_all` (explicit)
    - **Icon**: mdi:broom-clean
    - **Workflow**: Both kids claim → Both kids approve → Chore completes

---

### SHARED_FIRST Chores (3 chores)

First kid to approve completes the chore for everyone.

13. **Garage Cleanup** (Zoë, Max!)

    - **Frequency**: Weekly (explicit recurring_frequency)
    - **Points**: 25
    - **Tests**: Weekly shared_first, 2 kids
    - **Completion Criteria**: `shared_first` (explicit)
    - **Icon**: mdi:garage
    - **Workflow**: Any kid claims → First kid approves → Chore completes

14. **Täke Öut Trash** (Zoë, Max!, Lila)

    - **Frequency**: Daily (explicit recurring_frequency)
    - **Points**: 12
    - **Tests**: Daily shared_first, 3 kids
    - **Completion Criteria**: `shared_first` (explicit)
    - **Icon**: mdi:delete
    - **Workflow**: Any kid claims → First kid approves → Chore completes

15. **Wåsh Family Car** (Zoë, Lila)
    - **Frequency**: Weekly (explicit recurring_frequency)
    - **Points**: 30
    - **Tests**: Weekly shared_first, 2 kids, higher points
    - **Completion Criteria**: `shared_first` (explicit)
    - **Icon**: mdi:car-wash
    - **Workflow**: Any kid claims → First kid approves → Chore completes

---

### CUSTOM FREQUENCY Chores (3 chores)

Non-standard recurring intervals (every N days).

16. **Refill Bird Fëeder** (Zoë)

    - **Frequency**: Custom (every 3 days)
    - **Points**: 8
    - **Tests**: Independent with custom interval
    - **Completion Criteria**: `independent` (explicit)
    - **Recurring Frequency**: `custom`
    - **Custom Interval**: 3 days
    - **Icon**: mdi:bird

17. **Clëan Pool Fïlter** (Max!, Lila)

    - **Frequency**: Custom (every 5 days)
    - **Points**: 22
    - **Tests**: Shared_first with custom interval
    - **Completion Criteria**: `shared_first` (explicit)
    - **Recurring Frequency**: `custom`
    - **Custom Interval**: 5 days
    - **Icon**: mdi:pool

18. **Wåter the plänts** (Zoë) - _Duplicate for auto-approve testing_
    - Already listed as #2 above
    - Tests custom + auto-approve combination

---

## Test Coverage Analysis

### Completion Criteria Coverage

- ✅ **Independent**: 9 chores (50%)
- ✅ **Shared_all**: 3 chores (17%)
- ✅ **Shared_first**: 3 chores (17%)
- ✅ **Custom frequency variants**: 3 chores (17%)

### Frequency Coverage

- ✅ **Daily**: 7 chores (39%)
- ✅ **Weekly**: 8 chores (44%)
- ✅ **Monthly**: 1 chore (6%)
- ✅ **Custom interval**: 2 chores (11%)

### Assignment Pattern Coverage

- ✅ **Single kid**: 6 chores (33%)
- ✅ **Two kids**: 5 chores (28%)
- ✅ **Three kids**: 7 chores (39%)

### Special Features Coverage

- ✅ **Auto-approve**: 1 chore (Water plants)
- ✅ **Custom intervals**: 2 chores (Bird feeder: 3 days, Pool filter: 5 days)
- ✅ **Chore-level due dates**: Tested via shared_all workflows
- ✅ **Per-kid due dates**: Populated for all independent chores
- ✅ **High points**: Several chores 20-30 points
- ✅ **Unicode names**: All chores use special characters for robustness testing

---

## Testing Scenarios Enabled

### Workflow Tests (test*workflow*\*.py)

1. **SHARED Regression Tests** (test_workflow_shared_regression.py)

   - `test_shared_all_approval_uses_chore_level_due_date`: Uses "Family Dinner Prep"
   - `test_shared_first_only_first_kid_claims`: Uses "Garage Cleanup"
   - `test_alternating_chore_approval_rotation`: Uses "Weekend Yard Work"
   - `test_shared_disapprove_no_advancement`: Uses "Sibling Room Cleanup"

2. **Independent Chore Tests**

   - Multi-kid coordination: "Star sweep" (3 kids)
   - Auto-approve workflows: "Water plants"
   - Different frequencies: Daily, weekly, monthly, custom

3. **Mixed Scenario Tests**
   - Independent + shared combinations
   - Different point values
   - Varying assignment patterns

### Coordinator Tests (test_coordinator.py)

- Points calculation across all chore types
- Badge maintenance with varied chore completion
- Reward redemption with diverse point sources

### Service Tests (test_services.py)

- Claim/approve operations on shared vs independent
- Due date management across frequency types
- Reset operations with comprehensive chore set

### Dashboard Tests

- Entity list rendering with 18 chores
- Filtering by type/completion criteria
- Sort by frequency, points, assignment

---

## Data Integrity Checks

### Completion Criteria Migration Safety

All 18 chores explicitly specify `completion_criteria` field to prevent migration issues:

- No reliance on deprecated `shared_chore` boolean field
- Explicit `independent`, `shared_all`, or `shared_first` values
- Migration code tested to NOT overwrite existing values

### Per-Kid Due Dates

All independent chores initialize `per_kid_due_dates` dict:

- 9 chores with per-kid tracking
- Shared chores use chore-level due date only
- Validated in coordinator.\_create_chore() method

### Storage Persistence

All fields verified to persist correctly:

- completion_criteria saved by coordinator.\_create_chore()
- No loss of custom_interval values
- Recurring frequency properly stored

---

## Usage in Tests

### Accessing Chores by Name

```python
from tests.conftest import get_chore_by_name

# Get specific chore
family_dinner = get_chore_by_name(coordinator.data, "Family Dinner Prep")
assert family_dinner["completion_criteria"] == "shared_all"

# Get custom interval chore
bird_feeder = get_chore_by_name(coordinator.data, "Refill Bird Fëeder")
assert bird_feeder["recurring_frequency"] == "custom"
assert bird_feeder["custom_interval_days"] == 3
```

### Accessing Kids by Name

```python
from tests.conftest import get_kid_by_name

zoe = get_kid_by_name(coordinator.data, "Zoë")
max_kid = get_kid_by_name(coordinator.data, "Max!")
lila = get_kid_by_name(coordinator.data, "Lila")
```

### Entity ID Construction

```python
from tests.conftest import construct_entity_id

# Get sensor entity ID
points_sensor = construct_entity_id("sensor", "Zoë", "points")
# Returns: "sensor.kc_zoe_points"

# Get chore status sensor
chore_sensor = construct_entity_id("sensor", "Zoë", "chore_status_family_dinner_prep")
```

---

## Maintenance Notes

### Adding New Chores

When adding chores to scenario_full, ensure:

1. **Explicit completion_criteria** set (no defaults)
2. **Recurring_frequency** explicitly specified if not daily
3. **Custom_interval** specified if using `recurring_frequency: custom`
4. **Per_kid_due_dates** will be auto-initialized for independent chores
5. **Unicode characters** in name for robustness testing
6. **Update header comment** with new chore count
7. **Update this documentation** with new chore details

### Validation Checklist

- [ ] YAML syntax valid: `python -c "import yaml; yaml.safe_load(open('tests/testdata_scenario_full.yaml'))"`
- [ ] Fixture loads: `pytest tests/test_config_flow.py -v`
- [ ] SHARED tests pass: `pytest tests/test_workflow_shared_regression.py -v`
- [ ] Storage debug shows completion_criteria for all chores
- [ ] No migration warnings in test output

---

## Related Documentation

- **[TESTING_AGENT_INSTRUCTIONS.md](TESTING_AGENT_INSTRUCTIONS.md)** - Test development guide
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Comprehensive testing patterns
- **[FIXTURE_GUIDE.md](FIXTURE_GUIDE.md)** - Fixture usage and scenarios
- **[docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md)** - Completion criteria system (v0.4.0+)

---

**Document Version**: 1.0
**Scenario Version**: 2.0 (18 chores)
**Last Updated**: December 28, 2025
