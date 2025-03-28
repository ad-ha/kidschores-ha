# File: options_flow.py
"""Options Flow for the KidsChores integration, managing entities by internal_id.

Handles add/edit/delete operations with entities referenced internally by internal_id.
Ensures consistency and reloads the integration upon changes.
"""

import datetime
import uuid
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from homeassistant.util import dt as dt_util

from . import const
from . import flow_helpers as fh
from . import kc_helpers as kh


def _ensure_str(value):
    """Convert anything to string safely."""
    if isinstance(value, dict):
        # Attempt to get a known key or fallback
        return str(
            value.get(const.CONF_VALUE, next(iter(value.values()), const.CONF_EMPTY))
        )
    return str(value)


class KidsChoresOptionsFlowHandler(config_entries.OptionsFlow):
    """Options Flow for adding/editing/deleting configuration elements."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize the options flow."""
        self._entry_options = {}
        self._action = None
        self._entity_type = None

    async def async_step_init(self, user_input=None):
        """Display the main menu for the Options Flow."""
        self._entry_options = dict(self.config_entry.options)

        if user_input is not None:
            selection = user_input[const.OPTIONS_FLOW_INPUT_MENU_SELECTION]

            if selection == const.OPTIONS_FLOW_POINTS:
                return await self.async_step_manage_points()

            elif selection == const.OPTIONS_FLOW_GENERAL_OPTIONS:
                return await self.async_step_manage_general_options()

            elif selection.startswith(const.OPTIONS_FLOW_MENU_MANAGE_PREFIX):
                self._entity_type = selection.replace(
                    const.OPTIONS_FLOW_MENU_MANAGE_PREFIX, const.CONF_EMPTY
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
        if user_input is not None:
            new_label = user_input.get(
                const.CONF_POINTS_LABEL, const.DEFAULT_POINTS_LABEL
            )
            new_icon = user_input.get(const.CONF_POINTS_ICON, const.DEFAULT_POINTS_ICON)

            self._entry_options = dict(self.config_entry.options)
            self._entry_options[const.CONF_POINTS_LABEL] = new_label
            self._entry_options[const.CONF_POINTS_ICON] = new_icon
            const.LOGGER.debug(
                "Configured points with %s and icon %s", new_label, new_icon
            )
            await self._update_and_reload()

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
            description_placeholders={
                const.OPTIONS_FLOW_PLACEHOLDER_ENTITY_TYPE: self._entity_type
            },
        )

    async def async_step_select_entity(self, user_input=None):
        """Select an entity (kid, chore, etc.) to edit or delete based on internal_id."""
        if self._action not in [
            const.OPTIONS_FLOW_ACTIONS_EDIT,
            const.OPTIONS_FLOW_ACTIONS_DELETE,
        ]:
            return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_ACTION)

        entity_dict = self._get_entity_dict()
        entity_names = [
            data.get(const.OPTIONS_FLOW_DATA_ENTITY_NAME, const.UNKNOWN_ENTITY)
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
            self.context[const.OPTIONS_FLOW_INPUT_INTERNAL_ID] = internal_id

            # Route to the corresponding edit/delete step
            return await getattr(
                self,
                f"{const.OPTIONS_FLOW_ASYNC_STEP_PREFIX}{self._action}_{self._entity_type}",
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
            description_placeholders={
                const.OPTIONS_FLOW_PLACEHOLDER_ENTITY_TYPE: self._entity_type,
                const.OPTIONS_FLOW_PLACEHOLDER_ACTION: self._action,
            },
        )

    def _get_entity_dict(self):
        """Retrieve the appropriate entity dictionary based on entity_type."""
        entity_type_to_conf = {
            const.OPTIONS_FLOW_DIC_KID: const.CONF_KIDS,
            const.OPTIONS_FLOW_DIC_PARENT: const.CONF_PARENTS,
            const.OPTIONS_FLOW_DIC_CHORE: const.CONF_CHORES,
            const.OPTIONS_FLOW_DIC_BADGE: const.CONF_BADGES,
            const.OPTIONS_FLOW_DIC_REWARD: const.CONF_REWARDS,
            const.OPTIONS_FLOW_DIC_BONUS: const.CONF_BONUSES,
            const.OPTIONS_FLOW_DIC_PENALTY: const.CONF_PENALTIES,
            const.OPTIONS_FLOW_DIC_ACHIEVEMENT: const.CONF_ACHIEVEMENTS,
            const.OPTIONS_FLOW_DIC_CHALLENGE: const.CONF_CHALLENGES,
        }
        key = entity_type_to_conf.get(self._entity_type)
        if key is None:
            const.LOGGER.error(
                "Unknown entity_type '%s'. Cannot retrieve entity dictionary",
                self._entity_type,
            )
            return {}
        return self._entry_options.get(key, {})

    # ------------------ ADD ENTITY ------------------
    async def async_step_add_kid(self, user_input=None):
        """Add a new kid."""
        self._entry_options = dict(self.config_entry.options)

        errors = {}
        kids_dict = self._entry_options.setdefault(const.CONF_KIDS, {})

        if user_input is not None:
            kid_name = user_input[const.CFOF_KIDS_INPUT_KID_NAME].strip()
            ha_user_id = (
                user_input.get(const.CFOF_KIDS_INPUT_HA_USER) or const.CONF_EMPTY
            )
            enable_mobile_notifications = user_input.get(
                const.CFOF_KIDS_INPUT_ENABLE_MOBILE_NOTIFICATIONS, True
            )
            notify_service = (
                user_input.get(const.CFOF_KIDS_INPUT_MOBILE_NOTIFY_SERVICE)
                or const.CONF_EMPTY
            )
            enable_persist = user_input.get(
                const.CFOF_KIDS_INPUT_ENABLE_PERSISTENT_NOTIFICATIONS, True
            )

            if not kid_name:
                errors[const.CFOP_ERROR_KID_NAME] = (
                    const.TRANS_KEY_CFOF_INVALID_KID_NAME
                )

            elif any(
                kid_data[const.DATA_KID_NAME] == kid_name
                for kid_data in kids_dict.values()
            ):
                errors[const.CFOP_ERROR_KID_NAME] = const.TRANS_KEY_CFOF_DUPLICATE_KID

            else:
                internal_id = user_input.get(
                    const.CFOF_GLOBAL_INPUT_INTERNAL_ID, str(uuid.uuid4())
                )
                kids_dict[internal_id] = {
                    const.DATA_KID_NAME: kid_name,
                    const.DATA_KID_HA_USER_ID: ha_user_id,
                    const.DATA_KID_ENABLE_NOTIFICATIONS: enable_mobile_notifications,
                    const.DATA_KID_MOBILE_NOTIFY_SERVICE: notify_service,
                    const.DATA_KID_USE_PERSISTENT_NOTIFICATIONS: enable_persist,
                    const.DATA_KID_INTERNAL_ID: internal_id,
                }
                self._entry_options[const.CONF_KIDS] = kids_dict

                const.LOGGER.debug("Added kid '%s' with ID: %s", kid_name, internal_id)
                await self._update_and_reload()
                return await self.async_step_init()

        # Retrieve HA users for linking
        users = await self.hass.auth.async_get_users()
        schema = fh.build_kid_schema(
            self.hass,
            users=users,
            default_kid_name=const.CONF_EMPTY,
            default_ha_user_id=None,
            default_enable_mobile_notifications=False,
            default_mobile_notify_service=None,
            default_enable_persistent_notifications=False,
        )
        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_ADD_KID, data_schema=schema, errors=errors
        )

    async def async_step_add_parent(self, user_input=None):
        """Add a new parent."""
        self._entry_options = dict(self.config_entry.options)

        errors = {}
        parents_dict = self._entry_options.setdefault(const.CONF_PARENTS, {})

        if user_input is not None:
            parent_name = user_input[const.CFOF_PARENTS_INPUT_NAME].strip()
            ha_user_id = (
                user_input.get(const.CFOF_PARENTS_INPUT_HA_USER) or const.CONF_EMPTY
            )
            associated_kids = user_input.get(
                const.CFOF_PARENTS_INPUT_ASSOCIATED_KIDS, []
            )
            enable_mobile_notifications = user_input.get(
                const.CFOF_PARENTS_INPUT_ENABLE_MOBILE_NOTIFICATIONS, True
            )
            notify_service = (
                user_input.get(const.CFOF_PARENTS_INPUT_MOBILE_NOTIFY_SERVICE)
                or const.CONF_EMPTY
            )
            enable_persist = user_input.get(
                const.CFOF_PARENTS_INPUT_ENABLE_PERSISTENT_NOTIFICATIONS, True
            )

            if any(
                parent_data[const.DATA_PARENT_NAME] == parent_name
                for parent_data in parents_dict.values()
            ):
                errors[const.CFPO_ERROR_PARENT_NAME] = (
                    const.TRANS_KEY_CFOF_DUPLICATE_PARENT
                )
            else:
                internal_id = user_input.get(
                    const.CFOF_GLOBAL_INPUT_INTERNAL_ID, str(uuid.uuid4())
                )
                parents_dict[internal_id] = {
                    const.DATA_PARENT_NAME: parent_name,
                    const.DATA_PARENT_HA_USER_ID: ha_user_id,
                    const.DATA_PARENT_ASSOCIATED_KIDS: associated_kids,
                    const.DATA_PARENT_ENABLE_NOTIFICATIONS: enable_mobile_notifications,
                    const.DATA_PARENT_MOBILE_NOTIFY_SERVICE: notify_service,
                    const.DATA_PARENT_USE_PERSISTENT_NOTIFICATIONS: enable_persist,
                    const.DATA_PARENT_INTERNAL_ID: internal_id,
                }
                self._entry_options[const.CONF_PARENTS] = parents_dict

                const.LOGGER.debug(
                    "Added parent '%s' with ID: %s", parent_name, internal_id
                )
                await self._update_and_reload()
                return await self.async_step_init()

        # Retrieve HA users and existing kids for linking
        users = await self.hass.auth.async_get_users()
        kids_dict = {
            kid_data[const.DATA_KID_NAME]: kid_id
            for kid_id, kid_data in self._entry_options.get(const.CONF_KIDS, {}).items()
        }

        parent_schema = fh.build_parent_schema(
            self.hass,
            users=users,
            kids_dict=kids_dict,
            default_parent_name=const.CONF_EMPTY,
            default_ha_user_id=None,
            default_associated_kids=[],
            default_enable_mobile_notifications=False,
            default_mobile_notify_service=None,
            default_enable_persistent_notifications=False,
            internal_id=None,
        )
        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_ADD_PARENT,
            data_schema=parent_schema,
            errors=errors,
        )

    async def async_step_add_chore(self, user_input=None):
        """Add a new chore."""
        self._entry_options = dict(self.config_entry.options)

        errors = {}
        chores_dict = self._entry_options.setdefault(const.CONF_CHORES, {})

        if user_input is not None:
            chore_name = user_input[const.CFOF_CHORES_INPUT_NAME].strip()
            internal_id = user_input.get(
                const.CFOF_GLOBAL_INPUT_INTERNAL_ID, str(uuid.uuid4())
            )

            if user_input.get(const.CFOF_CHORES_INPUT_DUE_DATE):
                raw_due = user_input[const.CFOF_CHORES_INPUT_DUE_DATE]
                try:
                    due_date_str = fh.ensure_utc_datetime(self.hass, raw_due)
                    due_dt = dt_util.parse_datetime(due_date_str)
                    if due_dt and due_dt < dt_util.utcnow():
                        errors[const.CFOP_ERROR_DUE_DATE] = (
                            const.TRANS_KEY_CFOF_DUE_DATE_IN_PAST
                        )
                except ValueError:
                    errors[const.CFOP_ERROR_DUE_DATE] = (
                        const.TRANS_KEY_CFOF_INVALID_DUE_DATE
                    )
                    due_date_str = None
            else:
                due_date_str = None

            if any(
                chore_data[const.DATA_CHORE_NAME] == chore_name
                for chore_data in chores_dict.values()
            ):
                errors[const.CFOP_ERROR_CHORE_NAME] = (
                    const.TRANS_KEY_CFOF_DUPLICATE_CHORE
                )

            if errors:
                kids_dict = {
                    data[const.DATA_KID_NAME]: eid
                    for eid, data in self._entry_options.get(
                        const.CONF_KIDS, {}
                    ).items()
                }
                schema = fh.build_chore_schema(kids_dict, default=user_input)
                return self.async_show_form(
                    step_id=const.OPTIONS_FLOW_STEP_ADD_CHORE,
                    data_schema=schema,
                    errors=errors,
                )

            if (
                user_input.get(const.CFOF_CHORES_INPUT_RECURRING_FREQUENCY)
                != const.FREQUENCY_CUSTOM
            ):
                user_input.pop(const.CFOF_CHORES_INPUT_CUSTOM_INTERVAL, None)
                user_input.pop(const.CFOF_CHORES_INPUT_CUSTOM_INTERVAL_UNIT, None)

            chores_dict[internal_id] = {
                const.DATA_CHORE_NAME: chore_name,
                const.DATA_CHORE_DEFAULT_POINTS: user_input[
                    const.CFOF_CHORES_INPUT_DEFAULT_POINTS
                ],
                const.DATA_CHORE_PARTIAL_ALLOWED: user_input[
                    const.CFOF_CHORES_INPUT_PARTIAL_ALLOWED
                ],
                const.DATA_CHORE_SHARED_CHORE: user_input[
                    const.CFOF_CHORES_INPUT_SHARED_CHORE
                ],
                const.DATA_CHORE_ALLOW_MULTIPLE_CLAIMS_PER_DAY: user_input[
                    const.CFOF_CHORES_INPUT_ALLOW_MULTIPLE_CLAIMS
                ],
                const.DATA_CHORE_ASSIGNED_KIDS: user_input[
                    const.CFOF_CHORES_INPUT_ASSIGNED_KIDS
                ],
                const.DATA_CHORE_DESCRIPTION: user_input.get(
                    const.CFOF_CHORES_INPUT_DESCRIPTION, const.CONF_EMPTY
                ),
                const.DATA_CHORE_LABELS: user_input.get(
                    const.CFOF_CHORES_INPUT_LABELS, []
                ),
                const.DATA_CHORE_ICON: user_input.get(
                    const.CFOF_CHORES_INPUT_ICON, const.DEFAULT_CHORE_ICON
                ),
                const.DATA_CHORE_RECURRING_FREQUENCY: user_input.get(
                    const.CFOF_CHORES_INPUT_RECURRING_FREQUENCY, const.CONF_EMPTY
                ),
                const.DATA_CHORE_CUSTOM_INTERVAL: user_input.get(
                    const.CFOF_CHORES_INPUT_CUSTOM_INTERVAL
                ),
                const.DATA_CHORE_CUSTOM_INTERVAL_UNIT: user_input.get(
                    const.CFOF_CHORES_INPUT_CUSTOM_INTERVAL_UNIT
                ),
                const.DATA_CHORE_DUE_DATE: due_date_str,
                const.DATA_CHORE_APPLICABLE_DAYS: user_input.get(
                    const.CFOF_CHORES_INPUT_APPLICABLE_DAYS,
                    const.DEFAULT_APPLICABLE_DAYS,
                ),
                const.DATA_CHORE_NOTIFY_ON_CLAIM: user_input.get(
                    const.CFOF_CHORES_INPUT_NOTIFY_ON_CLAIM,
                    const.DEFAULT_NOTIFY_ON_CLAIM,
                ),
                const.DATA_CHORE_NOTIFY_ON_APPROVAL: user_input.get(
                    const.CFOF_CHORES_INPUT_NOTIFY_ON_APPROVAL,
                    const.DEFAULT_NOTIFY_ON_APPROVAL,
                ),
                const.DATA_CHORE_NOTIFY_ON_DISAPPROVAL: user_input.get(
                    const.CFOF_CHORES_INPUT_NOTIFY_ON_DISAPPROVAL,
                    const.DEFAULT_NOTIFY_ON_DISAPPROVAL,
                ),
                const.DATA_CHORE_INTERNAL_ID: internal_id,
            }
            self._entry_options[const.CONF_CHORES] = chores_dict

            const.LOGGER.debug(
                "Added chore '%s' with ID: %s and Due Date %s",
                chore_name,
                internal_id,
                due_date_str,
            )

            await self._update_and_reload()
            return await self.async_step_init()

        # Use flow_helpers.fh.build_chore_schema, passing current kids
        kids_dict = {
            data[const.DATA_KID_NAME]: eid
            for eid, data in self._entry_options.get(const.CONF_KIDS, {}).items()
        }
        schema = fh.build_chore_schema(kids_dict)
        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_ADD_CHORE, data_schema=schema, errors=errors
        )

    async def async_step_add_badge(self, user_input=None):
        """Entry point to add a new badge."""
        if user_input is not None:
            badge_type = user_input[const.CFOF_BADGES_INPUT_TYPE]
            self.context[const.CFOF_BADGES_INPUT_TYPE] = badge_type
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
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        translation_key=const.TRANS_KEY_CFOF_BADGE_TYPE,
                    )
                )
            }
        )
        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_ADD_BADGE, data_schema=schema
        )

    # ----- Add Cumulative Badge (Points-only) -----
    async def async_step_add_badge_cumulative(self, user_input=None):
        """Add a new cumulative badge."""

        self._entry_options = dict(self.config_entry.options)
        errors = {}
        badges_dict = self._entry_options.setdefault(const.CONF_BADGES, {})

        if user_input is not None:
            award_mode = user_input.get(
                const.CFOF_BADGES_INPUT_AWARD_MODE, const.DEFAULT_BADGE_AWARD_MODE
            )
            # Clean the non‑applicable field:
            if award_mode == const.CFOF_BADGES_INPUT_AWARD_POINTS:
                user_input[const.CFOF_BADGES_INPUT_AWARD_REWARD] = const.CONF_EMPTY
            elif award_mode == const.CFOF_BADGES_INPUT_AWARD_REWARD:
                user_input[const.CFOF_BADGES_INPUT_AWARD_POINTS] = const.DEFAULT_ZERO
            elif award_mode == const.CONF_BADGE_AWARD_NONE:
                # When "none" is chosen, ensure both extra points and reward are cleared.
                user_input[const.CFOF_BADGES_INPUT_AWARD_POINTS] = const.DEFAULT_ZERO
                user_input[const.CFOF_BADGES_INPUT_AWARD_REWARD] = const.CONF_EMPTY
            # (If award mode is points + reward leave both fields)

            badge_name = user_input[const.CFOF_BADGES_INPUT_NAME].strip()
            internal_id = user_input.get(
                const.CFOF_GLOBAL_INPUT_INTERNAL_ID, str(uuid.uuid4())
            )

            if any(
                badge.get(const.DATA_BADGE_NAME) == badge_name
                for badge in badges_dict.values()
            ):
                errors[const.CFOP_ERROR_BADGE_NAME] = (
                    const.TRANS_KEY_CFOF_DUPLICATE_BADGE
                )
            else:
                # Cumulative badges now use only points.
                badges_dict[internal_id] = {
                    const.DATA_BADGE_NAME: badge_name,
                    const.DATA_BADGE_DESCRIPTION: user_input.get(
                        const.CFOF_BADGES_INPUT_DESCRIPTION, const.CONF_EMPTY
                    ),
                    const.DATA_BADGE_LABELS: user_input.get(
                        const.CFOF_BADGES_INPUT_LABELS, []
                    ),
                    const.DATA_BADGE_ICON: user_input.get(
                        const.CFOF_BADGES_INPUT_ICON, const.DEFAULT_BADGE_ICON
                    ),
                    const.DATA_BADGE_THRESHOLD_VALUE: user_input[
                        const.CFOF_BADGES_INPUT_THRESHOLD_VALUE
                    ],
                    const.DATA_BADGE_AWARD_MODE: award_mode,
                    const.DATA_BADGE_AWARD_POINTS: user_input.get(
                        const.CFOF_BADGES_INPUT_AWARD_POINTS,
                        const.DEFAULT_BADGE_AWARD_POINTS,
                    ),
                    const.DATA_BADGE_AWARD_REWARD: user_input.get(
                        const.CFOF_BADGES_INPUT_AWARD_REWARD, const.CONF_EMPTY
                    ),
                    const.DATA_BADGE_POINTS_MULTIPLIER: user_input[
                        const.CFOF_BADGES_INPUT_POINTS_MULTIPLIER
                    ],
                    # Periodic reset settings for maintenance (if enabled)
                    const.DATA_BADGE_RESET_PERIODICALLY: user_input.get(
                        const.CFOF_BADGES_INPUT_RESET_PERIODICALLY, False
                    ),
                    const.DATA_BADGE_RESET_TYPE: user_input.get(
                        const.CFOF_BADGES_INPUT_RESET_TYPE, const.CONF_YEAR_END
                    ),
                    const.DATA_BADGE_CUSTOM_RESET_DATE: user_input.get(
                        const.CFOF_BADGES_INPUT_CUSTOM_RESET_DATE
                    ),
                    const.DATA_BADGE_RESET_GRACE_PERIOD: user_input.get(
                        const.CFOF_BADGES_INPUT_RESET_GRACE_PERIOD,
                        const.DEFAULT_BADGE_RESET_GRACE_PERIOD,
                    ),
                    const.DATA_BADGE_MAINTENANCE_RULES: user_input.get(
                        const.CFOF_BADGES_INPUT_MAINTENANCE_RULES, const.CONF_EMPTY
                    ),
                    const.DATA_BADGE_TYPE: const.BADGE_TYPE_CUMULATIVE,
                    const.DATA_BADGE_INTERNAL_ID: internal_id,
                }
                self._entry_options[const.CONF_BADGES] = badges_dict
                const.LOGGER.debug(
                    "Added cumulative badge '%s' with ID: %s", badge_name, internal_id
                )
                await self._update_and_reload()
                return await self.async_step_init()

        rewards_options = [
            {
                "value": reward_id,
                "label": reward.get(const.DATA_REWARD_NAME, const.CONF_NONE_TEXT),
            }
            for reward_id, reward in self._entry_options.get(
                const.CONF_REWARDS, {}
            ).items()
        ]

        schema = fh.build_badge_cumulative_schema(
            default=user_input, rewards_list=rewards_options
        )
        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_ADD_BADGE_CUMULATIVE,
            data_schema=schema,
            errors=errors,
        )

    # ----- Add Daily Badge -----
    async def async_step_add_badge_daily(self, user_input=None):
        """Add a new daily badge."""
        self._entry_options = dict(self.config_entry.options)
        errors = {}
        badges_dict = self._entry_options.setdefault(const.CONF_BADGES, {})

        if user_input is not None:
            award_mode = user_input.get(
                const.CFOF_BADGES_INPUT_AWARD_MODE, const.DEFAULT_BADGE_AWARD_MODE
            )
            # Clean the non‑applicable field:
            if award_mode == const.CFOF_BADGES_INPUT_AWARD_POINTS:
                user_input[const.CFOF_BADGES_INPUT_AWARD_REWARD] = const.CONF_EMPTY
            elif award_mode == const.CFOF_BADGES_INPUT_AWARD_REWARD:
                user_input[const.CFOF_BADGES_INPUT_AWARD_POINTS] = const.DEFAULT_ZERO
            elif award_mode == const.CONF_BADGE_AWARD_NONE:
                # When "none" is chosen, ensure both extra points and reward are cleared.
                user_input[const.CFOF_BADGES_INPUT_AWARD_POINTS] = const.DEFAULT_ZERO
                user_input[const.CFOF_BADGES_INPUT_AWARD_REWARD] = const.CONF_EMPTY
            # (If award mode is points + reward leave both fields)

            badge_name = user_input[const.CFOF_BADGES_INPUT_NAME].strip()
            internal_id = user_input.get(
                const.CFOF_GLOBAL_INPUT_INTERNAL_ID, str(uuid.uuid4())
            )
            if any(
                badge.get(const.DATA_BADGE_NAME) == badge_name
                for badge in badges_dict.values()
            ):
                errors[const.CFOP_ERROR_BADGE_NAME] = (
                    const.TRANS_KEY_CFOF_DUPLICATE_BADGE
                )
            else:
                badges_dict[internal_id] = {
                    const.DATA_BADGE_NAME: badge_name,
                    const.DATA_BADGE_DESCRIPTION: user_input.get(
                        const.CFOF_BADGES_INPUT_DESCRIPTION, const.CONF_EMPTY
                    ),
                    const.DATA_BADGE_LABELS: user_input.get(
                        const.CFOF_BADGES_INPUT_LABELS, []
                    ),
                    const.DATA_BADGE_ICON: user_input.get(
                        const.CFOF_BADGES_INPUT_ICON, const.DEFAULT_BADGE_ICON
                    ),
                    const.DATA_BADGE_DAILY_THRESHOLD_TYPE: user_input.get(
                        const.CFOF_BADGES_INPUT_DAILY_THRESHOLD_TYPE,
                        const.DEFAULT_BADGE_THRESHOLD_TYPE,
                    ),
                    const.DATA_BADGE_DAILY_THRESHOLD: user_input[
                        const.CFOF_BADGES_INPUT_DAILY_THRESHOLD
                    ],
                    const.DATA_BADGE_AWARD_MODE: award_mode,
                    const.DATA_BADGE_AWARD_POINTS: user_input.get(
                        const.CFOF_BADGES_INPUT_AWARD_POINTS,
                        const.DEFAULT_BADGE_AWARD_POINTS,
                    ),
                    const.DATA_BADGE_AWARD_REWARD: user_input.get(
                        const.CFOF_BADGES_INPUT_AWARD_REWARD, const.CONF_EMPTY
                    ),
                    const.DATA_BADGE_TYPE: const.BADGE_TYPE_DAILY,
                    const.DATA_BADGE_INTERNAL_ID: internal_id,
                }
                self._entry_options[const.CONF_BADGES] = badges_dict
                const.LOGGER.debug(
                    "Added daily badge '%s' with ID: %s", badge_name, internal_id
                )
                await self._update_and_reload()
                return await self.async_step_init()

        rewards_options = [
            {
                "value": reward_id,
                "label": reward.get(const.DATA_REWARD_NAME, const.CONF_NONE_TEXT),
            }
            for reward_id, reward in self._entry_options.get(
                const.CONF_REWARDS, {}
            ).items()
        ]

        schema = fh.build_badge_daily_schema(
            default=user_input, rewards_list=rewards_options
        )
        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_ADD_BADGE_DAILY,
            data_schema=schema,
            errors=errors,
        )

    # ----- Add Periodic Badge -----
    async def async_step_add_badge_periodic(self, user_input=None):
        """Add a new periodic badge."""
        self._entry_options = dict(self.config_entry.options)
        errors = {}
        badges_dict = self._entry_options.setdefault(const.CONF_BADGES, {})

        if user_input is not None:
            award_mode = user_input.get(
                const.CFOF_BADGES_INPUT_AWARD_MODE, const.DEFAULT_BADGE_AWARD_MODE
            )
            # Clean the non‑applicable field:
            if award_mode == const.CFOF_BADGES_INPUT_AWARD_POINTS:
                user_input[const.CFOF_BADGES_INPUT_AWARD_REWARD] = const.CONF_EMPTY
            elif award_mode == const.CFOF_BADGES_INPUT_AWARD_REWARD:
                user_input[const.CFOF_BADGES_INPUT_AWARD_POINTS] = const.DEFAULT_ZERO
            elif award_mode == const.CONF_BADGE_AWARD_NONE:
                # When "none" is chosen, ensure both extra points and reward are cleared.
                user_input[const.CFOF_BADGES_INPUT_AWARD_POINTS] = const.DEFAULT_ZERO
                user_input[const.CFOF_BADGES_INPUT_AWARD_REWARD] = const.CONF_EMPTY
            # (If award mode is points + reward leave both fields)

            badge_name = user_input[const.CFOF_BADGES_INPUT_NAME].strip()
            internal_id = user_input.get(
                const.CFOF_GLOBAL_INPUT_INTERNAL_ID, str(uuid.uuid4())
            )
            if any(
                badge.get(const.DATA_BADGE_NAME) == badge_name
                for badge in badges_dict.values()
            ):
                errors[const.CFOP_ERROR_BADGE_NAME] = (
                    const.TRANS_KEY_CFOF_DUPLICATE_BADGE
                )
            else:
                badges_dict[internal_id] = {
                    const.DATA_BADGE_NAME: badge_name,
                    const.DATA_BADGE_DESCRIPTION: user_input.get(
                        const.CFOF_BADGES_INPUT_DESCRIPTION, const.CONF_EMPTY
                    ),
                    const.DATA_BADGE_LABELS: user_input.get(
                        const.CFOF_BADGES_INPUT_LABELS, []
                    ),
                    const.DATA_BADGE_ICON: user_input.get(
                        const.CFOF_BADGES_INPUT_ICON, const.DEFAULT_BADGE_ICON
                    ),
                    const.DATA_BADGE_RESET_SCHEDULE: user_input.get(
                        const.CFOF_BADGES_INPUT_RESET_SCHEDULE, const.CONF_WEEKLY
                    ),
                    const.DATA_BADGE_START_DATE: user_input.get(
                        const.CFOF_BADGES_INPUT_START_DATE, None
                    ),
                    const.DATA_BADGE_END_DATE: user_input.get(
                        const.CFOF_BADGES_INPUT_END_DATE, None
                    ),
                    const.DATA_BADGE_PERIODIC_RECURRENT: user_input.get(
                        const.CFOF_BADGES_INPUT_PERIODIC_RECURRENT, False
                    ),
                    const.DATA_BADGE_THRESHOLD_TYPE: user_input.get(
                        const.CFOF_BADGES_INPUT_THRESHOLD_TYPE,
                        const.DEFAULT_BADGE_THRESHOLD_TYPE,
                    ),
                    const.DATA_BADGE_REQUIRED_CHORES: user_input.get(
                        const.CFOF_BADGES_INPUT_REQUIRED_CHORES, []
                    ),
                    const.DATA_BADGE_THRESHOLD_VALUE: user_input[
                        const.CFOF_BADGES_INPUT_THRESHOLD_VALUE
                    ],
                    const.DATA_BADGE_AWARD_MODE: award_mode,
                    const.DATA_BADGE_AWARD_POINTS: user_input.get(
                        const.CFOF_BADGES_INPUT_AWARD_POINTS,
                        const.DEFAULT_BADGE_AWARD_POINTS,
                    ),
                    const.DATA_BADGE_AWARD_REWARD: user_input.get(
                        const.CFOF_BADGES_INPUT_AWARD_REWARD, const.CONF_EMPTY
                    ),
                    const.DATA_BADGE_TYPE: const.BADGE_TYPE_PERIODIC,
                    const.DATA_BADGE_INTERNAL_ID: internal_id,
                }
                self._entry_options[const.CONF_BADGES] = badges_dict
                const.LOGGER.debug(
                    "Added periodic badge '%s' with ID: %s", badge_name, internal_id
                )
                await self._update_and_reload()
                return await self.async_step_init()

        rewards_options = [
            {
                "value": reward_id,
                "label": reward.get(const.DATA_REWARD_NAME, const.CONF_NONE_TEXT),
            }
            for reward_id, reward in self._entry_options.get(
                const.CONF_REWARDS, {}
            ).items()
        ]
        chores_options = [
            {
                "value": chore_id,
                "label": chore.get(const.DATA_CHORE_NAME, const.CONF_NONE_TEXT),
            }
            for chore_id, chore in self._entry_options.get(
                const.CONF_CHORES, {}
            ).items()
        ]
        schema = fh.build_badge_periodic_schema(
            default=user_input, rewards_list=rewards_options, chores_list=chores_options
        )

        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_ADD_BADGE_PERIODIC,
            data_schema=schema,
            errors=errors,
        )

    # ----- Add Achievement-Linked Badge -----
    async def async_step_add_badge_achievement(self, user_input=None):
        """Add a new achievement-linked badge."""
        self._entry_options = dict(self.config_entry.options)
        errors = {}
        badges_dict = self._entry_options.setdefault(const.CONF_BADGES, {})

        if user_input is not None:
            award_mode = user_input.get(
                const.CFOF_BADGES_INPUT_AWARD_MODE, const.DEFAULT_BADGE_AWARD_MODE
            )
            # Clean the non‑applicable field:
            if award_mode == const.CFOF_BADGES_INPUT_AWARD_POINTS:
                user_input[const.CFOF_BADGES_INPUT_AWARD_REWARD] = const.CONF_EMPTY
            elif award_mode == const.CFOF_BADGES_INPUT_AWARD_REWARD:
                user_input[const.CFOF_BADGES_INPUT_AWARD_POINTS] = const.DEFAULT_ZERO
            elif award_mode == const.CONF_BADGE_AWARD_NONE:
                # When "none" is chosen, ensure both extra points and reward are cleared.
                user_input[const.CFOF_BADGES_INPUT_AWARD_POINTS] = const.DEFAULT_ZERO
                user_input[const.CFOF_BADGES_INPUT_AWARD_REWARD] = const.CONF_EMPTY
            # (If award mode is points + reward leave both fields)

            badge_name = user_input[const.CFOF_BADGES_INPUT_NAME].strip()
            internal_id = user_input.get(
                const.CFOF_GLOBAL_INPUT_INTERNAL_ID, str(uuid.uuid4())
            )
            if any(
                badge.get(const.DATA_BADGE_NAME) == badge_name
                for badge in badges_dict.values()
            ):
                errors[const.CFOP_ERROR_BADGE_NAME] = (
                    const.TRANS_KEY_CFOF_DUPLICATE_BADGE
                )
            else:
                badges_dict[internal_id] = {
                    const.DATA_BADGE_NAME: badge_name,
                    const.DATA_BADGE_DESCRIPTION: user_input.get(
                        const.CFOF_BADGES_INPUT_DESCRIPTION, const.CONF_EMPTY
                    ),
                    const.DATA_BADGE_LABELS: user_input.get(
                        const.CFOF_BADGES_INPUT_LABELS, []
                    ),
                    const.DATA_BADGE_ICON: user_input.get(
                        const.CFOF_BADGES_INPUT_ICON, const.DEFAULT_BADGE_ICON
                    ),
                    const.DATA_BADGE_ASSOCIATED_ACHIEVEMENT: user_input.get(
                        const.CFOF_BADGES_INPUT_ASSOCIATED_ACHIEVEMENT, const.CONF_EMPTY
                    ),
                    const.DATA_BADGE_AWARD_MODE: award_mode,
                    const.DATA_BADGE_AWARD_POINTS: user_input.get(
                        const.CFOF_BADGES_INPUT_AWARD_POINTS,
                        const.DEFAULT_BADGE_AWARD_POINTS,
                    ),
                    const.DATA_BADGE_AWARD_REWARD: user_input.get(
                        const.CFOF_BADGES_INPUT_AWARD_REWARD, const.CONF_EMPTY
                    ),
                    const.DATA_BADGE_TYPE: const.BADGE_TYPE_ACHIEVEMENT_LINKED,
                    const.DATA_BADGE_INTERNAL_ID: internal_id,
                }
                self._entry_options[const.CONF_BADGES] = badges_dict
                const.LOGGER.debug(
                    "Added achievement-linked badge '%s' with ID: %s",
                    badge_name,
                    internal_id,
                )
                await self._update_and_reload()
                return await self.async_step_init()

        achievements_options = [
            {
                "value": achievement_id,
                "label": ach.get(const.DATA_ACHIEVEMENT_NAME, const.CONF_NONE_TEXT),
            }
            for achievement_id, ach in self._entry_options.get(
                const.CONF_ACHIEVEMENTS, {}
            ).items()
        ]
        rewards_options = [
            {
                "value": reward_id,
                "label": reward.get(const.DATA_REWARD_NAME, const.CONF_NONE_TEXT),
            }
            for reward_id, reward in self._entry_options.get(
                const.CONF_REWARDS, {}
            ).items()
        ]
        schema = fh.build_badge_achievement_schema(
            default=user_input,
            achievements_list=achievements_options,
            rewards_list=rewards_options,
        )

        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_ADD_BADGE_ACHIEVEMENT,
            data_schema=schema,
            errors=errors,
        )

    # ----- Add Challenge-Linked Badge -----
    async def async_step_add_badge_challenge(self, user_input=None):
        """Add a new challenge-linked badge."""
        self._entry_options = dict(self.config_entry.options)
        errors = {}
        badges_dict = self._entry_options.setdefault(const.CONF_BADGES, {})

        if user_input is not None:
            award_mode = user_input.get(
                const.CFOF_BADGES_INPUT_AWARD_MODE, const.DEFAULT_BADGE_AWARD_MODE
            )
            # Clean the non‑applicable field:
            if award_mode == const.CFOF_BADGES_INPUT_AWARD_POINTS:
                user_input[const.CFOF_BADGES_INPUT_AWARD_REWARD] = const.CONF_EMPTY
            elif award_mode == const.CFOF_BADGES_INPUT_AWARD_REWARD:
                user_input[const.CFOF_BADGES_INPUT_AWARD_POINTS] = const.DEFAULT_ZERO
            elif award_mode == const.CONF_BADGE_AWARD_NONE:
                # When "none" is chosen, ensure both extra points and reward are cleared.
                user_input[const.CFOF_BADGES_INPUT_AWARD_POINTS] = const.DEFAULT_ZERO
                user_input[const.CFOF_BADGES_INPUT_AWARD_REWARD] = const.CONF_EMPTY
            # (If award mode is points + reward leave both fields)

            badge_name = user_input[const.CFOF_BADGES_INPUT_NAME].strip()
            internal_id = user_input.get(
                const.CFOF_GLOBAL_INPUT_INTERNAL_ID, str(uuid.uuid4())
            )
            if any(
                badge.get(const.DATA_BADGE_NAME) == badge_name
                for badge in badges_dict.values()
            ):
                errors[const.CFOP_ERROR_BADGE_NAME] = (
                    const.TRANS_KEY_CFOF_DUPLICATE_BADGE
                )
            else:
                badges_dict[internal_id] = {
                    const.DATA_BADGE_NAME: badge_name,
                    const.DATA_BADGE_DESCRIPTION: user_input.get(
                        const.CFOF_BADGES_INPUT_DESCRIPTION, const.CONF_EMPTY
                    ),
                    const.DATA_BADGE_LABELS: user_input.get(
                        const.CFOF_BADGES_INPUT_LABELS, []
                    ),
                    const.DATA_BADGE_ICON: user_input.get(
                        const.CFOF_BADGES_INPUT_ICON, const.DEFAULT_BADGE_ICON
                    ),
                    const.DATA_BADGE_ASSOCIATED_CHALLENGE: user_input.get(
                        const.CFOF_BADGES_INPUT_ASSOCIATED_CHALLENGE, const.CONF_EMPTY
                    ),
                    const.DATA_BADGE_AWARD_MODE: award_mode,
                    const.DATA_BADGE_AWARD_POINTS: user_input.get(
                        const.CFOF_BADGES_INPUT_AWARD_POINTS,
                        const.DEFAULT_BADGE_AWARD_POINTS,
                    ),
                    const.DATA_BADGE_AWARD_REWARD: user_input.get(
                        const.CFOF_BADGES_INPUT_AWARD_REWARD, const.CONF_EMPTY
                    ),
                    const.DATA_BADGE_TYPE: const.BADGE_TYPE_CHALLENGE_LINKED,
                    const.DATA_BADGE_INTERNAL_ID: internal_id,
                }
                self._entry_options[const.CONF_BADGES] = badges_dict
                const.LOGGER.debug(
                    "Added challenge-linked badge '%s' with ID: %s",
                    badge_name,
                    internal_id,
                )
                await self._update_and_reload()
                return await self.async_step_init()

        challenges_options = [
            {
                "value": challenge_id,
                "label": chall.get(const.DATA_CHALLENGE_NAME, const.CONF_NONE_TEXT),
            }
            for challenge_id, chall in self._entry_options.get(
                const.CONF_CHALLENGES, {}
            ).items()
        ]
        rewards_options = [
            {
                "value": reward_id,
                "label": reward.get(const.DATA_REWARD_NAME, const.CONF_NONE_TEXT),
            }
            for reward_id, reward in self._entry_options.get(
                const.CONF_REWARDS, {}
            ).items()
        ]
        schema = fh.build_badge_challenge_schema(
            default=user_input,
            challenges_list=challenges_options,
            rewards_list=rewards_options,
        )

        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_ADD_BADGE_CHALLENGE,
            data_schema=schema,
            errors=errors,
        )

    # ----- Add Special Occasion Badge -----
    async def async_step_add_badge_special(self, user_input=None):
        """Add a new special occasion badge."""
        self._entry_options = dict(self.config_entry.options)
        errors = {}
        badges_dict = self._entry_options.setdefault(const.CONF_BADGES, {})
        if user_input is not None:
            badge_name = user_input[const.CFOF_BADGES_INPUT_NAME].strip()
            internal_id = user_input.get(
                const.CFOF_GLOBAL_INPUT_INTERNAL_ID, str(uuid.uuid4())
            )
            if any(
                badge.get(const.DATA_BADGE_NAME) == badge_name
                for badge in badges_dict.values()
            ):
                errors[const.CFOP_ERROR_BADGE_NAME] = (
                    const.TRANS_KEY_CFOF_DUPLICATE_BADGE
                )
            else:
                badges_dict[internal_id] = {
                    const.DATA_BADGE_NAME: badge_name,
                    const.DATA_BADGE_DESCRIPTION: user_input.get(
                        const.CFOF_BADGES_INPUT_DESCRIPTION, const.CONF_EMPTY
                    ),
                    const.DATA_BADGE_LABELS: user_input.get(
                        const.CFOF_BADGES_INPUT_LABELS, []
                    ),
                    const.DATA_BADGE_ICON: user_input.get(
                        const.CFOF_BADGES_INPUT_ICON, const.DEFAULT_BADGE_ICON
                    ),
                    const.DATA_BADGE_ASSIGNED_KIDS: user_input[
                        const.CFOF_BADGES_INPUT_ASSIGNED_KIDS
                    ],
                    const.DATA_BADGE_OCCASION_TYPE: user_input.get(
                        const.CFOF_BADGES_INPUT_OCCASION_TYPE, const.CONF_HOLIDAY
                    ),
                    const.DATA_BADGE_OCCASION_DATE: user_input.get(
                        const.CFOF_BADGES_INPUT_OCCASION_DATE, const.CONF_EMPTY
                    ),
                    const.DATA_BADGE_AWARD_MODE: user_input.get(
                        const.CFOF_BADGES_INPUT_AWARD_MODE,
                        const.DEFAULT_BADGE_AWARD_MODE,
                    ),
                    const.DATA_BADGE_AWARD_POINTS: user_input.get(
                        const.CFOF_BADGES_INPUT_AWARD_POINTS,
                        const.DEFAULT_BADGE_AWARD_POINTS,
                    ),
                    const.DATA_BADGE_AWARD_REWARD: user_input.get(
                        const.CFOF_BADGES_INPUT_AWARD_REWARD, const.CONF_EMPTY
                    ),
                    const.DATA_BADGE_SPECIAL_OCCASION_RECURRENCY: user_input.get(
                        const.CFOF_BADGES_INPUT_SPECIAL_OCCASION_RECURRENCY, False
                    ),
                    const.DATA_BADGE_TYPE: const.BADGE_TYPE_SPECIAL_OCCASION,
                    const.DATA_BADGE_INTERNAL_ID: internal_id,
                }
                self._entry_options[const.CONF_BADGES] = badges_dict
                const.LOGGER.debug(
                    "Added special occasion badge '%s' with ID: %s",
                    badge_name,
                    internal_id,
                )
                await self._update_and_reload()
                return await self.async_step_init()

        kids_dict = {
            kid_data[const.DATA_KID_NAME]: kid_id
            for kid_id, kid_data in self._entry_options.get(const.CONF_KIDS, {}).items()
        }

        rewards_options = [
            {
                "value": reward_id,
                "label": reward.get(const.DATA_REWARD_NAME, const.CONF_NONE_TEXT),
            }
            for reward_id, reward in self._entry_options.get(
                const.CONF_REWARDS, {}
            ).items()
        ]

        schema = fh.build_badge_special_occasions_schema(
            default=user_input,
            rewards_list=rewards_options,
            kids_dict=kids_dict,
        )
        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_ADD_BADGE_SPECIAL,
            data_schema=schema,
            errors=errors,
        )

    async def async_step_add_reward(self, user_input=None):
        """Add a new reward."""
        self._entry_options = dict(self.config_entry.options)

        errors = {}
        rewards_dict = self._entry_options.setdefault(const.CONF_REWARDS, {})

        if user_input is not None:
            reward_name = user_input[const.CFOF_REWARDS_INPUT_NAME].strip()
            internal_id = user_input.get(
                const.CFOF_GLOBAL_INPUT_INTERNAL_ID, str(uuid.uuid4())
            )

            if any(
                reward_data[const.DATA_REWARD_NAME] == reward_name
                for reward_data in rewards_dict.values()
            ):
                errors[const.CFOP_ERROR_REWARD_NAME] = (
                    const.TRANS_KEY_CFOF_DUPLICATE_REWARD
                )
            else:
                rewards_dict[internal_id] = {
                    const.DATA_REWARD_NAME: reward_name,
                    const.DATA_REWARD_COST: user_input[const.CFOF_REWARDS_INPUT_COST],
                    const.DATA_REWARD_DESCRIPTION: user_input.get(
                        const.CFOF_REWARDS_INPUT_DESCRIPTION, const.CONF_EMPTY
                    ),
                    const.DATA_REWARD_LABELS: user_input.get(
                        const.CFOF_REWARDS_INPUT_LABELS, []
                    ),
                    const.DATA_REWARD_ICON: user_input.get(
                        const.CFOF_REWARDS_INPUT_ICON, const.DEFAULT_REWARD_ICON
                    ),
                    const.DATA_REWARD_INTERNAL_ID: internal_id,
                }
                self._entry_options[const.CONF_REWARDS] = rewards_dict

                const.LOGGER.debug(
                    "Added reward '%s' with ID: %s", reward_name, internal_id
                )
                await self._update_and_reload()
                return await self.async_step_init()

        schema = fh.build_reward_schema()
        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_ADD_REWARD,
            data_schema=schema,
            errors=errors,
        )

    async def async_step_add_bonus(self, user_input=None):
        """Add a new bonus."""
        self._entry_options = dict(self.config_entry.options)

        errors = {}
        bonuses_dict = self._entry_options.setdefault(const.CONF_BONUSES, {})

        if user_input is not None:
            bonus_name = user_input[const.CFOF_BONUSES_INPUT_NAME].strip()
            bonus_points = user_input[const.CFOF_BONUSES_INPUT_POINTS]
            internal_id = user_input.get(
                const.CFOF_GLOBAL_INPUT_INTERNAL_ID, str(uuid.uuid4())
            )

            if any(
                bonus_data[const.DATA_BONUS_NAME] == bonus_name
                for bonus_data in bonuses_dict.values()
            ):
                errors[const.CFOP_ERROR_BONUS_NAME] = (
                    const.TRANS_KEY_CFOF_DUPLICATE_BONUS
                )
            else:
                bonuses_dict[internal_id] = {
                    const.DATA_BONUS_NAME: bonus_name,
                    const.DATA_BONUS_DESCRIPTION: user_input.get(
                        const.CFOF_BONUSES_INPUT_DESCRIPTION, const.CONF_EMPTY
                    ),
                    const.DATA_BONUS_LABELS: user_input.get(
                        const.CFOF_BONUSES_INPUT_LABELS, []
                    ),
                    const.DATA_BONUS_POINTS: abs(bonus_points),
                    const.DATA_BONUS_ICON: user_input.get(
                        const.CFOF_BONUSES_INPUT_ICON, const.DEFAULT_BONUS_ICON
                    ),
                    const.DATA_BONUS_INTERNAL_ID: internal_id,
                }
                self._entry_options[const.CONF_BONUSES] = bonuses_dict

                const.LOGGER.debug(
                    "Added bonus '%s' with ID: %s", bonus_name, internal_id
                )
                await self._update_and_reload()
                return await self.async_step_init()

        schema = fh.build_bonus_schema()
        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_ADD_BONUS, data_schema=schema, errors=errors
        )

    async def async_step_add_penalty(self, user_input=None):
        """Add a new penalty."""
        self._entry_options = dict(self.config_entry.options)

        errors = {}
        penalties_dict = self._entry_options.setdefault(const.CONF_PENALTIES, {})

        if user_input is not None:
            penalty_name = user_input[const.CFOF_PENALTIES_INPUT_NAME].strip()
            penalty_points = user_input[const.CFOF_PENALTIES_INPUT_POINTS]
            internal_id = user_input.get(
                const.CFOF_GLOBAL_INPUT_INTERNAL_ID, str(uuid.uuid4())
            )

            if any(
                penalty_data[const.DATA_PENALTY_NAME] == penalty_name
                for penalty_data in penalties_dict.values()
            ):
                errors[const.CFOP_ERROR_PENALTY_NAME] = (
                    const.TRANS_KEY_CFOF_DUPLICATE_PENALTY
                )
            else:
                penalties_dict[internal_id] = {
                    const.DATA_PENALTY_NAME: penalty_name,
                    const.DATA_PENALTY_DESCRIPTION: user_input.get(
                        const.CFOF_PENALTIES_INPUT_DESCRIPTION, const.CONF_EMPTY
                    ),
                    const.DATA_PENALTY_LABELS: user_input.get(
                        const.CFOF_PENALTIES_INPUT_LABELS, []
                    ),
                    const.DATA_PENALTY_POINTS: -abs(
                        penalty_points
                    ),  # Ensure points are negative
                    const.DATA_PENALTY_ICON: user_input.get(
                        const.CFOF_PENALTIES_INPUT_ICON, const.DEFAULT_PENALTY_ICON
                    ),
                    const.DATA_PENALTY_INTERNAL_ID: internal_id,
                }
                self._entry_options[const.CONF_PENALTIES] = penalties_dict

                const.LOGGER.debug(
                    "Added penalty '%s' with ID: %s", penalty_name, internal_id
                )
                await self._update_and_reload()
                return await self.async_step_init()

        schema = fh.build_penalty_schema()
        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_ADD_PENALTY,
            data_schema=schema,
            errors=errors,
        )

    async def async_step_add_achievement(self, user_input=None):
        """Add a new achievement."""
        self._entry_options = dict(self.config_entry.options)

        errors = {}
        achievements_dict = self._entry_options.setdefault(const.CONF_ACHIEVEMENTS, {})

        chores_dict = self._entry_options.get(const.CONF_CHORES, {})

        if user_input is not None:
            achievement_name = user_input[const.CFOF_ACHIEVEMENTS_INPUT_NAME].strip()
            if any(
                data[const.DATA_ACHIEVEMENT_NAME] == achievement_name
                for data in achievements_dict.values()
            ):
                errors[const.CFOP_ERROR_ACHIEVEMENT_NAME] = (
                    const.TRANS_KEY_CFOF_DUPLICATE_ACHIEVEMENT
                )
            else:
                _type = user_input[const.CFOF_ACHIEVEMENTS_INPUT_TYPE]

                chore_id = const.CONF_EMPTY

                if _type == const.ACHIEVEMENT_TYPE_STREAK:
                    c = (
                        user_input.get(const.CFOF_ACHIEVEMENTS_INPUT_SELECTED_CHORE_ID)
                        or const.CONF_EMPTY
                    )
                    if not c or c == const.CONF_NONE_TEXT:
                        errors[const.CFOP_ERROR_SELECT_CHORE_ID] = (
                            const.TRANS_KEY_CFOF_CHORE_MUST_BE_SELECTED
                        )
                    chore_id = c

                if not errors:
                    internal_id = user_input.get(
                        const.CFOF_GLOBAL_INPUT_INTERNAL_ID, str(uuid.uuid4())
                    )
                    achievements_dict[internal_id] = {
                        const.DATA_ACHIEVEMENT_NAME: achievement_name,
                        const.DATA_ACHIEVEMENT_DESCRIPTION: user_input.get(
                            const.CFOF_ACHIEVEMENTS_INPUT_DESCRIPTION, const.CONF_EMPTY
                        ),
                        const.DATA_ACHIEVEMENT_LABELS: user_input.get(
                            const.CFOF_ACHIEVEMENTS_INPUT_LABELS, []
                        ),
                        const.DATA_ACHIEVEMENT_ICON: user_input.get(
                            const.CFOF_ACHIEVEMENTS_INPUT_ICON,
                            const.DEFAULT_ACHIEVEMENTS_ICON,
                        ),
                        const.DATA_ACHIEVEMENT_ASSIGNED_KIDS: user_input[
                            const.CFOF_ACHIEVEMENTS_INPUT_ASSIGNED_KIDS
                        ],
                        const.DATA_ACHIEVEMENT_TYPE: _type,
                        const.DATA_ACHIEVEMENT_SELECTED_CHORE_ID: chore_id,
                        const.DATA_ACHIEVEMENT_CRITERIA: user_input.get(
                            const.CFOF_ACHIEVEMENTS_INPUT_CRITERIA, const.CONF_EMPTY
                        ).strip(),
                        const.DATA_ACHIEVEMENT_TARGET_VALUE: user_input[
                            const.CFOF_ACHIEVEMENTS_INPUT_TARGET_VALUE
                        ],
                        const.DATA_ACHIEVEMENT_REWARD_POINTS: user_input[
                            const.CFOF_ACHIEVEMENTS_INPUT_REWARD_POINTS
                        ],
                        const.DATA_ACHIEVEMENT_INTERNAL_ID: internal_id,
                        const.DATA_ACHIEVEMENT_PROGRESS: {},
                    }
                    self._entry_options[const.CONF_ACHIEVEMENTS] = achievements_dict
                    const.LOGGER.debug(
                        "Added achievement '%s' with ID: %s",
                        achievement_name,
                        internal_id,
                    )
                    await self._update_and_reload()
                    return await self.async_step_init()

        kids_dict = {
            kid_data[const.DATA_KID_NAME]: kid_id
            for kid_id, kid_data in self._entry_options.get(const.CONF_KIDS, {}).items()
        }
        achievement_schema = fh.build_achievement_schema(
            kids_dict=kids_dict, chores_dict=chores_dict, default=None
        )
        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_ADD_ACHIEVEMENT,
            data_schema=achievement_schema,
            errors=errors,
        )

    async def async_step_add_challenge(self, user_input=None):
        """Add a new challenge."""
        self._entry_options = dict(self.config_entry.options)

        errors = {}
        challenges_dict = self._entry_options.setdefault(const.CONF_CHALLENGES, {})

        chores_dict = self._entry_options.get(const.CONF_CHORES, {})

        if user_input is not None:
            challenge_name = user_input[const.CFOF_CHALLENGES_INPUT_NAME].strip()
            if any(
                data[const.DATA_CHALLENGE_NAME] == challenge_name
                for data in challenges_dict.values()
            ):
                errors[const.CFOP_ERROR_CHALLENGE_NAME] = (
                    const.TRANS_KEY_CFOF_DUPLICATE_CHALLENGE
                )
            else:
                _type = user_input[const.CFOF_CHALLENGES_INPUT_TYPE]

                chore_id = const.CONF_EMPTY
                if _type == const.CHALLENGE_TYPE_TOTAL_WITHIN_WINDOW:
                    c = (
                        user_input.get(const.CFOF_CHALLENGES_INPUT_SELECTED_CHORE_ID)
                        or const.CONF_EMPTY
                    )
                    if not c or c == const.CONF_NONE_TEXT:
                        errors[const.CFOP_ERROR_SELECT_CHORE_ID] = (
                            const.TRANS_KEY_CFOF_CHORE_MUST_BE_SELECTED
                        )
                    chore_id = c

                # Process start_date and end_date using the helper:
                start_date_input = user_input.get(
                    const.CFOF_CHALLENGES_INPUT_START_DATE
                )
                end_date_input = user_input.get(const.CFOF_CHALLENGES_INPUT_END_DATE)

                if start_date_input:
                    try:
                        start_date = fh.ensure_utc_datetime(self.hass, start_date_input)
                        start_dt = dt_util.parse_datetime(start_date)
                        if start_dt and start_dt < dt_util.utcnow():
                            errors[const.CFOP_ERROR_START_DATE] = (
                                const.TRANS_KEY_CFOF_START_DATE_IN_PAST
                            )
                    except Exception:
                        errors[const.CFOP_ERROR_START_DATE] = (
                            const.TRANS_KEY_CFOF_INVALID_START_DATE
                        )
                        start_date = None
                else:
                    start_date = None

                if end_date_input:
                    try:
                        end_date = fh.ensure_utc_datetime(self.hass, end_date_input)
                        end_dt = dt_util.parse_datetime(end_date)
                        if end_dt and end_dt <= dt_util.utcnow():
                            errors[const.CFOP_ERROR_END_DATE] = (
                                const.TRANS_KEY_CFOF_END_DATE_IN_PAST
                            )
                        if start_date:
                            sdt = dt_util.parse_datetime(start_date)
                            if sdt and end_dt and end_dt <= sdt:
                                errors[const.CFOP_ERROR_END_DATE] = (
                                    const.TRANS_KEY_CFOF_END_DATE_NOT_AFTER_START_DATE
                                )
                    except Exception:
                        errors[const.CFOP_ERROR_END_DATE] = (
                            const.TRANS_KEY_CFOF_INVALID_END_DATE
                        )
                        end_date = None
                else:
                    end_date = None

                if not errors:
                    internal_id = user_input.get(
                        const.CFOF_GLOBAL_INPUT_INTERNAL_ID, str(uuid.uuid4())
                    )
                    challenges_dict[internal_id] = {
                        const.DATA_CHALLENGE_NAME: challenge_name,
                        const.DATA_CHALLENGE_DESCRIPTION: user_input.get(
                            const.CFOF_CHALLENGES_INPUT_DESCRIPTION, const.CONF_EMPTY
                        ),
                        const.DATA_CHALLENGE_LABELS: user_input.get(
                            const.CFOF_CHALLENGES_INPUT_LABELS, []
                        ),
                        const.DATA_CHALLENGE_ICON: user_input.get(
                            const.CFOF_CHALLENGES_INPUT_ICON,
                            const.DEFAULT_CHALLENGES_ICON,
                        ),
                        const.DATA_CHALLENGE_ASSIGNED_KIDS: user_input[
                            const.CFOF_CHALLENGES_INPUT_ASSIGNED_KIDS
                        ],
                        const.DATA_CHALLENGE_TYPE: _type,
                        const.DATA_CHALLENGE_SELECTED_CHORE_ID: chore_id,
                        const.DATA_CHALLENGE_CRITERIA: user_input.get(
                            const.CFOF_CHALLENGES_INPUT_CRITERIA, const.CONF_EMPTY
                        ).strip(),
                        const.DATA_CHALLENGE_TARGET_VALUE: user_input[
                            const.CFOF_CHALLENGES_INPUT_TARGET_VALUE
                        ],
                        const.DATA_CHALLENGE_REWARD_POINTS: user_input[
                            const.CFOF_CHALLENGES_INPUT_REWARD_POINTS
                        ],
                        const.DATA_CHALLENGE_START_DATE: start_date,
                        const.DATA_CHALLENGE_END_DATE: end_date,
                        const.DATA_CHALLENGE_INTERNAL_ID: internal_id,
                        const.DATA_CHALLENGE_PROGRESS: {},
                    }
                    self._entry_options[const.CONF_CHALLENGES] = challenges_dict
                    const.LOGGER.debug(
                        "Added challenge '%s' with ID: %s", challenge_name, internal_id
                    )
                    await self._update_and_reload()
                    return await self.async_step_init()

        kids_dict = {
            kid_data[const.DATA_KID_NAME]: kid_id
            for kid_id, kid_data in self._entry_options.get(const.CONF_KIDS, {}).items()
        }
        challenge_schema = fh.build_challenge_schema(
            kids_dict=kids_dict, chores_dict=chores_dict, default=user_input
        )
        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_ADD_CHALLENGE,
            data_schema=challenge_schema,
            errors=errors,
        )

    # ------------------ EDIT ENTITY ------------------
    async def async_step_edit_kid(self, user_input=None):
        """Edit an existing kid."""
        self._entry_options = dict(self.config_entry.options)

        errors = {}
        kids_dict = self._entry_options.get(const.CONF_KIDS, {})
        internal_id = self.context.get(const.DATA_INTERNAL_ID)

        if not internal_id or internal_id not in kids_dict:
            const.LOGGER.error("Edit kid: Invalid internal_id '%s'", internal_id)
            return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_KID)

        kid_data = kids_dict[internal_id]

        if user_input is not None:
            new_name = user_input[const.CFOF_KIDS_INPUT_KID_NAME].strip()
            ha_user_id = (
                user_input.get(const.CFOF_KIDS_INPUT_HA_USER) or const.CONF_EMPTY
            )
            enable_notifications = user_input.get(
                const.CFOF_KIDS_INPUT_ENABLE_MOBILE_NOTIFICATIONS, True
            )
            mobile_notify_service = (
                user_input.get(const.CFOF_KIDS_INPUT_MOBILE_NOTIFY_SERVICE)
                or const.CONF_EMPTY
            )
            use_persistent = user_input.get(
                const.CFOF_KIDS_INPUT_ENABLE_PERSISTENT_NOTIFICATIONS, True
            )

            # Check for duplicate names excluding current kid
            if any(
                data[const.DATA_KID_NAME] == new_name and eid != internal_id
                for eid, data in kids_dict.items()
            ):
                errors[const.CFOP_ERROR_KID_NAME] = const.TRANS_KEY_CFOF_DUPLICATE_KID
            else:
                kid_data[const.DATA_KID_NAME] = new_name
                kid_data[const.DATA_KID_HA_USER_ID] = ha_user_id
                kid_data[const.DATA_KID_ENABLE_NOTIFICATIONS] = enable_notifications
                kid_data[const.DATA_KID_MOBILE_NOTIFY_SERVICE] = mobile_notify_service
                kid_data[const.DATA_KID_USE_PERSISTENT_NOTIFICATIONS] = use_persistent

                self._entry_options[const.CONF_KIDS] = kids_dict

                const.LOGGER.debug("Edited kid '%s' with ID: %s", new_name, internal_id)
                await self._update_and_reload()
                return await self.async_step_init()

        # Retrieve HA users for linking
        users = await self.hass.auth.async_get_users()
        schema = fh.build_kid_schema(
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
            internal_id=internal_id,
        )
        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_EDIT_KID, data_schema=schema, errors=errors
        )

    async def async_step_edit_parent(self, user_input=None):
        """Edit an existing parent."""
        self._entry_options = dict(self.config_entry.options)

        errors = {}
        parents_dict = self._entry_options.get(const.CONF_PARENTS, {})
        internal_id = self.context.get(const.DATA_INTERNAL_ID)

        if not internal_id or internal_id not in parents_dict:
            const.LOGGER.error("Edit parent: Invalid internal_id '%s'", internal_id)
            return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_PARENT)

        parent_data = parents_dict[internal_id]

        if user_input is not None:
            new_name = user_input[const.CFOF_PARENTS_INPUT_NAME].strip()
            ha_user_id = (
                user_input.get(const.CFOF_PARENTS_INPUT_HA_USER) or const.CONF_EMPTY
            )
            associated_kids = user_input.get(
                const.CFOF_PARENTS_INPUT_ASSOCIATED_KIDS, []
            )
            enable_notifications = user_input.get(
                const.CFOF_PARENTS_INPUT_ENABLE_MOBILE_NOTIFICATIONS, True
            )
            mobile_notify_service = (
                user_input.get(const.CFOF_PARENTS_INPUT_MOBILE_NOTIFY_SERVICE)
                or const.CONF_EMPTY
            )
            use_persistent = user_input.get(
                const.CFOF_PARENTS_INPUT_ENABLE_PERSISTENT_NOTIFICATIONS, True
            )

            # Check for duplicate names excluding current parent
            if any(
                data[const.DATA_PARENT_NAME] == new_name and eid != internal_id
                for eid, data in parents_dict.items()
            ):
                errors[const.CFPO_ERROR_PARENT_NAME] = (
                    const.TRANS_KEY_CFOF_DUPLICATE_PARENT
                )
            else:
                parent_data[const.DATA_PARENT_NAME] = new_name
                parent_data[const.DATA_PARENT_HA_USER_ID] = ha_user_id
                parent_data[const.DATA_PARENT_ASSOCIATED_KIDS] = associated_kids
                parent_data[const.DATA_PARENT_ENABLE_NOTIFICATIONS] = (
                    enable_notifications
                )
                parent_data[const.DATA_PARENT_MOBILE_NOTIFY_SERVICE] = (
                    mobile_notify_service
                )
                parent_data[const.DATA_PARENT_USE_PERSISTENT_NOTIFICATIONS] = (
                    use_persistent
                )

                self._entry_options[const.CONF_PARENTS] = parents_dict

                const.LOGGER.debug(
                    "Edited parent '%s' with ID: %s", new_name, internal_id
                )

                await self._update_and_reload()
                return await self.async_step_init()

        # Retrieve HA users and existing kids for linking
        users = await self.hass.auth.async_get_users()
        kids_dict = {
            kid_data[const.DATA_KID_NAME]: kid_id
            for kid_id, kid_data in self._entry_options.get(const.CONF_KIDS, {}).items()
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
            internal_id=internal_id,
        )
        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_EDIT_PARENT,
            data_schema=parent_schema,
            errors=errors,
        )

    async def async_step_edit_chore(self, user_input=None):
        """Edit an existing chore."""
        self._entry_options = dict(self.config_entry.options)

        errors = {}
        chores_dict = self._entry_options.get(const.CONF_CHORES, {})
        internal_id = self.context.get(const.DATA_INTERNAL_ID)

        if not internal_id or internal_id not in chores_dict:
            const.LOGGER.error("Edit chore: Invalid internal_id '%s'", internal_id)
            return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_CHORE)

        chore_data = chores_dict[internal_id]

        if user_input is not None:
            new_name = user_input[const.CFOF_CHORES_INPUT_NAME].strip()
            raw_due = user_input.get(const.CFOF_CHORES_INPUT_DUE_DATE)

            # Check for duplicate names excluding current chore
            if any(
                data[const.DATA_CHORE_NAME] == new_name and eid != internal_id
                for eid, data in chores_dict.items()
            ):
                errors[const.CFOP_ERROR_CHORE_NAME] = (
                    const.TRANS_KEY_CFOF_DUPLICATE_CHORE
                )
            else:
                if (
                    user_input.get(const.CFOF_CHORES_INPUT_RECURRING_FREQUENCY)
                    != const.FREQUENCY_CUSTOM
                ):
                    user_input.pop(const.CFOF_CHORES_INPUT_CUSTOM_INTERVAL, None)
                    user_input.pop(const.CFOF_CHORES_INPUT_CUSTOM_INTERVAL_UNIT, None)

                chore_data[const.DATA_CHORE_NAME] = new_name
                chore_data[const.DATA_CHORE_DESCRIPTION] = user_input.get(
                    const.CFOF_CHORES_INPUT_DESCRIPTION, const.CONF_EMPTY
                )
                chore_data[const.DATA_CHORE_LABELS] = user_input.get(
                    const.CFOF_CHORES_INPUT_LABELS, []
                )
                chore_data[const.DATA_CHORE_DEFAULT_POINTS] = user_input[
                    const.CFOF_CHORES_INPUT_DEFAULT_POINTS
                ]
                chore_data[const.DATA_CHORE_SHARED_CHORE] = user_input[
                    const.CFOF_CHORES_INPUT_SHARED_CHORE
                ]
                chore_data[const.DATA_CHORE_PARTIAL_ALLOWED] = user_input[
                    const.CFOF_CHORES_INPUT_PARTIAL_ALLOWED
                ]
                chore_data[const.DATA_CHORE_ALLOW_MULTIPLE_CLAIMS_PER_DAY] = user_input[
                    const.CFOF_CHORES_INPUT_ALLOW_MULTIPLE_CLAIMS
                ]
                chore_data[const.DATA_CHORE_ASSIGNED_KIDS] = user_input[
                    const.CFOF_CHORES_INPUT_ASSIGNED_KIDS
                ]
                chore_data[const.DATA_CHORE_ICON] = user_input.get(
                    const.CFOF_CHORES_INPUT_ICON, const.CONF_EMPTY
                )
                chore_data[const.DATA_CHORE_RECURRING_FREQUENCY] = user_input.get(
                    const.CFOF_CHORES_INPUT_RECURRING_FREQUENCY, const.FREQUENCY_NONE
                )
                chore_data[const.DATA_CHORE_CUSTOM_INTERVAL] = user_input.get(
                    const.CFOF_CHORES_INPUT_CUSTOM_INTERVAL
                )
                chore_data[const.DATA_CHORE_CUSTOM_INTERVAL_UNIT] = user_input.get(
                    const.CFOF_CHORES_INPUT_CUSTOM_INTERVAL_UNIT
                )
                if raw_due:
                    try:
                        if isinstance(raw_due, datetime.datetime):
                            parsed_due = raw_due
                        else:
                            parsed_due = dt_util.parse_datetime(
                                raw_due
                            ) or datetime.datetime.fromisoformat(raw_due)
                        due_utc = dt_util.as_utc(parsed_due)
                        if due_utc < dt_util.utcnow():
                            errors[const.CFOP_ERROR_DUE_DATE] = (
                                const.TRANS_KEY_CFOF_DUE_DATE_IN_PAST
                            )
                        else:
                            chore_data[const.DATA_CHORE_DUE_DATE] = due_utc.isoformat()
                    except Exception:
                        errors[const.CFOP_ERROR_DUE_DATE] = (
                            const.TRANS_KEY_CFOF_INVALID_DUE_DATE
                        )
                else:
                    chore_data[const.DATA_CHORE_DUE_DATE] = None
                    const.LOGGER.debug("No date/time provided; defaulting to None")

                chore_data[const.DATA_CHORE_APPLICABLE_DAYS] = user_input.get(
                    const.CFOF_CHORES_INPUT_APPLICABLE_DAYS, []
                )
                chore_data[const.DATA_CHORE_NOTIFY_ON_CLAIM] = user_input.get(
                    const.CFOF_CHORES_INPUT_NOTIFY_ON_CLAIM, True
                )
                chore_data[const.DATA_CHORE_NOTIFY_ON_APPROVAL] = user_input.get(
                    const.CFOF_CHORES_INPUT_NOTIFY_ON_APPROVAL, True
                )
                chore_data[const.DATA_CHORE_NOTIFY_ON_DISAPPROVAL] = user_input.get(
                    const.CFOF_CHORES_INPUT_NOTIFY_ON_DISAPPROVAL, True
                )

            if errors:
                kids_dict = {
                    data[const.DATA_KID_NAME]: eid
                    for eid, data in self._entry_options.get(
                        const.CONF_KIDS, {}
                    ).items()
                }
                default_data = user_input.copy()
                return self.async_show_form(
                    step_id=const.OPTIONS_FLOW_STEP_EDIT_CHORE,
                    data_schema=fh.build_chore_schema(
                        kids_dict, default={**chore_data, **default_data}
                    ),
                    errors=errors,
                )

            self._entry_options[const.CONF_CHORES] = chores_dict

            const.LOGGER.debug("Edited chore '%s' with ID: %s", new_name, internal_id)
            await self._update_and_reload()
            return await self.async_step_init()

        # Use flow_helpers.fh.build_chore_schema, passing current kids
        kids_dict = {
            data[const.DATA_KID_NAME]: eid
            for eid, data in self._entry_options.get(const.CONF_KIDS, {}).items()
        }

        # Convert stored string to datetime for DateTimeSelector
        existing_due_str = chore_data.get(const.DATA_CHORE_DUE_DATE)
        existing_due_date = None

        if existing_due_str:
            try:
                # Attempt to parse using dt_util or fallback to fromisoformat
                parsed_date = dt_util.parse_datetime(
                    existing_due_str
                ) or datetime.datetime.fromisoformat(existing_due_str)
                # Convert to the required format for DateTimeSelector
                existing_due_date = dt_util.as_local(parsed_date).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                const.LOGGER.debug(
                    "Processed existing_due_date for DateTimeSelector: %s",
                    existing_due_date,
                )
            except ValueError as e:
                const.LOGGER.error(
                    "Failed to parse existing_due_date '%s': %s", existing_due_str, e
                )

        schema = fh.build_chore_schema(
            kids_dict,
            default={**chore_data, const.DATA_CHORE_DUE_DATE: existing_due_date},
        )
        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_EDIT_CHORE,
            data_schema=schema,
            errors=errors,
        )

    async def async_step_edit_badge(self, user_input=None):
        """Edit an existing badge."""
        self._entry_options = dict(self.config_entry.options)
        badges_dict = self._entry_options.get(const.CONF_BADGES, {})
        internal_id = self.context.get(const.DATA_INTERNAL_ID)

        if not internal_id or internal_id not in badges_dict:
            const.LOGGER.error("Edit badge: Invalid internal_id '%s'", internal_id)
            return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_BADGE)

        badge_data = badges_dict[internal_id]
        badge_type = badge_data.get(const.DATA_BADGE_TYPE, const.BADGE_TYPE_CUMULATIVE)

        errors = {}

        if user_input is not None:
            award_mode = user_input.get(
                const.CFOF_BADGES_INPUT_AWARD_MODE, const.DEFAULT_BADGE_AWARD_MODE
            )
            # Clean the non‑applicable field:
            if award_mode == const.CFOF_BADGES_INPUT_AWARD_POINTS:
                user_input[const.CFOF_BADGES_INPUT_AWARD_REWARD] = const.CONF_EMPTY
            elif award_mode == const.CFOF_BADGES_INPUT_AWARD_REWARD:
                user_input[const.CFOF_BADGES_INPUT_AWARD_POINTS] = const.DEFAULT_ZERO
            elif award_mode == const.CONF_BADGE_AWARD_NONE:
                # When "none" is chosen, ensure both extra points and reward are cleared.
                user_input[const.CFOF_BADGES_INPUT_AWARD_POINTS] = const.DEFAULT_ZERO
                user_input[const.CFOF_BADGES_INPUT_AWARD_REWARD] = const.CONF_EMPTY
            # (If award mode is points + reward leave both fields)

            new_name = user_input[const.CFOF_BADGES_INPUT_NAME].strip()
            if any(
                data.get(const.DATA_BADGE_NAME) == new_name and eid != internal_id
                for eid, data in badges_dict.items()
            ):
                errors[const.CFOP_ERROR_BADGE_NAME] = (
                    const.TRANS_KEY_CFOF_DUPLICATE_BADGE
                )
            else:
                badge_data[const.DATA_BADGE_NAME] = new_name
                badge_data[const.DATA_BADGE_DESCRIPTION] = user_input.get(
                    const.CFOF_BADGES_INPUT_DESCRIPTION,
                    badge_data.get(const.DATA_BADGE_DESCRIPTION, const.CONF_EMPTY),
                )
                badge_data[const.DATA_BADGE_LABELS] = user_input.get(
                    const.CFOF_BADGES_INPUT_LABELS,
                    badge_data.get(const.DATA_BADGE_LABELS, []),
                )
                badge_data[const.DATA_BADGE_ICON] = user_input.get(
                    const.CFOF_BADGES_INPUT_ICON,
                    badge_data.get(const.DATA_BADGE_ICON, const.CONF_EMPTY),
                )
                badge_data[const.DATA_BADGE_AWARD_MODE] = award_mode
                badge_data[const.DATA_BADGE_AWARD_POINTS] = user_input.get(
                    const.CFOF_BADGES_INPUT_AWARD_POINTS,
                    badge_data.get(const.DATA_BADGE_AWARD_POINTS),
                )
                badge_data[const.DATA_BADGE_AWARD_REWARD] = user_input.get(
                    const.CFOF_BADGES_INPUT_AWARD_REWARD,
                    badge_data.get(const.DATA_BADGE_AWARD_REWARD),
                )
                badge_data[const.DATA_BADGE_ASSIGNED_KIDS] = user_input.get(
                    const.CFOF_BADGES_INPUT_ASSIGNED_KIDS,
                    badge_data.get(const.DATA_BADGE_ASSIGNED_KIDS),
                )

                # Update type-specific fields:
                if badge_type == const.BADGE_TYPE_CUMULATIVE:
                    badge_data[const.DATA_BADGE_THRESHOLD_VALUE] = user_input.get(
                        const.CFOF_BADGES_INPUT_THRESHOLD_VALUE,
                        badge_data.get(const.DATA_BADGE_THRESHOLD_VALUE),
                    )
                    badge_data[const.DATA_BADGE_POINTS_MULTIPLIER] = user_input.get(
                        const.CFOF_BADGES_INPUT_POINTS_MULTIPLIER,
                        badge_data.get(const.DATA_BADGE_POINTS_MULTIPLIER),
                    )
                    badge_data[const.DATA_BADGE_RESET_PERIODICALLY] = user_input.get(
                        const.CFOF_BADGES_INPUT_RESET_PERIODICALLY,
                        badge_data.get(const.DATA_BADGE_RESET_PERIODICALLY, False),
                    )
                    badge_data[const.DATA_BADGE_RESET_TYPE] = user_input.get(
                        const.CFOF_BADGES_INPUT_RESET_TYPE,
                        badge_data.get(
                            const.DATA_BADGE_RESET_TYPE, const.CONF_YEAR_END
                        ),
                    )
                    badge_data[const.DATA_BADGE_CUSTOM_RESET_DATE] = user_input.get(
                        const.CFOF_BADGES_INPUT_CUSTOM_RESET_DATE,
                        badge_data.get(const.DATA_BADGE_CUSTOM_RESET_DATE),
                    )
                    badge_data[const.DATA_BADGE_RESET_GRACE_PERIOD] = user_input.get(
                        const.CFOF_BADGES_INPUT_RESET_GRACE_PERIOD,
                        badge_data.get(
                            const.DATA_BADGE_RESET_GRACE_PERIOD,
                            const.DEFAULT_BADGE_RESET_GRACE_PERIOD,
                        ),
                    )
                    badge_data[const.DATA_BADGE_MAINTENANCE_RULES] = user_input.get(
                        const.CFOF_BADGES_INPUT_MAINTENANCE_RULES,
                        badge_data.get(
                            const.DATA_BADGE_MAINTENANCE_RULES, const.CONF_EMPTY
                        ),
                    )

                elif badge_type == const.BADGE_TYPE_DAILY:
                    badge_data[const.DATA_BADGE_DAILY_THRESHOLD_TYPE] = user_input.get(
                        const.CFOF_BADGES_INPUT_DAILY_THRESHOLD_TYPE,
                        badge_data.get(
                            const.DATA_BADGE_DAILY_THRESHOLD_TYPE,
                            const.DEFAULT_BADGE_THRESHOLD_TYPE,
                        ),
                    )
                    badge_data[const.DATA_BADGE_DAILY_THRESHOLD] = user_input.get(
                        const.CFOF_BADGES_INPUT_DAILY_THRESHOLD,
                        badge_data.get(const.DATA_BADGE_DAILY_THRESHOLD),
                    )
                    badge_data[const.DATA_BADGE_REWARD] = user_input.get(
                        const.CFOF_BADGES_INPUT_REWARD,
                        badge_data.get(const.DATA_BADGE_REWARD),
                    )

                elif badge_type == const.BADGE_TYPE_PERIODIC:
                    # Update reset schedule; if not custom, clear dates
                    reset_schedule = user_input.get(
                        const.CFOF_BADGES_INPUT_RESET_SCHEDULE,
                        badge_data.get(
                            const.DATA_BADGE_RESET_SCHEDULE, const.CONF_WEEKLY
                        ),
                    )
                    badge_data[const.DATA_BADGE_RESET_SCHEDULE] = reset_schedule
                    if reset_schedule == const.CONF_CUSTOM:
                        badge_data[const.DATA_BADGE_START_DATE] = user_input.get(
                            const.CFOF_BADGES_INPUT_START_DATE,
                            badge_data.get(const.DATA_BADGE_START_DATE),
                        )
                        badge_data[const.DATA_BADGE_END_DATE] = user_input.get(
                            const.CFOF_BADGES_INPUT_END_DATE,
                            badge_data.get(const.DATA_BADGE_END_DATE),
                        )
                    else:
                        badge_data[const.DATA_BADGE_START_DATE] = None
                        badge_data[const.DATA_BADGE_END_DATE] = None
                    badge_data[const.DATA_BADGE_PERIODIC_RECURRENT] = user_input.get(
                        const.CFOF_BADGES_INPUT_PERIODIC_RECURRENT,
                        badge_data.get(const.DATA_BADGE_PERIODIC_RECURRENT, False),
                    )
                    badge_data[const.DATA_BADGE_THRESHOLD_TYPE] = user_input.get(
                        const.CFOF_BADGES_INPUT_THRESHOLD_TYPE,
                        badge_data.get(
                            const.DATA_BADGE_THRESHOLD_TYPE,
                            const.DEFAULT_BADGE_THRESHOLD_TYPE,
                        ),
                    )
                    badge_data[const.DATA_BADGE_REQUIRED_CHORES] = user_input.get(
                        const.CFOF_BADGES_INPUT_REQUIRED_CHORES,
                        badge_data.get(const.DATA_BADGE_REQUIRED_CHORES, []),
                    )
                    badge_data[const.DATA_BADGE_THRESHOLD_VALUE] = user_input.get(
                        const.CFOF_BADGES_INPUT_THRESHOLD_VALUE,
                        badge_data.get(const.DATA_BADGE_THRESHOLD_VALUE),
                    )

                elif badge_type == const.BADGE_TYPE_ACHIEVEMENT_LINKED:
                    badge_data[const.DATA_BADGE_ASSOCIATED_ACHIEVEMENT] = (
                        user_input.get(
                            const.CFOF_BADGES_INPUT_ASSOCIATED_ACHIEVEMENT,
                            badge_data.get(
                                const.DATA_BADGE_ASSOCIATED_ACHIEVEMENT,
                                const.CONF_EMPTY,
                            ),
                        )
                    )

                elif badge_type == const.BADGE_TYPE_CHALLENGE_LINKED:
                    badge_data[const.DATA_BADGE_ASSOCIATED_CHALLENGE] = user_input.get(
                        const.CFOF_BADGES_INPUT_ASSOCIATED_CHALLENGE,
                        badge_data.get(
                            const.DATA_BADGE_ASSOCIATED_CHALLENGE, const.CONF_EMPTY
                        ),
                    )

                elif badge_type == const.BADGE_TYPE_SPECIAL_OCCASION:
                    badge_data[const.DATA_BADGE_OCCASION_TYPE] = user_input.get(
                        const.CFOF_BADGES_INPUT_OCCASION_TYPE,
                        badge_data.get(
                            const.DATA_BADGE_OCCASION_TYPE, const.CONF_HOLIDAY
                        ),
                    )
                    badge_data[const.DATA_BADGE_OCCASION_DATE] = user_input.get(
                        const.CFOF_BADGES_INPUT_OCCASION_DATE,
                        badge_data.get(
                            const.DATA_BADGE_OCCASION_DATE, const.CONF_EMPTY
                        ),
                    )
                    badge_data[const.DATA_BADGE_SPECIAL_OCCASION_RECURRENCY] = (
                        user_input.get(
                            const.CFOF_BADGES_INPUT_SPECIAL_OCCASION_RECURRENCY,
                            badge_data.get(
                                const.DATA_BADGE_SPECIAL_OCCASION_RECURRENCY, False
                            ),
                        )
                    )
                    badge_data[const.DATA_BADGE_TRIGGER_INFO] = user_input.get(
                        const.CFOF_BADGES_INPUT_TRIGGER_INFO,
                        badge_data.get(const.DATA_BADGE_TRIGGER_INFO, const.CONF_EMPTY),
                    )

                badges_dict[internal_id] = badge_data
                self._entry_options[const.CONF_BADGES] = badges_dict

                const.LOGGER.debug(
                    "Edited badge '%s' with ID: %s",
                    badge_data[const.DATA_BADGE_NAME],
                    internal_id,
                )

                await self._update_and_reload()
                return await self.async_step_init()

        kids_dict = {
            kid_data[const.DATA_KID_NAME]: kid_id
            for kid_id, kid_data in self._entry_options.get(const.CONF_KIDS, {}).items()
        }

        # Build the schema based on badge_type:
        if badge_type == const.BADGE_TYPE_CUMULATIVE:
            schema = fh.build_badge_cumulative_schema(default=badge_data)
        elif badge_type == const.BADGE_TYPE_DAILY:
            schema = fh.build_badge_daily_schema(default=badge_data)
        elif badge_type == const.BADGE_TYPE_PERIODIC:
            rewards_options = [
                {
                    "value": reward_id,
                    "label": reward.get(const.DATA_REWARD_NAME, const.CONF_NONE_TEXT),
                }
                for reward_id, reward in self._entry_options.get(
                    const.CONF_REWARDS, {}
                ).items()
            ]
            chores_options = [
                {
                    "value": chore_id,
                    "label": chore.get(const.DATA_CHORE_NAME, const.CONF_NONE_TEXT),
                }
                for chore_id, chore in self._entry_options.get(
                    const.CONF_CHORES, {}
                ).items()
            ]
            schema = fh.build_badge_periodic_schema(
                default=badge_data,
                rewards_list=rewards_options,
                chores_list=chores_options,
            )
        elif badge_type == const.BADGE_TYPE_ACHIEVEMENT_LINKED:
            achievements_options = [
                {
                    "value": achievement_id,
                    "label": ach.get(const.DATA_ACHIEVEMENT_NAME, const.CONF_NONE_TEXT),
                }
                for achievement_id, ach in self._entry_options.get(
                    const.CONF_ACHIEVEMENTS, {}
                ).items()
            ]
            rewards_options = [
                {
                    "value": reward_id,
                    "label": reward.get(const.DATA_REWARD_NAME, const.CONF_NONE_TEXT),
                }
                for reward_id, reward in self._entry_options.get(
                    const.CONF_REWARDS, {}
                ).items()
            ]
            schema = fh.build_badge_achievement_schema(
                default=badge_data,
                achievements_list=achievements_options,
                rewards_list=rewards_options,
            )
        elif badge_type == const.BADGE_TYPE_CHALLENGE_LINKED:
            challenges_options = [
                {
                    "value": challenge_id,
                    "label": chall.get(const.DATA_CHALLENGE_NAME, const.CONF_NONE_TEXT),
                }
                for challenge_id, chall in self._entry_options.get(
                    const.CONF_CHALLENGES, {}
                ).items()
            ]
            rewards_options = [
                {
                    "value": reward_id,
                    "label": reward.get(const.DATA_REWARD_NAME, const.CONF_NONE_TEXT),
                }
                for reward_id, reward in self._entry_options.get(
                    const.CONF_REWARDS, {}
                ).items()
            ]
            schema = fh.build_badge_challenge_schema(
                default=badge_data,
                challenges_list=challenges_options,
                rewards_list=rewards_options,
            )
        elif badge_type == const.BADGE_TYPE_SPECIAL_OCCASION:
            rewards_options = [
                {
                    "value": reward_id,
                    "label": reward.get(const.DATA_REWARD_NAME, const.CONF_NONE_TEXT),
                }
                for reward_id, reward in self._entry_options.get(
                    const.CONF_REWARDS, {}
                ).items()
            ]
            schema = fh.build_badge_special_occasions_schema(
                default=badge_data,
                rewards_list=rewards_options,
                kids_dict=kids_dict,
            )
        else:
            schema = fh.build_badge_cumulative_schema(default=badge_data)

        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_EDIT_BADGE,
            data_schema=schema,
            errors=errors,
        )

    async def async_step_edit_reward(self, user_input=None):
        """Edit an existing reward."""
        self._entry_options = dict(self.config_entry.options)

        errors = {}
        rewards_dict = self._entry_options.get(const.CONF_REWARDS, {})
        internal_id = self.context.get(const.DATA_INTERNAL_ID)

        if not internal_id or internal_id not in rewards_dict:
            const.LOGGER.error("Edit reward: Invalid internal_id '%s'", internal_id)
            return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_REWARD)

        reward_data = rewards_dict[internal_id]

        if user_input is not None:
            new_name = user_input[const.CFOF_REWARDS_INPUT_NAME].strip()

            # Check for duplicate names excluding current reward
            if any(
                data[const.DATA_REWARD_NAME] == new_name and eid != internal_id
                for eid, data in rewards_dict.items()
            ):
                errors[const.CFOP_ERROR_REWARD_NAME] = (
                    const.TRANS_KEY_CFOF_DUPLICATE_REWARD
                )
            else:
                reward_data[const.DATA_REWARD_NAME] = new_name
                reward_data[const.DATA_REWARD_COST] = user_input[
                    const.CFOF_REWARDS_INPUT_COST
                ]
                reward_data[const.DATA_REWARD_DESCRIPTION] = user_input.get(
                    const.CFOF_REWARDS_INPUT_DESCRIPTION, const.CONF_EMPTY
                )
                reward_data[const.DATA_REWARD_LABELS] = user_input.get(
                    const.CFOF_REWARDS_INPUT_LABELS, []
                )
                reward_data[const.DATA_REWARD_ICON] = user_input.get(
                    const.CFOF_REWARDS_INPUT_ICON, const.CONF_EMPTY
                )

                self._entry_options[const.CONF_REWARDS] = rewards_dict

                const.LOGGER.debug(
                    "Edited reward '%s' with ID: %s", new_name, internal_id
                )

                await self._update_and_reload()
                return await self.async_step_init()

        schema = fh.build_reward_schema(default=reward_data)
        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_EDIT_REWARD,
            data_schema=schema,
            errors=errors,
        )

    async def async_step_edit_penalty(self, user_input=None):
        """Edit an existing penalty."""
        self._entry_options = dict(self.config_entry.options)

        errors = {}
        penalties_dict = self._entry_options.get(const.CONF_PENALTIES, {})
        internal_id = self.context.get(const.DATA_INTERNAL_ID)

        if not internal_id or internal_id not in penalties_dict:
            const.LOGGER.error("Edit penalty: Invalid internal_id '%s'", internal_id)
            return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_PENALTY)

        penalty_data = penalties_dict[internal_id]

        if user_input is not None:
            new_name = user_input[const.CFOF_PENALTIES_INPUT_NAME].strip()
            penalty_points = user_input[const.CFOF_PENALTIES_INPUT_POINTS]

            # Check for duplicate names excluding current penalty
            if any(
                data[const.DATA_PENALTY_NAME] == new_name and eid != internal_id
                for eid, data in penalties_dict.items()
            ):
                errors[const.CFOP_ERROR_PENALTY_NAME] = (
                    const.TRANS_KEY_CFOF_DUPLICATE_PENALTY
                )
            else:
                penalty_data[const.DATA_PENALTY_NAME] = new_name
                penalty_data[const.DATA_PENALTY_DESCRIPTION] = user_input.get(
                    const.CFOF_PENALTIES_INPUT_DESCRIPTION, const.CONF_EMPTY
                )
                penalty_data[const.DATA_PENALTY_LABELS] = user_input.get(
                    const.CFOF_PENALTIES_INPUT_LABELS, []
                )
                penalty_data[const.DATA_PENALTY_POINTS] = -abs(
                    penalty_points
                )  # Ensure points are negative
                penalty_data[const.DATA_PENALTY_ICON] = user_input.get(
                    const.CFOF_PENALTIES_INPUT_ICON, const.CONF_EMPTY
                )

                self._entry_options[const.CONF_PENALTIES] = penalties_dict

                const.LOGGER.debug(
                    "Edited penalty '%s' with ID: %s", new_name, internal_id
                )

                await self._update_and_reload()
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

    async def async_step_edit_bonus(self, user_input=None):
        """Edit an existing bonus."""
        self._entry_options = dict(self.config_entry.options)

        errors = {}
        bonuses_dict = self._entry_options.get(const.CONF_BONUSES, {})
        internal_id = self.context.get(const.DATA_INTERNAL_ID)

        if not internal_id or internal_id not in bonuses_dict:
            const.LOGGER.error("Edit bonus: Invalid internal_id '%s'", internal_id)
            return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_BONUS)

        bonus_data = bonuses_dict[internal_id]

        if user_input is not None:
            new_name = user_input[const.CFOF_BONUSES_INPUT_NAME].strip()
            bonus_points = user_input[const.CFOF_BONUSES_INPUT_POINTS]

            # Check for duplicate names excluding current bonus
            if any(
                data[const.DATA_BONUS_NAME] == new_name and eid != internal_id
                for eid, data in bonuses_dict.items()
            ):
                errors[const.CFOP_ERROR_BONUS_NAME] = (
                    const.TRANS_KEY_CFOF_DUPLICATE_BONUS
                )
            else:
                bonus_data[const.DATA_BONUS_NAME] = new_name
                bonus_data[const.DATA_BONUS_DESCRIPTION] = user_input.get(
                    const.CFOF_BONUSES_INPUT_DESCRIPTION, const.CONF_EMPTY
                )
                bonus_data[const.DATA_BONUS_LABELS] = user_input.get(
                    const.CFOF_BONUSES_INPUT_LABELS, []
                )
                bonus_data[const.DATA_BONUS_POINTS] = abs(
                    bonus_points
                )  # Ensure points are positive
                bonus_data[const.DATA_BONUS_ICON] = user_input.get(
                    const.CFOF_BONUSES_INPUT_ICON, const.CONF_EMPTY
                )

                self._entry_options[const.CONF_BONUSES] = bonuses_dict

                const.LOGGER.debug(
                    "Edited bonus '%s' with ID: %s", new_name, internal_id
                )

                await self._update_and_reload()
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

    async def async_step_edit_achievement(self, user_input=None):
        """Edit an existing achievement."""
        self._entry_options = dict(self.config_entry.options)

        errors = {}
        achievements_dict = self._entry_options.get(const.CONF_ACHIEVEMENTS, {})

        internal_id = self.context.get(const.DATA_INTERNAL_ID)
        if not internal_id or internal_id not in achievements_dict:
            const.LOGGER.error(
                "Edit achievement: Invalid internal_id '%s'", internal_id
            )
            return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_ACHIEVEMENT)

        achievement_data = achievements_dict[internal_id]

        if user_input is not None:
            new_name = user_input[const.CFOF_ACHIEVEMENTS_INPUT_NAME].strip()
            if any(
                data[const.DATA_ACHIEVEMENT_NAME] == new_name and eid != internal_id
                for eid, data in achievements_dict.items()
            ):
                errors[const.CFOP_ERROR_ACHIEVEMENT_NAME] = (
                    const.TRANS_KEY_CFOF_DUPLICATE_ACHIEVEMENT
                )
            else:
                _type = user_input[const.CFOF_ACHIEVEMENTS_INPUT_TYPE]

                chore_id = const.CONF_EMPTY
                if _type == const.ACHIEVEMENT_TYPE_STREAK:
                    c = (
                        user_input.get(const.CFOF_ACHIEVEMENTS_INPUT_SELECTED_CHORE_ID)
                        or const.CONF_EMPTY
                    )
                    if not c or c == const.CONF_NONE_TEXT:
                        errors[const.CFOP_ERROR_SELECT_CHORE_ID] = (
                            const.TRANS_KEY_CFOF_CHORE_MUST_BE_SELECTED
                        )
                    chore_id = c

                if not errors:
                    achievement_data[const.DATA_ACHIEVEMENT_NAME] = new_name
                    achievement_data[const.DATA_ACHIEVEMENT_DESCRIPTION] = (
                        user_input.get(
                            const.CFOF_ACHIEVEMENTS_INPUT_DESCRIPTION, const.CONF_EMPTY
                        )
                    )
                    achievement_data[const.DATA_ACHIEVEMENT_LABELS] = user_input.get(
                        const.CFOF_ACHIEVEMENTS_INPUT_LABELS, []
                    )
                    achievement_data[const.DATA_ACHIEVEMENT_ICON] = user_input.get(
                        const.CFOF_ACHIEVEMENTS_INPUT_ICON, const.CONF_EMPTY
                    )
                    achievement_data[const.DATA_ACHIEVEMENT_ASSIGNED_KIDS] = user_input[
                        const.CFOF_ACHIEVEMENTS_INPUT_ASSIGNED_KIDS
                    ]
                    achievement_data[const.DATA_ACHIEVEMENT_TYPE] = _type
                    achievement_data[const.DATA_ACHIEVEMENT_SELECTED_CHORE_ID] = (
                        chore_id
                    )
                    achievement_data[const.DATA_ACHIEVEMENT_CRITERIA] = user_input.get(
                        const.CFOF_ACHIEVEMENTS_INPUT_CRITERIA, const.CONF_EMPTY
                    ).strip()
                    achievement_data[const.DATA_ACHIEVEMENT_TARGET_VALUE] = user_input[
                        const.CFOF_ACHIEVEMENTS_INPUT_TARGET_VALUE
                    ]
                    achievement_data[const.DATA_ACHIEVEMENT_REWARD_POINTS] = user_input[
                        const.CFOF_ACHIEVEMENTS_INPUT_REWARD_POINTS
                    ]
                    achievements_dict[internal_id] = achievement_data
                    self._entry_options[const.CONF_ACHIEVEMENTS] = achievements_dict

                    const.LOGGER.debug(
                        "Edited achievement '%s' with ID: %s", new_name, internal_id
                    )

                    await self._update_and_reload()
                    return await self.async_step_init()

        kids_dict = {
            kid_data[const.DATA_KID_NAME]: kid_id
            for kid_id, kid_data in self._entry_options.get(const.CONF_KIDS, {}).items()
        }
        chores_dict = self._entry_options.get(const.CONF_CHORES, {})

        achievement_schema = fh.build_achievement_schema(
            kids_dict=kids_dict, chores_dict=chores_dict, default=achievement_data
        )
        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_EDIT_ACHIEVEMENT,
            data_schema=achievement_schema,
            errors=errors,
        )

    async def async_step_edit_challenge(self, user_input=None):
        """Edit an existing challenge."""
        self._entry_options = dict(self.config_entry.options)
        errors = {}
        challenges_dict = self._entry_options.get(const.CONF_CHALLENGES, {})
        internal_id = self.context.get(const.DATA_INTERNAL_ID)

        if not internal_id or internal_id not in challenges_dict:
            const.LOGGER.error("Edit challenge: Invalid internal_id '%s'", internal_id)
            return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_CHALLENGE)

        challenge_data = challenges_dict[internal_id]

        if user_input is None:
            kids_dict = {
                data[const.DATA_KID_NAME]: kid_id
                for kid_id, data in self._entry_options.get(const.CONF_KIDS, {}).items()
            }
            chores_dict = self._entry_options.get(const.CONF_CHORES, {})
            # Convert stored start/end dates to a display format (e.g. local time string)
            default_data = {
                **challenge_data,
                const.DATA_CHALLENGE_START_DATE: challenge_data.get(
                    const.DATA_CHALLENGE_START_DATE
                )
                and dt_util.as_local(
                    dt_util.parse_datetime(
                        challenge_data[const.DATA_CHALLENGE_START_DATE]
                    )
                ).strftime("%Y-%m-%d %H:%M:%S"),
                const.DATA_CHALLENGE_END_DATE: challenge_data.get(
                    const.DATA_CHALLENGE_END_DATE
                )
                and dt_util.as_local(
                    dt_util.parse_datetime(
                        challenge_data[const.DATA_CHALLENGE_END_DATE]
                    )
                ).strftime("%Y-%m-%d %H:%M:%S"),
            }
            schema = fh.build_challenge_schema(
                kids_dict=kids_dict, chores_dict=chores_dict, default=default_data
            )
            return self.async_show_form(
                step_id=const.OPTIONS_FLOW_STEP_EDIT_CHALLENGE,
                data_schema=schema,
                errors=errors,
            )

        start_date_input = user_input.get(const.CFOF_CHALLENGES_INPUT_START_DATE)
        if start_date_input:
            try:
                new_start_date = fh.ensure_utc_datetime(self.hass, start_date_input)
                start_dt = dt_util.parse_datetime(new_start_date)
                if start_dt and start_dt < dt_util.utcnow():
                    errors[const.CFOP_ERROR_START_DATE] = (
                        const.TRANS_KEY_CFOF_START_DATE_IN_PAST
                    )
            except Exception:
                errors[const.CFOP_ERROR_START_DATE] = (
                    const.TRANS_KEY_CFOF_INVALID_START_DATE
                )
                new_start_date = None
        else:
            new_start_date = None

        end_date_input = user_input.get(const.CFOF_CHALLENGES_INPUT_END_DATE)
        if end_date_input:
            try:
                new_end_date = fh.ensure_utc_datetime(self.hass, end_date_input)
                end_dt = dt_util.parse_datetime(new_end_date)

                if end_dt and end_dt <= dt_util.utcnow():
                    errors[const.CFOP_ERROR_END_DATE] = (
                        const.TRANS_KEY_CFOF_END_DATE_IN_PAST
                    )

                if new_start_date:
                    sdt = dt_util.parse_datetime(new_start_date)
                    if sdt and end_dt and end_dt <= sdt:
                        errors[const.CFOP_ERROR_END_DATE] = (
                            const.TRANS_KEY_CFOF_END_DATE_NOT_AFTER_START_DATE
                        )
            except Exception:
                errors[const.CFOP_ERROR_END_DATE] = (
                    const.TRANS_KEY_CFOF_INVALID_END_DATE
                )
                new_end_date = None
        else:
            new_end_date = None

        if user_input is not None:
            new_name = user_input[const.CFOF_CHALLENGES_INPUT_NAME].strip()
            if any(
                data[const.DATA_CHALLENGE_NAME] == new_name and eid != internal_id
                for eid, data in challenges_dict.items()
            ):
                errors[const.CFOP_ERROR_CHALLENGE_NAME] = (
                    const.TRANS_KEY_CFOF_DUPLICATE_CHALLENGE
                )
            else:
                _type = user_input[const.CFOF_CHALLENGES_INPUT_TYPE]

                chore_id = const.CONF_EMPTY
                if _type == const.CHALLENGE_TYPE_TOTAL_WITHIN_WINDOW:
                    c = (
                        user_input.get(const.CFOF_CHALLENGES_INPUT_SELECTED_CHORE_ID)
                        or const.CONF_EMPTY
                    )
                    if not c or c == const.CONF_NONE_TEXT:
                        errors[const.CFOP_ERROR_SELECT_CHORE_ID] = (
                            const.TRANS_KEY_CFOF_CHORE_MUST_BE_SELECTED
                        )
                    chore_id = c

                if not errors:
                    challenge_data[const.DATA_CHALLENGE_NAME] = new_name
                    challenge_data[const.DATA_CHALLENGE_DESCRIPTION] = user_input.get(
                        const.CFOF_CHALLENGES_INPUT_DESCRIPTION, const.CONF_EMPTY
                    )
                    challenge_data[const.DATA_CHALLENGE_LABELS] = user_input.get(
                        const.CFOF_CHALLENGES_INPUT_LABELS, []
                    )
                    challenge_data[const.DATA_CHALLENGE_ICON] = user_input.get(
                        const.CFOF_CHALLENGES_INPUT_ICON, const.CONF_EMPTY
                    )
                    challenge_data[const.DATA_CHALLENGE_ASSIGNED_KIDS] = user_input[
                        const.CFOF_CHALLENGES_INPUT_ASSIGNED_KIDS
                    ]
                    challenge_data[const.DATA_CHALLENGE_TYPE] = _type
                    challenge_data[const.DATA_CHALLENGE_SELECTED_CHORE_ID] = chore_id
                    challenge_data[const.DATA_CHALLENGE_CRITERIA] = user_input.get(
                        const.CFOF_CHALLENGES_INPUT_CRITERIA, const.CONF_EMPTY
                    ).strip()
                    challenge_data[const.DATA_CHALLENGE_TARGET_VALUE] = user_input[
                        const.CFOF_CHALLENGES_INPUT_TARGET_VALUE
                    ]
                    challenge_data[const.DATA_CHALLENGE_REWARD_POINTS] = user_input[
                        const.CFOF_CHALLENGES_INPUT_REWARD_POINTS
                    ]
                    challenge_data[const.DATA_CHALLENGE_START_DATE] = new_start_date
                    challenge_data[const.DATA_CHALLENGE_END_DATE] = new_end_date

                    const.LOGGER.debug(
                        "Edited challenge '%s' with ID: %s", new_name, internal_id
                    )

                    await self._update_and_reload()
                    return await self.async_step_init()

        kids_dict = {
            kid_data[const.DATA_KID_NAME]: kid_id
            for kid_id, kid_data in self._entry_options.get(const.CONF_KIDS, {}).items()
        }
        chores_dict = self._entry_options.get(const.CONF_CHORES, {})

        default_data = {
            **challenge_data,
            const.DATA_CHALLENGE_START_DATE: new_start_date,
            const.DATA_CHALLENGE_END_DATE: new_end_date,
        }
        challenge_schema = fh.build_challenge_schema(
            kids_dict=kids_dict, chores_dict=chores_dict, default=default_data
        )
        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_EDIT_CHALLENGE,
            data_schema=challenge_schema,
            errors=errors,
        )

    # ------------------ DELETE ENTITY ------------------
    async def async_step_delete_kid(self, user_input=None):
        """Delete a kid."""
        self._entry_options = dict(self.config_entry.options)

        kids_dict = self._entry_options.get(const.CONF_KIDS, {})
        internal_id = self.context.get(const.DATA_INTERNAL_ID)

        if not internal_id or internal_id not in kids_dict:
            const.LOGGER.error("Delete kid: Invalid internal_id '%s'", internal_id)
            return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_KID)

        kid_name = kids_dict[internal_id][const.DATA_KID_NAME]

        if user_input is not None:
            kids_dict.pop(internal_id, None)

            self._entry_options[const.CONF_KIDS] = kids_dict

            const.LOGGER.debug("Deleted kid '%s' with ID: %s", kid_name, internal_id)
            await self._update_and_reload()
            return await self.async_step_init()

        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_DELETE_KID,
            data_schema=vol.Schema({}),
            description_placeholders={
                const.OPTIONS_FLOW_PLACEHOLDER_KID_NAME: kid_name
            },
        )

    async def async_step_delete_parent(self, user_input=None):
        """Delete a parent."""
        self._entry_options = dict(self.config_entry.options)

        parents_dict = self._entry_options.get(const.CONF_PARENTS, {})
        internal_id = self.context.get(const.DATA_INTERNAL_ID)

        if not internal_id or internal_id not in parents_dict:
            const.LOGGER.error("Delete parent: Invalid internal_id '%s'", internal_id)
            return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_PARENT)

        parent_name = parents_dict[internal_id][const.DATA_PARENT_NAME]

        if user_input is not None:
            parents_dict.pop(internal_id, None)

            self._entry_options[const.CONF_PARENTS] = parents_dict

            const.LOGGER.debug(
                "Deleted parent '%s' with ID: %s", parent_name, internal_id
            )
            await self._update_and_reload()
            return await self.async_step_init()

        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_DELETE_PARENT,
            data_schema=vol.Schema({}),
            description_placeholders={
                const.OPTIONS_FLOW_PLACEHOLDER_PARENT_NAME: parent_name
            },
        )

    async def async_step_delete_chore(self, user_input=None):
        """Delete a chore."""
        self._entry_options = dict(self.config_entry.options)

        chores_dict = self._entry_options.get(const.CONF_CHORES, {})
        internal_id = self.context.get(const.DATA_INTERNAL_ID)

        if not internal_id or internal_id not in chores_dict:
            const.LOGGER.error("Delete chore: Invalid internal_id '%s'", internal_id)
            return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_CHORE)

        chore_name = chores_dict[internal_id][const.DATA_CHORE_NAME]

        if user_input is not None:
            chores_dict.pop(internal_id, None)

            self._entry_options[const.CONF_CHORES] = chores_dict

            const.LOGGER.debug(
                "Deleted chore '%s' with ID: %s", chore_name, internal_id
            )
            await self._update_and_reload()
            return await self.async_step_init()

        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_DELETE_CHORE,
            data_schema=vol.Schema({}),
            description_placeholders={
                const.OPTIONS_FLOW_PLACEHOLDER_CHORE_NAME: chore_name
            },
        )

    async def async_step_delete_badge(self, user_input=None):
        """Delete a badge."""
        self._entry_options = dict(self.config_entry.options)

        badges_dict = self._entry_options.get(const.CONF_BADGES, {})
        internal_id = self.context.get(const.DATA_INTERNAL_ID)

        if not internal_id or internal_id not in badges_dict:
            const.LOGGER.error("Delete badge: Invalid internal_id '%s'", internal_id)
            return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_BADGE)

        badge_name = badges_dict[internal_id][const.DATA_BADGE_NAME]

        if user_input is not None:
            badges_dict.pop(internal_id, None)

            self._entry_options[const.CONF_BADGES] = badges_dict

            const.LOGGER.debug(
                "Deleted badge '%s' with ID: %s", badge_name, internal_id
            )
            await self._update_and_reload()
            return await self.async_step_init()

        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_DELETE_BADGE,
            data_schema=vol.Schema({}),
            description_placeholders={
                const.OPTIONS_FLOW_PLACEHOLDER_BADGE_NAME: badge_name
            },
        )

    async def async_step_delete_reward(self, user_input=None):
        """Delete a reward."""
        self._entry_options = dict(self.config_entry.options)

        rewards_dict = self._entry_options.get(const.CONF_REWARDS, {})
        internal_id = self.context.get(const.DATA_INTERNAL_ID)

        if not internal_id or internal_id not in rewards_dict:
            const.LOGGER.error("Delete reward: Invalid internal_id '%s'", internal_id)
            return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_REWARD)

        reward_name = rewards_dict[internal_id][const.DATA_REWARD_NAME]

        if user_input is not None:
            rewards_dict.pop(internal_id, None)

            self._entry_options[const.CONF_REWARDS] = rewards_dict

            const.LOGGER.debug(
                "Deleted reward '%s' with ID: %s", reward_name, internal_id
            )
            await self._update_and_reload()
            return await self.async_step_init()

        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_DELETE_REWARD,
            data_schema=vol.Schema({}),
            description_placeholders={
                const.OPTIONS_FLOW_PLACEHOLDER_REWARD_NAME: reward_name
            },
        )

    async def async_step_delete_penalty(self, user_input=None):
        """Delete a penalty."""
        self._entry_options = dict(self.config_entry.options)

        penalties_dict = self._entry_options.get(const.CONF_PENALTIES, {})
        internal_id = self.context.get(const.DATA_INTERNAL_ID)

        if not internal_id or internal_id not in penalties_dict:
            const.LOGGER.error("Delete penalty: Invalid internal_id '%s'", internal_id)
            return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_PENALTY)

        penalty_name = penalties_dict[internal_id][const.DATA_PENALTY_NAME]

        if user_input is not None:
            penalties_dict.pop(internal_id, None)

            self._entry_options[const.CONF_PENALTIES] = penalties_dict

            const.LOGGER.debug(
                "Deleted penalty '%s' with ID: %s", penalty_name, internal_id
            )
            await self._update_and_reload()
            return await self.async_step_init()

        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_DELETE_PENALTY,
            data_schema=vol.Schema({}),
            description_placeholders={
                const.OPTIONS_FLOW_PLACEHOLDER_PENALTY_NAME: penalty_name
            },
        )

    async def async_step_delete_achievement(self, user_input=None):
        """Delete an achievement."""
        self._entry_options = dict(self.config_entry.options)

        achievements_dict = self._entry_options.get(const.CONF_ACHIEVEMENTS, {})
        internal_id = self.context.get(const.DATA_INTERNAL_ID)

        if not internal_id or internal_id not in achievements_dict:
            const.LOGGER.error(
                "Delete achievement: Invalid internal_id '%s'", internal_id
            )
            return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_ACHIEVEMENT)

        achievement_name = achievements_dict[internal_id][const.DATA_ACHIEVEMENT_NAME]
        if user_input is not None:
            achievements_dict.pop(internal_id, None)
            self._entry_options[const.CONF_ACHIEVEMENTS] = achievements_dict
            const.LOGGER.debug(
                "Deleted achievement '%s' with ID: %s", achievement_name, internal_id
            )

            await self._update_and_reload()
            return await self.async_step_init()

        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_DELETE_ACHIEVEMENT,
            data_schema=vol.Schema({}),
            description_placeholders={
                const.OPTIONS_FLOW_PLACEHOLDER_ACHIEVEMENT_NAME: achievement_name
            },
        )

    async def async_step_delete_challenge(self, user_input=None):
        """Delete a challenge."""
        self._entry_options = dict(self.config_entry.options)

        challenges_dict = self._entry_options.get(const.CONF_CHALLENGES, {})
        internal_id = self.context.get(const.DATA_INTERNAL_ID)

        if not internal_id or internal_id not in challenges_dict:
            const.LOGGER.error(
                "Delete challenge: Invalid internal_id '%s'", internal_id
            )
            return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_CHALLENGE)

        challenge_name = challenges_dict[internal_id][const.DATA_CHALLENGE_NAME]
        if user_input is not None:
            challenges_dict.pop(internal_id, None)
            self._entry_options[const.CONF_CHALLENGES] = challenges_dict
            const.LOGGER.debug(
                "Deleted challenge '%s' with ID: %s", challenge_name, internal_id
            )

            await self._update_and_reload()
            return await self.async_step_init()

        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_DELETE_CHALLENGE,
            data_schema=vol.Schema({}),
            description_placeholders={
                const.OPTIONS_FLOW_PLACEHOLDER_CHALLENGE_NAME: challenge_name
            },
        )

    async def async_step_delete_bonus(self, user_input=None):
        """Delete a bonus."""
        self._entry_options = dict(self.config_entry.options)

        bonuses_dict = self._entry_options.get(const.CONF_BONUSES, {})
        internal_id = self.context.get(const.DATA_INTERNAL_ID)

        if not internal_id or internal_id not in bonuses_dict:
            const.LOGGER.error("Delete bonus: Invalid internal_id '%s'", internal_id)
            return self.async_abort(reason=const.TRANS_KEY_CFOF_INVALID_BONUS)

        bonus_name = bonuses_dict[internal_id][const.DATA_BONUS_NAME]

        if user_input is not None:
            bonuses_dict.pop(internal_id, None)

            self._entry_options[const.CONF_BONUSES] = bonuses_dict

            const.LOGGER.debug(
                "Deleted bonus '%s' with ID: %s", bonus_name, internal_id
            )
            await self._update_and_reload()
            return await self.async_step_init()

        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_DELETE_BONUS,
            data_schema=vol.Schema({}),
            description_placeholders={
                const.OPTIONS_FLOW_PLACEHOLDER_BONUS_NAME: bonus_name
            },
        )

    # ------------------ GENERAL OPTIONS ------------------
    async def async_step_manage_general_options(self, user_input=None):
        """Manage general options: points adjust values and update interval."""
        if user_input is not None:
            # Get the raw text from the multiline text area.
            points_str = user_input.get(
                const.CONF_POINTS_ADJUST_VALUES, const.CONF_EMPTY
            ).strip()
            if points_str:
                # Parse the values by splitting on newlines and commas.
                parsed_values = kh.parse_points_adjust_values(points_str)
                # Always store as a list of floats.
                self._entry_options[const.CONF_POINTS_ADJUST_VALUES] = parsed_values
            else:
                # Remove the key if the field is left empty.
                self._entry_options.pop(const.CONF_POINTS_ADJUST_VALUES, None)
            # Update the update interval.
            self._entry_options[const.CONF_UPDATE_INTERVAL] = user_input.get(
                const.CONF_UPDATE_INTERVAL
            )
            # update calendar show period
            self._entry_options[const.CONF_CALENDAR_SHOW_PERIOD] = user_input.get(
                const.CONF_CALENDAR_SHOW_PERIOD
            )
            const.LOGGER.debug(
                "General options updated: Points Adjust Values=%s, Update Interval=%s, Calendar Period to Show=%s",
                self._entry_options.get(const.CONF_POINTS_ADJUST_VALUES),
                self._entry_options.get(const.CONF_UPDATE_INTERVAL),
                self._entry_options.get(const.CONF_CALENDAR_SHOW_PERIOD),
            )
            await self._update_and_reload()
            return await self.async_step_init()

        # Use the helper schema (which now shows one value per line)
        general_schema = fh.build_general_options_schema(self._entry_options)
        return self.async_show_form(
            step_id=const.OPTIONS_FLOW_STEP_MANAGE_GENERAL_OPTIONS,
            data_schema=general_schema,
            description_placeholders={},
        )

    # ------------------ HELPER METHODS ------------------
    async def _update_and_reload(self):
        """Update the config entry options and reload the integration."""
        new_data = dict(self.config_entry.data)
        new_data[const.DATA_LAST_CHANGE] = dt_util.utcnow().isoformat()

        self.hass.config_entries.async_update_entry(
            self.config_entry, data=new_data, options=self._entry_options
        )
        const.LOGGER.debug(
            "Called update_entry. Now reloading entry: %s", self.config_entry.entry_id
        )
        await self.hass.config_entries.async_reload(self.config_entry.entry_id)
        const.LOGGER.debug("Options updated and integration reloaded")
