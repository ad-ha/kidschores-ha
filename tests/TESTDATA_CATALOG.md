# KidsChores Test Data Catalog

**Version:** 1.0
**Last Updated:** 2025-12-20
**Purpose:** Quick reference guide for selecting appropriate test scenarios

---

## Quick Reference Table

| Scenario               | Kids | Parents | Chores | Badges | Rewards | Bonuses | Penalties | Complexity        | Best For                             |
| ---------------------- | ---- | ------- | ------ | ------ | ------- | ------- | --------- | ----------------- | ------------------------------------ |
| **minimal**            | 1    | 1       | 2      | 1      | 1       | 1       | 1         | ⭐ Basic          | Setup, single-kid flows              |
| **medium**             | 2    | 2       | 4      | 6      | 2       | 2       | 2         | ⭐⭐ Moderate     | Multi-kid, shared chores             |
| **full**               | 3    | 2       | 7      | 5      | 5       | 2       | 0         | ⭐⭐⭐ Complete   | Full feature coverage                |
| **full**               | 2    | 3       | 7      | 5      | 2       | 2       | 0         | ⭐⭐⭐ Complete   | Baseline reference (Stârblüm family) |
| **performance_stress** | 100  | 25      | 500+   | 18     | 30+     | 15+     | 10+       | ⭐⭐⭐⭐⭐ Stress | Performance testing                  |

---

## Detailed Scenario Descriptions

### 1. `testdata_scenario_minimal.yaml` ⭐ BASIC

**Theme:** The Stârblüm Family (Minimal Setup)
**Complexity:** Simplest possible working configuration
**File:** `tests/testdata_scenario_minimal.yaml`

#### Entities Overview

- **Kids:** 1 (Zoë, age 8)
- **Parents:** 1 (Môm Astrid Stârblüm)
- **Chores:** 2 daily chores
- **Badges:** 1 cumulative badge with maintenance
- **Rewards:** 1 reward
- **Bonuses:** 1 bonus
- **Penalties:** 1 penalty

#### Available Entities

**Kids:**

- Zoë (ha_user: kid1, interests: animals)
  - Initial points: 10
  - Completed chores: ["Feed the cåts"]

**Parents:**

- Môm Astrid Stârblüm (ha_user: parent1, role: gardener)

**Chores:**

- "Feed the cåts" → Zoë, daily, 10pts, icon:mdi:cat
- "Wåter the plänts" → Zoë, daily, 10pts, icon:mdi:watering-can

**Badges:**

- "Brønze Står" → cumulative, 400pt threshold, 1.05x multiplier
  - Maintenance: weekly, 300pt required, demote_on_fail

**Rewards:**

- "Ice Créam!" → 60pt cost, icon:mdi:ice-cream

**Bonuses:**

- "Stär Sprïnkle Bonus" → 15pts, "Extra points for helping a sibling"

**Penalties:**

- "Førget Chöre" → -5pts, "Missed a daily chore"

#### Use Cases

- ✅ Basic integration setup tests
- ✅ Single-kid dashboard rendering
- ✅ Simple point calculation
- ✅ Entity creation validation
- ✅ Badge maintenance logic
- ✅ Config flow testing

#### Search Keywords

`minimal`, `basic`, `simple`, `single kid`, `Zoë`, `setup`, `installation`

---

### 2. `testdata_scenario_medium.yaml` ⭐⭐ MODERATE

**Theme:** The Stârblüm Family (Typical Setup)
**Complexity:** Realistic family scenario with moderate complexity
**File:** `tests/testdata_scenario_medium.yaml`

#### Entities Overview

- **Kids:** 2 (Zoë age 8, Max! age 6)
- **Parents:** 2 (Môm Astrid, Dad Leo)
- **Chores:** 4 chores (including 1 shared)
- **Badges:** 6 badges (cumulative + periodic + daily + special_occasion)
- **Rewards:** 2 rewards
- **Bonuses:** 2 bonuses
- **Penalties:** 2 penalties

#### Available Entities

**Kids:**

- Zoë (ha_user: kid1, interests: animals)
  - Initial points: 35
  - Net all-time points: 350.0
  - Completed: ["Feed the cåts", "Stär sweep"]
  - Badges earned: ["Dåily Dëlight"]
- Max! (ha_user: kid2, interests: robots)
  - Initial points: 15
  - Net all-time points: 180.0
  - Completed: ["Pick up Lëgo!"]

**Parents:**

- Môm Astrid Stârblüm (ha_user: parent1)
- Dad Leo (ha_user: parent2)

**Chores:**

- "Feed the cåts" → Zoë only, daily, 10pts
- "Wåter the plänts" → Zoë only, daily, 10pts
- "Pick up Lëgo!" → Max! only, weekly, 15pts
- "Stär sweep" → **SHARED** [Zoë, Max!], periodic, 20pts ⭐

**Badges:**

- "Brønze Står" → cumulative, 400pt threshold, 1.05x multiplier
- "Sïlver Står" → cumulative, 800pt threshold, 1.15x multiplier
- "Gøld Står" → cumulative, 1600pt threshold, 1.25x multiplier
- "Wëekly Wïzard" → periodic, weekly reset (Q4 2025)
- "Dåily Dëlight" → daily, 2-chore threshold, +3pts
- "Spëcial Öccasion" → special_occasion, birthday bonus (Dec 21)

**Rewards:**

- "Ice Créam!" → 60pt cost
- "Extra Plåytime" → 40pt cost

**Bonuses:**

- "Stär Sprïnkle Bonus" → 15pts
- "Mågic Mïnute Bonus" → 10pts

**Penalties:**

- "Førget Chöre" → -5pts
- "Messÿ Røom" → -10pts

#### Use Cases

- ✅ Multi-kid coordination tests
- ✅ Shared chore workflows
- ✅ Badge progression (Bronze → Silver → Gold)
- ✅ Badge maintenance validation
- ✅ Reward redemption flows
- ✅ Special occasion badge testing (time-bound)
- ✅ Bonus/penalty application
- ✅ Point statistics tracking

#### Search Keywords

`medium`, `multi-kid`, `shared chores`, `badge progression`, `Zoë`, `Max!`, `typical`, `realistic`

---

### 3. `testdata_scenario_full.yaml` ⭐⭐⭐ COMPLETE

**Theme:** The Stârblüm Family (Full Feature Set)
**Complexity:** Comprehensive coverage of all KidsChores features
**File:** `tests/testdata_scenario_full.yaml`

#### Entities Overview

- **Kids:** 3 (Zoë, Max!, Lila)
- **Parents:** 2 (Môm Astrid, Dad Leo)
- **Chores:** 7 chores (daily, weekly, periodic, shared)
- **Badges:** 5 badges (cumulative + periodic + daily types)
- **Rewards:** 5 rewards (varied costs: 40-300pts)
- **Bonuses:** 2 bonuses
- **Penalties:** 0 (not included in full)

#### Available Entities

**Kids:**

- Zoë (age 8, interests: animals)
- Max! (age 6, interests: robots)
- Lila (age 8, interests: painting)

**Parents:**

- Môm Astrid Stârblüm
- Dad Leo

**Chores (7 total):**

- Daily: "Feed the cåts", "Wåter the plänts", "Charge Røbot", "Sweep the p@tio"
- Weekly: "Pick up Lëgo!", "Paint the rãinbow"
- Periodic: "Stär sweep" (shared by all 3 kids) ⭐

**Badges (5 types):**

- Cumulative: "Brønze Står", "Sïlver Står", "Gøld Står" (400/800/1600pt thresholds)
- Periodic: "Wëekly Wïzard" (10-chore goal)
- Daily: "Dåily Dëlight" (2-chore goal)

**Rewards (5 tiers):**

- 40pts: "Extra Plåytime"
- 60pts: "Ice Créam!"
- 120pts: "Movie Nïght"
- 200pts: "Stär Adventure Pack"
- 300pts: "Gården Picnic"

**Bonuses:**

- "Stär Sprïnkle Bonus" → 15pts
- "Mågic Mïnute Bonus" → 10pts

#### Use Cases

- ✅ Complete workflow testing (end-to-end)
- ✅ All entity type coverage
- ✅ Multi-kid dashboard rendering
- ✅ Calendar entity testing (daily/weekly/periodic chores)
- ✅ Badge earning & maintenance flows
- ✅ Reward tier selection
- ✅ Shared chore multi-approval workflows
- ✅ Point multiplier calculations

#### Search Keywords

`full`, `complete`, `comprehensive`, `all features`, `3 kids`, `Zoë`, `Max!`, `Lila`, `baseline`, `Stârblüm`

---

### 4. `testdata_scenario_full.yaml` ⭐⭐⭐ BASELINE REFERENCE (Stârblüm Family)

**Theme:** The Stârblüm Family (Canonical Baseline)
**Complexity:** Reference implementation for test standardization
**File:** `tests/testdata_scenario_full.yaml`

**NOTE:** This file is **identical to `scenario_full`** and serves as the canonical baseline. Use `scenario_full` in tests for clarity; this exists for naming consistency.

#### Use Cases

- ✅ Reference implementation for test patterns
- ✅ Baseline for deriving minimal/medium variants
- ✅ Standard fixture for consistent test data

#### Search Keywords

`baseline`, `reference`, `canonical`, `standard`, `Stârblüm family`

---

### 5. `testdata_scenario_performance_stress.yaml` ⭐⭐⭐⭐⭐ STRESS TEST

**Theme:** The Enchanted Lumière Estate
**Complexity:** Maximum scale stress testing with 24 kids, 8 parents
**File:** `tests/testdata_scenario_performance_stress.yaml`

#### Entities Overview

- **Kids:** 24 (3 age cohorts: older 10-14, middle 8-10, younger 6-8)
- **Parents:** 8 guardians with specialized roles
- **Chores:** 50+ chores (individual, shared, collaborative)
- **Badges:** 30+ badges (tiered by age cohort)
- **Rewards:** 30+ rewards (tiered costs)
- **Bonuses:** 15+ bonuses
- **Penalties:** 10+ penalties

#### Kid Cohorts

**Older Cohort (10-14 years) - Bronze/Silver/Gold badges:**

1. Elïas Thörnfield (14, robotics/coding)
2. Këjsarîn Volkova (13, mathematics/strategy)
3. Márcos Cortés-Blanche (13, sports/mechanics)
4. Søphïe Andrésson-Lumière (12, literature/history)
5. Yäsïn Müllar (12, astronomy/physics)
6. Cärlotta Sörensdöttir (12, environmental science/gardening)
7. Nïcölás de la Pöña (11, cooking/culinary arts)
8. Alëxïs Voronova (11, languages/communication)

**Middle Cohort (8-10 years) - Wizard-themed badges:** 9. Lëönardö Thörnfield (10, magic tricks/illusions) 10. Ïsabëlla Lumière (10, potion-making/brewing) 11. Rüdïger Müller (9, spellcasting/puzzles) 12. Améliä Cortés (9, enchantments/nature) 13. Örvär Sörensdöttir (9, alchemy/experiments) 14. Piërrö Voronov (8, wands/staffs)

**Younger Cohort (6-8 years) - Princess-themed badges:** 15. Zäïnab Andrésson (8, tiaras/crowns) 16. Émïlïë Blanche (8, ball gowns/dancing) 17. Rösë de la Pöña (7, castles/kingdoms) 18. Söraya Volkova (7, jewels/treasures) 19. Fëlïcïtä Müllar (7, royal duties/etiquette) 20. Lïlïanä Lumière (6, fairy tales/fantasy) 21. Kärïnä Sörensdöttir (6, magic mirrors/enchanted gardens) 22. Ëlënä de la Pöña (6, royal courts/kingdoms) 23. Màïnë Thörnfield (6, tiaras/princesses) 24. Måya Cortés-Blanche (6, fantasy/adventures)

#### Parents/Guardians (8 specialists)

1. Grandmère Céleste Lumière (estate curator, garden overseer)
2. Onkel Fjörn Søren (kitchen master, food forager)
3. Tía Marisöl Cortés (arts & crafts, library keeper)
4. Uncle Dmitri Voronov (maintenance chief, workshop guide)
5. Maman Véronique Blanche (animal care, meadow warden)
6. Däddy Sven Andrésson (logistics, supply manager)
7. Tante Ingrid Müller (wellness, activity planner)
8. Señor Raúl de la Pöña (entertainment, music curator)

#### Notable Chore Patterns

- **Shared Collaborative:** "Sweëp the Grand Halls" (3 kids work together on one task)
- **Individual Multi-Assign:** "Dust the Library Shelvës" (each kid does their own task)
- **Periodic with Recurrence:** "Stär Sweep & Moonlight Mörning" (biweekly)
- **One-Time with Due Date:** "Organize Common Spacës" (due 2025-12-27)

#### Use Cases

- ✅ Performance testing (24 kids, 50+ chores)
- ✅ Scale validation (entity limits, dashboard rendering)
- ✅ Name encoding edge cases (special characters: ë, ö, ï, ü, å, ñ)
- ✅ Multi-cohort badge testing (age-appropriate badges)
- ✅ Shared vs collaborative chore workflows
- ✅ Complex family structures (8 guardians)
- ✅ International character support (UTF-8 validation)
- ✅ Dashboard pagination/filtering
- ✅ Memory profiling & optimization

#### Search Keywords

`stress`, `performance`, `scale`, `24 kids`, `max`, `complex`, `edge cases`, `Lumière`, `estate`, `international`

---

## Entity Type Reference

### Chore Types

- **`daily`** - Recurs every day (e.g., "Feed the cåts")
- **`weekly`** - Recurs every week (e.g., "Pick up Lëgo!")
- **`periodic`** - Custom recurrence or non-recurring (e.g., "Stär sweep")
- **`shared`** - Multiple kids work together on one chore instance (collaborative)

### Badge Types

- **`cumulative`** - Based on lifetime points (e.g., Bronze/Silver/Gold)
- **`periodic`** - Based on time-bound goals (e.g., "Wëekly Wïzard")
- **`daily`** - Based on daily chore completion (e.g., "Dåily Dëlight")
- **`special_occasion`** - Time-bound event (e.g., birthday bonus)

### Badge Maintenance

- **`interval`** - How often maintenance is checked (weekly, monthly, etc.)
- **`required_points`** - Points needed to maintain badge
- **`demote_on_fail`** - Whether badge is removed if maintenance fails

---

## Fixture Selection Guide

### By Test Type

| Test Type            | Recommended Fixture | Rationale                              |
| -------------------- | ------------------- | -------------------------------------- |
| Config Flow          | `mock_config_entry` | Clean slate, no data dependencies      |
| Entity Creation      | `scenario_minimal`  | Fast, simple validation                |
| Multi-Kid Logic      | `scenario_medium`   | Realistic family with shared chores    |
| Dashboard Rendering  | `scenario_full`     | Complete feature coverage              |
| Performance/Scale    | `scenario_stress`   | Performance stress test with 100 kids  |
| Workflow Testing     | `scenario_full`     | End-to-end flows with all entity types |
| Badge Logic          | `scenario_medium`   | Multiple badge types + maintenance     |
| Calendar Integration | `scenario_full`     | Daily/weekly/periodic chores           |

### By Entity Count

| Need                    | Use This                                 |
| ----------------------- | ---------------------------------------- |
| 1 kid                   | `scenario_minimal`                       |
| 2 kids                  | `scenario_medium`                        |
| 3 kids                  | `scenario_full` fixture                  |
| 100 kids                | `scenario_stress` fixture                |
| Shared chores           | `scenario_medium` or `scenario_full`     |
| Badge maintenance       | Any scenario (all have maintenance)      |
| Special occasion badges | `scenario_medium` (has time-bound badge) |

---

## Common Testing Scenarios

### Scenario: "I need to test basic chore claim/approve workflow"

**Use:** `scenario_minimal`
**Why:** Simplest setup, single kid, 2 chores, fast execution

### Scenario: "I need to test shared chore multi-approval"

**Use:** `scenario_medium` or `scenario_full`
**Why:** Both have shared chores (Stär sweep)

### Scenario: "I need to test badge maintenance logic"

**Use:** Any scenario (all have badges with maintenance)
**Best:** `scenario_medium` (6 badge types including special_occasion)

### Scenario: "I need to test reward redemption"

**Use:** `scenario_medium` (2 rewards) or `scenario_full` (5 rewards)
**Why:** Enough points on kids to actually redeem

### Scenario: "I need to test dashboard with lots of entities"

**Use:** `scenario_stress` fixture
**Why:** 24 kids, 50+ chores - tests pagination, performance

### Scenario: "I need to test calendar entity with different recurrence types"

**Use:** `scenario_full`
**Why:** Has daily, weekly, and periodic chores

### Scenario: "I need to test special characters in names"

**Use:** ANY scenario (all use special characters)
**Best:** `scenario_stress` fixture (100 kids with international characters from multiple languages)

### Scenario: "I need to test bonus/penalty application"

**Use:** `scenario_medium` (2 bonuses, 2 penalties)
**Why:** Realistic variety without overwhelming complexity

---

## Cross-Reference: Test Files Using Scenarios

### `scenario_minimal` Used By:

- `test_calendar_scenarios.py` - Basic calendar entity tests
- `test_config_flow_direct_to_storage.py` - Config flow validation
- (Many other simple entity creation tests)

### `scenario_medium` Used By:

- `test_badge_assignment_baseline.py` - Badge assignment logic
- `test_badge_creation.py` - Badge entity creation

### `scenario_full` / `storyline` Used By:

- Integration tests requiring complete feature coverage
- End-to-end workflow tests
- Dashboard rendering tests

### `storyline_max` Used By:

- Performance benchmarking
- Scale validation tests
- UTF-8/international character tests

---

## Migration Notes

### Switching Between Scenarios

All scenarios follow the same YAML schema, so switching is straightforward:

```python
# Change this:
@pytest.fixture
def my_test_scenario(scenario_minimal):
    return scenario_minimal

# To this:
@pytest.fixture
def my_test_scenario(scenario_medium):
    return scenario_medium
```

### Accessing Data

All scenarios return: `(MockConfigEntry, dict[str, str])`
Where dict maps: `{"kid:Name": "uuid", "chore:Name": "uuid", ...}`

```python
async def test_example(hass, scenario_medium):
    config_entry, name_to_id_map = scenario_medium

    # Get kid UUID
    zoe_id = name_to_id_map["kid:Zoë"]

    # Get chore UUID
    chore_id = name_to_id_map["chore:Feed the cåts"]
```

---

## Quick Search Index

### By Keyword

- **"simple"** → `scenario_minimal`
- **"realistic"** → `scenario_medium`
- **"complete"** → `scenario_full` or `storyline`
- **"stress"** → `storyline_max`
- **"shared chore"** → `scenario_medium` or `scenario_full`
- **"badge maintenance"** → Any scenario
- **"special occasion"** → `scenario_medium`
- **"performance"** → `storyline_max`
- **"24 kids"** → `storyline_max`
- **"calendar"** → `scenario_full`

### By Kid Name

- **Zoë** → All scenarios
- **Max!** → `medium`, `full`, `storyline`
- **Lila** → `full`, `storyline`
- **Elïas, Këjsarîn, etc.** → `storyline_max` only

### By Chore Name

- **"Feed the cåts"** → All scenarios
- **"Stär sweep"** → `medium`, `full`, `storyline` (shared chore)
- **"Sweëp the Grand Halls"** → `storyline_max` (collaborative)

---

## Version History

| Version | Date       | Changes                            |
| ------- | ---------- | ---------------------------------- |
| 1.0     | 2025-12-20 | Initial catalog creation (Phase 2) |

---

**Last Updated:** 2025-12-20
**Maintainer:** Testing Infrastructure Team
**See Also:** [TESTING_AGENT_INSTRUCTIONS.md](TESTING_AGENT_INSTRUCTIONS.md), [TESTING_GUIDE.md](TESTING_GUIDE.md), [FIXTURE_GUIDE.md](FIXTURE_GUIDE.md)
