# Scale-Up Plan - MVP to Full System

**Timeline:** 6 months from MVP completion
**Approach:** Incremental monthly additions
**Goal:** Full chore system + banking + advanced features

---

## Scaling Strategy

### Core Principle: **ONE NEW FEATURE PER MONTH**

**Why gradual?**
- Kids need time to adjust to new routines
- Point values need tuning before adding complexity
- Prevents parent burnout from setup overload
- Allows course-correction before too much is built

**Each month:**
1. **Week 1:** Plan and build
2. **Week 2:** Test and refine
3. **Week 3-4:** Run in production
4. **End of month:** Review and adjust before next feature

---

## Month 1: MVP Foundation ✅

**Status:** Complete (see MVP_IMPLEMENTATION_PLAN.md)

**What's running:**
- 15 core chores (daily + weekly)
- Basic allowance ($10 + bonus for extra points)
- Simple dashboard
- Manual custody toggle

**Metrics to track:**
- Average points per week per kid
- Allowance qualification rate (should be ~80%+)
- Chore approval time (how long until parent approves?)
- System engagement (are kids checking dashboard?)

---

## Month 2: Bathroom Rotation System

**Goal:** Add proper bathroom cleaning schedule with fair rotation

### New Chores to Add (8 chores)

**Weekly Rotation (Bella & Lilly alternate):**
1. Toilet scrub (every 2 weeks)
2. Bathroom mirror clean (weekly)

**Monthly Deep Clean (Rotate each month):**
3. Mop bathroom floor
4. Scrub tub/shower
5. Dust ceiling/corners
6. Wipe baseboards
7. Clean countertop edges
8. Wash bath mat

**Point Values:**
- Toilet: 4 points
- Mirror: 2 points
- Floor/Tub: 4-5 points each
- Other monthly: 2-3 points each

### Automation to Build

**File:** `/config/automations_bathroom.yaml`

```yaml
# Track last kid who did toilet duty
input_select:
  bathroom_toilet_last_assignee:
    name: "Last Kid: Toilet Duty"
    options:
      - Bella
      - Lilly
      - None
    initial: None

  bathroom_monthly_last_assignee:
    name: "Last Kid: Monthly Deep Clean"
    options:
      - Bella
      - Lilly
      - None
    initial: None

automation:
  # Toilet rotation - every 2 weeks, alternating kid
  - id: bathroom_toilet_rotation
    alias: "Bathroom: Toilet Scrub Rotation"
    trigger:
      - platform: time
        at: "18:00:00"
    condition:
      # Every 14 days from baseline
      - condition: template
        value_template: >
          {{ (as_timestamp(now()) - as_timestamp('2025-01-12 00:00:00')) / 86400 % 14 == 0 }}
    action:
      - variables:
          last_kid: "{{ states('input_select.bathroom_toilet_last_assignee') }}"
          lilly_home: "{{ is_state('input_boolean.lilly_home_this_week', 'on') }}"
      - choose:
          # Lilly's turn (if home and last was Bella or None)
          - conditions:
              - "{{ lilly_home }}"
              - "{{ last_kid in ['Bella', 'None'] }}"
            sequence:
              - service: kidschores.set_chore_due_date
                data:
                  chore_name: "Toilet Scrub - Lilly"
                  due_date: "{{ now().replace(hour=20, minute=0, second=0).isoformat() }}"
              - service: input_select.select_option
                target:
                  entity_id: input_select.bathroom_toilet_last_assignee
                data:
                  option: "Lilly"
          # Bella's turn (default)
          - conditions: true
            sequence:
              - service: kidschores.set_chore_due_date
                data:
                  chore_name: "Toilet Scrub - Bella"
                  due_date: "{{ now().replace(hour=20, minute=0, second=0).isoformat() }}"
              - service: input_select.select_option
                target:
                  entity_id: input_select.bathroom_toilet_last_assignee
                data:
                  option: "Bella"

  # Monthly deep clean - first Saturday, alternating kid
  - id: bathroom_monthly_rotation
    alias: "Bathroom: Monthly Deep Clean Rotation"
    trigger:
      - platform: time
        at: "10:00:00"
    condition:
      - condition: time
        weekday:
          - sat
      - condition: template
        # First Saturday of month
        value_template: "{{ now().day <= 7 }}"
    action:
      - variables:
          last_kid: "{{ states('input_select.bathroom_monthly_last_assignee') }}"
          lilly_home: "{{ is_state('input_boolean.lilly_home_this_week', 'on') }}"
          this_month_kid: >
            {% if lilly_home and last_kid != 'Lilly' %}
              Lilly
            {% else %}
              Bella
            {% endif %}
      # Assign all monthly tasks to same kid
      - service: kidschores.set_chore_due_date
        data:
          chore_name: "Bathroom Floor Mop - {{ this_month_kid }}"
          due_date: "{{ now().replace(hour=14, minute=0, second=0).isoformat() }}"
      - service: kidschores.set_chore_due_date
        data:
          chore_name: "Bathroom Tub Scrub - {{ this_month_kid }}"
          due_date: "{{ (now() + timedelta(days=1)).replace(hour=14, minute=0, second=0).isoformat() }}"
      # ... repeat for other monthly tasks
      - service: input_select.select_option
        target:
          entity_id: input_select.bathroom_monthly_last_assignee
        data:
          option: "{{ this_month_kid }}"
```

### Success Metrics
- Bathroom tasks rotate fairly (check input_select history)
- Both kids complete bathroom tasks within due date
- No complaints about unfair distribution

---

## Month 3: Laundry System Expansion

**Goal:** Add towels, delicates, and extra loads for Bella-only weeks

### New Chores (4 chores)

1. **Towels - Lilly** (Wednesday, weekly)
   - Points: 3
   - Includes bathroom towels + bath mat

2. **Delicates - Bella** (Thursday, weekly)
   - Points: 3

3. **Extra Laundry - Bella** (Sun/Mon/Tue, Bella-only weeks)
   - Points: 3
   - Only active when Lilly is away

4. **Sheets - Bella** (Every 4 weeks, variable)
   - Points: 4

5. **Sheets - Lilly** (Every 4 weeks, offset from Bella)
   - Points: 4

### Automation to Build

```yaml
automation:
  # Enable/disable Bella's extra laundry based on custody
  - id: bella_extra_laundry_toggle
    alias: "Laundry: Toggle Bella Extra Load"
    trigger:
      - platform: state
        entity_id: input_boolean.lilly_home_this_week
    action:
      - choose:
          # Lilly away - enable extra load
          - conditions:
              - condition: state
                entity_id: input_boolean.lilly_home_this_week
                state: "off"
            sequence:
              - service: kidschores.set_chore_due_date
                data:
                  chore_name: "Laundry Extra - Bella"
                  due_date: "{{ now().replace(day=(now().day + 2), hour=18, minute=0, second=0).isoformat() }}"
          # Lilly home - skip/clear extra load
          - conditions: true
            sequence:
              - service: kidschores.skip_chore_due_date
                data:
                  chore_name: "Laundry Extra - Bella"
```

### Success Metrics
- Bella gets extra laundry only on Lilly-away weeks
- Towels done weekly (bath mat included)
- Sheets done monthly (each kid)

---

## Month 4: Banking System (Part 1 - Accounts)

**Goal:** Introduce checking/savings accounts and basic transfers

### New Entities

```yaml
# Add to input_number.yaml

# Checking accounts (immediate spending)
bella_checking_account:
  name: "Bella - Checking"
  min: 0
  max: 999
  step: 0.50
  mode: box
  unit_of_measurement: "$"
  icon: mdi:bank-check
  initial: 0

lilly_checking_account:
  name: "Lilly - Checking"
  min: 0
  max: 999
  step: 0.50
  mode: box
  unit_of_measurement: "$"
  icon: mdi:bank-check
  initial: 0

# Savings accounts (earns interest)
bella_savings_account:
  name: "Bella - Savings"
  min: 0
  max: 9999
  step: 0.50
  mode: box
  unit_of_measurement: "$"
  icon: mdi:piggy-bank
  initial: 0

lilly_savings_account:
  name: "Lilly - Savings"
  min: 0
  max: 9999
  step: 0.50
  mode: box
  unit_of_measurement: "$"
  icon: mdi:piggy-bank
  initial: 0

# Savings goals
bella_savings_goal:
  name: "Bella - Savings Goal"
  min: 0
  max: 500
  step: 5
  mode: box
  unit_of_measurement: "$"
  icon: mdi:bullseye-arrow
  initial: 50

lilly_savings_goal:
  name: "Lilly - Savings Goal"
  min: 0
  max: 500
  step: 5
  mode: box
  unit_of_measurement: "$"
  icon: mdi:bullseye-arrow
  initial: 50
```

### Scripts for Transfers

```yaml
# scripts.yaml

bella_deposit_to_savings:
  alias: "Bella: Deposit to Savings"
  fields:
    amount:
      description: "Amount to transfer"
      example: 10.00
  sequence:
    - variables:
        checking: "{{ states('input_number.bella_checking_account') | float(0) }}"
        savings: "{{ states('input_number.bella_savings_account') | float(0) }}"
    - condition: template
      value_template: "{{ amount <= checking }}"
    - service: input_number.set_value
      target:
        entity_id: input_number.bella_checking_account
      data:
        value: "{{ (checking - amount) | round(2) }}"
    - service: input_number.set_value
      target:
        entity_id: input_number.bella_savings_account
      data:
        value: "{{ (savings + amount) | round(2) }}"
    - service: notify.mobile_app_parent_phone
      data:
        title: "🏦 Bella Deposited to Savings"
        message: "${{ amount }} moved to savings. New balance: ${{ (savings + amount) | round(2) }}"

bella_withdraw_from_savings:
  alias: "Bella: Withdraw from Savings"
  fields:
    amount:
      description: "Amount to withdraw"
      example: 10.00
  sequence:
    - variables:
        checking: "{{ states('input_number.bella_checking_account') | float(0) }}"
        savings: "{{ states('input_number.bella_savings_account') | float(0) }}"
    - condition: template
      value_template: "{{ amount <= savings }}"
    - service: input_number.set_value
      target:
        entity_id: input_number.bella_savings_account
      data:
        value: "{{ (savings - amount) | round(2) }}"
    - service: input_number.set_value
      target:
        entity_id: input_number.bella_checking_account
      data:
        value: "{{ (checking + amount) | round(2) }}"
    - service: notify.mobile_app_parent_phone
      data:
        title: "🏦 Bella Withdrew from Savings"
        message: "${{ amount }} withdrawn. New checking balance: ${{ (checking + amount) | round(2) }}"

# Repeat for Lilly
```

### Modified Allowance Payout

```yaml
# Update allowance payout to deposit to CHECKING instead of wallet
automation:
  - id: allowance_weekly_payout_v2
    alias: "Allowance: Weekly Payout (Banking Version)"
    # ... same triggers ...
    action:
      - variables:
          bella_payout: "{{ states('sensor.bella_allowance_preview') | float(0) }}"
          lilly_payout: "{{ states('sensor.lilly_allowance_preview') | float(0) }}"
      - if:
          - condition: template
            value_template: "{{ bella_payout > 0 }}"
        then:
          - service: input_number.set_value
            target:
              entity_id: input_number.bella_checking_account  # Changed from wallet
            data:
              value: >
                {{ (states('input_number.bella_checking_account') | float(0) + bella_payout) | round(2) }}
      # ... repeat for Lilly ...
```

### Dashboard Updates

Add banking section to dashboard:

```yaml
# Dashboard card for Bella banking
type: entities
title: "💰 Bella - Banking"
entities:
  - entity: input_number.bella_checking_account
    name: "Checking"
  - entity: input_number.bella_savings_account
    name: "Savings"
  - entity: input_number.bella_savings_goal
    name: "Savings Goal"
  - type: custom:bar-card
    entity: input_number.bella_savings_account
    max: input_number.bella_savings_goal
    name: "Savings Progress"
  - type: button
    name: "Deposit $5 to Savings"
    tap_action:
      action: call-service
      service: script.bella_deposit_to_savings
      data:
        amount: 5
  - type: button
    name: "Deposit $10 to Savings"
    tap_action:
      action: call-service
      service: script.bella_deposit_to_savings
      data:
        amount: 10
```

### Success Metrics
- Kids understand checking vs savings
- Transfers work correctly (no money lost/created)
- Kids start building savings

---

## Month 5: Banking System (Part 2 - Interest & Goals)

**Goal:** Add monthly interest to encourage saving + goal tracking

### Interest Automation

```yaml
automation:
  - id: apply_monthly_interest
    alias: "Banking: Apply Monthly Interest"
    trigger:
      - platform: time
        at: "00:00:00"
    condition:
      - condition: template
        value_template: "{{ now().day == 1 }}"  # First of month
    action:
      - variables:
          bella_savings: "{{ states('input_number.bella_savings_account') | float(0) }}"
          lilly_savings: "{{ states('input_number.lilly_savings_account') | float(0) }}"
          interest_rate: 0.05  # 5% monthly (high to make it exciting)
          bella_interest: "{{ (bella_savings * interest_rate) | round(2) }}"
          lilly_interest: "{{ (lilly_savings * interest_rate) | round(2) }}"

      # Apply Bella's interest
      - service: input_number.set_value
        target:
          entity_id: input_number.bella_savings_account
        data:
          value: "{{ (bella_savings + bella_interest) | round(2) }}"

      # Apply Lilly's interest
      - service: input_number.set_value
        target:
          entity_id: input_number.lilly_savings_account
        data:
          value: "{{ (lilly_savings + lilly_interest) | round(2) }}"

      # Notify
      - service: notify.mobile_app_parent_phone
        data:
          title: "🏦 Monthly Interest Applied"
          message: >
            Bella earned ${{ bella_interest }} interest (balance: ${{ (bella_savings + bella_interest) | round(2) }})
            Lilly earned ${{ lilly_interest }} interest (balance: ${{ (lilly_savings + lilly_interest) | round(2) }})
```

### Goal Progress Sensors

```yaml
template:
  - sensor:
      - name: "Bella Savings Progress"
        unique_id: bella_savings_progress
        unit_of_measurement: "%"
        icon: mdi:percent
        state: >
          {% set current = states('input_number.bella_savings_account') | float(0) %}
          {% set goal = states('input_number.bella_savings_goal') | float(1) %}
          {{ min(100, ((current / goal) * 100) | round(0)) }}
        attributes:
          current: "{{ states('input_number.bella_savings_account') | float(0) }}"
          goal: "{{ states('input_number.bella_savings_goal') | float(0) }}"
          remaining: >
            {{ max(0, states('input_number.bella_savings_goal') | float(0) -
               states('input_number.bella_savings_account') | float(0)) | round(2) }}

      - name: "Lilly Savings Progress"
        # ... same for Lilly ...
```

### Goal Reached Notification

```yaml
automation:
  - id: savings_goal_reached
    alias: "Banking: Savings Goal Reached"
    trigger:
      - platform: numeric_state
        entity_id: input_number.bella_savings_account
        above: input_number.bella_savings_goal
      - platform: numeric_state
        entity_id: input_number.lilly_savings_account
        above: input_number.lilly_savings_goal
    action:
      - variables:
          kid_name: >
            {{ trigger.entity_id.split('_')[0] | title }}
          goal_amount: >
            {{ states('input_number.' + kid_name.lower() + '_savings_goal') }}
      - service: notify.mobile_app_parent_phone
        data:
          title: "🎉 Savings Goal Reached!"
          message: "{{ kid_name }} has saved ${{ goal_amount }}! Time to celebrate!"
```

### Success Metrics
- Interest applies correctly on 1st of month
- Kids see savings grow without effort
- Goal notifications trigger when reached

---

## Month 6: Advanced Features & Refinements

**Goal:** Add remaining chores + polish system

### Additions

**1. Seasonal Tasks**
- Garden watering (summer only)
- Vegetable harvest (in season)
- Solar panel rinse (parent task, seasonal)

```yaml
input_boolean:
  growing_season_active:
    name: "Growing Season Active"
    icon: mdi:sprout
    initial: false  # Toggle on ~April, off ~October

automation:
  # Enable garden chores when season starts
  - id: enable_garden_chores
    alias: "Garden: Enable Seasonal Chores"
    trigger:
      - platform: state
        entity_id: input_boolean.growing_season_active
        to: "on"
    action:
      - service: kidschores.set_chore_due_date
        data:
          chore_name: "Water Outdoor Plants - Bella"
          due_date: "{{ now().replace(hour=18, minute=0, second=0).isoformat() }}"
      # ... enable for Lilly too ...
```

**2. Pet Tasks Expansion**
- Pip habitat cleaning (monthly, rotating)
- Pet food refill tracking
- Litter waste bin (parent task)

**3. Required Chores Fraction**

Build the sensor referenced in original design:

```yaml
template:
  - sensor:
      - name: "Bella Required Chores Completion Fraction"
        unique_id: bella_required_chores_fraction
        unit_of_measurement: "%"
        state: >
          {% set ns = namespace(total=0, completed=0) %}
          {% set required_chores = [
            'sensor.kidschores_bella_chore_litter_scoop',
            'sensor.kidschores_bella_chore_room_reset',
            'sensor.kidschores_bella_chore_laundry',
            'sensor.kidschores_bella_chore_blinds_open',
            'sensor.kidschores_bella_chore_blinds_close'
          ] %}
          {% for chore in required_chores %}
            {% if states(chore) != 'unknown' %}
              {% set ns.total = ns.total + 1 %}
              {% if states(chore) == 'approved' %}
                {% set ns.completed = ns.completed + 1 %}
              {% endif %}
            {% endif %}
          {% endfor %}
          {{ (ns.completed / ns.total * 100) | round(0) if ns.total > 0 else 0 }}
```

**4. Allowance Requirement Update**

Add required chores threshold:

```yaml
# Update allowance preview to include required chores check
template:
  - sensor:
      - name: "Bella Allowance Preview V2"
        state: >
          {% set pts = states('sensor.kidschores_bella_points') | float(0) %}
          {% set min_pts = states('input_number.allowance_min_points') | float(40) %}
          {% set req_fraction = states('sensor.bella_required_chores_completion_fraction') | float(0) / 100 %}
          {% set req_threshold = states('input_number.allowance_required_chore_fraction') | float(0.8) %}
          {% set base = states('input_number.allowance_base_bella') | float(10) %}
          {% set bonus_rate = states('input_number.allowance_bonus_rate') | float(0.25) %}
          {% if pts >= min_pts and req_fraction >= req_threshold %}
            {{ (base + (pts - min_pts) * bonus_rate) | round(2) }}
          {% else %}
            0
          {% endif %}
```

**5. Overdue Chore Penalties (Optional)**

```yaml
automation:
  - id: penalty_for_overdue_chores
    alias: "Chores: Penalty for Overdue"
    trigger:
      - platform: time
        at: "20:00:00"  # Daily check
    action:
      # Check for overdue chores
      - variables:
          bella_overdue_count: >
            {{ states.sensor
               | selectattr('entity_id', 'search', 'kidschores_bella.*chore')
               | selectattr('state', 'eq', 'overdue')
               | list | count }}
      - if:
          - condition: template
            value_template: "{{ bella_overdue_count > 2 }}"
        then:
          - service: notify.mobile_app_parent_phone
            data:
              title: "⚠️ Chores Overdue"
              message: "Bella has {{ bella_overdue_count }} overdue chores. Consider applying penalty."
```

### Success Metrics
- All ~50 chores from original design are active
- Seasonal tasks enable/disable correctly
- Required chores fraction calculates accurately
- Allowance considers both points AND completion rate

---

## Month 7+: Maintenance & Optimization

**Ongoing tasks:**

### Weekly
- Review point accumulation trends
- Adjust point values if needed
- Handle edge cases (sick days, vacations)

### Monthly
- Review rotation fairness
- Check for "stuck" chores (always overdue)
- Celebrate achievements

### Quarterly
- Major point value rebalancing
- Add new chores as needed
- Remove chores that don't work
- Update custody schedule if changes

### Annually
- Full system review
- Update for new ages/capabilities
- Plan new features (college savings? investment tracking?)

---

## Feature Wishlist (Post-Month 6)

**If you want to go even further:**

1. **Investment Simulation**
   - Virtual "stocks" that fluctuate
   - Teach risk/reward
   - Dividends as passive income

2. **Loan System**
   - Kids can borrow from "Bank of Parents"
   - Interest charged on loans
   - Payment schedules

3. **Chore Marketplace**
   - Kids can "bid" on bonus chores
   - Higher points for less desirable tasks
   - Supply/demand dynamics

4. **Streak Bonuses**
   - 7-day streak = bonus multiplier
   - Track via KidsChores achievements

5. **Vacation Mode**
   - One-click pause all chores
   - Resume with recalculated due dates

6. **Voice Integration**
   - "Alexa, claim litter scoop for Bella"
   - Voice notifications of due chores

---

## Rollback Plan

If any month's changes cause problems:

1. **Keep automations disabled initially**
   - Test manually before enabling triggers

2. **Document working state before changes**
   - Backup `/config` folder
   - Note current point values

3. **Have rollback YAML ready**
   - Keep previous month's configs in separate folder

4. **Monitor for 1 week before considering "stable"**
   - Kids should adapt within 3-5 days
   - Longer = design problem, not adjustment period

---

## Success Indicators by Month

**Month 2:** Bathroom is consistently clean, rotations feel fair
**Month 3:** Laundry never piles up, Bella isn't overwhelmed on solo weeks
**Month 4:** Kids understand checking vs savings concept
**Month 5:** Kids excited about interest, setting goals
**Month 6:** System runs itself, minimal parent intervention

**Overall 6-Month Goal:**
- 90%+ of chores completed on time
- <10 minutes/week parent management time
- Kids independently tracking own progress
- Measurable improvement in household cleanliness
- Financial literacy concepts internalized

---

**Document Version:** 1.0
**Last Updated:** 2025-11-16
**Next:** See `FULL_DESIGN_BANKING.md` for complete banking system details
