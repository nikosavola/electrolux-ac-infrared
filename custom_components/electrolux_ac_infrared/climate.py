"""Climate platform for Electrolux air conditioners controlled over infrared."""

from typing import Any, override

from homeassistant.components.climate import (
    ATTR_FAN_MODE,
    ATTR_HVAC_MODE,
    ATTR_SWING_MODE,
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    SWING_OFF,
    SWING_VERTICAL,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.components.infrared import (
    InfraredEmitterConsumerEntity,
    InfraredReceivedSignal,
    InfraredReceiverConsumerEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_TEMPERATURE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util.unit_conversion import TemperatureConverter

from .const import (
    CONF_INFRARED_EMITTER_ENTITY_ID,
    CONF_INFRARED_RECEIVER_ENTITY_ID,
    DOMAIN,
)
from .electrolux_ac import (
    MAX_TEMP,
    MIN_TEMP,
    ElectroluxAcCommand,
    ElectroluxAcFanSpeed,
    ElectroluxAcMode,
)

PARALLEL_UPDATES = 1

_DEFAULT_TEMPERATURE = 24.0

_HA_MODE_TO_LIB: dict[HVACMode, ElectroluxAcMode] = {
    HVACMode.HEAT_COOL: ElectroluxAcMode.AUTO,
    HVACMode.COOL: ElectroluxAcMode.COOL,
    HVACMode.HEAT: ElectroluxAcMode.HEAT,
    HVACMode.DRY: ElectroluxAcMode.DRY,
    HVACMode.FAN_ONLY: ElectroluxAcMode.FAN_ONLY,
}
_LIB_MODE_TO_HA: dict[ElectroluxAcMode, HVACMode] = {
    lib: ha for ha, lib in _HA_MODE_TO_LIB.items()
}

_HA_FAN_TO_LIB: dict[str, ElectroluxAcFanSpeed] = {
    FAN_AUTO: ElectroluxAcFanSpeed.AUTO,
    FAN_LOW: ElectroluxAcFanSpeed.LOW,
    FAN_MEDIUM: ElectroluxAcFanSpeed.MEDIUM,
    FAN_HIGH: ElectroluxAcFanSpeed.HIGH,
}
_LIB_FAN_TO_HA: dict[ElectroluxAcFanSpeed, str] = {
    lib: ha for ha, lib in _HA_FAN_TO_LIB.items()
}


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Electrolux AC climate entity from a config entry."""
    emitter_entity_id = entry.data[CONF_INFRARED_EMITTER_ENTITY_ID]
    if receiver_entity_id := entry.data.get(CONF_INFRARED_RECEIVER_ENTITY_ID):
        async_add_entities([
            ElectroluxAcClimateWithReceiver(
                entry, emitter_entity_id, receiver_entity_id
            )
        ])
    else:
        async_add_entities([ElectroluxAcClimate(entry, emitter_entity_id)])


class ElectroluxAcClimate(InfraredEmitterConsumerEntity, ClimateEntity, RestoreEntity):
    """Electrolux air conditioner controlled through an infrared emitter."""

    _attr_name = None
    _attr_has_entity_name = True
    _attr_assumed_state = True
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 1.0
    _attr_min_temp = float(MIN_TEMP)
    _attr_max_temp = float(MAX_TEMP)
    _attr_hvac_modes = [
        HVACMode.OFF,
        HVACMode.HEAT_COOL,
        HVACMode.COOL,
        HVACMode.HEAT,
        HVACMode.DRY,
        HVACMode.FAN_ONLY,
    ]
    _attr_fan_modes = [FAN_AUTO, FAN_LOW, FAN_MEDIUM, FAN_HIGH]
    _attr_swing_modes = [SWING_OFF, SWING_VERTICAL]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.SWING_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(self, entry: ConfigEntry, emitter_entity_id: str) -> None:
        """Initialize the Electrolux AC climate entity."""
        self._infrared_emitter_entity_id = emitter_entity_id
        self._attr_unique_id = entry.entry_id
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_target_temperature = _DEFAULT_TEMPERATURE
        self._attr_fan_mode = FAN_AUTO
        self._attr_swing_mode = SWING_OFF
        self._last_on_hvac_mode = HVACMode.COOL
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer="Electrolux",
            name=entry.title,
        )

    @override
    async def async_added_to_hass(self) -> None:
        """Restore the assumed state, as infrared cannot read it back from the AC."""
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state is None or last_state.state in {
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        }:
            return

        if last_state.state in self._attr_hvac_modes:
            self._attr_hvac_mode = HVACMode(last_state.state)
            if self._attr_hvac_mode is not HVACMode.OFF:
                self._last_on_hvac_mode = self._attr_hvac_mode
        if (fan_mode := last_state.attributes.get(ATTR_FAN_MODE)) in _HA_FAN_TO_LIB:
            self._attr_fan_mode = fan_mode
        if (swing_mode := last_state.attributes.get(ATTR_SWING_MODE)) in {
            SWING_OFF,
            SWING_VERTICAL,
        }:
            self._attr_swing_mode = swing_mode
        if (temperature := last_state.attributes.get(ATTR_TEMPERATURE)) is not None:
            # The restored attribute is in the unit the frontend displays, which is not
            # necessarily the Celsius the protocol speaks.
            self._attr_target_temperature = _clamp_temperature(
                TemperatureConverter.convert(
                    float(temperature),
                    self.hass.config.units.temperature_unit,
                    UnitOfTemperature.CELSIUS,
                )
            )

    @override
    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set the HVAC mode."""
        await self._async_apply(hvac_mode=hvac_mode)

    @override
    async def async_turn_on(self) -> None:
        """Turn the air conditioner on, restoring the last mode it ran in."""
        await self._async_apply(hvac_mode=self._last_on_hvac_mode)

    @override
    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set the target temperature, switching the HVAC mode when one is given."""
        if (hvac_mode := kwargs.get(ATTR_HVAC_MODE)) is not None:
            self._valid_mode_or_raise("hvac", hvac_mode, self.hvac_modes)
        await self._async_apply(
            hvac_mode=hvac_mode, temperature=float(kwargs[ATTR_TEMPERATURE])
        )

    @override
    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set the fan mode."""
        await self._async_apply(fan_mode=fan_mode)

    @override
    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set the swing mode."""
        await self._async_apply(swing_mode=swing_mode)

    async def _async_apply(
        self,
        *,
        hvac_mode: HVACMode | None = None,
        temperature: float | None = None,
        fan_mode: str | None = None,
        swing_mode: str | None = None,
    ) -> None:
        """Transmit the given settings on top of the current ones, then adopt them.

        Every frame carries the full state, so each service call resends everything.
        """
        switching_mode = hvac_mode is not None
        if hvac_mode is None:
            hvac_mode = self._attr_hvac_mode or HVACMode.OFF
        if temperature is None:
            temperature = self._attr_target_temperature or _DEFAULT_TEMPERATURE
        if swing_mode is None:
            swing_mode = self._attr_swing_mode or SWING_OFF
        fan_mode = _coerce_fan_mode(
            hvac_mode, fan_mode or self._attr_fan_mode or FAN_AUTO
        )
        # The protocol only carries whole degrees, so the entity must not claim a
        # target it did not transmit.
        temperature = float(round(_clamp_temperature(temperature)))

        power = hvac_mode is not HVACMode.OFF
        # Adjusting a setting on a unit that is off is a preference change: remember it
        # for the next power-on rather than firing a frame that keeps it off.
        transmitted = power or switching_mode
        if transmitted:
            await self._send_command(
                ElectroluxAcCommand(
                    # A power-off frame carries the operating mode the remote sends
                    # with it, the auto mode rather than the one the unit was running.
                    mode=_HA_MODE_TO_LIB[hvac_mode] if power else ElectroluxAcMode.AUTO,
                    temperature=int(temperature),
                    fan=_HA_FAN_TO_LIB[fan_mode],
                    # The unit only ever swings vertically, and powering it off
                    # disables swing along with everything else.
                    swing=power and swing_mode == SWING_VERTICAL,
                    power=power,
                )
            )

        self._attr_hvac_mode = hvac_mode
        self._attr_target_temperature = temperature
        self._attr_fan_mode = fan_mode
        if power:
            self._last_on_hvac_mode = hvac_mode
        # The unit comes back with vertical swing after a power cycle, so the assumed
        # swing mode follows it even though the power-off frame disables swing.
        self._attr_swing_mode = (
            SWING_VERTICAL if transmitted and not power else swing_mode
        )
        self.async_write_ha_state()


class ElectroluxAcClimateWithReceiver(
    ElectroluxAcClimate, InfraredReceiverConsumerEntity
):
    """Electrolux AC climate entity that also tracks an infrared receiver."""

    def __init__(
        self, entry: ConfigEntry, emitter_entity_id: str, receiver_entity_id: str
    ) -> None:
        """Initialize the Electrolux AC climate entity with a receiver."""
        super().__init__(entry, emitter_entity_id)
        self._infrared_receiver_entity_id = receiver_entity_id

    @override
    @callback
    def _handle_signal(self, signal: InfraredReceivedSignal) -> None:
        """Update the assumed state from a physical remote signal."""
        command = ElectroluxAcCommand.from_raw_timings(signal.timings)
        if command is None:
            return

        if command.power:
            self._attr_hvac_mode = _LIB_MODE_TO_HA[command.mode]
            self._last_on_hvac_mode = self._attr_hvac_mode
            self._attr_swing_mode = SWING_VERTICAL if command.swing else SWING_OFF
        else:
            self._attr_hvac_mode = HVACMode.OFF
            # A power-off frame always disables swing, but the unit comes back
            # vertical, so it says nothing about the swing mode to assume.
            self._attr_swing_mode = SWING_VERTICAL

        self._attr_target_temperature = float(command.temperature)
        self._attr_fan_mode = _LIB_FAN_TO_HA[command.fan]
        self.async_write_ha_state()


def _clamp_temperature(temperature: float) -> float:
    """Clamp a temperature to what the protocol can express."""
    return min(float(MAX_TEMP), max(float(MIN_TEMP), temperature))


def _coerce_fan_mode(hvac_mode: HVACMode, fan_mode: str) -> str:
    """Return the fan mode the unit actually runs at in the given HVAC mode.

    Dry mode always runs the fan at low, and fan-only mode has no auto speed.

    Returns:
        The fan mode that will actually be sent, given the requested one.

    """
    if hvac_mode is HVACMode.DRY:
        return FAN_LOW
    if hvac_mode is HVACMode.FAN_ONLY and fan_mode == FAN_AUTO:
        return FAN_LOW
    return fan_mode
