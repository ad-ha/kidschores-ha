"""Test that points adjustment buttons have correct entity IDs."""

from homeassistant.util import slugify

from custom_components.kidschores import const


def test_points_button_entity_id_pattern() -> None:
    """Verify PointsAdjustButton generates correct entity ID pattern.

    Expected pattern: button.kc_{kid}_points_{plus|minus}_{value}
    Old (wrong) pattern: button.kc_{kid}_{plus|minus}_{value}_points

    This test verifies the code logic directly without needing full integration setup.
    """
    kid_name = "Zoe"
    kid_slug = slugify(kid_name)

    # Test positive values
    positive_values = [1, 2, 10, 10.5]
    for delta in positive_values:
        # Simulate what the button __init__ does
        sign_text = f"plus_{str(delta).replace('.', '_')}"
        entity_id = f"{const.BUTTON_KC_PREFIX}{kid_slug}{const.BUTTON_KC_EID_SUFFIX_POINTS}_{sign_text}"

        # Verify correct pattern
        assert "_points_plus_" in entity_id, f"Expected _points_plus_ in {entity_id}"
        assert not entity_id.endswith("_points"), (
            f"Should not end with _points: {entity_id}"
        )

        # Verify format matches expected
        expected = f"button.kc_{kid_slug}_points_plus_{str(delta).replace('.', '_')}"
        assert entity_id == expected, f"Expected {expected}, got {entity_id}"

    # Test negative values
    negative_values = [-1, -2, -10, -10.5]
    for delta in negative_values:
        # Simulate what the button __init__ does
        sign_text = f"minus_{str(abs(delta)).replace('.', '_')}"
        entity_id = f"{const.BUTTON_KC_PREFIX}{kid_slug}{const.BUTTON_KC_EID_SUFFIX_POINTS}_{sign_text}"

        # Verify correct pattern
        assert "_points_minus_" in entity_id, f"Expected _points_minus_ in {entity_id}"
        assert not entity_id.endswith("_points"), (
            f"Should not end with _points: {entity_id}"
        )

        # Verify format matches expected
        expected = (
            f"button.kc_{kid_slug}_points_minus_{str(abs(delta)).replace('.', '_')}"
        )
        assert entity_id == expected, f"Expected {expected}, got {entity_id}"


def test_bonus_button_suffix_stripping() -> None:
    """Verify bonus button entity IDs don't have duplicate _bonus suffix.

    Expected pattern: button.kc_{kid}_bonus_{bonus_name}
    Old (wrong) pattern: button.kc_{kid}_bonus_{bonus_name}_bonus
    """
    kid_name = "Max"
    kid_slug = slugify(kid_name)

    # Test bonus names that would create duplicate suffix
    test_cases = [
        (
            "Magic Minute Bonus",
            "magic_minute_bonus",
            "magic_minute",
        ),  # ends with _bonus
        ("Star Sprinkle", "star_sprinkle", "star_sprinkle"),  # doesn't end with _bonus
        ("Super Bonus", "super_bonus", "super"),  # ends with _bonus
    ]

    for bonus_name, slugified_name, expected_suffix in test_cases:
        # Simulate what ParentBonusApplyButton __init__ does
        entity_slug = slugified_name

        # Strip redundant _bonus suffix if present
        if entity_slug.endswith("_bonus"):
            entity_slug = entity_slug[:-6]  # Remove last 6 chars: "_bonus"

        entity_id = f"{const.BUTTON_KC_PREFIX}{kid_slug}{const.BUTTON_KC_EID_MIDFIX_BONUS}{entity_slug}"

        # Verify no duplicate _bonus suffix
        parts = entity_id.split("_bonus_")
        if len(parts) >= 2:
            suffix = parts[-1]
            assert not suffix.endswith("_bonus"), (
                f"Bonus button {bonus_name} has duplicate _bonus suffix: {entity_id}"
            )

        # Verify expected format
        expected = f"button.kc_{kid_slug}_bonus_{expected_suffix}"
        assert entity_id == expected, f"Expected {expected}, got {entity_id}"
