"""Test dashboard Jinja template rendering.

Tests that the KidsChores dashboard YAML templates render correctly
with integration data, ensuring frontend compatibility.
"""

# pylint: disable=redefined-outer-name  # pytest fixtures redefine names
# pylint: disable=unused-argument  # fixtures needed for test setup

from datetime import timedelta

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.template import Template
from homeassistant.util import dt as dt_util


@pytest.fixture
def kid_name():
    """Return test kid name."""
    return "Alice"


@pytest.fixture
def kid_slug(kid_name):
    """Return slugified kid name."""
    return kid_name.lower()


@pytest.fixture
async def dashboard_entities(hass: HomeAssistant, kid_slug: str):
    """Set up entity states for dashboard testing."""
    # Dashboard helper sensor with translations and entity lists
    hass.states.async_set(
        f"sensor.kc_{kid_slug}_ui_dashboard_helper",
        "available",
        {
            "ui_translations": {
                "welcome": "Welcome",
                "your_points": "Your Points",
                "weekly_completed": "This Week",
                "todays_completed": "Today's Completed",
                "overdue": "Overdue",
                "due_today": "Due Today",
                "due_this_week": "Due This Week",
                "upcoming_bonus": "Upcoming",
                "no_chores": "No chores available",
                "no_rewards": "No rewards available",
                "no_badges": "No badges available",
                "card_chores": "My Chores",
                "card_rewards": "My Rewards",
                "card_showcase": "Showcase",
                "card_badges": "My Badges",
            },
            "chores": [
                {"eid": "sensor.kc_chore_make_bed", "name": "Make Bed"},
                {"eid": "sensor.kc_chore_dishes", "name": "Dishes"},
            ],
            "rewards": [
                {"eid": "sensor.kc_reward_ice_cream", "name": "Ice Cream"},
            ],
            "badges": [
                {"eid": "sensor.kc_badge_bronze", "name": "Bronze Badge"},
                {"eid": "sensor.kc_badge_silver", "name": "Silver Badge"},
            ],
            "chores_by_label": {
                "Kitchen": ["sensor.kc_chore_dishes"],
                "Bedroom": ["sensor.kc_chore_make_bed"],
            },
        },
    )

    # Points sensor
    hass.states.async_set(
        f"sensor.kc_{kid_slug}_points",
        "250",
        {
            "unit_of_measurement": "Points",
            "icon": "mdi:star",
            "friendly_name": "Alice Points",
        },
    )

    # Chores completed total sensor
    hass.states.async_set(
        f"sensor.kc_{kid_slug}_chores_completed_total",
        "42",
        {
            "chore_stat_approved_week": 8,
            "chore_stat_approved_today": 3,
            "friendly_name": "Alice Chores Completed",
        },
    )

    # Highest badge sensor
    hass.states.async_set(
        f"sensor.kc_{kid_slug}_highest_badge",
        "Silver Badge",
        {
            "icon": "mdi:medal",
            "awards": {"points_multiplier": 1.5},
            "current_badge_name": "Silver Badge",
            "next_higher_badge_name": "Gold Badge",
            "next_lower_badge_name": "Bronze Badge",
            "points_to_next_badge": 50,
            "badge_status": "active",
            "cycle_points": 100,
            "maintenance_end_date": (dt_util.now() + timedelta(days=7)).isoformat(),
            "maintenance_grace_end_date": (
                dt_util.now() + timedelta(days=14)
            ).isoformat(),
            "maintenance_points_required": 100,
            "maintenance_points_remaining": 50,
            "last_awarded_date": (dt_util.now() - timedelta(days=30)).isoformat(),
            "award_count": 2,
            "friendly_name": "Alice Highest Badge",
        },
    )

    # Individual chore sensors
    hass.states.async_set(
        "sensor.kc_chore_make_bed",
        "available",
        {
            "friendly_name": "Make Bed",
            "chore_name": "Make Bed",
            "chore_points": 10,
            "chore_state": "available",
            "chore_type": "daily",
            "chore_due_date": dt_util.now().isoformat(),
            "kids_assigned": ["Alice"],
            "icon": "mdi:bed",
        },
    )

    hass.states.async_set(
        "sensor.kc_chore_dishes",
        "claimed",
        {
            "friendly_name": "Dishes",
            "chore_name": "Dishes",
            "chore_points": 15,
            "chore_state": "claimed",
            "chore_type": "daily",
            "chore_due_date": (dt_util.now() - timedelta(days=1)).isoformat(),
            "kids_assigned": ["Alice"],
            "icon": "mdi:silverware",
        },
    )

    # Individual reward sensors
    hass.states.async_set(
        "sensor.kc_reward_ice_cream",
        "available",
        {
            "friendly_name": "Ice Cream",
            "reward_name": "Ice Cream",
            "reward_points": 50,
            "reward_state": "available",
            "kids_assigned": ["Alice"],
            "icon": "mdi:ice-cream",
        },
    )

    # Individual badge sensors
    hass.states.async_set(
        "sensor.kc_badge_bronze",
        "earned",
        {
            "friendly_name": "Bronze Badge",
            "badge_name": "Bronze Badge",
            "badge_type": "cumulative",
            "threshold": 100,
            "kids_assigned": ["Alice"],
            "kids_earned": ["Alice"],
            "icon": "mdi:medal",
            "awards": {"points_multiplier": 1.2},
        },
    )

    hass.states.async_set(
        "sensor.kc_badge_silver",
        "earned",
        {
            "friendly_name": "Silver Badge",
            "badge_name": "Silver Badge",
            "badge_type": "cumulative",
            "threshold": 250,
            "kids_assigned": ["Alice"],
            "kids_earned": ["Alice"],
            "icon": "mdi:medal",
            "awards": {"points_multiplier": 1.5},
        },
    )


class TestDashboardWelcomeCard:
    """Test welcome card template rendering."""

    async def test_welcome_card_renders(
        self, hass: HomeAssistant, dashboard_entities, kid_name: str, kid_slug: str
    ):
        """Test welcome card template renders without errors."""
        template_str = (
            """
{%- set Kid_name = '"""
            + kid_name
            + """' -%}
{%- set Kid_name_normalize = Kid_name | slugify() -%}
{%- set dashboard_helper = 'sensor.kc_' ~ Kid_name_normalize ~ '_ui_dashboard_helper' -%}
{%- set points_sensor = 'sensor.kc_' ~ Kid_name_normalize ~ '_points' -%}
{%- set total_sensor = 'sensor.kc_' ~ Kid_name_normalize ~ '_chores_completed_total' -%}
{%- set highest_badge_entity = 'sensor.kc_' ~ Kid_name_normalize ~ '_highest_badge' -%}

{%- set ui = (state_attr(dashboard_helper, 'ui_translations') or {}) -%}
{%- set points = states(points_sensor) | int(default=0) -%}
{%- set points_label = state_attr(points_sensor, 'unit_of_measurement') -%}
{%- set weekly_completed = state_attr(total_sensor, 'chore_stat_approved_week') | int(default=0) -%}
{%- set todays_completed = state_attr(total_sensor, 'chore_stat_approved_today') | int(default=0) -%}
{%- set highest_badge = states(highest_badge_entity) or 'None' -%}

{%- set content =
  "## 👋 " ~ ui.get('welcome', 'err-welcome') ~ ", " ~ Kid_name ~ "! \\n"
  ~ "**⭐ " ~ ui.get('your_points', 'err-your_points') ~ ":** &nbsp;&nbsp;" ~ points ~ " " ~ points_label ~ "  \\n"
  ~ "**📅 " ~ ui.get('weekly_completed', 'err-weekly_completed') ~ ":** &nbsp;&nbsp;" ~ weekly_completed ~ "  \\n"
  ~ "**☀️ " ~ ui.get('todays_completed', 'err-todays_completed') ~ ":** &nbsp;&nbsp;" ~ todays_completed ~ "  \\n\\n"
-%}
{{ content }}
"""
        )
        template = Template(template_str, hass)
        result = template.async_render()

        assert result is not None
        assert "Welcome" in result
        assert kid_name in result
        assert "250" in result
        assert "Points" in result
        assert "8" in result  # weekly completed
        assert "3" in result  # today's completed
        assert "err-" not in result  # No missing translation errors

    async def test_welcome_card_handles_missing_data(
        self, hass: HomeAssistant, kid_name: str
    ):
        """Test welcome card gracefully handles missing entities."""
        # Don't set up entities - test default handling
        template_str = (
            """
{%- set Kid_name = '"""
            + kid_name
            + """' -%}
{%- set Kid_name_normalize = Kid_name | slugify() -%}
{%- set dashboard_helper = 'sensor.kc_' ~ Kid_name_normalize ~ '_ui_dashboard_helper' -%}
{%- set points_sensor = 'sensor.kc_' ~ Kid_name_normalize ~ '_points' -%}

{%- set ui = (state_attr(dashboard_helper, 'ui_translations') or {}) -%}
{%- set points = states(points_sensor) | int(default=0) -%}
{{ points }}
"""
        )
        template = Template(template_str, hass)
        result = template.async_render()

        assert result == 0  # Should default to 0 when sensor missing


class TestDashboardChoresCard:
    """Test chores card template rendering."""

    async def test_chores_card_renders(
        self, hass: HomeAssistant, dashboard_entities, kid_name: str, kid_slug: str
    ):
        """Test chores card template renders without errors."""
        template_str = (
            """
{%- set Kid_name = '"""
            + kid_name
            + """' -%}
{%- set Kid_name_normalize = Kid_name | slugify() -%}
{%- set dashboard_helper = 'sensor.kc_' ~ Kid_name_normalize ~ '_ui_dashboard_helper' -%}
{%- set points_sensor = 'sensor.kc_' ~ Kid_name_normalize ~ '_points' -%}
{%- set points_label = state_attr(points_sensor, 'unit_of_measurement') -%}

{%- set ui = state_attr(dashboard_helper, 'ui_translations') or {} -%}
{%- set chore_list = state_attr(dashboard_helper, 'chores') | default([], true) -%}

{%- set ns = namespace(chore_count=0) -%}
{%- for chore in chore_list -%}
  {%- set chore_sensor_id = chore.eid if chore is mapping else chore -%}
  {%- set chore_name = state_attr(chore_sensor_id, 'chore_name') -%}
  {%- if chore_name -%}
    {%- set ns.chore_count = ns.chore_count + 1 -%}
  {%- endif -%}
{%- endfor -%}
{{ ns.chore_count }}
"""
        )
        template = Template(template_str, hass)
        result = template.async_render()

        assert result == 2  # Should find both chores

    async def test_chores_card_processes_state_colors(
        self, hass: HomeAssistant, dashboard_entities, kid_slug: str
    ):
        """Test chore state determines correct icon color."""
        template_str = """
{%- set chore_sensor_id = 'sensor.kc_chore_make_bed' -%}
{%- set chore_state = state_attr(chore_sensor_id, 'chore_state') -%}

{%- if chore_state == 'available' -%}
  green
{%- elif chore_state == 'claimed' -%}
  orange
{%- elif chore_state == 'approved' -%}
  blue
{%- else -%}
  grey
{%- endif -%}
"""
        template = Template(template_str, hass)
        result = template.async_render()

        assert result.strip() == "green"  # Make bed is available

    async def test_chores_card_identifies_overdue(
        self, hass: HomeAssistant, dashboard_entities, kid_slug: str
    ):
        """Test overdue chore detection."""
        template_str = """
{%- set chore_sensor_id = 'sensor.kc_chore_dishes' -%}
{%- set due_date_str = state_attr(chore_sensor_id, 'chore_due_date') -%}
{%- set chore_state = state_attr(chore_sensor_id, 'chore_state') -%}

{%- if due_date_str and chore_state not in ['approved', 'multi-approved'] -%}
  {%- set due_date = as_datetime(due_date_str) -%}
  {%- set now = now() -%}
  {%- if due_date and due_date < now -%}
    overdue
  {%- else -%}
    on-time
  {%- endif -%}
{%- else -%}
  no-due-date
{%- endif -%}
"""
        template = Template(template_str, hass)
        result = template.async_render()

        assert result.strip() == "overdue"  # Dishes is overdue


class TestDashboardRewardsCard:
    """Test rewards card template rendering."""

    async def test_rewards_card_renders(
        self, hass: HomeAssistant, dashboard_entities, kid_name: str, kid_slug: str
    ):
        """Test rewards card template renders without errors."""
        template_str = (
            """
{%- set Kid_name = '"""
            + kid_name
            + """' -%}
{%- set Kid_name_normalize = Kid_name | slugify() -%}
{%- set dashboard_helper = 'sensor.kc_' ~ Kid_name_normalize ~ '_ui_dashboard_helper' -%}

{%- set reward_list = state_attr(dashboard_helper, 'rewards') | default([], true) -%}

{%- set ns = namespace(reward_count=0) -%}
{%- for reward in reward_list -%}
  {%- set reward_sensor_id = reward.eid if reward is mapping else reward -%}
  {%- set reward_name = state_attr(reward_sensor_id, 'reward_name') -%}
  {%- if reward_name -%}
    {%- set ns.reward_count = ns.reward_count + 1 -%}
  {%- endif -%}
{%- endfor -%}
{{ ns.reward_count }}
"""
        )
        template = Template(template_str, hass)
        result = template.async_render()

        assert result == 1  # Should find ice cream reward


class TestDashboardBadgesCard:
    """Test badges card template rendering."""

    async def test_badges_card_renders(
        self, hass: HomeAssistant, dashboard_entities, kid_name: str, kid_slug: str
    ):
        """Test badges card template renders without errors."""
        template_str = (
            """
{%- set Kid_name = '"""
            + kid_name
            + """' -%}
{%- set Kid_name_normalize = Kid_name | slugify() -%}
{%- set dashboard_helper = 'sensor.kc_' ~ Kid_name_normalize ~ '_ui_dashboard_helper' -%}
{%- set highest_badge_sensor = 'sensor.kc_' ~ Kid_name_normalize ~ '_highest_badge' -%}

{%- set hb_current_name = states(highest_badge_sensor) -%}
{%- set hb_next_higher_name = state_attr(highest_badge_sensor, 'next_higher_badge_name') | default('') -%}
{%- set hb_next_lower_name = state_attr(highest_badge_sensor, 'next_lower_badge_name') | default('') -%}

{{ hb_current_name }},{{ hb_next_higher_name }},{{ hb_next_lower_name }}
"""
        )
        template = Template(template_str, hass)
        result = template.async_render()

        assert "Silver Badge" in result
        assert "Gold Badge" in result
        assert "Bronze Badge" in result

    async def test_badges_maintenance_status(
        self, hass: HomeAssistant, dashboard_entities, kid_slug: str
    ):
        """Test badge maintenance status extraction."""
        template_str = (
            """
{%- set highest_badge_sensor = 'sensor.kc_"""
            + kid_slug
            + """_highest_badge' -%}
{%- set m_status = state_attr(highest_badge_sensor, 'badge_status') | default('active') -%}
{%- set m_remaining = state_attr(highest_badge_sensor, 'maintenance_points_remaining') | int(default=0) -%}

{{ m_status }},{{ m_remaining }}
"""
        )
        template = Template(template_str, hass)
        result = template.async_render()

        assert "active" in result
        assert "50" in result  # maintenance points remaining


class TestDashboardTranslations:
    """Test translation handling in templates."""

    async def test_translations_loaded_from_helper(
        self, hass: HomeAssistant, dashboard_entities, kid_slug: str
    ):
        """Test that translations are loaded from dashboard helper."""
        template_str = (
            """
{%- set dashboard_helper = 'sensor.kc_"""
            + kid_slug
            + """_ui_dashboard_helper' -%}
{%- set ui = state_attr(dashboard_helper, 'ui_translations') or {} -%}

{{ ui.get('welcome', 'err-welcome') }}|{{ ui.get('your_points', 'err-your_points') }}
"""
        )
        template = Template(template_str, hass)
        result = template.async_render()

        assert "Welcome" in result
        assert "Your Points" in result
        assert "err-" not in result

    async def test_missing_translation_shows_error_key(
        self, hass: HomeAssistant, dashboard_entities, kid_slug: str
    ):
        """Test that missing translations show error keys."""
        template_str = (
            """
{%- set dashboard_helper = 'sensor.kc_"""
            + kid_slug
            + """_ui_dashboard_helper' -%}
{%- set ui = state_attr(dashboard_helper, 'ui_translations') or {} -%}

{{ ui.get('nonexistent_key', 'err-nonexistent_key') }}
"""
        )
        template = Template(template_str, hass)
        result = template.async_render()

        assert result == "err-nonexistent_key"


class TestDashboardFilters:
    """Test template filter operations."""

    async def test_slugify_filter(self, hass: HomeAssistant):
        """Test slugify filter works correctly."""
        template_str = """{{ 'Test Kid Name' | slugify() }}"""
        template = Template(template_str, hass)
        result = template.async_render()

        assert result == "test_kid_name"

    async def test_int_filter_with_default(self, hass: HomeAssistant):
        """Test int filter with default value."""
        template_str = """{{ 'invalid' | int(default=42) }}"""
        template = Template(template_str, hass)
        result = template.async_render()

        assert result == 42

    async def test_datetime_parsing(self, hass: HomeAssistant):
        """Test datetime parsing in templates."""
        now = dt_util.now()
        template_str = (
            """
{%- set date_str = '"""
            + now.isoformat()
            + """' -%}
{%- set parsed = strptime(date_str[:19], '%Y-%m-%dT%H:%M:%S') -%}
{{ parsed.year }}
"""
        )
        template = Template(template_str, hass)
        result = template.async_render()

        assert result == now.year


class TestDashboardComplexScenarios:
    """Test complex multi-entity scenarios."""

    async def test_empty_chore_list(
        self, hass: HomeAssistant, kid_name: str, kid_slug: str
    ):
        """Test dashboard handles empty chore lists gracefully."""
        # Set up helper with empty chore list
        hass.states.async_set(
            f"sensor.kc_{kid_slug}_ui_dashboard_helper",
            "available",
            {
                "ui_translations": {"no_chores": "No chores available"},
                "chores": [],
            },
        )

        template_str = (
            """
{%- set Kid_name = '"""
            + kid_name
            + """' -%}
{%- set Kid_name_normalize = Kid_name | slugify() -%}
{%- set dashboard_helper = 'sensor.kc_' ~ Kid_name_normalize ~ '_ui_dashboard_helper' -%}
{%- set chore_list = state_attr(dashboard_helper, 'chores') | default([], true) -%}
{%- set ui = state_attr(dashboard_helper, 'ui_translations') or {} -%}

{%- if chore_list | length == 0 -%}
{{ ui.get('no_chores', 'err-no_chores') }}
{%- else -%}
{{ chore_list | length }} chores
{%- endif -%}
"""
        )
        template = Template(template_str, hass)
        result = template.async_render()

        assert result == "No chores available"

    async def test_multiple_kids_filtering(
        self, hass: HomeAssistant, dashboard_entities, kid_name: str
    ):
        """Test that chores filter correctly by assigned kid."""
        # Add a chore NOT assigned to Alice
        hass.states.async_set(
            "sensor.kc_chore_bob_only",
            "available",
            {
                "chore_name": "Bob's Chore",
                "kids_assigned": ["Bob"],
            },
        )

        template_str = (
            """
{%- set Kid_name = '"""
            + kid_name
            + """' -%}
{%- set chore_sensor_id = 'sensor.kc_chore_bob_only' -%}
{%- set assigned = state_attr(chore_sensor_id, 'kids_assigned') -%}

{%- if assigned is iterable and assigned is not string and assigned | length > 0 and Kid_name not in assigned -%}
  filtered_out
{%- else -%}
  included
{%- endif -%}
"""
        )
        template = Template(template_str, hass)
        result = template.async_render()

        assert result.strip() == "filtered_out"

    async def test_chores_by_label_grouping(
        self, hass: HomeAssistant, dashboard_entities, kid_slug: str
    ):
        """Test chores_by_label structure works correctly."""
        template_str = (
            """
{%- set dashboard_helper = 'sensor.kc_"""
            + kid_slug
            + """_ui_dashboard_helper' -%}
{%- set chores_by_label = state_attr(dashboard_helper, 'chores_by_label') | default({}, true) -%}

{%- set label_count = chores_by_label.keys() | list | length -%}
{{ label_count }}
"""
        )
        template = Template(template_str, hass)
        result = template.async_render()

        assert result == 2  # Kitchen and Bedroom labels


@pytest.mark.asyncio
async def test_full_dashboard_integration(
    hass: HomeAssistant, dashboard_entities, kid_name: str, kid_slug: str
):
    """Integration test: Verify all major dashboard sections render together."""
    # Test that all key dashboard elements can coexist
    template_str = (
        """
{%- set Kid_name = '"""
        + kid_name
        + """' -%}
{%- set Kid_name_normalize = Kid_name | slugify() -%}
{%- set dashboard_helper = 'sensor.kc_' ~ Kid_name_normalize ~ '_ui_dashboard_helper' -%}

{#- Test all major data sources accessible -#}
{%- set ui = state_attr(dashboard_helper, 'ui_translations') or {} -%}
{%- set chore_list = state_attr(dashboard_helper, 'chores') | default([], true) -%}
{%- set reward_list = state_attr(dashboard_helper, 'rewards') | default([], true) -%}
{%- set badge_list = state_attr(dashboard_helper, 'badges') | default([], true) -%}
{%- set points = states('sensor.kc_' ~ Kid_name_normalize ~ '_points') | int(default=0) -%}

PASS:{{ ui.keys() | length }},{{ chore_list | length }},{{ reward_list | length }},{{ badge_list | length }},{{ points }}
"""
    )
    template = Template(template_str, hass)
    result = template.async_render()

    assert "PASS:" in result
    assert ",2," in result  # 2 chores
    assert ",1," in result  # 1 reward
    assert ",250" in result  # 250 points
    parts = result.split(",")
    assert len(parts) == 5  # All data present


class TestDashboardPreferenceValidation:
    """Test preference validation with partial/invalid string inputs."""

    async def test_preference_partial_string_input(self, hass: HomeAssistant):
        """Test boolean preferences handle partial strings during typing."""
        # Simulate user typing "true" character by character: "t", "tr", "tru", "true"
        partial_values = ["t", "tr", "tru", "invalid", "123", ""]

        for partial_value in partial_values:
            template_str = (
                """
{%- set pref_exclude_approved = '"""
                + partial_value
                + """' -%}

{#-- Type coercion for preferences - should handle invalid input gracefully --#}
{%- set pref_exclude_approved = pref_exclude_approved if (pref_exclude_approved is boolean or pref_exclude_approved in ['true', 'false']) else false -%}
{%- set pref_exclude_approved = pref_exclude_approved | bool if pref_exclude_approved is not boolean else pref_exclude_approved -%}

{#-- Test that preference is now a valid boolean --#}
RESULT: {{ pref_exclude_approved }}
TYPE: {{ pref_exclude_approved is boolean }}
"""
            )
            template = Template(template_str, hass)
            result = template.async_render()

            assert "RESULT: False" in result or "RESULT: True" in result
            assert "TYPE: True" in result
            assert "err-" not in result

    async def test_preference_valid_boolean_strings(self, hass: HomeAssistant):
        """Test boolean preferences correctly parse valid 'true'/'false' strings."""
        test_cases = [
            ("true", True),
            ("false", False),
            (True, True),
            (False, False),
        ]

        for input_value, expected_bool in test_cases:
            if isinstance(input_value, bool):
                template_str = (
                    """
{%- set pref_exclude_approved = """
                    + str(input_value).lower()
                    + """ -%}
"""
                )
            else:
                template_str = (
                    """
{%- set pref_exclude_approved = '"""
                    + input_value
                    + """' -%}
"""
                )

            template_str += """
{%- set pref_exclude_approved = pref_exclude_approved if (pref_exclude_approved is boolean or pref_exclude_approved in ['true', 'false']) else false -%}
{%- set pref_exclude_approved = pref_exclude_approved | bool if pref_exclude_approved is not boolean else pref_exclude_approved -%}

RESULT: {{ pref_exclude_approved }}
"""
            template = Template(template_str, hass)
            result = template.async_render()

            expected_str = str(expected_bool)
            assert f"RESULT: {expected_str}" in result

    async def test_all_preferences_safe_coercion(
        self, hass: HomeAssistant, dashboard_entities, kid_name: str, kid_slug: str
    ):
        """Test all boolean preferences use safe coercion pattern."""
        # Test with partial string that would cause bool filter to fail
        template_str = (
            """
{%- set name = '"""
            + kid_name
            + """' -%}
{%- set pref_use_overdue_grouping = 't' -%}
{%- set pref_use_today_grouping = 'tr' -%}
{%- set pref_exclude_approved = 'invalid' -%}
{%- set pref_use_label_grouping = 123 -%}
{%- set pref_show_penalties = '' -%}

{#-- Type coercion using safe pattern --#}
{%- set pref_use_overdue_grouping = pref_use_overdue_grouping if (pref_use_overdue_grouping is boolean or pref_use_overdue_grouping in ['true', 'false']) else true -%}
{%- set pref_use_overdue_grouping = pref_use_overdue_grouping | bool if pref_use_overdue_grouping is not boolean else pref_use_overdue_grouping -%}

{%- set pref_use_today_grouping = pref_use_today_grouping if (pref_use_today_grouping is boolean or pref_use_today_grouping in ['true', 'false']) else true -%}
{%- set pref_use_today_grouping = pref_use_today_grouping | bool if pref_use_today_grouping is not boolean else pref_use_today_grouping -%}

{%- set pref_exclude_approved = pref_exclude_approved if (pref_exclude_approved is boolean or pref_exclude_approved in ['true', 'false']) else false -%}
{%- set pref_exclude_approved = pref_exclude_approved | bool if pref_exclude_approved is not boolean else pref_exclude_approved -%}

{%- set pref_use_label_grouping = pref_use_label_grouping if (pref_use_label_grouping is boolean or pref_use_label_grouping in ['true', 'false']) else false -%}
{%- set pref_use_label_grouping = pref_use_label_grouping | bool if pref_use_label_grouping is not boolean else pref_use_label_grouping -%}

{%- set pref_show_penalties = pref_show_penalties if (pref_show_penalties is boolean or pref_show_penalties in ['true', 'false']) else true -%}
{%- set pref_show_penalties = pref_show_penalties | bool if pref_show_penalties is not boolean else pref_show_penalties -%}

PASS: {{ pref_use_overdue_grouping is boolean }},{{ pref_use_today_grouping is boolean }},{{ pref_exclude_approved is boolean }},{{ pref_use_label_grouping is boolean }},{{ pref_show_penalties is boolean }}
"""
        )
        template = Template(template_str, hass)
        result = template.async_render()

        # All should be valid booleans
        assert "PASS: True,True,True,True,True" in result


class TestDashboardApprovalButtonsFullCard:
    """Test full approval buttons card rendering end-to-end."""

    async def test_approval_card_full_render_with_claimed_chore(
        self, hass: HomeAssistant, dashboard_entities, kid_name: str, kid_slug: str
    ):
        """Test full approval card template renders mushroom-template-card entries for claimed chores.

        This is an end-to-end test that renders the complete approval card template,
        including all button building and rendering logic. It verifies that:
        1. Pending approvals are collected from sensor
        2. Button EIDs are properly extracted (None values filtered)
        3. Button groups are built with proper structure
        4. Mushroom-template-card entries are generated in output
        """
        # Set up pending chore approvals sensor with proper button EIDs
        hass.states.async_set(
            "sensor.kc_global_chore_pending_approvals",
            "1",
            {
                kid_name: [
                    {
                        "chore_name": "Dishes",
                        "claimed_on": dt_util.now().isoformat(),
                        "approve_button_eid": "button.kc_alice_approve_dishes",
                        "disapprove_button_eid": "button.kc_alice_disapprove_dishes",
                    }
                ]
            },
        )

        # Also set up reward approvals
        hass.states.async_set(
            "sensor.kc_global_reward_pending_approvals",
            "1",
            {
                kid_name: [
                    {
                        "reward_name": "Ice Cream",
                        "claimed_on": dt_util.now().isoformat(),
                        "approve_button_eid": "button.kc_alice_approve_ice_cream",
                        "disapprove_button_eid": "button.kc_alice_disapprove_ice_cream",
                    }
                ]
            },
        )

        # Render the FULL approval card template including rendering logic
        template_str = (
            """
{%- set name = '"""
            + kid_name
            + """' -%}
{%- set pref_column_count = 2 -%}
{%- set name_normalize = name | slugify() -%}
{%- set dashboard_helper = 'sensor.kc_' ~ name_normalize ~ '_ui_dashboard_helper' -%}

{%- set ns = namespace(
  approve_chore_buttons=[],
  approve_reward_buttons=[],
  group_cards=[],
  has_approvals='false'
) -%}

{#-- Validation: Check if name is configured --#}
{%- if name == 'Kidname' | replace(' ', '') or name == '' -%}
  {%- set skip_render = true -%}
{%- elif states(dashboard_helper) in ['unknown', 'unavailable'] -%}
  {%- set skip_render = true -%}
{%- else -%}
  {%- set skip_render = false -%}
{%- endif -%}

{#-- 3. Collect Data --#}
{%- set ui = state_attr(dashboard_helper, 'ui_translations') or {} -%}

{%- set pending_chore_data = state_attr('sensor.kc_global_chore_pending_approvals', name) | default([], true) if states('sensor.kc_global_chore_pending_approvals') not in ['unavailable', 'unknown'] else state_attr('sensor.kc_pending_chore_approvals', name) | default([], true) if states('sensor.kc_pending_chore_approvals') not in ['unavailable', 'unknown'] else [] -%}

{%- set pending_reward_data = state_attr('sensor.kc_global_reward_pending_approvals', name) | default([], true) if states('sensor.kc_global_reward_pending_approvals') not in ['unavailable', 'unknown'] else state_attr('sensor.kc_global_pending_reward_approvals', name) | default([], true) if states('sensor.kc_global_pending_reward_approvals') not in ['unavailable', 'unknown'] else state_attr('sensor.kc_pending_reward_approvals', name) | default([], true) if states('sensor.kc_pending_reward_approvals') not in ['unavailable', 'unknown'] else [] -%}

{#-- 4. Build Display --#}
{%- if pending_chore_data | count > 0 -%}
  {%- for entry in pending_chore_data -%}
    {%- set ap = (entry.approve_button_eid if entry.approve_button_eid not in [None, 'None', ''] else '') | default('') -%}
    {%- set dis = (entry.disapprove_button_eid if entry.disapprove_button_eid not in [None, 'None', ''] else '') | default('') -%}
    {%- set cname = entry.chore_name | default('') -%}

    {%- if ap != '' -%}
      {%- if ap not in (ns.approve_chore_buttons | map(attribute='eid') | list) -%}
        {%- set ns.approve_chore_buttons = ns.approve_chore_buttons + [{'eid': ap, 'primary': ui.get('ok', 'err-ok') ~ ': ' ~ cname, 'icon': 'mdi:thumb-up', 'icon_color': 'green'}] -%}
      {%- endif -%}
    {%- endif -%}

    {%- if dis != '' -%}
      {%- if dis not in (ns.approve_chore_buttons | map(attribute='eid') | list) -%}
        {%- set ns.approve_chore_buttons = ns.approve_chore_buttons + [{'eid': dis, 'primary': ui.get('no', 'err-no') ~ ': ' ~ cname, 'icon': 'mdi:thumb-down', 'icon_color': 'red'}] -%}
      {%- endif -%}
    {%- endif -%}
  {%- endfor -%}
{%- endif -%}

{%- if pending_reward_data | count > 0 -%}
  {%- for entry in pending_reward_data -%}
    {%- set ap = (entry.approve_button_eid if entry.approve_button_eid not in [None, 'None', ''] else '') | default('') -%}
    {%- set dis = (entry.disapprove_button_eid if entry.disapprove_button_eid not in [None, 'None', ''] else '') | default('') -%}
    {%- set rname = entry.reward_name | default('') -%}

    {%- if ap != '' -%}
      {%- if ap not in (ns.approve_reward_buttons | map(attribute='eid') | list) -%}
        {%- set ns.approve_reward_buttons = ns.approve_reward_buttons + [{'eid': ap, 'primary': ui.get('ok', 'err-ok') ~ ': ' ~ rname, 'icon': 'mdi:thumb-up', 'icon_color': 'green'}] -%}
      {%- endif -%}
    {%- endif -%}

    {%- if dis != '' -%}
      {%- if dis not in (ns.approve_reward_buttons | map(attribute='eid') | list) -%}
        {%- set ns.approve_reward_buttons = ns.approve_reward_buttons + [{'eid': dis, 'primary': ui.get('no', 'err-no') ~ ': ' ~ rname, 'icon': 'mdi:thumb-down', 'icon_color': 'red'}] -%}
      {%- endif -%}
    {%- endif -%}
  {%- endfor -%}
{%- endif -%}

{%- set button_groups = [
    {'name': ui.get('chore_approvals', 'err-chore_approvals'), 'buttons': ns.approve_chore_buttons, 'icon': 'mdi:thumb-up-outline'},
    {'name': ui.get('reward_approvals', 'err-reward_approvals'), 'buttons': ns.approve_reward_buttons, 'icon': 'mdi:thumb-up-outline'}
] -%}

{#-- 5. Render --#}
{%- if not skip_render -%}
  {%- for group in button_groups -%}
  {%- set ns.group_cards = [] -%}

  {%- if group.buttons | length > 0 -%}
    {%- set heading_card = {
      'type': 'heading',
      'icon': group.icon,
      'heading': group.name,
      'heading_style': 'title'
    } -%}

    {%- for button in group.buttons -%}
      {%- if button is mapping -%}
        {%- set eid = button.eid -%}
        {%- set primary = button.primary -%}
        {%- set icon = button.icon -%}
        {%- set icon_color = button.icon_color -%}
      {%- endif -%}

      {%- set ns.group_cards = ns.group_cards + [{
        'type': 'custom:mushroom-template-card',
        'entity': eid,
        'primary': primary,
        'icon': icon,
        'layout': '',
        'icon_color': icon_color,
        'tap_action': {
          'action': 'toggle'
        },
        'hold_action': {
          'action': 'more-info'
        }
      }] -%}
    {%- endfor -%}

    RENDERED_GROUP: {{ group.name }}|{{ ns.group_cards | length }}
    {%- for card in ns.group_cards -%}
CARD:{{ card.entity }}|{{ card.type }}
    {%- endfor -%}
  {%- endif -%}
  {%- endfor -%}
{%- endif -%}

CHORE_BUTTONS:{{ ns.approve_chore_buttons | length }}
REWARD_BUTTONS:{{ ns.approve_reward_buttons | length }}
SKIP_RENDER:{{ skip_render }}
"""
        )
        template = Template(template_str, hass)
        result = template.async_render()

        # Verify rendering completed
        assert "SKIP_RENDER:False" in result, (
            f"Template rendering failed. Output: {result}"
        )

        # Verify buttons were collected
        assert "CHORE_BUTTONS:2" in result, (
            f"Expected 2 chore buttons (approve + disapprove). Output: {result}"
        )
        assert "REWARD_BUTTONS:2" in result, (
            f"Expected 2 reward buttons (approve + disapprove). Output: {result}"
        )

        # Verify groups were rendered
        assert "RENDERED_GROUP:" in result, f"No groups rendered. Output: {result}"

        # Verify mushroom-template-card entries exist
        assert (
            "CARD:button.kc_alice_approve_dishes|custom:mushroom-template-card"
            in result
        ), f"Approve chore card not rendered. Output: {result}"
        assert (
            "CARD:button.kc_alice_disapprove_dishes|custom:mushroom-template-card"
            in result
        ), f"Disapprove chore card not rendered. Output: {result}"
        assert (
            "CARD:button.kc_alice_approve_ice_cream|custom:mushroom-template-card"
            in result
        ), f"Approve reward card not rendered. Output: {result}"
        assert (
            "CARD:button.kc_alice_disapprove_ice_cream|custom:mushroom-template-card"
            in result
        ), f"Disapprove reward card not rendered. Output: {result}"


def state_attr(hass: HomeAssistant, entity_id: str, attr: str):
    """Get state attribute from entity."""
    state = hass.states.get(entity_id)
    if state:
        return state.attributes.get(attr)
    return None


class TestDashboardApprovalButtonsCard:
    """Test approval buttons card rendering with pending approvals."""

    async def test_approval_buttons_with_claimed_chore(
        self, hass: HomeAssistant, dashboard_entities, kid_name: str, kid_slug: str
    ):
        """Test approval buttons card renders when chore is claimed.

        This test verifies the approval buttons appear after a chore is claimed.
        The pending approvals sensor must have the button entity IDs populated.
        """
        # Set up pending chore approvals sensor with claimed chore
        hass.states.async_set(
            "sensor.kc_global_chore_pending_approvals",
            "1",
            {
                kid_name: [
                    {
                        "chore_name": "Dishes",
                        "claimed_on": dt_util.now().isoformat(),
                        "approve_button_eid": "button.kc_alice_approve_dishes",
                        "disapprove_button_eid": "button.kc_alice_disapprove_dishes",
                    }
                ]
            },
        )

        # Render the approval buttons card template
        template_str = (
            """
{%- set name = '"""
            + kid_name
            + """' -%}
{%- set pref_column_count = 2 -%}
{%- set name_normalize = name | slugify() -%}
{%- set dashboard_helper = 'sensor.kc_' ~ name_normalize ~ '_ui_dashboard_helper' -%}

{%- set ns = namespace(
  approve_chore_buttons=[],
  group_cards=[]
) -%}

{#-- Check if name is configured --#}
{%- if name == 'Kidname' | replace(' ', '') or name == '' -%}
  {{- 'ERROR: Name not configured' -}}
  {%- set skip_render = true -%}
{%- elif states(dashboard_helper) in ['unknown', 'unavailable'] -%}
  {{- 'ERROR: Dashboard helper unavailable' -}}
  {%- set skip_render = true -%}
{%- else -%}
  {%- set skip_render = false -%}
{%- endif -%}

{#-- Get translations --#}
{%- set ui = state_attr(dashboard_helper, 'ui_translations') or {} -%}

{#-- Get pending approvals --#}
{%- set pending_chore_data = state_attr('sensor.kc_global_chore_pending_approvals', name) | default([], true) if states('sensor.kc_global_chore_pending_approvals') not in ['unavailable', 'unknown'] else [] -%}

{#-- Build button list from pending chore data --#}
{%- if pending_chore_data | count > 0 -%}
  {%- for entry in pending_chore_data -%}
    {%- set ap = entry.approve_button_eid | default('') -%}
    {%- set dis = entry.disapprove_button_eid | default('') -%}
    {%- set cname = entry.chore_name | default('') -%}

    {%- if ap != '' -%}
      {%- if ap not in (ns.approve_chore_buttons | map(attribute='eid') | list) -%}
        {%- set ns.approve_chore_buttons = ns.approve_chore_buttons + [{'eid': ap, 'primary': 'Approve: ' ~ cname}] -%}
      {%- endif -%}
    {%- endif -%}

    {%- if dis != '' -%}
      {%- if dis not in (ns.approve_chore_buttons | map(attribute='eid') | list) -%}
        {%- set ns.approve_chore_buttons = ns.approve_chore_buttons + [{'eid': dis, 'primary': 'Disapprove: ' ~ cname}] -%}
      {%- endif -%}
    {%- endif -%}
  {%- endfor -%}
{%- endif -%}

RESULT: {{ ns.approve_chore_buttons | length }},{{ ns.approve_chore_buttons | map(attribute='eid') | list | string }}
"""
        )
        template = Template(template_str, hass)
        result = template.async_render()

        # Verify buttons were found
        assert "RESULT:" in result
        assert "ERROR:" not in result
        assert "skip_render = true" not in result

        # Verify both approve and disapprove buttons found
        assert "'button.kc_alice_approve_dishes'" in result
        assert "'button.kc_alice_disapprove_dishes'" in result

        # Verify correct count
        assert "RESULT: 2," in result

    async def test_approval_buttons_empty_when_no_pending(
        self, hass: HomeAssistant, dashboard_entities, kid_name: str, kid_slug: str
    ):
        """Test approval buttons card renders empty when no pending approvals."""
        # Don't set up pending chore approvals sensor

        template_str = (
            """
{%- set name = '"""
            + kid_name
            + """' -%}
{%- set name_normalize = name | slugify() -%}

{%- set pending_chore_data = state_attr('sensor.kc_global_chore_pending_approvals', name) | default([], true) if states('sensor.kc_global_chore_pending_approvals') not in ['unavailable', 'unknown'] else [] -%}

PENDING_COUNT: {{ pending_chore_data | count }}
"""
        )
        template = Template(template_str, hass)
        result = template.async_render()

        # Should have empty list
        assert "PENDING_COUNT: 0" in result

    async def test_approval_buttons_missing_button_eid(
        self, hass: HomeAssistant, dashboard_entities, kid_name: str, kid_slug: str
    ):
        """Test approval buttons card handles missing button entity IDs gracefully.

        When approve_button_eid is None, it should be filtered out and not rendered.
        Only disapprove_button_eid should appear in the button list.
        """
        # Set up pending chore approvals sensor with missing button EIDs
        hass.states.async_set(
            "sensor.kc_global_chore_pending_approvals",
            "1",
            {
                kid_name: [
                    {
                        "chore_name": "Dishes",
                        "claimed_on": dt_util.now().isoformat(),
                        "approve_button_eid": None,  # Missing!
                        "disapprove_button_eid": "button.kc_alice_disapprove_dishes",
                    }
                ]
            },
        )

        template_str = (
            """
{%- set name = '"""
            + kid_name
            + """' -%}
{%- set ns = namespace(approve_chore_buttons=[]) -%}

{%- set pending_chore_data = state_attr('sensor.kc_global_chore_pending_approvals', name) | default([], true) if states('sensor.kc_global_chore_pending_approvals') not in ['unavailable', 'unknown'] else [] -%}

{%- if pending_chore_data | count > 0 -%}
  {%- for entry in pending_chore_data -%}
    {%- set ap = (entry.approve_button_eid if entry.approve_button_eid not in [None, 'None', ''] else '') | default('') -%}
    {%- set dis = (entry.disapprove_button_eid if entry.disapprove_button_eid not in [None, 'None', ''] else '') | default('') -%}

    {%- if ap != '' -%}
      {%- set ns.approve_chore_buttons = ns.approve_chore_buttons + [{'eid': ap}] -%}
    {%- endif -%}

    {%- if dis != '' -%}
      {%- set ns.approve_chore_buttons = ns.approve_chore_buttons + [{'eid': dis}] -%}
    {%- endif -%}
  {%- endfor -%}
{%- endif -%}

BUTTONS: {{ ns.approve_chore_buttons | length }}
"""
        )
        template = Template(template_str, hass)
        result = template.async_render()

        # Should only have disapprove button (approve is None and filtered out)
        assert "BUTTONS: 1" in result
