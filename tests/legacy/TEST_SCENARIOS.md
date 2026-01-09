# KidsChores Test Scenarios

This directory contains test data scenarios for the KidsChores integration, all based on **The Stârblüm Family** theme.

## The Stârblüm Family

A magical family living in a home with a star-filled garden. The family uses chores, badges, and rewards to teach responsibility and teamwork.

### Family Members

**Parents:**

- **Môm Astrid Stârblüm** - Gardener who loves stars
- **Dad Leo** - Adventurer who loves maps

**Kids:**

- **Zoë** (8 years old) - Loves animals
- **Max!** (6 years old) - Loves robots
- **Lila** (8 years old) - Loves painting

## Test Scenarios

### 1. Minimal Scenario (`testdata_scenario_minimal.yaml`)

**Scope:** 1 parent, 1 kid, basic setup

- **Family:** Môm Astrid + Zoë
- **Chores:** 2 (Feed the cåts, Wåter the plänts)
- **Badges:** 1 (Brønze Står - cumulative)
- **Bonuses:** 1 (Stär Sprïnkle Bonus)
- **Rewards:** 1 (Ice Créam!)
- **Progress:** Zoë has 10 points, completed 1 chore

**Test Focus:**

- Basic entity creation
- Single kid dashboard
- Simple point tracking
- Entry-level user experience

### 2. Medium Scenario (`testdata_scenario_medium.yaml`)

**Scope:** 2 parents, 2 kids, moderate complexity

- **Family:** Both parents + Zoë + Max!
- **Chores:** 4 (including 1 shared chore - Stär sweep)
- **Badges:** 2 (Brønze Står cumulative, Dåily Dëlight daily)
- **Bonuses:** 2 (Stär Sprïnkle, Mågic Mïnute)
- **Rewards:** 2 (Ice Créam!, Extra Plåytime)
- **Progress:**
  - Zoë: 35 points, earned Dåily Dëlight badge
  - Max!: 15 points, working toward first badge

**Test Focus:**

- Multi-kid coordination
- Shared chore claiming
- Badge progression and daily badges
- Reward redemption flows
- Dashboard filtering

### 3. Full Scenario (`testdata_scenario_full.yaml`)

**Scope:** 2 parents, 3 kids, complete feature set

- **Family:** All family members
- **Chores:** 7 (mix of daily, weekly, periodic, shared)
- **Badges:** 5 (3 cumulative with multipliers, 1 periodic, 1 daily)
- **Bonuses:** 2 (various point awards)
- **Rewards:** 5 (ranging from 60 to 300 points)
- **Progress:**
  - Zoë: 520 lifetime points, earned Brønze Står (1.05x multiplier), redeemed reward
  - Max!: 280 lifetime points, no badges yet
  - Lila: 310 lifetime points, earned Dåily Dëlight

**Test Focus:**

- Badge maintenance and demotion
- Point multiplier effects
- Complex reward redemption
- Shared chore multi-claiming
- Full dashboard with all cards
- Entity filtering across 3 kids
- Performance with full dataset

## Special Characters

All test data includes special characters (å, ï, ë, ø, @, !) to ensure proper:

- Unicode handling in entity IDs
- Name slugification
- Dashboard rendering
- Translation key matching
- Storage/retrieval integrity

## Using Test Scenarios

### In Fixtures

```python
import yaml
from pathlib import Path

@pytest.fixture
def minimal_family():
    with open(Path(__file__).parent / "testdata_scenario_minimal.yaml") as f:
        return yaml.safe_load(f)

@pytest.fixture
def full_family():
    with open(Path(__file__).parent / "testdata_scenario_full.yaml") as f:
        return yaml.safe_load(f)
```

### In Tests

```python
async def test_single_kid_dashboard(hass, minimal_family):
    """Test dashboard rendering with minimal scenario."""
    # Set up entities from minimal_family data
    # Test dashboard template rendering
    # Validate entity counts, points, etc.

async def test_badge_maintenance(hass, full_family):
    """Test badge maintenance with full scenario."""
    # Set up entities from full_family data
    # Simulate weekly progression
    # Test maintenance pass/fail
    # Verify multiplier changes
```

### Scenario Selection Guide

| Test Type           | Use Scenario | Reason                        |
| ------------------- | ------------ | ----------------------------- |
| Config flow         | Minimal      | Test basic setup path         |
| Options flow CRUD   | Medium       | Test entity management        |
| Badge logic         | Full         | Test multipliers, maintenance |
| Dashboard rendering | All          | Test filtering, special chars |
| Services            | Medium/Full  | Test complex interactions     |
| Performance         | Full         | Stress test with max entities |
| Edge cases          | Minimal      | Isolate specific behaviors    |

## Extending Scenarios

To create new scenarios:

1. Start with `scenario_minimal` fixture (testdata_scenario_minimal.yaml)
2. Copy to `testdata_scenario_<name>.yaml`
3. Subset or modify family members, entities, progress
4. Add test focus comment at bottom
5. Update this README with scenario details

## Data Structure

Each scenario YAML contains:

```yaml
family:
  parents: []
  kids: []
chores: []
badges: []
bonuses: []
rewards: []
progress: {} # Kid-specific completion data
```

All entities include `name`, `icon`, and type-specific attributes (points, thresholds, awards, maintenance rules, etc.).
