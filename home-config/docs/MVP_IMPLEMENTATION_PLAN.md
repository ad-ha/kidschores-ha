# MVP Implementation Plan - KidsChores System

**Goal:** Get a working chore system operational in **2 weeks** with **core functionality only**

**Timeline:** 2 weeks (10-20 hours total effort)
**Outcome:** 15-20 chores, basic allowance, functional rotation

---

## MVP Scope - What's Included

### Core Chores (15 total)

**Daily (6 chores x 2 kids = 12 entries)**
1. Open blinds (morning)
2. Close blinds (evening)
3. Turn on plant lights (morning)
4. Turn off plant lights (evening)
5. Scoop cat litter
6. Let dog out after school

**Weekly (4 chores, rotating)**
7. Bella: Weekly laundry
8. Lilly: Weekly laundry (when home)
9. Bella: Bathroom sink clean (alternating weeks)
10. Lilly: Bathroom sink clean (alternating weeks)

**Weekly (5 chores, individual)**
11. Bella: Room reset (Wednesday)
12. Lilly: Room reset (Wednesday, when home)
13. Empty bathroom trash (Thursday)
14. Sweep kitchen (2x/week, whoever volunteers)
15. Pip feeding - Lilly (Wednesday)

### Core Features
- ✅ Points accumulation
- ✅ Basic allowance calculation ($10 base if >40 points)
- ✅ Weekly payout automation
- ✅ Custody week toggle (manual)
- ✅ Simple dashboard

### What's NOT in MVP
- ❌ All bathroom deep cleaning (monthly tasks)
- ❌ Sheets/towels/delicates (laundry variations)
- ❌ Banking/savings/interest
- ❌ Complex rotations (toilet scrub, tub, floor)
- ❌ Seasonal tasks (garden, solar)
- ❌ Required chores fraction tracking
- ❌ Advanced dashboards
- ❌ Automated custody schedule
- ❌ Parent maintenance tasks
- ❌ Pip habitat cleaning
- ❌ Penalty/bonus tracking
- ❌ Achievements/challenges (use KidsChores built-in)

**MVP Philosophy:** Prove the concept works before investing in full complexity

---

## Week-by-Week Implementation

### Week 1: Foundation & Setup (8-10 hours)

#### Day 1-2: Install & Configure KidsChores (3 hours)

**Tasks:**
1. Install KidsChores via HACS
   ```
   HACS > Integrations > Custom Repositories
   Add: https://github.com/ad-ha/kidschores-ha
   Search: "KidsChores" > Install > Restart HA
   ```

2. Add integration
   ```
   Settings > Devices & Services > Add Integration > KidsChores
   ```

3. Configure via UI:
   - **Points Settings:**
     - Currency name: "Stars"
     - Icon: `mdi:star`

   - **Add Kids:**
     - Name: Bella
     - Icon: `mdi:account-child` (or custom)
     - Name: Lilly
     - Icon: `mdi:account-child-circle`

   - **Add Parent:**
     - Name: Blake (or primary parent name)
     - Role: Parent

**Validation:**
- Check Entities: `sensor.kidschores_bella_points` exists
- Check Services: `kidschores.claim_chore` available in Developer Tools

---

#### Day 3-4: Create Core Daily Chores (4 hours)

**Process:**
Settings > Devices & Services > KidsChores > Configure > Manage Chores

**Create these chores** (use checklist format):

**For BELLA:**

□ **Chore:** Blinds - Open (Morning)
  - Description: Open all blinds in common areas
  - Icon: `mdi:blinds-open`
  - Points: 1
  - Recurrence: Daily
  - Due time: 09:00
  - Labels: Required

□ **Chore:** Blinds - Close (Evening)
  - Description: Close all blinds after 5pm
  - Icon: `mdi:blinds`
  - Points: 1
  - Recurrence: Daily
  - Due time: 18:00
  - Labels: Required

□ **Chore:** Plant Lights - On
  - Description: Turn on grow lights
  - Icon: `mdi:lightbulb-on`
  - Points: 1
  - Recurrence: Daily
  - Due time: 09:00
  - Labels: Required

□ **Chore:** Plant Lights - Off
  - Description: Turn off grow lights
  - Icon: `mdi:lightbulb-off`
  - Points: 1
  - Recurrence: Daily
  - Due time: 18:00
  - Labels: Required

□ **Chore:** Litter Scoop
  - Description: Scoop cat litter box
  - Icon: `mdi:cat`
  - Points: 3
  - Recurrence: Daily
  - Due time: 17:00
  - Labels: Required
  - Note: "Rotate with Lilly by day of week"

□ **Chore:** Dog - After School
  - Description: Let dog out when home from school
  - Icon: `mdi:dog`
  - Points: 2
  - Recurrence: Mon, Tue, Thu, Fri (school days, not Wed)
  - Due time: 16:00
  - Labels: Required

**Repeat for LILLY** (same chores, but):
- Dog duty: Only Mon, Tue (not Wed when gone)
- Litter: Alternate days from Bella

---

#### Day 5-6: Create Weekly Chores (2 hours)

**For BELLA:**

□ **Chore:** Laundry - Bella
  - Description: Wash, dry, fold, and put away your laundry
  - Icon: `mdi:washing-machine`
  - Points: 4
  - Recurrence: Weekly (Sunday)
  - Due time: 18:00
  - Labels: Required

□ **Chore:** Room Reset
  - Description: Full room clean - floor clear, trash out, surfaces clean
  - Icon: `mdi:home-floor-1`
  - Points: 5
  - Recurrence: Weekly (Wednesday)
  - Due time: 20:00
  - Labels: Required

□ **Chore:** Bathroom Sink - Bella
  - Description: Clean faucet, handles, and sink bowl
  - Icon: `mdi:faucet`
  - Points: 3
  - Recurrence: Every 2 weeks (alternating)
  - Due date: Manual (set first Thursday)
  - Labels: Required

**For LILLY:**

□ **Chore:** Laundry - Lilly
  - Description: Wash, dry, fold, and put away your laundry
  - Icon: `mdi:washing-machine`
  - Points: 4
  - Recurrence: Weekly (Tuesday, when home)
  - Due time: 18:00
  - Labels: Required
  - Note: "Skip when Lilly is away"

□ **Chore:** Room Reset - Lilly
  - Description: Full room clean
  - Icon: `mdi:home-floor-1`
  - Points: 5
  - Recurrence: Weekly (Wednesday, when home)
  - Due time: 20:00
  - Labels: Required

□ **Chore:** Bathroom Sink - Lilly
  - Description: Clean faucet, handles, and sink bowl
  - Icon: `mdi:faucet`
  - Points: 3
  - Recurrence: Every 2 weeks (alternating with Bella)
  - Due date: Manual
  - Labels: Required

**SHARED CHORES:**

□ **Chore:** Bathroom Trash
  - Description: Empty bathroom trash can
  - Icon: `mdi:delete-empty`
  - Points: 2
  - Recurrence: Weekly (Thursday)
  - Due time: 18:00
  - Assignees: Both (or rotate via automation)
  - Labels: Required

□ **Chore:** Sweep Kitchen
  - Description: Sweep kitchen and entry areas
  - Icon: `mdi:broom`
  - Points: 3
  - Recurrence: 3x per week (Mon, Wed, Fri)
  - Due time: 18:00
  - Assignees: Whoever volunteers
  - Labels: Bonus (not required)

□ **Chore:** Pip Feeding (Lilly)
  - Description: Feed Pip worms and handle for exercise
  - Icon: `mdi:snake`
  - Points: 3
  - Recurrence: Weekly (Wednesday)
  - Due time: 17:00
  - Assignee: Lilly only
  - Labels: Required

---

#### Day 7: Create Helper Entities (1 hour)

Create file: `/config/input_boolean.yaml`

```yaml
# Custody schedule tracker
lilly_home_this_week:
  name: "Lilly Home This Week"
  icon: mdi:account-child
  initial: on  # Set based on current week
```

Create file: `/config/input_number.yaml`

```yaml
# Allowance settings
allowance_min_points:
  name: "Weekly Minimum Points for Allowance"
  min: 0
  max: 200
  step: 5
  unit_of_measurement: "points"
  icon: mdi:star-check
  initial: 40

allowance_base_bella:
  name: "Base Allowance - Bella"
  min: 0
  max: 50
  step: 0.50
  mode: box
  unit_of_measurement: "$"
  initial: 10

allowance_base_lilly:
  name: "Base Allowance - Lilly"
  min: 0
  max: 50
  step: 0.50
  mode: box
  unit_of_measurement: "$"
  initial: 10

allowance_bonus_rate:
  name: "Bonus Rate per Extra Point"
  min: 0
  max: 5
  step: 0.05
  mode: box
  unit_of_measurement: "$/point"
  initial: 0.25

# Allowance wallets
allowance_wallet_bella:
  name: "Allowance Wallet - Bella"
  min: 0
  max: 999
  step: 0.50
  mode: box
  unit_of_measurement: "$"
  initial: 0

allowance_wallet_lilly:
  name: "Allowance Wallet - Lilly"
  min: 0
  max: 999
  step: 0.50
  mode: box
  unit_of_measurement: "$"
  initial: 0
```

Add to `/config/configuration.yaml`:

```yaml
input_boolean: !include input_boolean.yaml
input_number: !include input_number.yaml
```

**Restart Home Assistant**

---

### Week 2: Automation & Testing (8 hours)

#### Day 8-9: Build Allowance Calculation (3 hours)

Create file: `/config/templates.yaml`

```yaml
template:
  # Allowance preview sensors
  - sensor:
      - name: "Bella Allowance Preview"
        unique_id: bella_allowance_preview
        unit_of_measurement: "$"
        icon: mdi:cash-check
        state: >
          {% set pts = states('sensor.kidschores_bella_points') | float(0) %}
          {% set min_pts = states('input_number.allowance_min_points') | float(40) %}
          {% set base = states('input_number.allowance_base_bella') | float(10) %}
          {% set bonus_rate = states('input_number.allowance_bonus_rate') | float(0.25) %}
          {% if pts >= min_pts %}
            {{ (base + (pts - min_pts) * bonus_rate) | round(2) }}
          {% else %}
            0
          {% endif %}
        attributes:
          points_earned: "{{ states('sensor.kidschores_bella_points') | float(0) }}"
          points_needed: "{{ states('input_number.allowance_min_points') | float(40) }}"
          points_above_min: >
            {{ max(0, states('sensor.kidschores_bella_points') | float(0) -
               states('input_number.allowance_min_points') | float(40)) }}
          qualified: >
            {{ states('sensor.kidschores_bella_points') | float(0) >=
               states('input_number.allowance_min_points') | float(40) }}

      - name: "Lilly Allowance Preview"
        unique_id: lilly_allowance_preview
        unit_of_measurement: "$"
        icon: mdi:cash-check
        state: >
          {% set pts = states('sensor.kidschores_lilly_points') | float(0) %}
          {% set min_pts = states('input_number.allowance_min_points') | float(40) %}
          {% set base = states('input_number.allowance_base_lilly') | float(10) %}
          {% set bonus_rate = states('input_number.allowance_bonus_rate') | float(0.25) %}
          {% if pts >= min_pts %}
            {{ (base + (pts - min_pts) * bonus_rate) | round(2) }}
          {% else %}
            0
          {% endif %}
        attributes:
          points_earned: "{{ states('sensor.kidschores_lilly_points') | float(0) }}"
          points_needed: "{{ states('input_number.allowance_min_points') | float(40) }}"
          points_above_min: >
            {{ max(0, states('sensor.kidschores_lilly_points') | float(0) -
               states('input_number.allowance_min_points') | float(40)) }}
          qualified: >
            {{ states('sensor.kidschores_lilly_points') | float(0) >=
               states('input_number.allowance_min_points') | float(40) }}
```

Add to `configuration.yaml`:
```yaml
template: !include templates.yaml
```

**Restart HA and verify:**
- `sensor.bella_allowance_preview` exists
- Shows correct calculation

---

#### Day 10: Create Weekly Payout Automation (2 hours)

Create file: `/config/automations.yaml` (or add to existing)

```yaml
# Weekly allowance payout
- id: allowance_weekly_payout
  alias: "Allowance: Weekly Payout"
  description: "Pay allowance every Sunday evening if qualified"

  trigger:
    - platform: time
      at: "20:00:00"

  condition:
    - condition: time
      weekday:
        - sun

  action:
    # Get payout amounts
    - variables:
        bella_payout: "{{ states('sensor.bella_allowance_preview') | float(0) }}"
        lilly_payout: "{{ states('sensor.lilly_allowance_preview') | float(0) }}"
        bella_current: "{{ states('input_number.allowance_wallet_bella') | float(0) }}"
        lilly_current: "{{ states('input_number.allowance_wallet_lilly') | float(0) }}"

    # Pay Bella if qualified
    - if:
        - condition: template
          value_template: "{{ bella_payout > 0 }}"
      then:
        - service: input_number.set_value
          target:
            entity_id: input_number.allowance_wallet_bella
          data:
            value: "{{ (bella_current + bella_payout) | round(2) }}"

        - service: notify.mobile_app_parent_phone  # Adjust to your device
          data:
            title: "💰 Allowance Paid"
            message: "Bella earned ${{ bella_payout }} this week!"

    # Pay Lilly if qualified
    - if:
        - condition: template
          value_template: "{{ lilly_payout > 0 }}"
      then:
        - service: input_number.set_value
          target:
            entity_id: input_number.allowance_wallet_lilly
          data:
            value: "{{ (lilly_current + lilly_payout) | round(2) }}"

        - service: notify.mobile_app_parent_phone
          data:
            title: "💰 Allowance Paid"
            message: "Lilly earned ${{ lilly_payout }} this week!"

    # Notify if anyone didn't qualify
    - if:
        - condition: template
          value_template: "{{ bella_payout == 0 }}"
      then:
        - service: notify.mobile_app_parent_phone
          data:
            title: "⚠️ Allowance Not Earned"
            message: "Bella didn't meet the 40-point minimum this week."

    - if:
        - condition: template
          value_template: "{{ lilly_payout == 0 }}"
      then:
        - service: notify.mobile_app_parent_phone
          data:
            title: "⚠️ Allowance Not Earned"
            message: "Lilly didn't meet the 40-point minimum this week."

  mode: single
```

**Note:** Adjust `notify.mobile_app_parent_phone` to match your actual notification entity

---

#### Day 11-12: Create Simple Dashboard (2 hours)

Create dashboard card:

```yaml
type: vertical-stack
cards:
  # Header
  - type: markdown
    content: |
      # 🏠 Kids Chore System
      **Current Week:** {{ 'Both Home' if is_state('input_boolean.lilly_home_this_week', 'on') else 'Bella Only' }}

  # Bella section
  - type: custom:mushroom-title-card
    title: "⭐ Bella"

  - type: horizontal-stack
    cards:
      - type: custom:mushroom-entity-card
        entity: sensor.kidschores_bella_points
        name: "Points This Week"
        icon: mdi:star
        primary_info: state
        secondary_info: none

      - type: custom:mushroom-entity-card
        entity: sensor.bella_allowance_preview
        name: "Allowance Preview"
        icon: mdi:cash-check
        primary_info: state
        secondary_info: none

      - type: custom:mushroom-entity-card
        entity: input_number.allowance_wallet_bella
        name: "Wallet"
        icon: mdi:wallet
        primary_info: state
        secondary_info: none

  # Lilly section
  - type: custom:mushroom-title-card
    title: "⭐ Lilly"

  - type: horizontal-stack
    cards:
      - type: custom:mushroom-entity-card
        entity: sensor.kidschores_lilly_points
        name: "Points This Week"
        icon: mdi:star
        primary_info: state
        secondary_info: none

      - type: custom:mushroom-entity-card
        entity: sensor.lilly_allowance_preview
        name: "Allowance Preview"
        icon: mdi:cash-check
        primary_info: state
        secondary_info: none

      - type: custom:mushroom-entity-card
        entity: input_number.allowance_wallet_lilly
        name: "Wallet"
        icon: mdi:wallet
        primary_info: state
        secondary_info: none

  # Controls
  - type: entities
    title: "Settings"
    entities:
      - entity: input_boolean.lilly_home_this_week
        name: "Lilly Home This Week"
      - entity: input_number.allowance_min_points
        name: "Minimum Points"
```

**Alternative: Use built-in KidsChores dashboard**
- KidsChores may provide auto-generated dashboards
- Check integration documentation for templates

---

#### Day 13-14: Testing & Refinement (1 hour)

**Test Scenarios:**

□ **Test 1: Claim a chore**
  - Bella claims "Litter Scoop"
  - Verify notification sent to parent
  - Parent approves via notification
  - Verify points added to `sensor.kidschores_bella_points`

□ **Test 2: Daily chore cycle**
  - Complete blinds/plant lights for 2 days
  - Verify points accumulate correctly
  - Check recurrence creates new instance next day

□ **Test 3: Allowance calculation**
  - Manually set Bella points to 45
  - Verify `sensor.bella_allowance_preview` = $11.25
    - Base: $10
    - Bonus: 5 points × $0.25 = $1.25
  - Set points to 35
  - Verify preview = $0 (below minimum)

□ **Test 4: Weekly payout**
  - Set Bella points to 50
  - Manually trigger automation (or wait for Sunday 8pm)
  - Verify `input_number.allowance_wallet_bella` increases
  - Verify notification sent

□ **Test 5: Custody week toggle**
  - Toggle `input_boolean.lilly_home_this_week` to OFF
  - Verify Lilly's school-day chores show as due (or skipped)
  - Verify dashboard shows "Bella Only Week"

**Fix any issues before proceeding**

---

## Success Criteria - MVP Complete When:

✅ All 15 core chores created and assigned
✅ Daily chores auto-recur
✅ Weekly chores scheduled correctly
✅ Points accumulate when chores approved
✅ Allowance preview calculates correctly
✅ Weekly payout automation works
✅ Dashboard displays all key metrics
✅ Custody week toggle functional
✅ Both kids and parents can claim/approve via mobile
✅ System runs for 1 full week without manual intervention

---

## Known Limitations of MVP

1. **No automatic custody schedule** - Manual toggle required
2. **No bathroom deep cleaning** - Only sink rotation included
3. **No "required chores" enforcement** - Just point threshold
4. **No banking/savings** - Only wallet tracking
5. **No complex rotations** - Bathroom alternates by week only
6. **No laundry variations** - Just one load per kid per week
7. **No seasonal tasks** - No garden/solar
8. **Manual chore reschedule on skip** - No automation for "Lilly away" weeks

**These are features, not bugs** - They're intentionally deferred to prove core concept first.

---

## Troubleshooting Common MVP Issues

### Issue: Points not accumulating
**Solution:** Check that:
- Parent approved (not just claimed)
- Chore has points value set
- Entity refresh delay (wait 30 seconds)

### Issue: Allowance shows $0 despite points
**Solution:**
- Verify sensor entity names match template
- Check Developer Tools > States for actual values
- Ensure points >= minimum threshold

### Issue: Chores not recurring
**Solution:**
- Recurrence must be set in chore config
- Due date must be in future
- Check KidsChores logs for errors

### Issue: Notifications not sending
**Solution:**
- Verify mobile app integration configured
- Check notification entity name
- Test with manual service call first

---

## Next Steps After MVP

Once MVP is stable for 2 weeks:

1. **Week 3-4:** Add bathroom deep cleaning tasks (see Scale-Up Plan)
2. **Week 5-6:** Implement banking system
3. **Week 7-8:** Add laundry variations and sheets
4. **Week 9-12:** Complex rotations and seasonal tasks

**Do not rush this** - Let the simple system prove itself first.

---

## MVP Checklist - Print and Track

**Week 1:**
- [ ] Day 1-2: Install KidsChores
- [ ] Day 3-4: Create daily chores (6 types × 2 kids)
- [ ] Day 5-6: Create weekly chores (9 chores)
- [ ] Day 7: Create helper entities

**Week 2:**
- [ ] Day 8-9: Build allowance templates
- [ ] Day 10: Create payout automation
- [ ] Day 11-12: Build dashboard
- [ ] Day 13-14: Test all scenarios

**Week 3:**
- [ ] Run system for full week
- [ ] Gather feedback from kids
- [ ] Adjust point values if needed
- [ ] Decide: proceed to scale-up or refine MVP?

**Estimated Total Time:** 16-20 hours spread over 2-3 weeks

---

**Document Version:** 1.0
**Last Updated:** 2025-11-16
**Next:** See `SCALE_UP_PLAN.md` for month-by-month feature additions
