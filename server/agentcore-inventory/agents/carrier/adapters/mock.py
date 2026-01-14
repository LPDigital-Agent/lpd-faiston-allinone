# =============================================================================
# Mock Shipping Adapter (Testing Only)
# =============================================================================
"""
Mock adapter for testing CarrierAgent without real API calls.

This adapter returns simulated data for:
- Development and local testing
- CI/CD pipeline tests
- Demo environments

All responses include is_simulated=True flag.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from .base import (
    ShippingAdapter,
    QuoteResult,
    ShipmentResult,
    TrackingResult,
    TrackingEvent,
)

logger = logging.getLogger(__name__)


class MockShippingAdapter(ShippingAdapter):
    """Mock implementation for testing without real API calls."""

    def __init__(self):
        self._tracking_counter = 0
        logger.info("[MockShippingAdapter] Initialized mock adapter")

    @property
    def adapter_name(self) -> str:
        return "MockShippingAdapter"

    @property
    def is_mock(self) -> bool:
        return True

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
        """Return mock quotes for testing."""
        logger.debug(f"[MockShippingAdapter] get_quotes: {origin_cep} -> {destination_cep}")

        weight_kg = weight_grams / 1000
        today = datetime.utcnow()

        quotes = [
            QuoteResult(
                carrier="Correios",
                service="SEDEX",
                service_code="04162",
                price=45.00 + (weight_kg * 5),
                delivery_days=3,
                delivery_date=(today + timedelta(days=3)).strftime("%Y-%m-%d"),
                is_simulated=True,
                weight_limit_kg=30.0,
                available=weight_kg <= 30,
                reason="" if weight_kg <= 30 else "Peso excede limite",
            ),
            QuoteResult(
                carrier="Correios",
                service="PAC",
                service_code="04669",
                price=25.00 + (weight_kg * 3),
                delivery_days=7,
                delivery_date=(today + timedelta(days=7)).strftime("%Y-%m-%d"),
                is_simulated=True,
                weight_limit_kg=30.0,
                available=weight_kg <= 30,
                reason="" if weight_kg <= 30 else "Peso excede limite",
            ),
            QuoteResult(
                carrier="Correios",
                service="SEDEX 10",
                service_code="40215",
                price=85.00 + (weight_kg * 8),
                delivery_days=1,
                delivery_date=(today + timedelta(days=1)).strftime("%Y-%m-%d"),
                is_simulated=True,
                weight_limit_kg=10.0,
                available=weight_kg <= 10,
                reason="" if weight_kg <= 10 else "Peso excede limite",
            ),
        ]

        return quotes

    async def create_shipment(
        self,
        origin: Dict[str, Any],
        destination: Dict[str, Any],
        volumes: List[Dict[str, Any]],
        invoices: Optional[List[Dict[str, Any]]] = None,
        declared_value: float = 0.0,
        service_code: Optional[str] = None,
    ) -> ShipmentResult:
        """Return mock shipment result for testing."""
        logger.debug(f"[MockShippingAdapter] create_shipment to {destination.get('cidade')}")

        self._tracking_counter += 1
        mock_tracking = f"MOCK{self._tracking_counter:09d}BR"

        return ShipmentResult(
            success=True,
            tracking_code=mock_tracking,
            carrier="Correios",
            service="SEDEX",
            service_code="04162",
            price=45.00,
            delivery_days=3,
            estimated_delivery=(datetime.utcnow() + timedelta(days=3)).strftime("%Y-%m-%d"),
            label_available=True,
            is_simulated=True,
        )

    async def track_shipment(
        self,
        tracking_code: str,
        full_details: bool = False,
    ) -> TrackingResult:
        """Return mock tracking result for testing."""
        logger.debug(f"[MockShippingAdapter] track_shipment: {tracking_code}")

        now = datetime.utcnow()

        return TrackingResult(
            tracking_code=tracking_code,
            carrier="Correios",
            status="IN_TRANSIT",
            status_description="Objeto em transito - por favor aguarde",
            is_delivered=False,
            estimated_delivery=(now + timedelta(days=2)).strftime("%Y-%m-%d"),
            events=[
                TrackingEvent(
                    timestamp=(now - timedelta(days=1)).isoformat(),
                    status="POSTED",
                    description="Objeto postado",
                    location="SAO PAULO / SP",
                ),
                TrackingEvent(
                    timestamp=now.isoformat(),
                    status="IN_TRANSIT",
                    description="Objeto em transito",
                    location="CURITIBA / PR",
                ),
            ],
            is_simulated=True,
        )

    async def get_label(
        self,
        tracking_code: str,
        format: str = "pdf",
    ) -> bytes:
        """Return mock label data for testing."""
        logger.debug(f"[MockShippingAdapter] get_label: {tracking_code}")

        # Return minimal valid PDF
        mock_pdf = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
        return mock_pdf

    async def liberate_shipment(
        self,
        tracking_code: str,
    ) -> bool:
        """Mock liberation always succeeds."""
        logger.debug(f"[MockShippingAdapter] liberate_shipment: {tracking_code}")
        return True

    async def health_check(self) -> Dict[str, Any]:
        """Mock health check always healthy."""
        return {
            "healthy": True,
            "adapter": self.adapter_name,
            "is_mock": True,
            "note": "Mock adapter - no real API connectivity",
        }
