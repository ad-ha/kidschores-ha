# File: options_flow.py
"""Options Flow for the KidsChores integration, managing entities by internal_id.

Handles add/edit/delete operations with entities referenced internally by internal_id.
Ensures consistency and reloads the integration upon changes.
"""
# pylint: disable=protected-access,broad-exception-caught,too-many-lines
# pylint: disable=import-outside-toplevel
# protected-access: Options flow is tightly coupled to coordinator and needs direct access
# to internal creation/persistence methods (_create_* and _persist).
# broad-exception-caught: Reload operations use broad catch to ensure robustness per HA guidelines.
# too-many-lines: Options flow inherently large (2862 lines) due to menu-driven architecture
# import-outside-toplevel: Backup operations conditionally import to avoid circular deps/performance

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers import selector
from homeassistant.util import dt as dt_util

from . import const
from . import flow_helpers as fh
from . import kc_helpers as kh

# ----------------------------------------------------------------------------------
# INITIALIZATION & HELPERS
# ----------------------------------------------------------------------------------


def _ensure_str(value):
    """Convert anything to string safely."""
    if isinstance(value, dict):
        # Attempt to get a known key or fallback
        return str(value.get("value", next(iter(value.values()), const.SENTINEL_EMPTY)))
    return str(value)


class KidsChoresOptionsFlowHandler(config_entries.OptionsFlow):
    """Options Flow for adding/editing/deleting configuration elements."""

    def __init__(self, _config_entry: config_entries.ConfigEntry):
        """Initialize the options flow."""
        self._entry_options = {}
        self._action = None
        self._entity_type = None
        self._reload_needed = False  # Track if reload is needed
        self._delete_confirmed = False  # Track backup deletion confirmation
        self._restore_confirmed = False  # Track backup restoration confirmation
        self._backup_to_delete = None  # Track backup filename to delete
        self._backup_to_restore = None  # Track backup filename to restore
        self._chore_being_edited: dict[str, Any] | None = (
            None  # For per-kid date editing
        )

    def _get_coordinator(self):
        """Get the coordinator from hass.data."""
        return self.hass.data[const.DOMAIN][self.config_entry.entry_id][
            const.COORDINATOR
        ]

    # ----------------------------------------------------------------------------------
    # MAIN MENU
    # ----------------------------------------------------------------------------------

    async def async_step_init(self, user_input=None):
        """Display the main menu for the Options Flow."""
        # Check if reload is needed from previous entity add/edit operations
        if self._reload_needed and user_input is None:
            const.LOGGER.debug("Performing deferred reload after entity changes")
            self._reload_needed = False
            # Wait briefly to ensure storage writes complete before reload
            await asyncio.sleep(0.1)
            await self._reload_entry_after_entity_change()
            # Note: After reload, the flow might be invalidated, but that's expected
            # The user will need to reopen the options flow to see new sensors

        self._entry_options = dict(self.config_entry.options)

        if user_input is not None:
            selection = user_input[const.OPTIONS_FLOW_INPUT_MENU_SELECTION]

            if selection == const.OPTIONS_FLOW_POINTS:
                return await self.async_step_manage_points()

            elif selection == const.OPTIONS_FLOW_GENERAL_OPTIONS:
                return await self.async_step_manage_general_options()

            elif selection.startswith(const.OPTIONS_FLOW_MENU_MANAGE_PREFIX):
                self._entity_type = selection.replace(
                    const.OPTIONS_FLOW_MENU_MANAGE_PREFIX, const.SENTINEL_EMPTY
                )
                return await self.async_step_manage_entity()

            elif selection == const.OPTIONS_FLOW_FINISH:
                return self.async_abort(reason=const.TRANS_KEY_CFOF_SETUP_COMPLETE)

        main_menu = [
            const.OPTIONS_FLOW_POINTS,
            const.OPTIONS_FLOW_KIDS,
            const.OPTIONS_FLOW_PARENTS,
            const.OPTIONS_FLOW_CHORES,
            const.OPTIONS_FLOW_BADGES,
            const.OPTIONS_FLOW_REWARDS,
            const.OPTIONS_FLOW_BONUSES,
            const.OPTIONS_FLOW_PENALTIES,
            const.OPTIONS_FLOW_ACHIEVEMENTS,
            const.OPTIONS_FLOW_CHALLENGES,
            const.OPTIONS_FLOW_GENERAL_OPTIONS,
            const.OPTIONS_FLOW_FINISH,
        ]

        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_INIT,
            data_schema=vol.Schema(
                {
                    vol.Required(
                        const.OPTIONS_FLOW_INPUT_MENU_SELECTION
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=main_menu,
                            mode=selector.SelectSelectorMode.LIST,
                            translation_key=const.TRANS_KEY_CFOF_MAIN_MENU,
                        )
                    )
                }
            ),
        )

    async def async_step_manage_points(self, user_input=None):
        """Let user edit the points label/icon after initial setup."""
        errors = {}

        if user_input is not None:
            # Validate inputs
            errors = fh.validate_points_inputs(user_input)

            if not errors:
                # Build points configuration
                points_data = fh.build_points_data(user_input)

                # Update options
                self._entry_options = dict(self.config_entry.options)
                self._entry_options.update(points_data)
                const.LOGGER.debug(
                    "Configured points with name %s and icon %s",
                    points_data[const.CONF_POINTS_LABEL],
                    points_data[const.CONF_POINTS_ICON],
                )
                await self._update_system_settings_and_reload()

                return await self.async_step_init()

        # Get existing values from entry options
        current_label = self._entry_options.get(
            const.CONF_POINTS_LABEL, const.DEFAULT_POINTS_LABEL
        )
        current_icon = self._entry_options.get(
            const.CONF_POINTS_ICON, const.DEFAULT_POINTS_ICON
        )

        # Build the form
        points_schema = fh.build_points_schema(
            default_label=current_label, default_icon=current_icon
        )

        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_MANAGE_POINTS,
            data_schema=points_schema,
            description_placeholders={},
        )

    async def async_step_manage_entity(self, user_input=None):
        """Handle the management actions for a selected entity type.

        Presents add/edit/delete options for the selected entity.
        """
        if user_input is not None:
            self._action = user_input[const.OPTIONS_FLOW_INPUT_MANAGE_ACTION]
            # Route to the corresponding step based on action
            if self._action == const.OPTIONS_FLOW_ACTIONS_ADD:
                return await getattr(
                    self,
                    f"{const.OPTIONS_FLOW_ASYNC_STEP_ADD_PREFIX}{self._entity_type}",
                )()
            elif self._action in [
                const.OPTIONS_FLOW_ACTIONS_EDIT,
                const.OPTIONS_FLOW_ACTIONS_DELETE,
            ]:
                return await self.async_step_select_entity()
            elif self._action == const.OPTIONS_FLOW_ACTIONS_BACK:
                return await self.async_step_init()

        # Define manage action choices
        manage_action_choices = [
            const.OPTIONS_FLOW_ACTIONS_ADD,
            const.OPTIONS_FLOW_ACTIONS_EDIT,
            const.OPTIONS_FLOW_ACTIONS_DELETE,
            const.OPTIONS_FLOW_ACTIONS_BACK,  # Option to go back to the main menu
        ]

        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_MANAGE_ENTITY,
            data_schema=vol.Schema(
                {
                    vol.Required(
                        const.OPTIONS_FLOW_INPUT_MANAGE_ACTION
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=manage_action_choices,
                            mode=selector.SelectSelectorMode.LIST,
                            translation_key=const.TRANS_KEY_CFOF_MANAGE_ACTIONS,
                        )
                    )
                }
            ),
            description_placeholders={  # type: ignore[arg-type]
                const.OPTIONS_FLOW_PLACEHOLDER_ENTITY_TYPE: self._entity_type
            },
        )

    async def async_step_select_entity(self, user_input=None):
        """Select an entity (kid, chore, badge, etc.) to edit or delete based on internal_id."""
        if self._action not in [
            const.OPTIONS_FLOW_ACTIONS_EDIT,
            const.OPTIONS_FLOW_ACTIONS_DELETE,
        ]:
            return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_ACTION)

        entity_dict = self._get_entity_dict()
        entity_names = [
            data.get(
                const.OPTIONS_FLOW_DATA_ENTITY_NAME,
                const.TRANS_KEY_DISPLAY_UNKNOWN_ENTITY,
            )
            for data in entity_dict.values()
        ]

        if user_input is not None:
            selected_name = _ensure_str(
                user_input[const.OPTIONS_FLOW_INPUT_ENTITY_NAME]
            )
            internal_id = next(
                (
                    eid
                    for eid, data in entity_dict.items()
                    if data[const.OPTIONS_FLOW_DATA_ENTITY_NAME] == selected_name
                ),
                None,
            )
            if not internal_id:
                const.LOGGER.error("Selected entity '%s' not found", selected_name)
                return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_ENTITY)

            # Store internal_id in context for later use
            self.context[  # type: ignore[typeddict-unknown-key]
                const.OPTIONS_FLOW_INPUT_INTERNAL_ID
            ] = internal_id

            # Route based on action
            if self._action == const.OPTIONS_FLOW_ACTIONS_EDIT:
                # Intercept for badges to route to the correct edit function
                if self._entity_type == const.OPTIONS_FLOW_DIC_BADGE:
                    badge_data = entity_dict[internal_id]
                    badge_type = badge_data.get(const.DATA_BADGE_TYPE)

                    # Route to the correct edit function based on badge type
                    if badge_type == const.BADGE_TYPE_CUMULATIVE:
                        return await self.async_step_edit_badge_cumulative(
                            default_data=badge_data
                        )
                    elif badge_type == const.BADGE_TYPE_DAILY:
                        return await self.async_step_edit_badge_daily(
                            default_data=badge_data
                        )
                    elif badge_type == const.BADGE_TYPE_PERIODIC:
                        return await self.async_step_edit_badge_periodic(
                            default_data=badge_data
                        )
                    elif badge_type == const.BADGE_TYPE_ACHIEVEMENT_LINKED:
                        return await self.async_step_edit_badge_achievement(
                            default_data=badge_data
                        )
                    elif badge_type == const.BADGE_TYPE_CHALLENGE_LINKED:
                        return await self.async_step_edit_badge_challenge(
                            default_data=badge_data
                        )
                    elif badge_type == const.BADGE_TYPE_SPECIAL_OCCASION:
                        return await self.async_step_edit_badge_special(
                            default_data=badge_data
                        )
                    else:
                        const.LOGGER.error(
                            "Unknown badge type '%s' for badge ID '%s'",
                            badge_type,
                            internal_id,
                        )
                        return self.async_abort(
                            reason=const.TRANS_KEY_CFOF_INVALID_BADGE_TYPE
                        )
                else:
                    # For other entity types, route to their specific edit step
                    return await getattr(
                        self,
                        f"async_step_edit_{self._entity_type}",
                    )()

            elif self._action == const.OPTIONS_FLOW_ACTIONS_DELETE:
                # Route to the delete step for the selected entity type
                return await getattr(
                    self,
                    f"async_step_delete_{self._entity_type}",
                )()

        if not entity_names:
            return self.async_abort(
                reason=const.TRANS_KEY_CFOF_NO_ENTITY_TYPE.format(self._entity_type)
            )

        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_SELECT_ENTITY,
            data_schema=vol.Schema(
                {
                    vol.Required(
                        const.OPTIONS_FLOW_INPUT_ENTITY_NAME
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=entity_names,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            sort=True,
                        )
                    )
                }
            ),
            description_placeholders={  # type: ignore[arg-type]
                const.OPTIONS_FLOW_PLACEHOLDER_ENTITY_TYPE: self._entity_type,
                const.OPTIONS_FLOW_PLACEHOLDER_ACTION: self._action,
            },
        )

    def _get_entity_dict(self):
        """Retrieve appropriate entity dict based on entity_type."""
        coordinator = self._get_coordinator()

        entity_type_to_data = {
            const.OPTIONS_FLOW_DIC_KID: const.DATA_KIDS,
            const.OPTIONS_FLOW_DIC_PARENT: const.DATA_PARENTS,
            const.OPTIONS_FLOW_DIC_CHORE: const.DATA_CHORES,
            const.OPTIONS_FLOW_DIC_BADGE: const.DATA_BADGES,
            const.OPTIONS_FLOW_DIC_REWARD: const.DATA_REWARDS,
            const.OPTIONS_FLOW_DIC_BONUS: const.DATA_BONUSES,
            const.OPTIONS_FLOW_DIC_PENALTY: const.DATA_PENALTIES,
            const.OPTIONS_FLOW_DIC_ACHIEVEMENT: const.DATA_ACHIEVEMENTS,
            const.OPTIONS_FLOW_DIC_CHALLENGE: const.DATA_CHALLENGES,
        }
        key = entity_type_to_data.get(self._entity_type)  # type: ignore[assignment]
        if key is None:
            const.LOGGER.error(
                "Unknown entity type '%s'. Cannot retrieve entity dictionary",
                self._entity_type,
            )
            return {}
        return coordinator.data.get(key, {})

    # ----------------------------------------------------------------------------------
    # KIDS MANAGEMENT
    # ----------------------------------------------------------------------------------

    async def async_step_add_kid(self, user_input=None):
        """Add a new kid."""
        coordinator = self._get_coordinator()
        errors = {}
        kids_dict = coordinator.kids_data

        if user_input is not None:
            # Validate inputs
            errors = fh.validate_kids_inputs(user_input, kids_dict)

            if not errors:
                # Build kid data
                kid_data = fh.build_kids_data(user_input, kids_dict)

                # Get internal_id and the kid data dict
                internal_id = list(kid_data.keys())[0]
                new_kid_data = kid_data[internal_id]
                kid_name = new_kid_data[const.DATA_KID_NAME]

                # Add to coordinator
                coordinator._create_kid(internal_id, new_kid_data)
                coordinator._persist()
                coordinator.async_update_listeners()

                const.LOGGER.debug("Added Kid '%s' with ID: %s", kid_name, internal_id)
                self._mark_reload_needed()
                return await self.async_step_init()

        # Retrieve HA users for linking
        users = await self.hass.auth.async_get_users()
        schema = await fh.build_kid_schema(
            self.hass,
            users=users,
            default_kid_name=const.SENTINEL_EMPTY,
            default_ha_user_id=None,
            default_enable_mobile_notifications=False,
            default_mobile_notify_service=None,
            default_enable_persistent_notifications=False,
        )
        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_ADD_KID, data_schema=schema, errors=errors
        )

    # ----------------------------------------------------------------------------------
    # PARENTS MANAGEMENT
    # ----------------------------------------------------------------------------------

    async def async_step_add_parent(self, user_input=None):
        """Add a new parent."""
        coordinator = self._get_coordinator()
        errors = {}
        parents_dict = coordinator.parents_data

        if user_input is not None:
            # Validate inputs
            errors = fh.validate_parents_inputs(user_input, parents_dict)

            if not errors:
                # Build parent data
                parent_data = fh.build_parents_data(user_input, parents_dict)

                # Get internal_id and the parent data dict
                internal_id = list(parent_data.keys())[0]
                new_parent_data = parent_data[internal_id]
                parent_name = new_parent_data[const.DATA_PARENT_NAME]

                # Add to coordinator
                coordinator._create_parent(internal_id, new_parent_data)
                coordinator._persist()
                coordinator.async_update_listeners()

                const.LOGGER.debug(
                    "Added Parent '%s' with ID: %s", parent_name, internal_id
                )
                return await self.async_step_init()

        # Retrieve HA users and existing kids for linking
        users = await self.hass.auth.async_get_users()
        kids_dict = {
            kid_data[const.DATA_KID_NAME]: kid_id
            for kid_id, kid_data in coordinator.kids_data.items()
        }

        parent_schema = fh.build_parent_schema(
            self.hass,
            users=users,
            kids_dict=kids_dict,
            default_parent_name=const.SENTINEL_EMPTY,
            default_ha_user_id=None,
            default_associated_kids=[],
            default_enable_mobile_notifications=False,
            default_mobile_notify_service=None,
            default_enable_persistent_notifications=False,
        )
        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_ADD_PARENT,
            data_schema=parent_schema,
            errors=errors,
        )

    # ----------------------------------------------------------------------------------
    # CHORES MANAGEMENT
    # ----------------------------------------------------------------------------------

    async def async_step_add_chore(self, user_input=None):
        """Add a new chore."""
        coordinator = self._get_coordinator()
        errors = {}
        chores_dict = coordinator.chores_data

        if user_input is not None:
            # Build kids_dict for name→UUID conversion
            kids_dict = {
                data[const.DATA_KID_NAME]: eid
                for eid, data in coordinator.kids_data.items()
            }

            # Build and validate chore data
            chore_data, errors = fh.build_chores_data(
                user_input, kids_dict, chores_dict
            )

            if errors:
                schema = fh.build_chore_schema(kids_dict, default=user_input)
                return self.async_show_form(
                    step_id=const.OPTIONS_FLOW_STEP_ADD_CHORE,
                    data_schema=schema,
                    errors=errors,
                )

            # Get internal_id and the chore data dict
            internal_id = list(chore_data.keys())[0]
            new_chore_data = chore_data[internal_id]
            chore_name = new_chore_data[const.DATA_CHORE_NAME]
            due_date_str = new_chore_data[const.DATA_CHORE_DUE_DATE]

            # Add to coordinator
            coordinator._create_chore(internal_id, new_chore_data)
            coordinator._persist()
            coordinator.async_update_listeners()

            const.LOGGER.debug(
                "Added Chore '%s' with ID: %s and Due Date %s",
                chore_name,
                internal_id,
                due_date_str,
            )
            self._mark_reload_needed()
            return await self.async_step_init()

        # Use flow_helpers.build_chore_schema, passing current kids
        kids_dict = {
            data[const.DATA_KID_NAME]: eid
            for eid, data in coordinator.kids_data.items()
        }
        schema = fh.build_chore_schema(kids_dict)
        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_ADD_CHORE, data_schema=schema, errors=errors
        )

    # ----------------------------------------------------------------------------------
    # BADGES MANAGEMENT
    # ----------------------------------------------------------------------------------

    async def async_step_add_badge(self, user_input=None):
        """Entry point to add a new badge."""
        if user_input is not None:
            badge_type = user_input[const.CFOF_BADGES_INPUT_TYPE]
            self.context[  # type: ignore[typeddict-unknown-key]
                const.CFOF_BADGES_INPUT_TYPE
            ] = badge_type

            # Redirect to the appropriate step based on badge type
            if badge_type == const.BADGE_TYPE_CUMULATIVE:
                return await self.async_step_add_badge_cumulative()
            elif badge_type == const.BADGE_TYPE_DAILY:
                return await self.async_step_add_badge_daily()
            elif badge_type == const.BADGE_TYPE_PERIODIC:
                return await self.async_step_add_badge_periodic()
            elif badge_type == const.BADGE_TYPE_ACHIEVEMENT_LINKED:
                return await self.async_step_add_badge_achievement()
            elif badge_type == const.BADGE_TYPE_CHALLENGE_LINKED:
                return await self.async_step_add_badge_challenge()
            elif badge_type == const.BADGE_TYPE_SPECIAL_OCCASION:
                return await self.async_step_add_badge_special()
            else:
                # Fallback to cumulative if unknown.
                return await self.async_step_add_badge_cumulative()

        badge_type_options = [
            const.BADGE_TYPE_CUMULATIVE,
            const.BADGE_TYPE_DAILY,
            const.BADGE_TYPE_PERIODIC,
            const.BADGE_TYPE_ACHIEVEMENT_LINKED,
            const.BADGE_TYPE_CHALLENGE_LINKED,
            const.BADGE_TYPE_SPECIAL_OCCASION,
        ]
        schema = vol.Schema(
            {
                vol.Required(const.CFOF_BADGES_INPUT_TYPE): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=badge_type_options,
                        mode=selector.SelectSelectorMode.LIST,
                        translation_key=const.TRANS_KEY_CFOF_BADGE_TYPE,
                    )
                )
            }
        )
        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_ADD_BADGE, data_schema=schema
        )

    # ----- Add Achievement-Linked Badge -----
    async def async_step_add_badge_achievement(self, user_input=None):
        """Handle adding an achievement-linked badge."""
        # Redirect to the common function with the appropriate badge type
        # Allows customization of the UI text for achievement-linked badges
        return await self.async_add_edit_badge_common(
            user_input=user_input,
            badge_type=const.BADGE_TYPE_ACHIEVEMENT_LINKED,
            is_edit=False,
        )

    # ----- Add Challenge-Linked Badge -----
    async def async_step_add_badge_challenge(self, user_input=None):
        """Handle adding a challenge-linked badge."""
        # Redirect to the common function with the appropriate badge type
        # Allows customization of the UI text for challenge-linked badges
        return await self.async_add_edit_badge_common(
            user_input=user_input,
            badge_type=const.BADGE_TYPE_CHALLENGE_LINKED,
            is_edit=False,
        )

    # ----- Add Cumulative Badge (Points-only) -----
    async def async_step_add_badge_cumulative(self, user_input=None):
        """Handle adding a cumulative badge."""
        # Redirect to the common function with the appropriate badge type
        # Allows customization of the UI text for cumulative badges
        return await self.async_add_edit_badge_common(
            user_input=user_input,
            badge_type=const.BADGE_TYPE_CUMULATIVE,
            is_edit=False,
        )

    # ----- Add Daily Badge -----
    async def async_step_add_badge_daily(self, user_input=None):
        """Handle adding a daily badge."""
        # Redirect to the common function with the appropriate badge type
        # Allows customization of the UI text for daily badges
        return await self.async_add_edit_badge_common(
            user_input=user_input,
            badge_type=const.BADGE_TYPE_DAILY,
            is_edit=False,
        )

    # ----- Add Periodic Badge -----
    async def async_step_add_badge_periodic(self, user_input=None):
        """Handle adding a periodic badge."""
        # Redirect to the common function with the appropriate badge type
        # Allows customization of the UI text for periodic badges
        return await self.async_add_edit_badge_common(
            user_input=user_input,
            badge_type=const.BADGE_TYPE_PERIODIC,
            is_edit=False,
        )

    # ----- Add Special Occasion Badge -----
    async def async_step_add_badge_special(self, user_input=None):
        """Handle adding a special occasion badge."""
        # Redirect to the common function with the appropriate badge type
        # Allows customization of the UI text for special occasion badges
        return await self.async_add_edit_badge_common(
            user_input=user_input,
            badge_type=const.BADGE_TYPE_SPECIAL_OCCASION,
            is_edit=False,
        )

    # ----- Add Badge Centralized Function for All Types -----
    async def async_add_edit_badge_common(
        self,
        user_input: Optional[Dict[str, Any]] = None,
        badge_type: str = const.BADGE_TYPE_CUMULATIVE,
        default_data: Optional[Dict[str, Any]] = None,
        is_edit: bool = False,
    ):
        """Handle adding or editing a badge."""
        coordinator = self._get_coordinator()
        badges_dict = coordinator.badges_data
        chores_dict = coordinator.chores_data
        kids_dict = coordinator.kids_data
        rewards_dict = coordinator.rewards_data
        achievements_dict = coordinator.achievements_data
        challenges_dict = coordinator.challenges_data
        bonuses_dict = coordinator.bonuses_data
        penalties_dict = coordinator.penalties_data

        errors: Dict[str, str] = {}

        # Determine internal_id (UUID-based primary key, persists across renames)
        if is_edit:
            # Edit mode: retrieve internal_id from context (set when user selected badge to edit)
            internal_id = self.context.get(const.CFOF_GLOBAL_INPUT_INTERNAL_ID)
            # Validate that the badge still exists (defensive: could have been deleted by another process)
            if not internal_id or internal_id not in badges_dict:
                const.LOGGER.error("Invalid Internal ID for editing badge.")
                return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_BADGE)
        else:
            # Add mode: generate new UUID and store in context for form resubmissions
            # Context persists across form validation errors (same internal_id on retry)
            internal_id = str(uuid.uuid4())
            self.context[  # type: ignore[typeddict-unknown-key]
                const.CFOF_GLOBAL_INPUT_INTERNAL_ID
            ] = internal_id

        if user_input is not None:
            # --- Validate Inputs ---
            # Badge validation is complex: checks name uniqueness, reward/bonus/penalty
            # existence, and type-specific rules (e.g., periodic requires repeat_interval)
            errors = fh.validate_badge_common_inputs(
                user_input=user_input,
                internal_id=internal_id,
                existing_badges=badges_dict,
                rewards_dict=rewards_dict,
                bonuses_dict=bonuses_dict,
                penalties_dict=penalties_dict,
                badge_type=badge_type,
            )

            if not errors:
                # --- Build Data ---
                # Convert form inputs to storage format, handling multi-select conversions
                updated_badge_data = fh.build_badge_common_data(
                    user_input=user_input,
                    internal_id=internal_id,
                    badge_type=badge_type,
                )
                updated_badge_data[const.DATA_BADGE_TYPE] = badge_type

                # --- Save Data ---
                # Edit vs Add have different coordinator methods and persistence needs
                if is_edit:
                    # Edit: update existing badge (triggers entity state update)
                    coordinator.update_badge_entity(internal_id, updated_badge_data)
                else:
                    # Add: create new badge + persist + notify listeners of new entity
                    coordinator._create_badge(internal_id, updated_badge_data)
                    # Sync badge progress for all kids (creates progress sensors)
                    for kid_id in coordinator.kids_data:
                        coordinator._sync_badge_progress_for_kid(kid_id)
                    # Recalculate badges to trigger initial evaluation
                    coordinator._recalculate_all_badges()
                    coordinator._persist()
                    coordinator.async_update_listeners()

                const.LOGGER.debug(
                    "%s Badge '%s' with ID: %s. Data: %s",
                    "Updated" if is_edit else "Added",
                    updated_badge_data[const.DATA_BADGE_NAME],
                    internal_id,
                    updated_badge_data,
                )

                self._mark_reload_needed()
                return await self.async_step_init()

        # --- Build Schema ---
        badge_schema_data = user_input if user_input else default_data or {}
        schema_fields = fh.build_badge_common_schema(
            default=badge_schema_data,
            kids_dict=kids_dict,
            chores_dict=chores_dict,
            rewards_dict=rewards_dict,
            achievements_dict=achievements_dict,
            challenges_dict=challenges_dict,
            bonuses_dict=bonuses_dict,
            penalties_dict=penalties_dict,
            badge_type=badge_type,
        )
        data_schema = vol.Schema(schema_fields)

        # Determine step name dynamically
        step_name = (
            const.OPTIONS_FLOW_EDIT_STEP.get(badge_type)
            if is_edit
            else const.OPTIONS_FLOW_ADD_STEP.get(badge_type)
        )
        if not step_name:
            const.LOGGER.error("Invalid badge type '%s'.", badge_type)
            return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_BADGE_TYPE)

        return self.async_show_form(
            step_id=step_name,
            data_schema=data_schema,
            errors=errors,
            description_placeholders=None,
            last_step=False,
        )

    # ----------------------------------------------------------------------------------
    # REWARDS MANAGEMENT
    # ----------------------------------------------------------------------------------

    async def async_step_add_reward(self, user_input=None):
        """Add a new reward."""
        coordinator = self._get_coordinator()
        errors = {}
        rewards_dict = coordinator.rewards_data

        if user_input is not None:
            errors = fh.validate_rewards_inputs(user_input, rewards_dict)
            if not errors:
                reward_data = fh.build_rewards_data(user_input, rewards_dict)
                internal_id = list(reward_data.keys())[0]
                new_reward_data = reward_data[internal_id]

                coordinator._create_reward(internal_id, new_reward_data)
                coordinator._persist()
                coordinator.async_update_listeners()

                reward_name = new_reward_data[const.DATA_REWARD_NAME]
                const.LOGGER.debug(
                    "Added Reward '%s' with ID: %s", reward_name, internal_id
                )
                self._mark_reload_needed()
                return await self.async_step_init()

        schema = fh.build_reward_schema()
        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_ADD_REWARD,
            data_schema=schema,
            errors=errors,
        )

    # ----------------------------------------------------------------------------------
    # BONUSES MANAGEMENT
    # ----------------------------------------------------------------------------------

    async def async_step_add_bonus(self, user_input=None):
        """Add a new bonus."""
        coordinator = self._get_coordinator()
        errors = {}
        bonuses_dict = coordinator.bonuses_data

        if user_input is not None:
            # Validate inputs
            errors = fh.validate_bonuses_inputs(user_input, bonuses_dict)

            if not errors:
                # Build bonus data
                bonus_data = fh.build_bonuses_data(user_input, bonuses_dict)
                internal_id, new_bonus_data = next(iter(bonus_data.items()))

                coordinator._create_bonus(internal_id, new_bonus_data)
                coordinator._persist()
                coordinator.async_update_listeners()

                bonus_name = user_input[const.CFOF_BONUSES_INPUT_NAME].strip()
                const.LOGGER.debug(
                    "Added Bonus '%s' with ID: %s", bonus_name, internal_id
                )
                self._mark_reload_needed()
                return await self.async_step_init()

        schema = fh.build_bonus_schema()
        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_ADD_BONUS, data_schema=schema, errors=errors
        )

    # ----------------------------------------------------------------------------------
    # PENALTIES MANAGEMENT
    # ----------------------------------------------------------------------------------

    async def async_step_add_penalty(self, user_input=None):
        """Add a new penalty."""
        coordinator = self._get_coordinator()
        errors = {}
        penalties_dict = coordinator.penalties_data

        if user_input is not None:
            # Validate inputs
            errors = fh.validate_penalties_inputs(user_input, penalties_dict)

            if not errors:
                # Build penalty data
                penalty_data = fh.build_penalties_data(user_input, penalties_dict)
                internal_id, new_penalty_data = next(iter(penalty_data.items()))

                coordinator._create_penalty(internal_id, new_penalty_data)
                coordinator._persist()
                coordinator.async_update_listeners()

                penalty_name = user_input[const.CFOF_PENALTIES_INPUT_NAME].strip()
                const.LOGGER.debug(
                    "Added Penalty '%s' with ID: %s", penalty_name, internal_id
                )
                self._mark_reload_needed()
                return await self.async_step_init()

        schema = fh.build_penalty_schema()
        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_ADD_PENALTY,
            data_schema=schema,
            errors=errors,
        )

    # ----------------------------------------------------------------------------------
    # ACHIEVEMENTS MANAGEMENT
    # ----------------------------------------------------------------------------------

    async def async_step_add_achievement(self, user_input=None):
        """Add a new achievement."""
        coordinator = self._get_coordinator()
        errors = {}
        achievements_dict = coordinator.achievements_data
        chores_dict = coordinator.chores_data

        if user_input is not None:
            # Build kids name to ID mapping for options flow
            kids_name_to_id = {
                kid[const.DATA_KID_NAME]: kid[const.DATA_KID_INTERNAL_ID]
                for kid in coordinator.data.get(const.DATA_KIDS, {}).values()
            }

            # Build achievement data with integrated validation
            achievement_data, errors = fh.build_achievements_data(
                user_input, achievements_dict, kids_name_to_id
            )

            if not errors:
                internal_id, new_achievement_data = next(iter(achievement_data.items()))

                coordinator._create_achievement(internal_id, new_achievement_data)
                coordinator._persist()
                coordinator.async_update_listeners()

                achievement_name = user_input[
                    const.CFOF_ACHIEVEMENTS_INPUT_NAME
                ].strip()
                const.LOGGER.debug(
                    "Added Achievement '%s' with ID: %s",
                    achievement_name,
                    internal_id,
                )
                self._mark_reload_needed()
                return await self.async_step_init()

        kids_dict = {
            kid_data[const.DATA_KID_NAME]: kid_id
            for kid_id, kid_data in coordinator.kids_data.items()
        }
        achievement_schema = fh.build_achievement_schema(
            kids_dict=kids_dict, chores_dict=chores_dict, default=None
        )
        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_ADD_ACHIEVEMENT,
            data_schema=achievement_schema,
            errors=errors,
        )

    # ----------------------------------------------------------------------------------
    # CHALLENGES MANAGEMENT
    # ----------------------------------------------------------------------------------

    async def async_step_add_challenge(self, user_input=None):
        """Add a new challenge."""
        coordinator = self._get_coordinator()
        errors = {}
        chores_dict = coordinator.chores_data

        if user_input is not None:
            # Use helper to build and validate challenge data
            challenge_data, errors = fh.build_challenges_data(
                user_input,
                coordinator.kids_data,
                existing_challenges=coordinator.challenges_data,
                current_id=None,  # New challenge
            )

            if not errors and challenge_data:
                # Additional validation for options flow: dates must be in the future
                internal_id = list(challenge_data.keys())[0]
                start_date_str = challenge_data[internal_id][
                    const.DATA_CHALLENGE_START_DATE
                ]
                end_date_str = challenge_data[internal_id][
                    const.DATA_CHALLENGE_END_DATE
                ]

                start_dt = dt_util.parse_datetime(start_date_str)
                end_dt = dt_util.parse_datetime(end_date_str)

                if start_dt and start_dt < dt_util.utcnow():
                    errors = {
                        const.CFOP_ERROR_START_DATE: const.TRANS_KEY_CFOF_START_DATE_IN_PAST
                    }
                elif end_dt and end_dt <= dt_util.utcnow():
                    errors = {
                        const.CFOP_ERROR_END_DATE: const.TRANS_KEY_CFOF_END_DATE_IN_PAST
                    }

            if not errors and challenge_data:
                internal_id = list(challenge_data.keys())[0]
                coordinator._create_challenge(internal_id, challenge_data[internal_id])
                coordinator._persist()
                coordinator.async_update_listeners()

                challenge_name = user_input[const.CFOF_CHALLENGES_INPUT_NAME].strip()
                const.LOGGER.debug(
                    "Added Challenge '%s' with ID: %s",
                    challenge_name,
                    internal_id,
                )
                self._mark_reload_needed()
                return await self.async_step_init()

        kids_dict = {
            data[const.DATA_KID_NAME]: eid
            for eid, data in coordinator.kids_data.items()
        }
        challenge_schema = fh.build_challenge_schema(
            kids_dict=kids_dict, chores_dict=chores_dict, default=user_input
        )
        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_ADD_CHALLENGE,
            data_schema=challenge_schema,
            errors=errors,
        )

    # ----------------------------------------------------------------------------------
    # EDIT METHODS (Cross-Entity - Keep Together)
    # ----------------------------------------------------------------------------------

    # --- Kids ---

    async def async_step_edit_kid(self, user_input=None):
        """Edit an existing kid."""
        coordinator = self._get_coordinator()

        errors = {}
        kids_dict = coordinator.kids_data
        internal_id = self.context.get(const.DATA_INTERNAL_ID)

        if not internal_id or internal_id not in kids_dict:
            const.LOGGER.error("Edit Kid - Invalid Internal ID '%s'", internal_id)
            return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_KID)

        kid_data = kids_dict[internal_id]

        if user_input is not None:
            new_name = user_input[const.CFOF_KIDS_INPUT_KID_NAME].strip()
            ha_user_id = (
                user_input.get(const.CFOF_KIDS_INPUT_HA_USER) or const.SENTINEL_EMPTY
            )
            enable_notifications = user_input.get(
                const.CFOF_KIDS_INPUT_ENABLE_MOBILE_NOTIFICATIONS, True
            )
            mobile_notify_service = (
                user_input.get(const.CFOF_KIDS_INPUT_MOBILE_NOTIFY_SERVICE)
                or const.SENTINEL_EMPTY
            )
            use_persistent = user_input.get(
                const.CFOF_KIDS_INPUT_ENABLE_PERSISTENT_NOTIFICATIONS, True
            )

            dashboard_language = user_input.get(
                const.CFOF_KIDS_INPUT_DASHBOARD_LANGUAGE,
                const.DEFAULT_DASHBOARD_LANGUAGE,
            )

            # Validate name is not empty
            if not new_name:
                errors[const.CFOP_ERROR_KID_NAME] = (
                    const.TRANS_KEY_CFOF_INVALID_KID_NAME
                )
            # Check for duplicate names excluding current kid
            elif any(
                data[const.DATA_KID_NAME] == new_name and eid != internal_id
                for eid, data in kids_dict.items()
            ):
                errors[const.CFOP_ERROR_KID_NAME] = const.TRANS_KEY_CFOF_DUPLICATE_KID
            else:
                # Build update data
                updated_kid_data = {
                    const.DATA_KID_NAME: new_name,
                    const.DATA_KID_HA_USER_ID: ha_user_id,
                    const.DATA_KID_ENABLE_NOTIFICATIONS: enable_notifications,
                    const.DATA_KID_MOBILE_NOTIFY_SERVICE: mobile_notify_service,
                    const.DATA_KID_USE_PERSISTENT_NOTIFICATIONS: use_persistent,
                    const.DATA_KID_DASHBOARD_LANGUAGE: dashboard_language,
                }

                # Update via coordinator
                coordinator.update_kid_entity(internal_id, updated_kid_data)

                const.LOGGER.debug("Edited Kid '%s' with ID: %s", new_name, internal_id)
                self._mark_reload_needed()
                return await self.async_step_init()

        # Retrieve HA users for linking
        users = await self.hass.auth.async_get_users()
        schema = await fh.build_kid_schema(
            self.hass,
            users=users,
            default_kid_name=kid_data[const.DATA_KID_NAME],
            default_ha_user_id=kid_data.get(const.DATA_KID_HA_USER_ID),
            default_enable_mobile_notifications=kid_data.get(
                const.DATA_KID_ENABLE_NOTIFICATIONS, True
            ),
            default_mobile_notify_service=kid_data.get(
                const.DATA_KID_MOBILE_NOTIFY_SERVICE
            ),
            default_enable_persistent_notifications=kid_data.get(
                const.DATA_KID_USE_PERSISTENT_NOTIFICATIONS, True
            ),
            default_dashboard_language=kid_data.get(
                const.DATA_KID_DASHBOARD_LANGUAGE, const.DEFAULT_DASHBOARD_LANGUAGE
            ),
        )
        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_EDIT_KID, data_schema=schema, errors=errors
        )

    # --- Parents ---

    async def async_step_edit_parent(self, user_input=None):
        """Edit an existing parent."""
        coordinator = self._get_coordinator()
        errors = {}
        parents_dict = coordinator.parents_data
        internal_id = self.context.get(const.DATA_INTERNAL_ID)

        if not internal_id or internal_id not in parents_dict:
            const.LOGGER.error("Edit Parent - Invalid Internal ID '%s'", internal_id)
            return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_PARENT)

        parent_data = parents_dict[internal_id]

        if user_input is not None:
            new_name = user_input[const.CFOF_PARENTS_INPUT_NAME].strip()
            ha_user_id = (
                user_input.get(const.CFOF_PARENTS_INPUT_HA_USER) or const.SENTINEL_EMPTY
            )
            associated_kids = user_input.get(
                const.CFOF_PARENTS_INPUT_ASSOCIATED_KIDS, []
            )
            enable_notifications = user_input.get(
                const.CFOF_PARENTS_INPUT_ENABLE_MOBILE_NOTIFICATIONS, True
            )
            mobile_notify_service = (
                user_input.get(const.CFOF_PARENTS_INPUT_MOBILE_NOTIFY_SERVICE)
                or const.SENTINEL_EMPTY
            )
            use_persistent = user_input.get(
                const.CFOF_PARENTS_INPUT_ENABLE_PERSISTENT_NOTIFICATIONS, True
            )

            # Validate name is not empty
            if not new_name:
                errors[const.CFOP_ERROR_PARENT_NAME] = (
                    const.TRANS_KEY_CFOF_INVALID_PARENT_NAME
                )
            # Check for duplicate names excluding current parent
            elif any(
                data[const.DATA_PARENT_NAME] == new_name and eid != internal_id
                for eid, data in parents_dict.items()
            ):
                errors[const.CFOP_ERROR_PARENT_NAME] = (
                    const.TRANS_KEY_CFOF_DUPLICATE_PARENT
                )
            else:
                updated_parent_data = {
                    const.DATA_PARENT_NAME: new_name,
                    const.DATA_PARENT_HA_USER_ID: ha_user_id,
                    const.DATA_PARENT_ASSOCIATED_KIDS: associated_kids,
                    const.DATA_PARENT_ENABLE_NOTIFICATIONS: enable_notifications,
                    const.DATA_PARENT_MOBILE_NOTIFY_SERVICE: mobile_notify_service,
                    const.DATA_PARENT_USE_PERSISTENT_NOTIFICATIONS: use_persistent,
                }

                coordinator.update_parent_entity(internal_id, updated_parent_data)

                const.LOGGER.debug(
                    "Edited Parent '%s' with ID: %s", new_name, internal_id
                )
                return await self.async_step_init()

        # Retrieve HA users and existing kids for linking
        users = await self.hass.auth.async_get_users()
        kids_dict = {
            kid_data[const.DATA_KID_NAME]: kid_id
            for kid_id, kid_data in coordinator.kids_data.items()
        }

        parent_schema = fh.build_parent_schema(
            self.hass,
            users=users,
            kids_dict=kids_dict,
            default_parent_name=parent_data[const.DATA_PARENT_NAME],
            default_ha_user_id=parent_data.get(const.DATA_PARENT_HA_USER_ID),
            default_associated_kids=parent_data.get(
                const.DATA_PARENT_ASSOCIATED_KIDS, []
            ),
            default_enable_mobile_notifications=parent_data.get(
                const.DATA_PARENT_ENABLE_NOTIFICATIONS, True
            ),
            default_mobile_notify_service=parent_data.get(
                const.DATA_PARENT_MOBILE_NOTIFY_SERVICE
            ),
            default_enable_persistent_notifications=parent_data.get(
                const.DATA_PARENT_USE_PERSISTENT_NOTIFICATIONS, True
            ),
        )
        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_EDIT_PARENT,
            data_schema=parent_schema,
            errors=errors,
        )

    # --- Chores ---

    async def async_step_edit_chore(self, user_input=None):
        """Edit an existing chore."""
        coordinator = self._get_coordinator()
        errors = {}
        chores_dict = coordinator.chores_data
        internal_id = self.context.get(const.DATA_INTERNAL_ID)

        if not internal_id or internal_id not in chores_dict:
            const.LOGGER.error("Edit Chore - Invalid Internal ID '%s'", internal_id)
            return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_CHORE)

        chore_data = chores_dict[internal_id]

        if user_input is not None:
            # Build kids_dict for name→UUID conversion
            kids_dict = {
                data[const.DATA_KID_NAME]: eid
                for eid, data in coordinator.kids_data.items()
            }

            # Add internal_id for validation
            # (to exclude current chore from duplicate check)
            user_input[const.CFOF_GLOBAL_INPUT_INTERNAL_ID] = internal_id

            # Build a temporary dict for duplicate checking that excludes current chore
            chores_for_validation = {
                cid: cdata for cid, cdata in chores_dict.items() if cid != internal_id
            }

            # Get existing per-kid due dates to preserve during edit
            existing_per_kid_due_dates = chore_data.get(
                const.DATA_CHORE_PER_KID_DUE_DATES, {}
            )

            # Build and validate chore data using helper function
            # Pass existing per-kid dates to preserve them for INDEPENDENT chores
            chore_data_dict, errors = fh.build_chores_data(
                user_input,
                kids_dict,
                chores_for_validation,
                existing_per_kid_due_dates,
            )

            # Extract chore data (must be before error check to avoid E0606)
            updated_chore_data = chore_data_dict.get(internal_id, {})

            if errors:
                default_data = user_input.copy()
                return self.async_show_form(
                    step_id=const.OPTIONS_FLOW_STEP_EDIT_CHORE,
                    data_schema=fh.build_chore_schema(
                        kids_dict, default={**chore_data, **default_data}
                    ),
                    errors=errors,
                )

            # Update chore and check if assigned kids changed
            assignments_changed = coordinator.update_chore_entity(
                internal_id, updated_chore_data
            )

            new_name = updated_chore_data.get(
                const.DATA_CHORE_NAME,
                chore_data.get(const.DATA_CHORE_NAME),
            )
            const.LOGGER.debug("Edited Chore '%s' with ID: %s", new_name, internal_id)

            # Only reload if assignments changed (entities added/removed)
            if assignments_changed:
                const.LOGGER.debug("Chore assignments changed, marking reload needed")
                self._mark_reload_needed()

            # For INDEPENDENT chores with assigned kids, offer per-kid date editing
            completion_criteria = updated_chore_data.get(
                const.DATA_CHORE_COMPLETION_CRITERIA
            )
            assigned_kids = updated_chore_data.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
            if (
                completion_criteria == const.COMPLETION_CRITERIA_INDEPENDENT
                and assigned_kids
            ):
                # Store chore data for the per-kid dates step
                self._chore_being_edited = updated_chore_data
                self._chore_being_edited[const.DATA_INTERNAL_ID] = internal_id  # type: ignore[reportOptionalSubscript]
                return await self.async_step_edit_chore_per_kid_dates()

            return await self.async_step_init()

        # Use flow_helpers.fh.build_chore_schema, passing current kids
        kids_dict = {
            data[const.DATA_KID_NAME]: eid
            for eid, data in coordinator.kids_data.items()
        }

        # Create reverse mapping from internal_id to name
        id_to_name = {
            eid: data[const.DATA_KID_NAME]
            for eid, data in coordinator.kids_data.items()
        }

        # Convert stored string to datetime for DateTimeSelector
        existing_due_str = chore_data.get(const.DATA_CHORE_DUE_DATE)
        existing_due_date = None

        # For INDEPENDENT chores, check if all per-kid dates are the same
        # If they differ, show blank (None) since the per-kid dates take precedence
        completion_criteria = chore_data.get(const.DATA_CHORE_COMPLETION_CRITERIA)
        per_kid_due_dates = chore_data.get(const.DATA_CHORE_PER_KID_DUE_DATES, {})
        assigned_kids_ids = chore_data.get(const.DATA_CHORE_ASSIGNED_KIDS, [])

        if (
            completion_criteria == const.COMPLETION_CRITERIA_INDEPENDENT
            and per_kid_due_dates
            and assigned_kids_ids
        ):
            # Get unique non-None date values for assigned kids only
            unique_dates = set()
            for kid_id in assigned_kids_ids:
                kid_date = per_kid_due_dates.get(kid_id)
                if kid_date:
                    unique_dates.add(kid_date)

            if len(unique_dates) == 1:
                # All assigned kids have the same date - show it
                common_date = next(iter(unique_dates))
                try:
                    existing_due_date = kh.normalize_datetime_input(
                        common_date,
                        default_tzinfo=const.DEFAULT_TIME_ZONE,
                        return_type=const.HELPER_RETURN_SELECTOR_DATETIME,
                    )
                    const.LOGGER.debug(
                        "INDEPENDENT chore: all kids have same date: %s",
                        existing_due_date,
                    )
                except ValueError as e:
                    const.LOGGER.error(
                        "Failed to parse common per-kid date '%s': %s",
                        common_date,
                        e,
                    )
            elif len(unique_dates) > 1:
                # Kids have different dates - show blank
                const.LOGGER.debug(
                    "INDEPENDENT chore: kids have different dates (%d unique), "
                    "showing blank due date field",
                    len(unique_dates),
                )
                existing_due_date = None
            # If no per-kid dates yet, fall through to template date
            elif existing_due_str:
                try:
                    existing_due_date = kh.normalize_datetime_input(
                        existing_due_str,
                        default_tzinfo=const.DEFAULT_TIME_ZONE,
                        return_type=const.HELPER_RETURN_SELECTOR_DATETIME,
                    )
                except ValueError:
                    pass
        elif existing_due_str:
            try:
                # Parse to local datetime string for DateTimeSelector
                # Storage is UTC ISO; display is local timezone
                existing_due_date = kh.normalize_datetime_input(
                    existing_due_str,
                    default_tzinfo=const.DEFAULT_TIME_ZONE,
                    return_type=const.HELPER_RETURN_SELECTOR_DATETIME,
                )
                const.LOGGER.debug(
                    "Processed existing_due_date for DateTimeSelector: %s",
                    existing_due_date,
                )
            except ValueError as e:
                const.LOGGER.error(
                    "Failed to parse existing_due_date '%s': %s",
                    existing_due_str,
                    e,
                )

        # Convert assigned_kids from internal_ids to names for display
        # (assigned_kids_ids already set above for per-kid date check)
        assigned_kids_names = [
            id_to_name.get(kid_id, kid_id) for kid_id in assigned_kids_ids
        ]

        schema = fh.build_chore_schema(
            kids_dict,
            default={
                **chore_data,
                const.DATA_CHORE_DUE_DATE: existing_due_date,
                const.DATA_CHORE_ASSIGNED_KIDS: assigned_kids_names,
            },
        )
        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_EDIT_CHORE,
            data_schema=schema,
            errors=errors,
        )

    # ----- Edit Per-Kid Due Dates for INDEPENDENT Chores -----
    async def async_step_edit_chore_per_kid_dates(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Allow editing per-kid due dates for INDEPENDENT chores.

        Features:
        - Shows template date from main form (if set) with "Apply to All" option
        - Each kid's current due date shown as default (editable)
        - Supports bulk application of template date to all or selected kids
        """
        coordinator = self._get_coordinator()
        errors: dict[str, str] = {}

        # Get chore data from stored state
        chore_data = getattr(self, "_chore_being_edited", None)
        if not chore_data:
            const.LOGGER.error("Per-kid dates step called without chore data")
            return await self.async_step_init()

        internal_id = chore_data.get(const.DATA_INTERNAL_ID)
        if not internal_id:
            const.LOGGER.error("Per-kid dates step: missing internal_id")
            return await self.async_step_init()

        # Only allow for INDEPENDENT chores
        completion_criteria = chore_data.get(const.DATA_CHORE_COMPLETION_CRITERIA)
        if completion_criteria != const.COMPLETION_CRITERIA_INDEPENDENT:
            const.LOGGER.debug(
                "Per-kid dates step skipped - not INDEPENDENT (criteria: %s)",
                completion_criteria,
            )
            return await self.async_step_init()

        assigned_kids = chore_data.get(const.DATA_CHORE_ASSIGNED_KIDS, [])
        if not assigned_kids:
            const.LOGGER.debug("Per-kid dates step skipped - no assigned kids")
            return await self.async_step_init()

        # Get fresh per-kid dates from storage (not from _chore_being_edited)
        stored_chore = coordinator.chores_data.get(internal_id, {})
        existing_per_kid_dates = stored_chore.get(
            const.DATA_CHORE_PER_KID_DUE_DATES, {}
        )

        # Get template date from main form (if set)
        # This is the date set on the main edit page
        template_date_str = chore_data.get(const.DATA_CHORE_DUE_DATE)
        template_date_display = None
        if template_date_str:
            try:
                template_date_display = kh.normalize_datetime_input(
                    template_date_str,
                    default_tzinfo=const.DEFAULT_TIME_ZONE,
                    return_type=const.HELPER_RETURN_SELECTOR_DATETIME,
                )
            except (ValueError, TypeError):
                pass

        # Build name-to-id mapping for assigned kids
        name_to_id: dict[str, str] = {}
        for kid_id in assigned_kids:
            kid_info = coordinator.kids_data.get(kid_id, {})
            kid_name = kid_info.get(const.DATA_KID_NAME, kid_id)
            name_to_id[kid_name] = kid_id

        if user_input is not None:
            # Check if "Apply to All" was selected
            apply_template_to_all = user_input.get(
                const.CFOF_CHORES_INPUT_APPLY_TEMPLATE_TO_ALL, False
            )

            # Process per-kid dates from user input
            # Field keys use kid names for readability; map back to IDs for storage
            per_kid_due_dates = {}
            for kid_name, kid_id in name_to_id.items():
                # If "Apply to All" is selected and we have a template date, use it
                if apply_template_to_all and template_date_str:
                    per_kid_due_dates[kid_id] = template_date_str
                    const.LOGGER.debug(
                        "Applied template date to %s: %s", kid_name, template_date_str
                    )
                else:
                    # Use individual date from form
                    date_value = user_input.get(kid_name)
                    if date_value:
                        # Convert to UTC datetime, then to ISO string for storage
                        # Per quality specs: dates stored in UTC ISO format
                        try:
                            utc_dt = kh.normalize_datetime_input(
                                date_value,
                                default_tzinfo=const.DEFAULT_TIME_ZONE,
                                return_type=const.HELPER_RETURN_DATETIME_UTC,
                            )
                            if utc_dt and isinstance(utc_dt, datetime):
                                per_kid_due_dates[kid_id] = utc_dt.isoformat()
                        except ValueError as e:
                            const.LOGGER.warning("Invalid date for %s: %s", kid_name, e)
                            errors[kid_name] = const.TRANS_KEY_CFOF_INVALID_DUE_DATE

            # Validate: If ALL dates are cleared, check recurring frequency compatibility
            # Only none, daily, weekly frequencies work without due dates
            if not errors and not per_kid_due_dates:
                stored_chore = coordinator.chores_data.get(internal_id, {})
                recurring_frequency = stored_chore.get(
                    const.DATA_CHORE_RECURRING_FREQUENCY, const.FREQUENCY_NONE
                )
                if recurring_frequency not in (
                    const.FREQUENCY_NONE,
                    const.FREQUENCY_DAILY,
                    const.FREQUENCY_WEEKLY,
                ):
                    errors[const.CFOP_ERROR_BASE] = (
                        const.TRANS_KEY_CFOF_DATE_REQUIRED_FOR_FREQUENCY
                    )
                    const.LOGGER.debug(
                        "Cannot clear all dates: frequency '%s' requires due dates",
                        recurring_frequency,
                    )

            if not errors:
                # Update the chore's per_kid_due_dates in storage
                chores_data = coordinator.chores_data
                if internal_id in chores_data:
                    chores_data[internal_id][const.DATA_CHORE_PER_KID_DUE_DATES] = (
                        per_kid_due_dates
                    )

                    # ISSUE #4 FIX: Also sync each kid's chore_data due_date
                    # This mirrors the logic in coordinator.set_chore_due_date()
                    for kid_id, due_date_iso in per_kid_due_dates.items():
                        if kid_id in coordinator.kids_data:
                            kid_info = coordinator.kids_data[kid_id]
                            kid_chore_data = kid_info.setdefault(
                                const.DATA_KID_CHORE_DATA, {}
                            )
                            if internal_id in kid_chore_data:
                                kid_chore_data[internal_id][
                                    const.DATA_KID_CHORE_DATA_DUE_DATE
                                ] = due_date_iso
                            const.LOGGER.debug(
                                "Synced kid %s chore_data due_date for %s: %s",
                                kid_info.get(const.DATA_KID_NAME),
                                internal_id,
                                due_date_iso,
                            )

                    # Also handle kids whose dates were cleared (not in per_kid_due_dates)
                    for kid_id in assigned_kids:
                        if kid_id not in per_kid_due_dates:
                            if kid_id in coordinator.kids_data:
                                kid_info = coordinator.kids_data[kid_id]
                                kid_chore_data = kid_info.get(
                                    const.DATA_KID_CHORE_DATA, {}
                                )
                                if internal_id in kid_chore_data:
                                    kid_chore_data[internal_id][
                                        const.DATA_KID_CHORE_DATA_DUE_DATE
                                    ] = None
                                const.LOGGER.debug(
                                    "Cleared kid %s chore_data due_date for %s",
                                    kid_info.get(const.DATA_KID_NAME),
                                    internal_id,
                                )

                    coordinator._persist()
                    coordinator.async_update_listeners()
                    const.LOGGER.debug(
                        "Updated per-kid due dates for chore %s: %s",
                        internal_id,
                        per_kid_due_dates,
                    )

                # Clear stored state
                self._chore_being_edited = None
                self._mark_reload_needed()
                return await self.async_step_init()

        # Build dynamic schema with kid names as field keys (for readable labels)
        chore_name = chore_data.get(const.DATA_CHORE_NAME, "Unknown")
        schema_fields: dict[Any, Any] = {}
        kid_names_list: list[str] = []

        # Add "Apply template to all" checkbox if template date exists
        if template_date_display:
            schema_fields[
                vol.Optional(
                    const.CFOF_CHORES_INPUT_APPLY_TEMPLATE_TO_ALL, default=False
                )
            ] = selector.BooleanSelector()

        for kid_name, kid_id in name_to_id.items():
            kid_names_list.append(kid_name)

            # Get existing date for this kid from storage
            existing_date = existing_per_kid_dates.get(kid_id)

            # Convert to local datetime string for DateTimeSelector display
            # Storage is UTC ISO; display is local timezone
            default_value = None
            if existing_date:
                try:
                    default_value = kh.normalize_datetime_input(
                        existing_date,
                        default_tzinfo=const.DEFAULT_TIME_ZONE,
                        return_type=const.HELPER_RETURN_SELECTOR_DATETIME,
                    )
                except (ValueError, TypeError):
                    pass

            # Use kid name as field key - HA will display it as the label
            # (field keys without translations are shown as-is)
            schema_fields[vol.Optional(kid_name, default=default_value)] = vol.Any(
                None, selector.DateTimeSelector()
            )

        # Build description with kid names in order
        kid_list_text = ", ".join(kid_names_list)

        # Build description placeholders
        description_placeholders = {
            "chore_name": chore_name,
            "kid_names": kid_list_text,
        }

        # Add template date info if available (shows in description)
        if template_date_display:
            description_placeholders["template_date"] = (
                f"\n\nTemplate date from main form: **{template_date_display}**. "
                "Check 'Apply template date to all kids' to use this date for everyone."
            )
        else:
            description_placeholders["template_date"] = ""

        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_EDIT_CHORE_PER_KID_DATES,
            data_schema=vol.Schema(schema_fields),
            errors=errors,
            description_placeholders=description_placeholders,
        )

    # ----- Edit Achievement-Linked Badge -----
    async def async_step_edit_badge_achievement(
        self, user_input=None, default_data=None
    ):
        """Handle editing an achievement-linked badge."""
        return await self.async_add_edit_badge_common(
            user_input=user_input,
            badge_type=const.BADGE_TYPE_ACHIEVEMENT_LINKED,
            default_data=default_data,
            is_edit=True,
        )

    # ----- Edit Challenge-Linked Badge -----
    async def async_step_edit_badge_challenge(self, user_input=None, default_data=None):
        """Handle editing a challenge-linked badge."""
        return await self.async_add_edit_badge_common(
            user_input=user_input,
            badge_type=const.BADGE_TYPE_CHALLENGE_LINKED,
            default_data=default_data,
            is_edit=True,
        )

    # ----- Edit Cumulative Badge -----
    async def async_step_edit_badge_cumulative(
        self, user_input=None, default_data=None
    ):
        """Handle editing a cumulative badge."""
        return await self.async_add_edit_badge_common(
            user_input=user_input,
            badge_type=const.BADGE_TYPE_CUMULATIVE,
            default_data=default_data,
            is_edit=True,
        )

    # ----- Edit Daily Badge -----
    async def async_step_edit_badge_daily(self, user_input=None, default_data=None):
        """Handle editing a daily badge."""
        return await self.async_add_edit_badge_common(
            user_input=user_input,
            badge_type=const.BADGE_TYPE_DAILY,
            default_data=default_data,
            is_edit=True,
        )

    # ----- Edit Periodic Badge -----
    async def async_step_edit_badge_periodic(self, user_input=None, default_data=None):
        """Handle editing a periodic badge."""
        return await self.async_add_edit_badge_common(
            user_input=user_input,
            badge_type=const.BADGE_TYPE_PERIODIC,
            default_data=default_data,
            is_edit=True,
        )

    # ----- Edit Special Occasion Badge -----
    async def async_step_edit_badge_special(self, user_input=None, default_data=None):
        """Handle editing a special occasion badge."""
        return await self.async_add_edit_badge_common(
            user_input=user_input,
            badge_type=const.BADGE_TYPE_SPECIAL_OCCASION,
            default_data=default_data,
            is_edit=True,
        )

    # --- Rewards ---

    async def async_step_edit_reward(self, user_input=None):
        """Edit an existing reward."""
        coordinator = self._get_coordinator()
        errors = {}
        rewards_dict = coordinator.rewards_data
        internal_id = self.context.get(const.DATA_INTERNAL_ID)

        if not internal_id or internal_id not in rewards_dict:
            const.LOGGER.error("Edit Reward - Invalid Internal ID '%s'", internal_id)
            return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_REWARD)

        reward_data = rewards_dict[internal_id]

        if user_input is not None:
            # Build a temporary dict for duplicate checking that excludes current reward
            rewards_for_validation = {
                rid: rdata for rid, rdata in rewards_dict.items() if rid != internal_id
            }

            errors = fh.validate_rewards_inputs(user_input, rewards_for_validation)
            if not errors:
                reward_data = fh.build_rewards_data(user_input, rewards_for_validation)
                # Extract the reward data (without the internal_id wrapper)
                updated_reward_data = list(reward_data.values())[0]
                # Remove internal_id from updated data as it's already set
                updated_reward_data = {
                    k: v
                    for k, v in updated_reward_data.items()
                    if k != const.DATA_REWARD_INTERNAL_ID
                }

                coordinator.update_reward_entity(internal_id, updated_reward_data)

                new_name = updated_reward_data[const.DATA_REWARD_NAME]
                const.LOGGER.debug(
                    "Edited Reward '%s' with ID: %s", new_name, internal_id
                )
                self._mark_reload_needed()
                return await self.async_step_init()

        schema = fh.build_reward_schema(default=reward_data)
        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_EDIT_REWARD,
            data_schema=schema,
            errors=errors,
        )

    # --- Penalties ---

    async def async_step_edit_penalty(self, user_input=None):
        """Edit an existing penalty."""
        coordinator = self._get_coordinator()
        errors = {}
        penalties_dict = coordinator.penalties_data
        internal_id = self.context.get(const.DATA_INTERNAL_ID)

        if not internal_id or internal_id not in penalties_dict:
            const.LOGGER.error("Edit Penalty - Invalid Internal ID '%s'", internal_id)
            return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_PENALTY)

        penalty_data = penalties_dict[internal_id]

        if user_input is not None:
            new_name = user_input[const.CFOF_PENALTIES_INPUT_NAME].strip()

            # Check for duplicate names excluding current penalty
            penalties_except_current = {
                eid: data for eid, data in penalties_dict.items() if eid != internal_id
            }
            errors = fh.validate_penalties_inputs(user_input, penalties_except_current)

            if not errors:
                # Build updated penalty data
                penalty_data_dict = fh.build_penalties_data(user_input, penalties_dict)
                _, updated_penalty_data = next(iter(penalty_data_dict.items()))

                coordinator.update_penalty_entity(internal_id, updated_penalty_data)

                const.LOGGER.debug(
                    "Edited Penalty '%s' with ID: %s", new_name, internal_id
                )
                self._mark_reload_needed()
                return await self.async_step_init()

        # Prepare data for schema (convert points to positive for display)
        display_data = dict(penalty_data)
        display_data[const.CFOF_PENALTIES_INPUT_POINTS] = abs(
            display_data[const.DATA_PENALTY_POINTS]
        )
        schema = fh.build_penalty_schema(default=display_data)
        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_EDIT_PENALTY,
            data_schema=schema,
            errors=errors,
        )

    # --- Bonuses ---

    async def async_step_edit_bonus(self, user_input=None):
        """Edit an existing bonus."""
        coordinator = self._get_coordinator()
        errors = {}
        bonuses_dict = coordinator.bonuses_data
        internal_id = self.context.get(const.DATA_INTERNAL_ID)

        if not internal_id or internal_id not in bonuses_dict:
            const.LOGGER.error("Edit Bonus - Invalid Internal ID '%s'", internal_id)
            return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_BONUS)

        bonus_data = bonuses_dict[internal_id]

        if user_input is not None:
            new_name = user_input[const.CFOF_BONUSES_INPUT_NAME].strip()

            # Check for duplicate names excluding current bonus
            bonuses_except_current = {
                eid: data for eid, data in bonuses_dict.items() if eid != internal_id
            }
            errors = fh.validate_bonuses_inputs(user_input, bonuses_except_current)

            if not errors:
                # Build updated bonus data
                bonus_data_dict = fh.build_bonuses_data(user_input, bonuses_dict)
                _, updated_bonus_data = next(iter(bonus_data_dict.items()))

                coordinator.update_bonus_entity(internal_id, updated_bonus_data)

                const.LOGGER.debug(
                    "Edited Bonus '%s' with ID: %s", new_name, internal_id
                )
                self._mark_reload_needed()
                return await self.async_step_init()

        # Prepare data for schema (convert points to positive for display)
        display_data = dict(bonus_data)
        display_data[const.CFOF_BONUSES_INPUT_POINTS] = abs(
            display_data[const.DATA_BONUS_POINTS]
        )
        schema = fh.build_bonus_schema(default=display_data)
        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_EDIT_BONUS,
            data_schema=schema,
            errors=errors,
        )

    # --- Achievements ---

    async def async_step_edit_achievement(self, user_input=None):
        """Edit an existing achievement."""
        coordinator = self._get_coordinator()
        errors = {}
        achievements_dict = coordinator.achievements_data

        internal_id = self.context.get(const.DATA_INTERNAL_ID)
        if not internal_id or internal_id not in achievements_dict:
            const.LOGGER.error(
                "Edit Achievement - Invalid Internal ID '%s'", internal_id
            )
            return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_ACHIEVEMENT)

        achievement_data = achievements_dict[internal_id]

        if user_input is not None:
            # Check for duplicate names excluding current achievement
            achievements_except_current = {
                eid: data
                for eid, data in achievements_dict.items()
                if eid != internal_id
            }

            # Build kids name to ID mapping for options flow
            kids_name_to_id = {
                kid[const.DATA_KID_NAME]: kid[const.DATA_KID_INTERNAL_ID]
                for kid in coordinator.data.get(const.DATA_KIDS, {}).values()
            }

            # Build achievement data with integrated validation
            achievement_data_dict, errors = fh.build_achievements_data(
                user_input, achievements_except_current, kids_name_to_id
            )

            if not errors:
                _, updated_achievement_data = next(iter(achievement_data_dict.items()))

                coordinator.update_achievement_entity(
                    internal_id, updated_achievement_data
                )

                new_name = user_input[const.CFOF_ACHIEVEMENTS_INPUT_NAME].strip()
                const.LOGGER.debug(
                    "Edited Achievement '%s' with ID: %s",
                    new_name,
                    internal_id,
                )
                self._mark_reload_needed()
                return await self.async_step_init()

        kids_dict = {
            kid_data[const.DATA_KID_NAME]: kid_id
            for kid_id, kid_data in coordinator.kids_data.items()
        }
        chores_dict = coordinator.chores_data

        # Create reverse mapping from internal_id to name
        id_to_name = {
            kid_id: kid_data[const.DATA_KID_NAME]
            for kid_id, kid_data in coordinator.kids_data.items()
        }

        # Convert assigned_kids from internal_ids to names for display
        assigned_kids_ids = achievement_data.get(
            const.DATA_ACHIEVEMENT_ASSIGNED_KIDS, []
        )
        assigned_kids_names = [
            id_to_name.get(kid_id, kid_id) for kid_id in assigned_kids_ids
        ]

        achievement_schema = fh.build_achievement_schema(
            kids_dict=kids_dict,
            chores_dict=chores_dict,
            default={
                **achievement_data,
                const.DATA_ACHIEVEMENT_ASSIGNED_KIDS: assigned_kids_names,
            },
        )
        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_EDIT_ACHIEVEMENT,
            data_schema=achievement_schema,
            errors=errors,
        )

    # --- Challenges ---

    async def async_step_edit_challenge(self, user_input=None):
        """Edit an existing challenge."""
        coordinator = self._get_coordinator()
        errors = {}
        challenges_dict = coordinator.challenges_data
        internal_id = self.context.get(const.DATA_INTERNAL_ID)

        if not internal_id or internal_id not in challenges_dict:
            const.LOGGER.error("Edit Challenge - Invalid Internal ID '%s'", internal_id)
            return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_CHALLENGE)

        challenge_data = challenges_dict[internal_id]

        if user_input is None:
            kids_dict = {
                data[const.DATA_KID_NAME]: kid_id
                for kid_id, data in coordinator.kids_data.items()
            }
            chores_dict = coordinator.chores_data

            # Create reverse mapping from internal_id to name
            id_to_name = {
                kid_id: data[const.DATA_KID_NAME]
                for kid_id, data in coordinator.kids_data.items()
            }

            # Convert assigned_kids from internal_ids to names for display
            assigned_kids_ids = challenge_data.get(
                const.DATA_CHALLENGE_ASSIGNED_KIDS, []
            )
            assigned_kids_names = [
                id_to_name.get(kid_id, kid_id) for kid_id in assigned_kids_ids
            ]

            # Convert stored start/end dates to selector format for display
            start_date_display = None
            end_date_display = None
            if challenge_data.get(const.DATA_CHALLENGE_START_DATE):
                start_date_display = kh.normalize_datetime_input(
                    challenge_data[const.DATA_CHALLENGE_START_DATE],
                    default_tzinfo=const.DEFAULT_TIME_ZONE,
                    return_type=const.HELPER_RETURN_SELECTOR_DATETIME,
                )
            if challenge_data.get(const.DATA_CHALLENGE_END_DATE):
                end_date_display = kh.normalize_datetime_input(
                    challenge_data[const.DATA_CHALLENGE_END_DATE],
                    default_tzinfo=const.DEFAULT_TIME_ZONE,
                    return_type=const.HELPER_RETURN_SELECTOR_DATETIME,
                )

            default_data = {
                **challenge_data,
                const.DATA_CHALLENGE_START_DATE: start_date_display,
                const.DATA_CHALLENGE_END_DATE: end_date_display,
                const.DATA_CHALLENGE_ASSIGNED_KIDS: assigned_kids_names,
            }
            schema = fh.build_challenge_schema(
                kids_dict=kids_dict, chores_dict=chores_dict, default=default_data
            )
            return self.async_show_form(
                step_id=const.OPTIONS_FLOW_STEP_EDIT_CHALLENGE,
                data_schema=schema,
                errors=errors,
            )

        # Use helper to build and validate challenge data
        challenge_data_dict, errors = fh.build_challenges_data(
            user_input,
            coordinator.kids_data,
            existing_challenges=coordinator.challenges_data,
            current_id=internal_id,  # Editing existing challenge
        )

        if not errors and challenge_data_dict:
            # Additional validation for options flow: dates must be in the future
            updated_data = challenge_data_dict[internal_id]
            start_date_str = updated_data[const.DATA_CHALLENGE_START_DATE]
            end_date_str = updated_data[const.DATA_CHALLENGE_END_DATE]

            start_dt = dt_util.parse_datetime(start_date_str)
            end_dt = dt_util.parse_datetime(end_date_str)

            if start_dt and start_dt < dt_util.utcnow():
                errors = {
                    const.CFOP_ERROR_START_DATE: const.TRANS_KEY_CFOF_START_DATE_IN_PAST
                }
            elif end_dt and end_dt <= dt_util.utcnow():
                errors = {
                    const.CFOP_ERROR_END_DATE: const.TRANS_KEY_CFOF_END_DATE_IN_PAST
                }

        if not errors and challenge_data_dict:
            updated_data = challenge_data_dict[internal_id]
            coordinator.update_challenge_entity(internal_id, updated_data)

            new_name = user_input[const.CFOF_CHALLENGES_INPUT_NAME].strip()
            const.LOGGER.debug(
                "Edited Challenge '%s' with ID: %s",
                new_name,
                internal_id,
            )
            self._mark_reload_needed()
            return await self.async_step_init()

        # Show form again with validation errors, preserving user input
        kids_dict = {
            kid_data[const.DATA_KID_NAME]: kid_id
            for kid_id, kid_data in coordinator.kids_data.items()
        }
        chores_dict = coordinator.chores_data

        challenge_schema = fh.build_challenge_schema(
            kids_dict=kids_dict, chores_dict=chores_dict, default=user_input
        )
        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_EDIT_CHALLENGE,
            data_schema=challenge_schema,
            errors=errors,
        )

    # ----------------------------------------------------------------------------------
    # DELETE METHODS (Cross-Entity - Keep Together)
    # ----------------------------------------------------------------------------------

    # --- Kids ---

    async def async_step_delete_kid(self, user_input=None):
        """Delete a kid."""
        coordinator = self._get_coordinator()
        kids_dict = coordinator.kids_data
        internal_id = self.context.get(const.DATA_INTERNAL_ID)

        if not internal_id or internal_id not in kids_dict:
            const.LOGGER.error("Delete Kid - Invalid Internal ID '%s'", internal_id)
            return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_KID)

        kid_name = kids_dict[internal_id][const.DATA_KID_NAME]

        if user_input is not None:
            coordinator.delete_kid_entity(internal_id)

            const.LOGGER.debug("Deleted Kid '%s' with ID: %s", kid_name, internal_id)
            return await self.async_step_init()

        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_DELETE_KID,
            data_schema=vol.Schema({}),
            description_placeholders={
                const.OPTIONS_FLOW_PLACEHOLDER_KID_NAME: kid_name
            },
        )

    # --- Parents ---

    async def async_step_delete_parent(self, user_input=None):
        """Delete a parent."""
        coordinator = self._get_coordinator()
        parents_dict = coordinator.parents_data
        internal_id = self.context.get(const.DATA_INTERNAL_ID)

        if not internal_id or internal_id not in parents_dict:
            const.LOGGER.error("Delete Parent - Invalid Internal ID '%s'", internal_id)
            return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_PARENT)

        parent_name = parents_dict[internal_id][const.DATA_PARENT_NAME]

        if user_input is not None:
            coordinator.delete_parent_entity(internal_id)

            const.LOGGER.debug(
                "Deleted Parent '%s' with ID: %s", parent_name, internal_id
            )
            return await self.async_step_init()

        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_DELETE_PARENT,
            data_schema=vol.Schema({}),
            description_placeholders={
                const.OPTIONS_FLOW_PLACEHOLDER_PARENT_NAME: parent_name
            },
        )

    # --- Chores ---

    async def async_step_delete_chore(self, user_input=None):
        """Delete a chore."""
        coordinator = self._get_coordinator()
        chores_dict = coordinator.chores_data
        internal_id = self.context.get(const.DATA_INTERNAL_ID)

        if not internal_id or internal_id not in chores_dict:
            const.LOGGER.error("Delete Chore - Invalid Internal ID '%s'", internal_id)
            return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_CHORE)

        chore_name = chores_dict[internal_id][const.DATA_CHORE_NAME]

        if user_input is not None:
            coordinator.delete_chore_entity(internal_id)

            const.LOGGER.debug(
                "Deleted Chore '%s' with ID: %s", chore_name, internal_id
            )
            return await self.async_step_init()

        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_DELETE_CHORE,
            data_schema=vol.Schema({}),
            description_placeholders={
                const.OPTIONS_FLOW_PLACEHOLDER_CHORE_NAME: chore_name
            },
        )

    # --- Badges ---

    async def async_step_delete_badge(self, user_input=None):
        """Delete a badge."""
        coordinator = self._get_coordinator()
        badges_dict = coordinator.badges_data
        internal_id = self.context.get(const.DATA_INTERNAL_ID)

        if not internal_id or internal_id not in badges_dict:
            const.LOGGER.error("Delete Badge - Invalid Internal ID '%s'", internal_id)
            return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_BADGE)

        badge_name = badges_dict[internal_id][const.DATA_BADGE_NAME]

        if user_input is not None:
            coordinator.delete_badge_entity(internal_id)

            const.LOGGER.debug(
                "Deleted Badge '%s' with ID: %s", badge_name, internal_id
            )
            return await self.async_step_init()

        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_DELETE_BADGE,
            data_schema=vol.Schema({}),
            description_placeholders={
                const.OPTIONS_FLOW_PLACEHOLDER_BADGE_NAME: badge_name
            },
        )

    # --- Rewards ---

    async def async_step_delete_reward(self, user_input=None):
        """Delete a reward."""
        coordinator = self._get_coordinator()
        rewards_dict = coordinator.rewards_data
        internal_id = self.context.get(const.DATA_INTERNAL_ID)

        if not internal_id or internal_id not in rewards_dict:
            const.LOGGER.error("Delete Reward - Invalid Internal ID '%s'", internal_id)
            return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_REWARD)

        reward_name = rewards_dict[internal_id][const.DATA_REWARD_NAME]

        if user_input is not None:
            coordinator.delete_reward_entity(internal_id)

            const.LOGGER.debug(
                "Deleted Reward '%s' with ID: %s", reward_name, internal_id
            )
            return await self.async_step_init()

        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_DELETE_REWARD,
            data_schema=vol.Schema({}),
            description_placeholders={
                const.OPTIONS_FLOW_PLACEHOLDER_REWARD_NAME: reward_name
            },
        )

    # --- Penalties ---

    async def async_step_delete_penalty(self, user_input=None):
        """Delete a penalty."""
        coordinator = self._get_coordinator()
        penalties_dict = coordinator.penalties_data
        internal_id = self.context.get(const.DATA_INTERNAL_ID)

        if not internal_id or internal_id not in penalties_dict:
            const.LOGGER.error("Delete Penalty - Invalid Internal ID '%s'", internal_id)
            return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_PENALTY)

        penalty_name = penalties_dict[internal_id][const.DATA_PENALTY_NAME]

        if user_input is not None:
            coordinator.delete_penalty_entity(internal_id)

            const.LOGGER.debug(
                "Deleted Penalty '%s' with ID: %s", penalty_name, internal_id
            )
            return await self.async_step_init()

        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_DELETE_PENALTY,
            data_schema=vol.Schema({}),
            description_placeholders={
                const.OPTIONS_FLOW_PLACEHOLDER_PENALTY_NAME: penalty_name
            },
        )

    # --- Achievements ---

    async def async_step_delete_achievement(self, user_input=None):
        """Delete an achievement."""
        coordinator = self._get_coordinator()
        achievements_dict = coordinator.achievements_data
        internal_id = self.context.get(const.DATA_INTERNAL_ID)

        if not internal_id or internal_id not in achievements_dict:
            const.LOGGER.error(
                "Delete Achievement - Invalid Internal ID '%s'", internal_id
            )
            return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_ACHIEVEMENT)

        achievement_name = achievements_dict[internal_id][const.DATA_ACHIEVEMENT_NAME]

        if user_input is not None:
            coordinator.delete_achievement_entity(internal_id)

            const.LOGGER.debug(
                "Deleted Achievement '%s' with ID: %s",
                achievement_name,
                internal_id,
            )
            return await self.async_step_init()

        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_DELETE_ACHIEVEMENT,
            data_schema=vol.Schema({}),
            description_placeholders={
                const.OPTIONS_FLOW_PLACEHOLDER_ACHIEVEMENT_NAME: achievement_name
            },
        )

    # --- Challenges ---

    async def async_step_delete_challenge(self, user_input=None):
        """Delete a challenge."""
        coordinator = self._get_coordinator()
        challenges_dict = coordinator.challenges_data
        internal_id = self.context.get(const.DATA_INTERNAL_ID)

        if not internal_id or internal_id not in challenges_dict:
            const.LOGGER.error(
                "Delete Challenge - Invalid Internal ID '%s'", internal_id
            )
            return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_CHALLENGE)

        challenge_name = challenges_dict[internal_id][const.DATA_CHALLENGE_NAME]

        if user_input is not None:
            coordinator.delete_challenge_entity(internal_id)

            const.LOGGER.debug(
                "Deleted Challenge '%s' with ID: %s", challenge_name, internal_id
            )
            return await self.async_step_init()

        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_DELETE_CHALLENGE,
            data_schema=vol.Schema({}),
            description_placeholders={
                const.OPTIONS_FLOW_PLACEHOLDER_CHALLENGE_NAME: challenge_name
            },
        )

    # --- Bonuses ---

    async def async_step_delete_bonus(self, user_input=None):
        """Delete a bonus."""
        coordinator = self._get_coordinator()
        bonuses_dict = coordinator.bonuses_data
        internal_id = self.context.get(const.DATA_INTERNAL_ID)

        if not internal_id or internal_id not in bonuses_dict:
            const.LOGGER.error("Delete Bonus - Invalid Internal ID '%s'", internal_id)
            return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_BONUS)

        bonus_name = bonuses_dict[internal_id][const.DATA_BONUS_NAME]

        if user_input is not None:
            coordinator.delete_bonus_entity(internal_id)

            const.LOGGER.debug(
                "Deleted Bonus '%s' with ID: %s", bonus_name, internal_id
            )
            return await self.async_step_init()

        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_DELETE_BONUS,
            data_schema=vol.Schema({}),
            description_placeholders={
                const.OPTIONS_FLOW_PLACEHOLDER_BONUS_NAME: bonus_name
            },
        )

    # ----------------------------------------------------------------------------------
    # GENERAL OPTIONS
    # ----------------------------------------------------------------------------------

    async def async_step_manage_general_options(self, user_input=None):
        """Manage general options: points adjust values, update interval, retention, and backup settings."""
        # Check if this is a backup management action
        if user_input is not None and const.CFOF_BACKUP_ACTION_SELECTION in user_input:
            action = user_input[const.CFOF_BACKUP_ACTION_SELECTION]
            # Skip empty/default selection
            if action and action.strip():
                if action == "create_backup":
                    return await self.async_step_create_manual_backup()
                elif action == "delete_backup":
                    return await self.async_step_select_backup_to_delete()
                elif action == "restore_backup":
                    return await self.async_step_select_backup_to_restore()

        if user_input is not None:
            # Get the raw text from the multiline text area.
            points_str = user_input.get(
                const.CFOF_SYSTEM_INPUT_POINTS_ADJUST_VALUES, const.SENTINEL_EMPTY
            ).strip()
            if points_str:
                # Parse the values by splitting on separator.
                parsed_values = kh.parse_points_adjust_values(points_str)
                # Always store as a list of floats.
                self._entry_options[const.CONF_POINTS_ADJUST_VALUES] = parsed_values
            else:
                # Remove the key if the field is left empty.
                self._entry_options.pop(const.CONF_POINTS_ADJUST_VALUES, None)
            # Update the update interval.
            self._entry_options[const.CONF_UPDATE_INTERVAL] = user_input.get(
                const.CFOF_SYSTEM_INPUT_UPDATE_INTERVAL
            )
            # update calendar show period
            self._entry_options[const.CONF_CALENDAR_SHOW_PERIOD] = user_input.get(
                const.CFOF_SYSTEM_INPUT_CALENDAR_SHOW_PERIOD
            )
            # Parse consolidated retention periods
            retention_str = user_input.get(
                const.CFOF_SYSTEM_INPUT_RETENTION_PERIODS, ""
            ).strip()
            if retention_str:
                try:
                    daily, weekly, monthly, yearly = fh.parse_retention_periods(
                        retention_str
                    )
                    self._entry_options[const.CONF_RETENTION_DAILY] = daily
                    self._entry_options[const.CONF_RETENTION_WEEKLY] = weekly
                    self._entry_options[const.CONF_RETENTION_MONTHLY] = monthly
                    self._entry_options[const.CONF_RETENTION_YEARLY] = yearly
                except ValueError as err:
                    const.LOGGER.error("Failed to parse retention periods: %s", err)
                    # Use defaults if parsing fails
                    self._entry_options[const.CONF_RETENTION_DAILY] = (
                        const.DEFAULT_RETENTION_DAILY
                    )
                    self._entry_options[const.CONF_RETENTION_WEEKLY] = (
                        const.DEFAULT_RETENTION_WEEKLY
                    )
                    self._entry_options[const.CONF_RETENTION_MONTHLY] = (
                        const.DEFAULT_RETENTION_MONTHLY
                    )
                    self._entry_options[const.CONF_RETENTION_YEARLY] = (
                        const.DEFAULT_RETENTION_YEARLY
                    )
            # Update legacy entities toggle
            self._entry_options[const.CONF_SHOW_LEGACY_ENTITIES] = user_input.get(
                const.CFOF_SYSTEM_INPUT_SHOW_LEGACY_ENTITIES,
                const.DEFAULT_SHOW_LEGACY_ENTITIES,
            )
            # Update backup retention (count-based)
            self._entry_options[const.CONF_BACKUPS_MAX_RETAINED] = user_input.get(
                const.CFOF_SYSTEM_INPUT_BACKUPS_MAX_RETAINED,
                const.DEFAULT_BACKUPS_MAX_RETAINED,
            )
            const.LOGGER.debug(
                "General Options Updated: Points Adjust Values=%s, "
                "Update Interval=%s, Calendar Period to Show=%s, "
                "Retention Periods=%s, "
                "Show Legacy Entities=%s, Backup Retention=%s",
                self._entry_options.get(const.CONF_POINTS_ADJUST_VALUES),
                self._entry_options.get(const.CONF_UPDATE_INTERVAL),
                self._entry_options.get(const.CONF_CALENDAR_SHOW_PERIOD),
                retention_str,
                self._entry_options.get(const.CONF_SHOW_LEGACY_ENTITIES),
                self._entry_options.get(const.CONF_BACKUPS_MAX_RETAINED),
            )
            await self._update_system_settings_and_reload()
            # After saving settings, return to main menu
            return await self.async_step_init()

        general_schema = fh.build_general_options_schema(self._entry_options)
        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_MANAGE_GENERAL_OPTIONS,
            data_schema=general_schema,
            description_placeholders={},
        )

    async def async_step_restore_backup(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle restore_backup step - delegate to restore_from_options."""
        return await self.async_step_restore_from_options(user_input)

    async def async_step_restore_from_options(self, user_input=None):
        """Handle restore options from general options menu (same as config flow)."""
        from pathlib import Path

        errors = {}

        if user_input is not None:
            selection = user_input.get(const.CFOF_DATA_RECOVERY_INPUT_SELECTION)

            if selection == "cancel":
                # Return to backup management menu without making changes
                return await self.async_step_manage_general_options()
            if selection == "start_fresh":
                return await self._handle_start_fresh_from_options()
            if selection == "current_active":
                return await self._handle_use_current_from_options()
            if selection == "paste_json":
                return await self.async_step_restore_paste_json_options()
            # Otherwise it's a backup filename - restore it
            if selection:
                return await self._handle_restore_backup_from_options(selection)

            errors[const.CFOP_ERROR_BASE] = const.TRANS_KEY_CFOF_INVALID_SELECTION

        # Build selection menu
        storage_path = Path(self.hass.config.path(".storage", const.STORAGE_KEY))
        storage_file_exists = await self.hass.async_add_executor_job(
            storage_path.exists
        )

        # Discover backups (pass None for storage_manager - not needed for discovery)
        backups = await fh.discover_backups(self.hass, None)
        if not isinstance(backups, list):
            backups = []  # Handle any unexpected return type

        # Build options list for SelectSelector
        # Start with fixed options that can be translated
        options = []

        # Add cancel option first (for easy access)
        options.append("cancel")

        # Only show "use current" if file actually exists
        if storage_file_exists:
            options.append("current_active")

        options.append("start_fresh")

        # Add discovered backups (these use dynamic labels)
        for backup in backups:
            options.append(backup["filename"])

        # Add paste JSON option
        options.append("paste_json")

        # Build description placeholders for dynamic backup labels
        backup_labels = {}
        for backup in backups:
            age_str = fh.format_backup_age(backup["age_hours"])
            tag_display = backup["tag"].replace("-", " ").title()
            backup_labels[backup["filename"]] = (
                f"[{tag_display}] {backup['filename']} ({age_str})"
            )

        # Build schema using SelectSelector with translation_key
        data_schema = vol.Schema(
            {
                vol.Required(
                    const.CFOF_DATA_RECOVERY_INPUT_SELECTION
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options,
                        mode=selector.SelectSelectorMode.LIST,
                        translation_key="data_recovery_selection",
                        custom_value=True,  # Allow backup filenames not in translations
                    )
                )
            }
        )

        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_RESTORE_BACKUP,
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "storage_path": str(storage_path.parent),
                "backup_count": str(len(backups)),
            },
        )

    async def _handle_start_fresh_from_options(self):
        """Handle 'Start Fresh' from options - backup existing and delete, then reload."""
        import os
        from pathlib import Path

        from .storage_manager import KidsChoresStorageManager

        try:
            storage_manager = KidsChoresStorageManager(self.hass)
            storage_path = Path(storage_manager.get_storage_path())

            # Create safety backup if file exists
            if storage_path.exists():
                backup_name = await fh.create_timestamped_backup(
                    self.hass, storage_manager, const.BACKUP_TAG_RECOVERY
                )
                if backup_name:
                    const.LOGGER.info(
                        "Created safety backup before fresh start: %s", backup_name
                    )

                # Delete active file
                await self.hass.async_add_executor_job(os.remove, str(storage_path))
                const.LOGGER.info("Deleted active storage file for fresh start")

            # Reload the entry to reinitialize from scratch
            self._mark_reload_needed()
            return await self.async_step_init()

        except Exception as err:  # pylint: disable=broad-except
            const.LOGGER.error("Fresh start failed: %s", err)
            return self.async_abort(reason="unknown")

    async def _handle_use_current_from_options(self):
        """Handle 'Use Current Active' from options - validate and reload."""
        import json
        from pathlib import Path

        try:
            # Get storage path without creating storage manager yet
            storage_path = Path(self.hass.config.path(".storage", const.STORAGE_KEY))

            if not storage_path.exists():
                return self.async_abort(reason="file_not_found")

            # Validate JSON
            data_str = await self.hass.async_add_executor_job(
                storage_path.read_text, "utf-8"
            )

            try:
                json.loads(data_str)  # Parse to validate
            except json.JSONDecodeError:
                return self.async_abort(reason="corrupt_file")

            # Validate structure
            if not fh.validate_backup_json(data_str):
                return self.async_abort(reason="invalid_structure")

            const.LOGGER.info("Using current active storage file")
            self._mark_reload_needed()
            return await self.async_step_init()

        except Exception as err:  # pylint: disable=broad-except
            const.LOGGER.error("Use current failed: %s", err)
            return self.async_abort(reason="unknown")

    async def async_step_restore_paste_json_options(self, user_input=None):
        """Allow user to paste JSON data from diagnostics in options flow."""
        import json
        from pathlib import Path

        errors = {}

        if user_input is not None:
            json_text = user_input.get(
                const.CFOF_DATA_RECOVERY_INPUT_JSON_DATA, ""
            ).strip()

            if not json_text:
                errors[const.CFOP_ERROR_BASE] = "empty_json"
            else:
                try:
                    # Parse JSON
                    pasted_data = json.loads(json_text)

                    # Validate structure
                    if not fh.validate_backup_json(json_text):
                        errors[const.CFOP_ERROR_BASE] = "invalid_structure"
                    else:
                        # Determine data format and extract storage data
                        storage_data = pasted_data

                        # Handle diagnostic format (KC 4.0+ diagnostic exports)
                        if "home_assistant" in pasted_data and "data" in pasted_data:
                            const.LOGGER.info("Processing diagnostic export format")
                            storage_data = pasted_data["data"]
                        # Handle Store format (KC 3.0/3.1/4.0beta1)
                        elif "version" in pasted_data and "data" in pasted_data:
                            const.LOGGER.info("Processing Store format")
                            storage_data = pasted_data["data"]
                        # Raw storage data format
                        else:
                            const.LOGGER.info("Processing raw storage format")
                            storage_data = pasted_data

                        # Always wrap in HA Store format for storage file
                        wrapped_data = {
                            "version": 1,
                            "minor_version": 1,
                            "key": const.STORAGE_KEY,
                            "data": storage_data,
                        }

                        # Write to storage file
                        storage_path = Path(
                            self.hass.config.path(".storage", const.STORAGE_KEY)
                        )

                        # Write wrapped data to storage (directory created by HA/test fixtures)
                        await self.hass.async_add_executor_job(
                            storage_path.write_text,
                            json.dumps(wrapped_data, indent=2),
                            "utf-8",
                        )

                        const.LOGGER.info("Successfully imported JSON data to storage")

                        # Cleanup old backups
                        from .storage_manager import KidsChoresStorageManager

                        storage_manager = KidsChoresStorageManager(self.hass)
                        max_backups = const.DEFAULT_BACKUPS_MAX_RETAINED
                        await fh.cleanup_old_backups(
                            self.hass, storage_manager, max_backups
                        )

                        # Reload and return to init
                        self._mark_reload_needed()
                        return await self.async_step_init()

                except json.JSONDecodeError:
                    errors[const.CFOP_ERROR_BASE] = "invalid_json"
                except Exception as err:  # pylint: disable=broad-except
                    const.LOGGER.error("Paste JSON failed: %s", err)
                    errors[const.CFOP_ERROR_BASE] = "unknown"

        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_PASTE_JSON_RESTORE,
            data_schema=vol.Schema(
                {
                    vol.Required(
                        const.CFOF_DATA_RECOVERY_INPUT_JSON_DATA
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            multiline=True,
                            type=selector.TextSelectorType.PASSWORD,
                        )
                    )
                }
            ),
            errors=errors,
        )

    async def async_step_paste_json_restore(self, user_input=None) -> dict[str, Any]:
        """Handle paste_json_restore step - delegate to paste_json_options."""
        return await self.async_step_restore_paste_json_options(user_input)

    async def _handle_restore_backup_from_options(self, backup_filename: str):
        """Handle restoring from a specific backup file in options flow."""
        import json
        import shutil
        from pathlib import Path

        from .storage_manager import KidsChoresStorageManager

        try:
            # Get storage path directly without creating storage manager yet
            storage_path = Path(self.hass.config.path(".storage", const.STORAGE_KEY))
            backup_path = storage_path.parent / backup_filename

            if not backup_path.exists():
                const.LOGGER.error("Backup file not found: %s", backup_filename)
                return self.async_abort(reason="file_not_found")

            # Read and validate backup
            backup_data_str = await self.hass.async_add_executor_job(
                backup_path.read_text, "utf-8"
            )

            try:
                json.loads(backup_data_str)  # Validate parseable JSON
            except json.JSONDecodeError:
                const.LOGGER.error("Backup file has invalid JSON: %s", backup_filename)
                return self.async_abort(reason="corrupt_file")

            # Validate structure
            if not fh.validate_backup_json(backup_data_str):
                const.LOGGER.error(
                    "Backup file missing required keys: %s", backup_filename
                )
                return self.async_abort(reason="invalid_structure")

            # Create safety backup of current file if it exists
            if storage_path.exists():
                # Create storage manager only for safety backup creation
                storage_manager = KidsChoresStorageManager(self.hass)
                safety_backup = await fh.create_timestamped_backup(
                    self.hass, storage_manager, const.BACKUP_TAG_RECOVERY
                )
                if safety_backup:
                    const.LOGGER.info(
                        "Created safety backup before restore: %s", safety_backup
                    )

            # Parse backup data
            backup_data = json.loads(backup_data_str)

            # Check if backup already has Home Assistant storage format
            if "version" in backup_data and "data" in backup_data:
                # Already in storage format - restore as-is
                await self.hass.async_add_executor_job(
                    shutil.copy2, str(backup_path), str(storage_path)
                )
            else:
                # Raw data format (like v30, v31, v40beta1 samples)
                # Load through storage manager to add proper wrapper
                storage_manager = KidsChoresStorageManager(self.hass)
                storage_manager.set_data(backup_data)
                await storage_manager.async_save()

            const.LOGGER.info("Restored backup: %s", backup_filename)

            # Cleanup old backups
            storage_manager = KidsChoresStorageManager(self.hass)
            max_backups = const.DEFAULT_BACKUPS_MAX_RETAINED
            await fh.cleanup_old_backups(self.hass, storage_manager, max_backups)

            # Reload and return to init
            self._mark_reload_needed()
            return await self.async_step_init()

        except Exception as err:  # pylint: disable=broad-except
            const.LOGGER.error("Restore backup failed: %s", err)
            return self.async_abort(reason="unknown")

    async def async_step_backup_actions_menu(self, user_input=None):
        """Show backup management actions menu."""
        from .storage_manager import KidsChoresStorageManager

        if user_input is not None:
            action = user_input[const.CFOF_BACKUP_ACTION_SELECTION]

            if action == "create_backup":
                return await self.async_step_create_manual_backup()
            elif action == "delete_backup":
                return await self.async_step_select_backup_to_delete()
            elif action == "restore_backup":
                return await self.async_step_select_backup_to_restore()
            elif action == "return_to_menu":
                return await self.async_step_init()

        # Discover backups to show count
        storage_manager = KidsChoresStorageManager(self.hass)
        backups = await fh.discover_backups(self.hass, storage_manager)
        backup_count = len(backups)

        # Calculate total storage usage
        total_size_mb = sum(b.get("size_bytes", 0) for b in backups) / (1024 * 1024)

        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_BACKUP_ACTIONS,
            data_schema=vol.Schema(
                {
                    vol.Required(
                        const.CFOF_BACKUP_ACTION_SELECTION
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                "create_backup",
                                "delete_backup",
                                "restore_backup",
                                "return_to_menu",
                            ],
                            mode=selector.SelectSelectorMode.LIST,
                            translation_key=const.TRANS_KEY_CFOF_BACKUP_ACTIONS_MENU,
                        )
                    )
                }
            ),
            description_placeholders={
                "backup_count": str(backup_count),
                "storage_size": f"{total_size_mb:.2f}",
            },
        )

    async def async_step_select_backup_to_delete(self, user_input=None):
        """Select a backup file to delete."""
        from .storage_manager import KidsChoresStorageManager

        storage_manager = KidsChoresStorageManager(self.hass)

        if user_input is not None:
            selection = user_input.get(const.CFOF_BACKUP_SELECTION)

            if selection == "cancel":
                return await self.async_step_backup_actions_menu()

            # Extract backup filename from emoji-prefixed selection
            if selection and selection.startswith("🗑️"):
                filename = self._extract_filename_from_selection(selection)
                if filename:
                    self._backup_to_delete = filename
                    return await self.async_step_delete_backup_confirm()

            return await self.async_step_backup_actions_menu()

        # Discover all backups
        backups = await fh.discover_backups(self.hass, storage_manager)

        # Build backup options - EMOJI ONLY for files (no hardcoded action text)
        # All backups can be deleted (no protected backups concept)
        backup_options = []

        for backup in backups:
            age_str = fh.format_backup_age(backup["age_hours"])
            size_kb = backup["size_bytes"] / 1024
            tag_display = backup["tag"].replace("-", " ").title()

            # Emoji-only prefix - NO hardcoded English text
            option = (
                f"🗑️ [{tag_display}] {backup['filename']} ({age_str}, {size_kb:.1f} KB)"
            )
            backup_options.append(option)

        # Add cancel option (translated via translation_key)
        backup_options.append("cancel")

        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_SELECT_BACKUP_TO_DELETE,
            data_schema=vol.Schema(
                {
                    vol.Required(const.CFOF_BACKUP_SELECTION): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=backup_options,
                            mode=selector.SelectSelectorMode.LIST,
                            translation_key=const.TRANS_KEY_CFOF_SELECT_BACKUP_TO_DELETE,
                            custom_value=True,
                        )
                    )
                }
            ),
            description_placeholders={
                "backup_count": str(len(backups)),
            },
        )

    async def async_step_select_backup_to_restore(self, user_input=None):
        """Select a backup file to restore."""
        from .storage_manager import KidsChoresStorageManager

        storage_manager = KidsChoresStorageManager(self.hass)

        if user_input is not None:
            selection = user_input.get(const.CFOF_BACKUP_SELECTION)

            if selection == "cancel":
                return await self.async_step_backup_actions_menu()

            # Extract backup filename from emoji-prefixed selection
            if selection and selection.startswith("🔄"):
                filename = self._extract_filename_from_selection(selection)
                if filename:
                    self._backup_to_restore = filename
                    return await self.async_step_restore_backup_confirm()

            return await self.async_step_backup_actions_menu()

        # Discover all backups
        backups = await fh.discover_backups(self.hass, storage_manager)

        if not backups:
            # No backups available - return to menu
            return await self.async_step_backup_actions_menu()

        # Build backup options - EMOJI ONLY for files (no hardcoded action text)
        backup_options = []

        for backup in backups:
            age_str = fh.format_backup_age(backup["age_hours"])
            size_kb = backup["size_bytes"] / 1024
            tag_display = backup["tag"].replace("-", " ").title()

            # Emoji-only prefix - NO hardcoded English text
            option = (
                f"🔄 [{tag_display}] {backup['filename']} ({age_str}, {size_kb:.1f} KB)"
            )
            backup_options.append(option)

        # Add cancel option (translated via translation_key)
        backup_options.append("cancel")

        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_SELECT_BACKUP_TO_RESTORE,
            data_schema=vol.Schema(
                {
                    vol.Required(const.CFOF_BACKUP_SELECTION): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=backup_options,
                            mode=selector.SelectSelectorMode.LIST,
                            translation_key=const.TRANS_KEY_CFOF_SELECT_BACKUP_TO_RESTORE,
                            custom_value=True,
                        )
                    )
                }
            ),
            description_placeholders={"backup_count": str(len(backups))},
        )

    def _extract_filename_from_selection(self, selection: str) -> str | None:
        """Extract backup filename from emoji-prefixed selection.

        Format: "🔄 [Tag] filename.json (age, size)" or "🗑️ [Tag] filename.json (age, size)"
        Returns: "filename.json" or None if extraction fails
        """
        # Remove emoji prefix (first 2-3 characters depending on emoji width)
        if selection.startswith("🔄 ") or selection.startswith("🗑️ "):
            display_part = selection[2:].strip()

            # Extract from "[Tag] filename.json (age, size)"
            if "] " in display_part and " (" in display_part:
                start_idx = display_part.find("] ") + 2
                end_idx = display_part.rfind(" (")
                if start_idx < end_idx:
                    return display_part[start_idx:end_idx]

        # Fallback: return None (couldn't parse)
        return None

    async def async_step_create_manual_backup(self, user_input=None):
        """Create a manual backup."""
        from .storage_manager import KidsChoresStorageManager

        storage_manager = KidsChoresStorageManager(self.hass)

        if user_input is not None:
            if user_input.get("confirm"):
                # Create manual backup
                backup_filename = await fh.create_timestamped_backup(
                    self.hass,
                    storage_manager,
                    const.BACKUP_TAG_MANUAL,
                )

                if backup_filename:
                    const.LOGGER.info("Manual backup created: %s", backup_filename)
                    # Run cleanup with current retention setting
                    retention = self._entry_options.get(
                        const.CONF_BACKUPS_MAX_RETAINED,
                        const.DEFAULT_BACKUPS_MAX_RETAINED,
                    )
                    await fh.cleanup_old_backups(self.hass, storage_manager, retention)

                    # Show success message and return to backup menu
                    const.LOGGER.info(
                        "Manual backup created successfully: %s", backup_filename
                    )
                    return await self.async_step_backup_actions_menu()
                else:
                    const.LOGGER.error("Failed to create manual backup")
                    return await self.async_step_backup_actions_menu()
            else:
                return await self.async_step_backup_actions_menu()

        # Get backup count and retention for placeholders
        available_backups = await fh.discover_backups(self.hass, storage_manager)
        backup_count = len(available_backups)
        retention = self._entry_options.get(
            const.CONF_BACKUPS_MAX_RETAINED,
            const.DEFAULT_BACKUPS_MAX_RETAINED,
        )

        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_CREATE_MANUAL_BACKUP,
            data_schema=vol.Schema(
                {
                    vol.Required("confirm", default=False): selector.BooleanSelector(),
                }
            ),
            description_placeholders={
                "backup_count": str(backup_count),
                "retention": str(retention),
            },
        )

    async def async_step_delete_backup_confirm(self, user_input=None):
        """Confirm backup deletion."""
        from pathlib import Path

        from .storage_manager import KidsChoresStorageManager

        # Get backup filename from context (set by select_backup_to_delete step)
        backup_filename = getattr(self, "_backup_to_delete", None)

        if user_input is not None:
            if user_input.get("confirm"):
                storage_manager = KidsChoresStorageManager(self.hass)
                storage_path = Path(storage_manager.get_storage_path())
                # Type guard: ensure backup_filename is a string before using in Path operation
                if isinstance(backup_filename, str):
                    backup_path = storage_path.parent / backup_filename

                    if backup_path.exists():
                        try:
                            await self.hass.async_add_executor_job(backup_path.unlink)
                            const.LOGGER.info("Deleted backup: %s", backup_filename)
                        except Exception as err:
                            const.LOGGER.error(
                                "Failed to delete backup %s: %s", backup_filename, err
                            )
                    else:
                        const.LOGGER.error("Backup file not found: %s", backup_filename)
                else:
                    const.LOGGER.error("Invalid backup filename: %s", backup_filename)

            # Clear the backup filename and return to backup menu
            self._backup_to_delete = None
            return await self.async_step_backup_actions_menu()

        # Show confirmation form
        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_DELETE_BACKUP_CONFIRM,
            data_schema=vol.Schema(
                {
                    vol.Required("confirm", default=False): selector.BooleanSelector(),
                }
            ),
            description_placeholders={"backup_filename": backup_filename or "unknown"},
        )

    async def async_step_restore_backup_confirm(self, user_input=None):
        """Confirm backup restoration."""
        import shutil
        from pathlib import Path

        from .storage_manager import KidsChoresStorageManager

        # Get backup filename from context (set by select_backup_to_restore step)
        backup_filename = getattr(self, "_backup_to_restore", None)

        if user_input is not None:
            if user_input.get("confirm"):
                storage_manager = KidsChoresStorageManager(self.hass)
                storage_path = Path(storage_manager.get_storage_path())
                # Type guard: ensure backup_filename is a string before using in Path operation
                if not isinstance(backup_filename, str):
                    const.LOGGER.error("Invalid backup filename: %s", backup_filename)
                    self._backup_to_restore = None
                    return await self.async_step_backup_actions_menu()

                backup_path = storage_path.parent / backup_filename

                if not backup_path.exists():
                    const.LOGGER.error("Backup file not found: %s", backup_filename)
                    self._backup_to_restore = None
                    return await self.async_step_backup_actions_menu()

                # Read and validate backup
                try:
                    backup_data_str = await self.hass.async_add_executor_job(
                        backup_path.read_text, "utf-8"
                    )
                except Exception as err:  # pylint: disable=broad-except
                    const.LOGGER.error(
                        "Failed to read backup file %s: %s", backup_filename, err
                    )
                    self._backup_to_restore = None
                    return await self.async_step_backup_actions_menu()

                if not fh.validate_backup_json(backup_data_str):
                    const.LOGGER.error("Invalid backup file: %s", backup_filename)
                    self._backup_to_restore = None
                    return await self.async_step_backup_actions_menu()

                try:
                    # Create safety backup of current file
                    safety_backup = await fh.create_timestamped_backup(
                        self.hass,
                        storage_manager,
                        const.BACKUP_TAG_RECOVERY,
                    )
                    const.LOGGER.info("Created safety backup: %s", safety_backup)

                    # Restore backup
                    await self.hass.async_add_executor_job(
                        shutil.copy2, backup_path, storage_path
                    )
                    const.LOGGER.info("Restored backup: %s", backup_filename)

                    # Cleanup old backups
                    retention = self._entry_options.get(
                        const.CONF_BACKUPS_MAX_RETAINED,
                        const.DEFAULT_BACKUPS_MAX_RETAINED,
                    )
                    await fh.cleanup_old_backups(self.hass, storage_manager, retention)

                    # Clear context and reload integration to pick up restored data
                    self._backup_to_restore = None
                    await self.hass.config_entries.async_reload(
                        self.config_entry.entry_id
                    )

                    return self.async_abort(reason="backup_restored")

                except Exception as err:
                    const.LOGGER.error(
                        "Failed to restore backup %s: %s", backup_filename, err
                    )
                    self._backup_to_restore = None
                    return await self.async_step_backup_actions_menu()
            else:
                # User cancelled - clear context and return to backup menu
                self._backup_to_restore = None
                return await self.async_step_backup_actions_menu()

        # Show confirmation form
        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_RESTORE_BACKUP_CONFIRM,
            data_schema=vol.Schema(
                {
                    vol.Required("confirm", default=False): selector.BooleanSelector(),
                }
            ),
            description_placeholders={"backup_filename": backup_filename or "unknown"},
        )

    # ----------------------------------------------------------------------------------
    # HELPER METHODS (RELOAD & PERSISTENCE)
    # ----------------------------------------------------------------------------------

    def _mark_reload_needed(self):
        """Mark that a reload is needed after the current flow completes.

        When entities (rewards, bonuses, chores, etc.) are added, edited, or deleted,
        the coordinator data is updated but new sensors are not automatically created.
        We defer the reload until the user returns to the main menu to avoid
        interrupting the flow mid-operation.
        """
        const.LOGGER.debug("Marking reload needed after entity change")
        self._reload_needed = True

    async def _reload_entry_after_entity_change(self):
        """Reload the config entry to recreate sensors.

        This is called when returning to the main menu after entity changes.
        After reload, triggers an immediate coordinator refresh so new entities get data.
        """
        const.LOGGER.debug(
            "Reloading entry after entity changes: %s",
            self.config_entry.entry_id,
        )
        try:
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            const.LOGGER.debug("Entry reloaded successfully")
        except Exception as err:
            const.LOGGER.error(
                "Failed to reload config entry after entity changes: %s",
                err,
                exc_info=True,
            )
            # Continue despite reload failure - UI still shows menu and entities
            # will reload on next Home Assistant restart

        # Trigger immediate coordinator refresh so new entities get data right away
        # instead of waiting for the next update interval
        coordinator = self._get_coordinator()
        if coordinator:
            const.LOGGER.debug("Triggering immediate coordinator refresh after reload")
            await coordinator.async_request_refresh()
            const.LOGGER.debug("Coordinator refresh completed")

    async def _update_system_settings_and_reload(self):
        """Update system settings in config and reload (for points_label, update_interval, etc.)."""
        new_data = dict(self.config_entry.data)
        new_data[const.DATA_LAST_CHANGE] = dt_util.utcnow().isoformat()

        self.hass.config_entries.async_update_entry(
            self.config_entry, data=new_data, options=self._entry_options
        )
        const.LOGGER.debug(
            "Updating system settings. Reloading entry: %s",
            self.config_entry.entry_id,
        )
        try:
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            const.LOGGER.debug("System settings updated and KidsChores reloaded")
        except Exception as err:
            const.LOGGER.error(
                "Failed to reload config entry after system settings update: %s",
                err,
                exc_info=True,
            )
            # Continue despite reload failure - settings saved in config entry
            # and will take effect on next Home Assistant restart
