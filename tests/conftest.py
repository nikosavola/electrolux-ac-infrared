"""Fixtures for the Electrolux Infrared tests."""

from collections.abc import Generator
from dataclasses import dataclass
from typing import override
from unittest.mock import patch

from homeassistant.components.infrared import (
    DOMAIN as INFRARED_DOMAIN,
    InfraredEmitterEntity,
    InfraredReceivedSignal,
    InfraredReceiverEntity,
)
from homeassistant.config_entries import ConfigEntry, ConfigFlow
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.setup import async_setup_component
from infrared_protocols.commands import Command as InfraredCommand
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    MockModule,
    MockPlatform,
    mock_config_flow,
    mock_integration,
    mock_platform,
)

from custom_components.electrolux_infrared.const import (
    CONF_INFRARED_EMITTER_ENTITY_ID,
    CONF_INFRARED_RECEIVER_ENTITY_ID,
    DOMAIN,
)

EMITTER_ENTITY_ID = "infrared.test_emitter"
RECEIVER_ENTITY_ID = "infrared.test_receiver"
CLIMATE_ENTITY_ID = "climate.electrolux_ac_via_test_emitter"

MOCK_IR_DOMAIN = "mock_ir"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> None:
    """Enable loading the integration from custom_components."""


class MockEmitter(InfraredEmitterEntity):
    """An infrared emitter that records the commands sent to it."""

    _attr_name = "Test emitter"
    _attr_unique_id = "test_emitter"

    def __init__(self) -> None:
        """Initialize the mock emitter."""
        self.commands: list[InfraredCommand] = []

    @override
    async def async_send_command(self, command: InfraredCommand) -> None:
        """Record the command instead of transmitting it."""
        self.commands.append(command)


class MockReceiver(InfraredReceiverEntity):
    """An infrared receiver that signals can be injected into."""

    _attr_name = "Test receiver"
    _attr_unique_id = "test_receiver"

    def emit(self, timings: list[int]) -> None:
        """Simulate a received IR signal."""
        self._handle_received_signal(InfraredReceivedSignal(timings=timings))


@dataclass(frozen=True, slots=True)
class MockInfrared:
    """The mock emitter and receiver a test can drive."""

    emitter: MockEmitter
    receiver: MockReceiver


@pytest.fixture
async def mock_infrared(hass: HomeAssistant) -> MockInfrared:
    """Set up an infrared emitter and receiver backed by a mock integration."""
    emitter = MockEmitter()
    receiver = MockReceiver()

    async def async_setup_entry_platform(
        _hass: HomeAssistant,
        _entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
    ) -> None:
        async_add_entities([emitter, receiver])

    async def async_setup_entry_init(hass: HomeAssistant, entry: ConfigEntry) -> bool:
        await hass.config_entries.async_forward_entry_setups(entry, [Platform.INFRARED])
        return True

    mock_integration(
        hass,
        MockModule(
            MOCK_IR_DOMAIN,
            async_setup_entry=async_setup_entry_init,
            partial_manifest={"dependencies": [INFRARED_DOMAIN]},
        ),
    )
    mock_platform(
        hass,
        f"{MOCK_IR_DOMAIN}.{INFRARED_DOMAIN}",
        MockPlatform(async_setup_entry=async_setup_entry_platform),
    )
    mock_platform(hass, f"{MOCK_IR_DOMAIN}.config_flow")

    assert await async_setup_component(hass, INFRARED_DOMAIN, {})
    entry = MockConfigEntry(domain=MOCK_IR_DOMAIN)
    entry.add_to_hass(hass)

    class MockFlow(ConfigFlow):
        """A config flow so the mock integration can be set up."""

    with mock_config_flow(MOCK_IR_DOMAIN, MockFlow):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    return MockInfrared(emitter=emitter, receiver=receiver)


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a config entry for the Electrolux AC."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Electrolux AC via Test emitter",
        unique_id=EMITTER_ENTITY_ID,
        data={CONF_INFRARED_EMITTER_ENTITY_ID: EMITTER_ENTITY_ID},
    )


@pytest.fixture
def mock_config_entry_with_receiver() -> MockConfigEntry:
    """Return a config entry for the Electrolux AC that also uses a receiver."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Electrolux AC via Test emitter",
        unique_id=EMITTER_ENTITY_ID,
        data={
            CONF_INFRARED_EMITTER_ENTITY_ID: EMITTER_ENTITY_ID,
            CONF_INFRARED_RECEIVER_ENTITY_ID: RECEIVER_ENTITY_ID,
        },
    )


@pytest.fixture
def mock_setup_entry() -> Generator[None]:
    """Prevent the integration from actually being set up."""
    with patch(
        "custom_components.electrolux_infrared.async_setup_entry", return_value=True
    ):
        yield
