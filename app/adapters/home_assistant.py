import os
import requests
from typing import Dict, Any, Optional

class HomeAssistantAdapter:
    """
    Client for Home Assistant API to control environmental variables
    (Lighting, Temperature) based on biological state.
    """
    def __init__(self):
        self.host = os.environ.get("HOME_ASSISTANT_HOST")
        self.token = os.environ.get("HOME_ASSISTANT_TOKEN")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def is_configured(self) -> bool:
        return bool(self.host and self.token)

    def set_light_kelvin(self, entity_id: str, kelvin: int):
        """Sets the color temperature of a light (Kelvin)."""
        if not self.is_configured(): return
        
        url = f"{self.host}/api/services/light/turn_on"
        payload = {
            "entity_id": entity_id,
            "kelvin": kelvin
        }
        try:
            requests.post(url, json=payload, headers=self.headers, timeout=5)
            print(f"--- [HomeAssistant] Light {entity_id} set to {kelvin}K ---")
        except Exception as e:
            print(f"--- [HomeAssistant Error] Light control failed: {e} ---")

    def set_temperature(self, entity_id: str, temperature: float):
        """Sets the thermostat target temperature."""
        if not self.is_configured(): return

        url = f"{self.host}/api/services/climate/set_temperature"
        payload = {
            "entity_id": entity_id,
            "temperature": temperature
        }
        try:
            requests.post(url, json=payload, headers=self.headers, timeout=5)
            print(f"--- [HomeAssistant] Climate {entity_id} set to {temperature}° ---")
        except Exception as e:
            print(f"--- [HomeAssistant Error] Temperature control failed: {e} ---")
