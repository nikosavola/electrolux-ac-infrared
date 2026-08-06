"""Config flow for the Electrolux Infrared integration."""

from typing import Any, override

from homeassistant.components import infrared
from homeassistant.components.infrared import DOMAIN as INFRARED_DOMAIN
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.data_entry_flow import AbortFlow
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig
import voluptuous as vol

from .const import (
    CONF_INFRARED_EMITTER_ENTITY_ID,
    CONF_INFRARED_RECEIVER_ENTITY_ID,
    DOMAIN,
)


class ElectroluxInfraredConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Electrolux Infrared."""

    VERSION = 1

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select the infrared emitter, and optionally a receiver, to use."""
        emitter_entity_ids = infrared.async_get_emitters(self.hass)
        if not emitter_entity_ids:
            return self.async_abort(reason="no_emitters")

        if user_input is not None:
            emitter_entity_id = user_input[CONF_INFRARED_EMITTER_ENTITY_ID]
            await self.async_set_unique_id(emitter_entity_id)
            self._abort_if_unique_id_configured()
            self._abort_if_receiver_in_use(user_input)

            return self.async_create_entry(
                title=self._title(emitter_entity_id), data=user_input
            )

        return self.async_show_form(
            step_id="user", data_schema=self._schema(emitter_entity_ids)
        )

    @override
    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the infrared emitter or receiver of an existing entry."""
        emitter_entity_ids = infrared.async_get_emitters(self.hass)
        if not emitter_entity_ids:
            return self.async_abort(reason="no_emitters")

        entry = self._get_reconfigure_entry()
        if user_input is not None:
            emitter_entity_id = user_input[CONF_INFRARED_EMITTER_ENTITY_ID]
            if emitter_entity_id != entry.unique_id:
                await self.async_set_unique_id(emitter_entity_id)
                self._abort_if_unique_id_configured()
            self._abort_if_receiver_in_use(user_input, ignore_entry_id=entry.entry_id)

            return self.async_update_reload_and_abort(
                entry,
                unique_id=emitter_entity_id,
                title=self._title(emitter_entity_id),
                data=user_input,
            )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                self._schema(emitter_entity_ids), entry.data
            ),
        )

    def _abort_if_receiver_in_use(
        self, user_input: dict[str, Any], *, ignore_entry_id: str | None = None
    ) -> None:
        """Abort if another entry already follows the selected receiver.

        Two entries sharing a receiver would both react to the same remote press.
        """
        receiver_entity_id = user_input.get(CONF_INFRARED_RECEIVER_ENTITY_ID)
        if receiver_entity_id is None:
            return

        for entry in self._async_current_entries(include_ignore=False):
            if entry.entry_id == ignore_entry_id:
                continue
            if entry.data.get(CONF_INFRARED_RECEIVER_ENTITY_ID) == receiver_entity_id:
                raise AbortFlow("receiver_in_use")

    def _schema(self, emitter_entity_ids: list[str]) -> vol.Schema:
        """Return the schema for selecting the emitter and receiver entities."""
        schema: dict[Any, Any] = {
            vol.Required(CONF_INFRARED_EMITTER_ENTITY_ID): EntitySelector(
                EntitySelectorConfig(
                    domain=INFRARED_DOMAIN, include_entities=emitter_entity_ids
                )
            )
        }
        # An empty include list would offer every entity, so the receiver is only
        # offered once at least one receiver exists.
        if receiver_entity_ids := infrared.async_get_receivers(self.hass):
            schema[vol.Optional(CONF_INFRARED_RECEIVER_ENTITY_ID)] = EntitySelector(
                EntitySelectorConfig(
                    domain=INFRARED_DOMAIN, include_entities=receiver_entity_ids
                )
            )
        return vol.Schema(schema)

    def _title(self, emitter_entity_id: str) -> str:
        """Return the entry title, naming the emitter the AC is controlled through."""
        entry = er.async_get(self.hass).async_get(emitter_entity_id)
        name = (
            entry.name or entry.original_name or emitter_entity_id
            if entry
            else emitter_entity_id
        )
        return f"Electrolux AC via {name}"
