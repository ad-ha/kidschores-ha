"""Legacy test suite.

These tests use direct coordinator manipulation and YAML-based test data loading.
They provide regression coverage but don't exercise the full integration flow.

For new tests, use the modern patterns in tests/ which:
- Use real config flow to create entities
- Test through Home Assistant service calls
- Verify state via entity attributes and dashboard helpers

Tests here will be gradually migrated to modern patterns as we validate them.
"""
