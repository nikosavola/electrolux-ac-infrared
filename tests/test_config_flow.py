"""Tests for the Electrolux Infrared config flow."""

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.electrolux_infrared.const import (
    CONF_INFRARED_EMITTER_ENTITY_ID,
    CONF_INFRARED_RECEIVER_ENTITY_ID,
    DOMAIN,
)

from .conftest import EMITTER_ENTITY_ID, RECEIVER_ENTITY_ID


@pytest.mark.usefixtures("mock_infrared", "mock_setup_entry")
async def test_user_flow(hass: HomeAssistant) -> None:
    """A config entry is created for the selected emitter."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_INFRARED_EMITTER_ENTITY_ID: EMITTER_ENTITY_ID},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Electrolux AC via Test emitter"
    assert result["data"] == {CONF_INFRARED_EMITTER_ENTITY_ID: EMITTER_ENTITY_ID}
    assert result["result"].unique_id == EMITTER_ENTITY_ID


@pytest.mark.usefixtures("mock_infrared", "mock_setup_entry")
async def test_user_flow_with_receiver(hass: HomeAssistant) -> None:
    """A receiver can be selected alongside the emitter."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_INFRARED_EMITTER_ENTITY_ID: EMITTER_ENTITY_ID,
            CONF_INFRARED_RECEIVER_ENTITY_ID: RECEIVER_ENTITY_ID,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_INFRARED_EMITTER_ENTITY_ID: EMITTER_ENTITY_ID,
        CONF_INFRARED_RECEIVER_ENTITY_ID: RECEIVER_ENTITY_ID,
    }


async def test_user_flow_without_emitters(hass: HomeAssistant) -> None:
    """The flow aborts when no infrared emitter is available."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_emitters"


@pytest.mark.usefixtures("mock_infrared", "mock_setup_entry")
async def test_user_flow_already_configured(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """An emitter can only drive one Electrolux air conditioner."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_INFRARED_EMITTER_ENTITY_ID: EMITTER_ENTITY_ID},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.usefixtures("mock_infrared", "mock_setup_entry")
async def test_user_flow_receiver_in_use(hass: HomeAssistant) -> None:
    """Two air conditioners cannot follow the same receiver."""
    MockConfigEntry(
        domain=DOMAIN,
        unique_id="infrared.other_emitter",
        data={
            CONF_INFRARED_EMITTER_ENTITY_ID: "infrared.other_emitter",
            CONF_INFRARED_RECEIVER_ENTITY_ID: RECEIVER_ENTITY_ID,
        },
    ).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_INFRARED_EMITTER_ENTITY_ID: EMITTER_ENTITY_ID,
            CONF_INFRARED_RECEIVER_ENTITY_ID: RECEIVER_ENTITY_ID,
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "receiver_in_use"


@pytest.mark.usefixtures("mock_infrared", "mock_setup_entry")
async def test_reconfigure_flow_keeps_own_receiver(
    hass: HomeAssistant, mock_config_entry_with_receiver: MockConfigEntry
) -> None:
    """An entry keeping the receiver it already uses is not rejected as a duplicate."""
    mock_config_entry_with_receiver.add_to_hass(hass)

    result = await mock_config_entry_with_receiver.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_INFRARED_EMITTER_ENTITY_ID: EMITTER_ENTITY_ID,
            CONF_INFRARED_RECEIVER_ENTITY_ID: RECEIVER_ENTITY_ID,
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"


@pytest.mark.usefixtures("mock_infrared", "mock_setup_entry")
async def test_reconfigure_flow(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Reconfiguring the entry adds a receiver to it."""
    mock_config_entry.add_to_hass(hass)

    result = await mock_config_entry.start_reconfigure_flow(hass)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_INFRARED_EMITTER_ENTITY_ID: EMITTER_ENTITY_ID,
            CONF_INFRARED_RECEIVER_ENTITY_ID: RECEIVER_ENTITY_ID,
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_config_entry.data == {
        CONF_INFRARED_EMITTER_ENTITY_ID: EMITTER_ENTITY_ID,
        CONF_INFRARED_RECEIVER_ENTITY_ID: RECEIVER_ENTITY_ID,
    }
    assert mock_config_entry.unique_id == EMITTER_ENTITY_ID


@pytest.mark.usefixtures("mock_infrared", "mock_setup_entry")
async def test_reconfigure_flow_emitter_in_use(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Reconfiguring onto an emitter another entry uses is rejected."""
    mock_config_entry.add_to_hass(hass)
    other_entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="infrared.other_emitter",
        data={CONF_INFRARED_EMITTER_ENTITY_ID: "infrared.other_emitter"},
    )
    other_entry.add_to_hass(hass)

    result = await other_entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_INFRARED_EMITTER_ENTITY_ID: EMITTER_ENTITY_ID},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.usefixtures("mock_setup_entry")
async def test_reconfigure_flow_without_emitters(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Reconfiguring aborts when no infrared emitter is available."""
    mock_config_entry.add_to_hass(hass)

    result = await mock_config_entry.start_reconfigure_flow(hass)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_emitters"
