# KidsChores Home Configuration - Bella & Lilly

This directory contains a complete Home Assistant chore system implementation using the [KidsChores integration](https://github.com/ad-ha/kidschores-ha).

## Quick Start

### 1. Review the Design
Read the comprehensive analysis:
- **[IMPLEMENTATION_REVIEW.md](docs/IMPLEMENTATION_REVIEW.md)** - Full review, ratings, and recommendations
- **[MVP_IMPLEMENTATION_PLAN.md](docs/MVP_IMPLEMENTATION_PLAN.md)** - Step-by-step 2-week MVP setup
- **[SCALE_UP_PLAN.md](docs/SCALE_UP_PLAN.md)** - 6-month roadmap to full system
- **[BULK_CHORE_CREATION_GUIDE.md](docs/BULK_CHORE_CREATION_GUIDE.md)** - How to create 50+ chores in 15 minutes

### 2. Install KidsChores in Home Assistant
```bash
# Via HACS
Settings > HACS > Integrations > Custom Repositories
Add: https://github.com/ad-ha/kidschores-ha
Search: "KidsChores" > Install > Restart HA
```

### 3. Configure Basic Setup
```
Settings > Devices & Services > Add Integration > KidsChores

Configure:
- Points name: "Stars"
- Add kids: Bella, Lilly
- Add parent: Blake (or your name)
```

### 4. Bulk Import Chores (15 minutes vs 15 hours!)

**Install PyYAML:**
```bash
pip install pyyaml
```

**Run the import:**
```bash
cd /path/to/kidschores-ha/home-config/scripts

# Dry run first to preview
python3 import_kidschores.py \
  --dry-run \
  ../config/chores_bella_lilly.yaml \
  /config/.storage/kidschores_data

# Actually import
python3 import_kidschores.py \
  ../config/chores_bella_lilly.yaml \
  /config/.storage/kidschores_data
```

**Restart Home Assistant:**
```bash
ha core restart
```

---

## What's Included

### Configuration Files

**[config/chores_bella_lilly.yaml](config/chores_bella_lilly.yaml)**
- 30+ pre-configured chores for Bella & Lilly
- Daily, weekly, biweekly, monthly, and seasonal tasks
- Points, icons, labels, recurrence all configured
- Custody-aware (Bella-only weeks, Lilly away weeks)
- Ready to import with script

### Scripts

**[scripts/import_kidschores.py](scripts/import_kidschores.py)**
- Bulk chore import from YAML to KidsChores storage
- Automatic backups before modification
- UUID management (kid name → kid UUID conversion)
- Due date calculation based on frequency
- Dry-run mode for testing
- ~15 minutes to import 50+ chores

### Documentation

**[docs/IMPLEMENTATION_REVIEW.md](docs/IMPLEMENTATION_REVIEW.md)**
- ✅ Overall rating: **8.5/10**
- Comprehensive analysis of the design
- What works, what needs adjustment
- Technical feasibility assessment
- Risk analysis

**[docs/MVP_IMPLEMENTATION_PLAN.md](docs/MVP_IMPLEMENTATION_PLAN.md)**
- 2-week timeline: 15-20 chores
- Day-by-day checklist
- 16-20 hours total effort
- Core features only
- Prove the concept before scaling

**[docs/SCALE_UP_PLAN.md](docs/SCALE_UP_PLAN.md)**
- Month-by-month feature additions
- Bathroom rotation system (Month 2)
- Laundry expansion (Month 3)
- Banking system (Month 4-5)
- Advanced features (Month 6+)

**[docs/BULK_CHORE_CREATION_GUIDE.md](docs/BULK_CHORE_CREATION_GUIDE.md)**
- **Solves the 15-20 hour UI problem**
- 4 methods for bulk import
- Python script walkthrough
- Complete chore structure reference
- Troubleshooting guide

### Example Configurations (Future)

After MVP, we'll add:
- `config/allowance_system.yaml` - Template sensors for allowance calculation
- `config/banking_accounts.yaml` - Input helpers for banking system
- `config/automations_bathroom.yaml` - Bathroom rotation automations
- `config/automations_custody.yaml` - Custody-aware chore assignments

---

## System Overview

### Kids & Constraints
- **Bella:** Always gone Wednesdays
- **Lilly:** Gone every other week (whole week)

### Chore Categories
- **Daily:** 8 chores (blinds, lights, pets, litter)
- **Weekly:** 12 chores (laundry, rooms, bathroom, floors)
- **Bi-weekly:** 2 chores (toilet, sink rotation)
- **Monthly:** 15 chores (bathroom deep clean, sheets, Pip habitat)
- **Seasonal:** 5 chores (garden, solar)
- **Parent-only:** 8 chores (maintenance tasks)

### Allowance System
```
Allowance = Base ($10) + Bonus (extra points × $0.25)

Requirements:
- Minimum 40 points per week
- 80% of required chores completed (future implementation)

Paid: Sunday evenings
Deposited to: Checking account (with banking system)
```

### Banking System (Future - Month 4-5)
- Checking account (immediate spending)
- Savings account (earns 5% monthly interest)
- Goal tracking
- Transfer buttons
- Purchase request workflow

---

## Implementation Approach

### Phase 1: MVP (Weeks 1-2)
**Goal:** 15-20 core chores, basic allowance, prove concept

**Includes:**
- Daily chores (blinds, lights, litter, dog)
- Weekly chores (laundry, room reset, trash)
- Simple allowance (points-based)
- Manual custody toggle

**Excludes:**
- Banking system
- Complex rotations
- Bathroom deep cleaning
- Seasonal tasks
- Required chores fraction

### Phase 2: Scale-Up (Months 2-6)
**Month 2:** Bathroom rotation system
**Month 3:** Laundry expansion
**Month 4:** Banking accounts
**Month 5:** Interest & goal tracking
**Month 6:** Full feature set

### Phase 3: Maintenance (Ongoing)
- Weekly: Review allowance, adjust custody toggle
- Monthly: Rebalance point values
- Quarterly: System optimization

---

## Key Design Decisions

### Why Two Chores for Alternating Tasks?
Example: "Scoop Litter - Bella" vs "Scoop Litter - Lilly"

**Reason:** KidsChores assigns chores to specific kids. Alternating requires automation to reassign, which is complex. Easier to:
1. Create two chores (one per kid)
2. Use `applicable_days` to split them
3. Bella: Mon/Wed/Fri/Sun
4. Lilly: Tue/Thu/Sat

### Why Labels?
- **"Required"** - Used for allowance calculation (future)
- **"Bonus"** - Optional tasks for extra points
- **Area labels** (Bathroom, Bedroom, Pets) - Filtering & organization
- **Frequency labels** (Daily, Weekly, Monthly) - Dashboard grouping

### Why Manual Rotation for Some Tasks?
Bathroom toilet/sink alternation is **complex** due to:
- Custody schedule (Lilly-away weeks)
- Fairness (avoid same kid always getting toilet duty)
- Low-use weeks (bathroom on Bella-only weeks)

**Solution:** Automations in Month 2 handle this logic

---

## Cost-Benefit Analysis

### Time Investment
| Phase | Setup Time | Ongoing Time |
|-------|-----------|--------------|
| MVP Setup | 16-20 hours | 10 min/week |
| Full System | 60-100 hours total | 15 min/week |
| **With Bulk Import** | **10-15 hours** | **10 min/week** |

### Benefits
- **Reduced nagging:** Chores visible, points motivating
- **Financial literacy:** Banking teaches real concepts
- **Fair distribution:** Automated rotation prevents resentment
- **Scalable:** Add chores as kids age
- **Data-driven:** Points history shows trends

### Risks
- **Complexity overwhelm:** Mitigated by MVP approach
- **Gaming the system:** Adjust point values as needed
- **Parent fatigue:** Automation reduces burden after setup
- **Technical debt:** Well-documented for future you

---

## Frequently Asked Questions

### Q: Do I have to create all 50+ chores manually?
**A:** NO! Use the bulk import script. Takes 15 minutes instead of 15 hours.

### Q: What if Lilly's custody schedule changes?
**A:** Toggle `input_boolean.lilly_home_this_week` weekly, or set up calendar automation (Month 6).

### Q: How do I adjust point values?
**A:** Settings > Devices & Services > KidsChores > Configure > Manage Chores > Edit chore

### Q: Can I add more chores later?
**A:** Yes! Either via UI or re-run import script with updated YAML (skips existing chores).

### Q: What if kids complain about unfair rotation?
**A:** Review `input_select` history for bathroom tasks (Month 2+). Adjust automation logic if needed.

### Q: Is banking system too complex for kids?
**A:** Start simple (Month 1-3: just points). Add banking only when ready (Month 4+).

### Q: What if I break something?
**A:** Script creates automatic backups. Restore: `cp /config/backups/kidschores_data.backup.TIMESTAMP /config/.storage/kidschores_data && ha core restart`

---

## Support & Resources

**KidsChores Integration:**
- [GitHub](https://github.com/ad-ha/kidschores-ha)
- [Wiki](https://github.com/ad-ha/kidschores-ha/wiki)
- [Community Forum](https://community.home-assistant.io/t/kidschores-family-chore-management-integration)

**Home Assistant:**
- [Automation Docs](https://www.home-assistant.io/docs/automation/)
- [Template Docs](https://www.home-assistant.io/docs/configuration/templating/)

**This Project:**
- Issues? Open GitHub issue or check docs/ folder
- Questions? Review MVP_IMPLEMENTATION_PLAN.md first

---

## Success Metrics

**After MVP (2 weeks):**
- ✅ 90%+ chore completion rate
- ✅ Kids checking dashboard daily
- ✅ Parents approving within 2 hours
- ✅ < 10 min/week parent management

**After Full System (6 months):**
- ✅ System runs autonomously
- ✅ Kids setting savings goals
- ✅ Measurable cleanliness improvement
- ✅ Financial literacy demonstrated

---

## Version History

**v1.0** (2025-01-16)
- Initial design review
- MVP implementation plan
- Bulk import script
- 30+ pre-configured chores

**Planned:**
- v1.1: Banking system implementation
- v1.2: Advanced automation examples
- v1.3: Dashboard templates

---

## License

This configuration is based on the [KidsChores integration](https://github.com/ad-ha/kidschores-ha) (GPL-3.0).

Custom scripts and configurations in this directory: MIT License (use freely, attribution appreciated).

---

## Quick Links

- **Start Here:** [IMPLEMENTATION_REVIEW.md](docs/IMPLEMENTATION_REVIEW.md)
- **Get Going Fast:** [BULK_CHORE_CREATION_GUIDE.md](docs/BULK_CHORE_CREATION_GUIDE.md)
- **Step-by-Step:** [MVP_IMPLEMENTATION_PLAN.md](docs/MVP_IMPLEMENTATION_PLAN.md)
- **Long-Term Plan:** [SCALE_UP_PLAN.md](docs/SCALE_UP_PLAN.md)

**Total time to working system: 2-3 weeks**
**Total time to full system: 6 months**
**Total time saved vs manual: ~15 hours (thanks to bulk import!)**

---

**Good luck! 🎉**
