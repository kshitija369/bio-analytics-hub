from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any

class BiometricProvider(ABC):
    """
    Abstract Base Class for all biometric data providers (Oura, Apple Health, etc.).
    """

    @abstractmethod
    def fetch_data(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """
        Fetches raw data from the provider's source.
        """
        pass

    @abstractmethod
    def transform_to_standard(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Standardizes raw data into a common format:
        {
            "ts": datetime (UTC),
            "metric": str,
            "val": float,
            "unit": str,
            "source": str,
            "tag": str
        }
        """
        pass
