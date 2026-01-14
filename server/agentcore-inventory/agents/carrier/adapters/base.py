# =============================================================================
# Shipping Adapter Base Interface
# =============================================================================
"""
Abstract base class for shipping carrier adapters.

This interface provides vendor-agnostic operations for:
- Getting shipping quotes
- Creating shipments
- Tracking shipments
- Generating labels

Implementations:
- PostalServiceAdapter: Real API integration (Correios via middleware)
- MockShippingAdapter: Test/development mock
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class QuoteResult:
    """Result from a shipping quote request."""
    carrier: str
    service: str
    service_code: str
    price: float
    delivery_days: int
    delivery_date: Optional[str] = None
    is_simulated: bool = False
    weight_limit_kg: float = 30.0
    available: bool = True
    reason: str = ""
    raw_response: Optional[Dict[str, Any]] = None


@dataclass
class TrackingEvent:
    """A single tracking event in shipment history."""
    timestamp: str
    status: str
    description: str
    location: Optional[str] = None
    details: Optional[str] = None


@dataclass
class TrackingResult:
    """Result from a tracking query."""
    tracking_code: str
    carrier: str
    status: str
    status_description: str
    is_delivered: bool = False
    delivery_date: Optional[str] = None
    estimated_delivery: Optional[str] = None
    events: List[TrackingEvent] = field(default_factory=list)
    is_simulated: bool = False
    raw_response: Optional[Dict[str, Any]] = None


@dataclass
class ShipmentResult:
    """Result from creating a shipment."""
    success: bool
    tracking_code: Optional[str] = None
    carrier: str = ""
    service: str = ""
    service_code: str = ""
    price: float = 0.0
    delivery_days: int = 0
    estimated_delivery: Optional[str] = None
    label_available: bool = False
    is_simulated: bool = False
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    errors: List[Dict[str, Any]] = field(default_factory=list)
    raw_response: Optional[Dict[str, Any]] = None


class ShippingAdapter(ABC):
    """
    Abstract base class for shipping carrier adapters.

    All carrier integrations must implement this interface to ensure
    consistent behavior across different shipping providers.
    """

    @property
    @abstractmethod
    def adapter_name(self) -> str:
        """Return the adapter name for logging/identification."""
        pass

    @property
    @abstractmethod
    def is_mock(self) -> bool:
        """Return True if this is a mock adapter."""
        pass

    @abstractmethod
    async def get_quotes(
        self,
        origin_cep: str,
        destination_cep: str,
        weight_grams: int,
        length_cm: int,
        width_cm: int,
        height_cm: int,
        declared_value: float,
    ) -> List[QuoteResult]:
        """
        Get shipping quotes without creating a shipment.

        Args:
            origin_cep: Origin postal code (8 digits, no formatting)
            destination_cep: Destination postal code (8 digits)
            weight_grams: Package weight in grams
            length_cm: Package length in centimeters
            width_cm: Package width in centimeters
            height_cm: Package height in centimeters
            declared_value: Declared value in BRL

        Returns:
            List of QuoteResult with available shipping options
        """
        pass

    @abstractmethod
    async def create_shipment(
        self,
        origin: Dict[str, Any],
        destination: Dict[str, Any],
        volumes: List[Dict[str, Any]],
        invoices: Optional[List[Dict[str, Any]]] = None,
        declared_value: float = 0.0,
        service_code: Optional[str] = None,
    ) -> ShipmentResult:
        """
        Create a shipment and get tracking code.

        Args:
            origin: Origin address dict with cep, city, state
            destination: Destination address dict with nome, endereco,
                        numero, cidade, uf, cep, telefone, email
            volumes: List of volume dicts with peso, altura, largura, comprimento
            invoices: Optional list of invoice dicts with numero, data, valor
            declared_value: Declared value for insurance
            service_code: Optional service code to force specific service

        Returns:
            ShipmentResult with tracking_code if successful
        """
        pass

    @abstractmethod
    async def track_shipment(
        self,
        tracking_code: str,
        full_details: bool = False,
    ) -> TrackingResult:
        """
        Track a shipment by tracking code.

        Args:
            tracking_code: The tracking code to query
            full_details: If True, request complete data with measurements

        Returns:
            TrackingResult with current status and history
        """
        pass

    @abstractmethod
    async def get_label(
        self,
        tracking_code: str,
        format: str = "pdf",
    ) -> bytes:
        """
        Get shipping label as binary data.

        Args:
            tracking_code: The tracking code for the label
            format: Output format ('pdf', 'zvp', etc.)

        Returns:
            Binary label data (PDF or ZVP)
        """
        pass

    @abstractmethod
    async def liberate_shipment(
        self,
        tracking_code: str,
    ) -> bool:
        """
        Liberate a shipment for tracking database access.

        Some APIs require a liberation step before tracking data
        becomes available. This method handles that step.

        Args:
            tracking_code: The tracking code to liberate

        Returns:
            True if liberation successful
        """
        pass

    async def health_check(self) -> Dict[str, Any]:
        """
        Check adapter health and API connectivity.

        Returns:
            Dict with 'healthy' bool and optional 'details'
        """
        return {
            "healthy": True,
            "adapter": self.adapter_name,
            "is_mock": self.is_mock,
        }
