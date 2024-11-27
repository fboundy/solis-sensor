from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.select import SelectEntity

import asyncio
import logging

from .const import (
    DOMAIN,
    LAST_UPDATED,
)

from .service import ServiceSubscriber, InverterService
from .control_const import SolisBaseControlEntity, RETRIES, RETRY_WAIT, SELECT_TYPES

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities):
    """Setup sensors from a config entry created in the integrations UI."""
    # Prepare the sensor entities.
    plant_id = config_entry.data["portal_plant_id"]
    _LOGGER.debug(f"config_entry.data: {config_entry.data}")
    service = hass.data[DOMAIN][config_entry.entry_id]

    _LOGGER.info(f"Scheduling discovery of Select entities for plant {plant_id}")
    await asyncio.sleep(8)
    attempts = 0
    while (attempts < RETRIES) and (not service.has_controls):
        _LOGGER.debug(f"    Attempt {attempts} failed")
        await asyncio.sleep(RETRY_WAIT)
        attempts += 1

    if service.has_controls:
        entities = []
        _LOGGER.debug(f"Plant ID {plant_id} has controls:")
        for inverter_sn in service.controls:
            for cid in service.controls[inverter_sn]:
                if cid in SELECT_TYPES:
                    _LOGGER.debug(
                        f"Adding select entity {SELECT_TYPES[cid].name} for inverter Sn {inverter_sn} cid {cid}"
                    )
                    entities.append(
                        SolisSelectEntity(service, config_entry.data["name"], inverter_sn, cid, SELECT_TYPES[cid])
                    )

        if len(entities) > 0:
            _LOGGER.debug(f"Creating {len(entities)} sensor entities")
            async_add_entities(entities)
        else:
            _LOGGER.debug(f"No select controls found for Plant ID {plant_id}")

    else:
        _LOGGER.debug(f"No controls found for Plant ID {plant_id}")

    return True


class SolisSelectEntity(SolisBaseControlEntity, ServiceSubscriber, SelectEntity):
    def __init__(self, service: InverterService, config_name, inverter_sn, cid, select_info):
        super().__init__(service, config_name, inverter_sn, cid, select_info)
        self._option_dict = select_info.option_dict
        self._icon = select_info.icon
        self._attr_options = list(select_info.option_dict.values())
        self._attr_current_option = None
        # Subscribe to the service with the cid as the index
        service.subscribe(self, inverter_sn, cid)

    def do_update(self, value, last_updated):
        # When the data from the API chnages this method will be called with value as the new value
        # return super().do_update(value, last_updated)
        if self.hass and self._attr_current_option != value:
            self._attr_current_option = value
            self._attributes[LAST_UPDATED] = last_updated
            self.async_write_ha_state()
            return True
        return False
