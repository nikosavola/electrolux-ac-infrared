"""Tests for the Electrolux Infrared climate entity."""

from typing import Any

from homeassistant.components.climate import (
    ATTR_FAN_MODE,
    ATTR_HVAC_MODE,
    ATTR_SWING_MODE,
    DOMAIN as CLIMATE_DOMAIN,
    SERVICE_SET_FAN_MODE,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_SWING_MODE,
    SERVICE_SET_TEMPERATURE,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_UNAVAILABLE,
)
from homeassistant.core import HomeAssistant, State
from homeassistant.exceptions import ServiceValidationError
from homeassistant.util.unit_system import (
    METRIC_SYSTEM,
    US_CUSTOMARY_SYSTEM,
    UnitSystem,
)
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    mock_restore_cache,
)

from custom_components.electrolux_infrared.electrolux_ac import (
    ElectroluxAcCommand,
    ElectroluxAcFanSpeed,
    ElectroluxAcMode,
)

from .conftest import (
    CLIMATE_ENTITY_ID,
    EMITTER_ENTITY_ID,
    MockEmitter,
    MockInfrared,
    MockReceiver,
)


@pytest.fixture
def emitter(mock_infrared: MockInfrared) -> MockEmitter:
    """Return the mock emitter the entity transmits through."""
    return mock_infrared.emitter


@pytest.fixture
def receiver(mock_infrared: MockInfrared) -> MockReceiver:
    """Return the mock receiver signals can be injected into."""
    return mock_infrared.receiver


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Set up the integration from a config entry."""
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def _service(hass: HomeAssistant, service: str, **data: Any) -> None:
    """Call a climate service on the entity under test."""
    await hass.services.async_call(
        CLIMATE_DOMAIN,
        service,
        {ATTR_ENTITY_ID: CLIMATE_ENTITY_ID, **data},
        blocking=True,
    )


async def _call(
    hass: HomeAssistant, emitter: MockEmitter, service: str, **data: Any
) -> ElectroluxAcCommand:
    """Call a climate service and return the single command it transmitted."""
    before = len(emitter.commands)
    await _service(hass, service, **data)

    assert len(emitter.commands) == before + 1
    command = emitter.commands[-1]
    assert isinstance(command, ElectroluxAcCommand)
    return command


def _state(hass: HomeAssistant) -> State:
    """Return the state of the entity under test."""
    state = hass.states.get(CLIMATE_ENTITY_ID)
    assert state is not None
    return state


@pytest.mark.usefixtures("mock_infrared")
async def test_entity_setup(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """The climate entity is created and starts out off."""
    await _setup(hass, mock_config_entry)

    state = _state(hass)
    assert state.state == HVACMode.OFF
    assert state.attributes[ATTR_FAN_MODE] == "auto"
    assert state.attributes[ATTR_SWING_MODE] == "off"
    assert state.attributes[ATTR_TEMPERATURE] == 24.0
    assert state.attributes["assumed_state"] is True
    assert state.attributes["min_temp"] == 16.0
    assert state.attributes["max_temp"] == 32.0


@pytest.mark.usefixtures("mock_infrared")
async def test_unload(hass: HomeAssistant, mock_config_entry: MockConfigEntry) -> None:
    """Unloading the entry makes the climate entity unavailable."""
    await _setup(hass, mock_config_entry)

    assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
    assert _state(hass).state == STATE_UNAVAILABLE


@pytest.mark.parametrize(
    ("hvac_mode", "expected_mode"),
    [
        pytest.param(HVACMode.HEAT_COOL, ElectroluxAcMode.AUTO, id="heat_cool"),
        pytest.param(HVACMode.COOL, ElectroluxAcMode.COOL, id="cool"),
        pytest.param(HVACMode.HEAT, ElectroluxAcMode.HEAT, id="heat"),
        pytest.param(HVACMode.DRY, ElectroluxAcMode.DRY, id="dry"),
        pytest.param(HVACMode.FAN_ONLY, ElectroluxAcMode.FAN_ONLY, id="fan_only"),
    ],
)
async def test_set_hvac_mode(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    emitter: MockEmitter,
    hvac_mode: HVACMode,
    expected_mode: ElectroluxAcMode,
) -> None:
    """Setting an HVAC mode transmits it and powers the unit on."""
    await _setup(hass, mock_config_entry)

    command = await _call(
        hass, emitter, SERVICE_SET_HVAC_MODE, **{ATTR_HVAC_MODE: hvac_mode}
    )

    assert command.mode is expected_mode
    assert command.power is True
    assert _state(hass).state == hvac_mode


async def test_turn_off(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, emitter: MockEmitter
) -> None:
    """Turning off clears the power bit and resets the assumed swing mode."""
    await _setup(hass, mock_config_entry)
    await _call(hass, emitter, SERVICE_SET_HVAC_MODE, **{ATTR_HVAC_MODE: HVACMode.COOL})

    command = await _call(hass, emitter, SERVICE_TURN_OFF)

    assert command.power is False
    assert command.mode is ElectroluxAcMode.AUTO
    assert command.swing is False
    state = _state(hass)
    assert state.state == HVACMode.OFF
    # The unit swings vertically again after a power cycle.
    assert state.attributes[ATTR_SWING_MODE] == "vertical"


async def test_turn_on_restores_last_mode(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, emitter: MockEmitter
) -> None:
    """Turning on returns the unit to the mode it last ran in."""
    await _setup(hass, mock_config_entry)
    await _call(hass, emitter, SERVICE_SET_HVAC_MODE, **{ATTR_HVAC_MODE: HVACMode.HEAT})
    await _call(hass, emitter, SERVICE_TURN_OFF)

    command = await _call(hass, emitter, SERVICE_TURN_ON)

    assert command.mode is ElectroluxAcMode.HEAT
    assert command.power is True
    assert _state(hass).state == HVACMode.HEAT


async def test_set_temperature(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, emitter: MockEmitter
) -> None:
    """Setting a temperature transmits it with the current mode."""
    await _setup(hass, mock_config_entry)
    await _call(hass, emitter, SERVICE_SET_HVAC_MODE, **{ATTR_HVAC_MODE: HVACMode.COOL})

    command = await _call(
        hass, emitter, SERVICE_SET_TEMPERATURE, **{ATTR_TEMPERATURE: 19}
    )

    assert command.temperature == 19
    assert command.mode is ElectroluxAcMode.COOL
    assert _state(hass).attributes[ATTR_TEMPERATURE] == 19.0


async def test_set_temperature_with_hvac_mode(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, emitter: MockEmitter
) -> None:
    """A temperature can be set together with a mode in one call."""
    await _setup(hass, mock_config_entry)

    command = await _call(
        hass,
        emitter,
        SERVICE_SET_TEMPERATURE,
        **{ATTR_TEMPERATURE: 27, ATTR_HVAC_MODE: HVACMode.HEAT},
    )

    assert command.temperature == 27
    assert command.mode is ElectroluxAcMode.HEAT
    state = _state(hass)
    assert state.state == HVACMode.HEAT
    assert state.attributes[ATTR_TEMPERATURE] == 27.0


async def test_set_temperature_off_resets_swing(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, emitter: MockEmitter
) -> None:
    """Switching off through set_temperature resets swing like turning off does."""
    await _setup(hass, mock_config_entry)
    await _call(hass, emitter, SERVICE_SET_HVAC_MODE, **{ATTR_HVAC_MODE: HVACMode.COOL})
    await _call(hass, emitter, SERVICE_SET_SWING_MODE, **{ATTR_SWING_MODE: "off"})

    command = await _call(
        hass,
        emitter,
        SERVICE_SET_TEMPERATURE,
        **{ATTR_TEMPERATURE: 20, ATTR_HVAC_MODE: HVACMode.OFF},
    )

    assert command.power is False
    state = _state(hass)
    assert state.state == HVACMode.OFF
    assert state.attributes[ATTR_SWING_MODE] == "vertical"


async def test_set_temperature_with_unsupported_hvac_mode(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, emitter: MockEmitter
) -> None:
    """A mode the unit does not have is rejected before anything is transmitted."""
    await _setup(hass, mock_config_entry)

    with pytest.raises(ServiceValidationError):
        await _service(
            hass,
            SERVICE_SET_TEMPERATURE,
            **{ATTR_TEMPERATURE: 20, ATTR_HVAC_MODE: HVACMode.AUTO},
        )

    assert emitter.commands == []


@pytest.mark.parametrize(
    ("fan_mode", "expected_fan"),
    [
        pytest.param("auto", ElectroluxAcFanSpeed.AUTO, id="auto"),
        pytest.param("low", ElectroluxAcFanSpeed.LOW, id="low"),
        pytest.param("medium", ElectroluxAcFanSpeed.MEDIUM, id="medium"),
        pytest.param("high", ElectroluxAcFanSpeed.HIGH, id="high"),
    ],
)
async def test_set_fan_mode(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    emitter: MockEmitter,
    fan_mode: str,
    expected_fan: ElectroluxAcFanSpeed,
) -> None:
    """Setting a fan mode transmits the matching fan speed."""
    await _setup(hass, mock_config_entry)
    await _call(hass, emitter, SERVICE_SET_HVAC_MODE, **{ATTR_HVAC_MODE: HVACMode.COOL})

    command = await _call(
        hass, emitter, SERVICE_SET_FAN_MODE, **{ATTR_FAN_MODE: fan_mode}
    )

    assert command.fan is expected_fan
    assert _state(hass).attributes[ATTR_FAN_MODE] == fan_mode


@pytest.mark.parametrize(
    ("hvac_mode", "requested_fan_mode", "expected_fan_mode"),
    [
        pytest.param(HVACMode.DRY, "high", "low", id="dry-forces-low"),
        pytest.param(HVACMode.FAN_ONLY, "auto", "low", id="fan-only-has-no-auto"),
        pytest.param(HVACMode.FAN_ONLY, "high", "high", id="fan-only-keeps-high"),
        pytest.param(HVACMode.COOL, "auto", "auto", id="cool-keeps-auto"),
    ],
)
async def test_fan_mode_coercion(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    emitter: MockEmitter,
    hvac_mode: HVACMode,
    requested_fan_mode: str,
    expected_fan_mode: str,
) -> None:
    """Fan speeds the unit ignores in a mode are replaced by the one it uses."""
    await _setup(hass, mock_config_entry)
    await _call(hass, emitter, SERVICE_SET_HVAC_MODE, **{ATTR_HVAC_MODE: hvac_mode})

    command = await _call(
        hass, emitter, SERVICE_SET_FAN_MODE, **{ATTR_FAN_MODE: requested_fan_mode}
    )

    assert command.fan is ElectroluxAcFanSpeed[expected_fan_mode.upper()]
    assert _state(hass).attributes[ATTR_FAN_MODE] == expected_fan_mode


@pytest.mark.parametrize(
    ("swing_mode", "expected_swing"),
    [
        pytest.param("vertical", True, id="vertical"),
        pytest.param("off", False, id="off"),
    ],
)
async def test_set_swing_mode(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    emitter: MockEmitter,
    swing_mode: str,
    expected_swing: bool,
) -> None:
    """Setting a swing mode transmits it."""
    await _setup(hass, mock_config_entry)
    await _call(hass, emitter, SERVICE_SET_HVAC_MODE, **{ATTR_HVAC_MODE: HVACMode.COOL})

    command = await _call(
        hass, emitter, SERVICE_SET_SWING_MODE, **{ATTR_SWING_MODE: swing_mode}
    )

    assert command.swing is expected_swing
    assert _state(hass).attributes[ATTR_SWING_MODE] == swing_mode


@pytest.mark.parametrize(
    ("service", "data", "attribute", "expected"),
    [
        pytest.param(
            SERVICE_SET_FAN_MODE,
            {ATTR_FAN_MODE: "high"},
            ATTR_FAN_MODE,
            "high",
            id="fan-mode",
        ),
        pytest.param(
            SERVICE_SET_SWING_MODE,
            {ATTR_SWING_MODE: "vertical"},
            ATTR_SWING_MODE,
            "vertical",
            id="swing-mode",
        ),
        pytest.param(
            SERVICE_SET_TEMPERATURE,
            {ATTR_TEMPERATURE: 21},
            ATTR_TEMPERATURE,
            21.0,
            id="temperature",
        ),
    ],
)
async def test_settings_while_off_are_not_transmitted(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    emitter: MockEmitter,
    service: str,
    data: dict[str, Any],
    attribute: str,
    expected: str | float,
) -> None:
    """Adjusting a setting on a unit that is off stores it without firing the LED."""
    await _setup(hass, mock_config_entry)

    await _service(hass, service, **data)

    assert emitter.commands == []
    state = _state(hass)
    assert state.state == HVACMode.OFF
    assert state.attributes[attribute] == expected


@pytest.mark.parametrize(
    ("units", "restored_temperature", "expected_celsius"),
    [
        pytest.param(METRIC_SYSTEM, 28.0, 28, id="metric"),
        pytest.param(US_CUSTOMARY_SYSTEM, 72.0, 22, id="us-customary"),
        pytest.param(US_CUSTOMARY_SYSTEM, 120.0, 32, id="clamped-to-max"),
    ],
)
async def test_state_is_restored(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    emitter: MockEmitter,
    units: UnitSystem,
    restored_temperature: float,
    expected_celsius: int,
) -> None:
    """The assumed state survives a restart, as the AC cannot be read back."""
    hass.config.units = units
    mock_restore_cache(
        hass,
        [
            State(
                CLIMATE_ENTITY_ID,
                HVACMode.HEAT,
                {
                    ATTR_FAN_MODE: "medium",
                    ATTR_SWING_MODE: "vertical",
                    ATTR_TEMPERATURE: restored_temperature,
                },
            )
        ],
    )
    await _setup(hass, mock_config_entry)

    state = _state(hass)
    assert state.state == HVACMode.HEAT
    assert state.attributes[ATTR_FAN_MODE] == "medium"
    assert state.attributes[ATTR_SWING_MODE] == "vertical"

    command = await _call(
        hass, emitter, SERVICE_SET_SWING_MODE, **{ATTR_SWING_MODE: "off"}
    )
    assert command.temperature == expected_celsius
    assert command.mode is ElectroluxAcMode.HEAT
    assert command.fan is ElectroluxAcFanSpeed.MEDIUM


@pytest.mark.usefixtures("mock_infrared")
async def test_becomes_unavailable_with_the_emitter(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """The entity follows the availability of the infrared emitter."""
    await _setup(hass, mock_config_entry)

    hass.states.async_set(EMITTER_ENTITY_ID, STATE_UNAVAILABLE)
    await hass.async_block_till_done()

    assert _state(hass).state == STATE_UNAVAILABLE


async def test_receiver_updates_state(
    hass: HomeAssistant,
    mock_config_entry_with_receiver: MockConfigEntry,
    receiver: MockReceiver,
) -> None:
    """A frame from the physical remote updates the assumed state."""
    await _setup(hass, mock_config_entry_with_receiver)

    receiver.emit(
        ElectroluxAcCommand(
            mode=ElectroluxAcMode.DRY,
            temperature=18,
            fan=ElectroluxAcFanSpeed.LOW,
            swing=True,
        ).get_raw_timings()
    )
    await hass.async_block_till_done()

    state = _state(hass)
    assert state.state == HVACMode.DRY
    assert state.attributes[ATTR_TEMPERATURE] == 18.0
    assert state.attributes[ATTR_FAN_MODE] == "low"
    assert state.attributes[ATTR_SWING_MODE] == "vertical"


async def test_receiver_power_off(
    hass: HomeAssistant,
    mock_config_entry_with_receiver: MockConfigEntry,
    emitter: MockEmitter,
    receiver: MockReceiver,
) -> None:
    """A power-off frame from the remote turns the entity off."""
    await _setup(hass, mock_config_entry_with_receiver)
    await _call(hass, emitter, SERVICE_SET_HVAC_MODE, **{ATTR_HVAC_MODE: HVACMode.COOL})
    await _call(hass, emitter, SERVICE_SET_SWING_MODE, **{ATTR_SWING_MODE: "off"})

    receiver.emit(
        ElectroluxAcCommand(
            mode=ElectroluxAcMode.AUTO,
            temperature=24,
            fan=ElectroluxAcFanSpeed.AUTO,
            power=False,
        ).get_raw_timings()
    )
    await hass.async_block_till_done()

    state = _state(hass)
    assert state.state == HVACMode.OFF
    # A power-off frame carries no swing setting; the unit comes back vertical.
    assert state.attributes[ATTR_SWING_MODE] == "vertical"


async def test_receiver_ignores_foreign_signal(
    hass: HomeAssistant,
    mock_config_entry_with_receiver: MockConfigEntry,
    emitter: MockEmitter,
    receiver: MockReceiver,
) -> None:
    """A signal that is not an Electrolux AC frame leaves the state alone."""
    await _setup(hass, mock_config_entry_with_receiver)
    await _call(hass, emitter, SERVICE_SET_HVAC_MODE, **{ATTR_HVAC_MODE: HVACMode.COOL})

    receiver.emit([9000, -4500, 560, -1690, 560, -560])
    await hass.async_block_till_done()

    assert _state(hass).state == HVACMode.COOL
