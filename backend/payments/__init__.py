"""Payment adapter stub — wire a real gateway later without changing order flow."""
from __future__ import annotations

from abc import ABC, abstractmethod

from flask import current_app


class PaymentProvider(ABC):
    @abstractmethod
    def create_checkout(self, order_id: str, amount: float, currency: str) -> dict:
        ...

    @abstractmethod
    def is_enabled(self) -> bool:
        ...


class NoopPaymentProvider(PaymentProvider):
    def is_enabled(self) -> bool:
        return False

    def create_checkout(self, order_id: str, amount: float, currency: str) -> dict:
        return {
            "enabled": False,
            "provider": "noop",
            "order_id": order_id,
            "amount": amount,
            "currency": currency,
            "message": "Payments not configured. Set PAYMENTS_ENABLED and a gateway provider later.",
        }


def get_payment_provider() -> PaymentProvider:
    return NoopPaymentProvider()


def payments_status() -> dict:
    provider = get_payment_provider()
    enabled = bool(current_app.config.get("PAYMENTS_ENABLED")) and provider.is_enabled()
    return {
        "enabled": enabled,
        "provider": "noop",
        "currency": current_app.config.get("CURRENCY", "PKR"),
    }
