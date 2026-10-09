from datetime import UTC, datetime, timedelta

import pytest

from app.agent.confirmation import parse_confirmation
from app.agent.decision import sanitize_decision
from app.llm.grounding import ungrounded_numbers
from app.llm.types import OrderItem, RouteDecision
from app.order.lifecycle import fulfilment_status
from app.order.policy import check_eligibility
from app.order.pricing import build_cart, stock_shortfalls
from app.product.catalog import load_catalog
from app.product.repository import keyword_query

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
LAPTOP = {"id": "probook-15", "name": "ProBook 15", "category": "laptops", "price_cents": 129999, "stock": 5}
CABLE = {"id": "usb-c", "name": "USB-C Cable", "category": "accessories", "price_cents": 1999, "stock": 50}


def _order(created_at: datetime, category: str = "accessories", status: str = "placed") -> dict:
    return {"id": "ORD-1000", "status": status, "created_at": created_at, "lines": [{"category": category}]}


class TestPricing:
    def test_total_includes_tax_and_free_shipping_over_threshold(self) -> None:
        cart = build_cart([(LAPTOP, 2)])
        assert cart["subtotal_cents"] == 259998
        assert cart["shipping_cents"] == 0
        assert cart["tax_cents"] == 20800
        assert cart["total_cents"] == 280798

    def test_flat_shipping_below_threshold(self) -> None:
        cart = build_cart([(CABLE, 1)])
        assert cart["shipping_cents"] == 599
        assert cart["total_cents"] == 1999 + 599 + 160

    def test_cart_hash_changes_when_price_changes(self) -> None:
        original = build_cart([(LAPTOP, 1)])
        discounted = build_cart([({**LAPTOP, "price_cents": 99999}, 1)])
        assert original["cart_hash"] == build_cart([(LAPTOP, 1)])["cart_hash"]
        assert original["cart_hash"] != discounted["cart_hash"]

    def test_stock_shortfall_reported_for_excess_quantity(self) -> None:
        assert stock_shortfalls([(LAPTOP, 6)]) == ["ProBook 15 (only 5 in stock)"]
        assert stock_shortfalls([(LAPTOP, 5)]) == []


class TestLifecycle:
    def test_stages_follow_the_demo_clock(self) -> None:
        assert fulfilment_status(NOW, NOW + timedelta(minutes=1)).stage == "processing"
        assert fulfilment_status(NOW, NOW + timedelta(minutes=5)).stage == "shipped"
        assert fulfilment_status(NOW, NOW + timedelta(minutes=11)).stage == "delivered"


class TestReturnPolicy:
    def test_processing_order_can_be_cancelled(self) -> None:
        result = check_eligibility(_order(NOW), "cancel", NOW + timedelta(minutes=1))
        assert result.allowed and result.clause == "§1"

    def test_shipped_order_cannot_be_cancelled(self) -> None:
        result = check_eligibility(_order(NOW), "cancel", NOW + timedelta(minutes=5))
        assert not result.allowed and result.clause == "§1"

    def test_undelivered_order_cannot_be_returned(self) -> None:
        assert not check_eligibility(_order(NOW), "return", NOW + timedelta(minutes=5)).allowed

    def test_accessory_returnable_within_thirty_days(self) -> None:
        result = check_eligibility(_order(NOW), "return", NOW + timedelta(days=20))
        assert result.allowed and result.clause == "§2"

    def test_laptop_return_outside_fifteen_day_window_cites_clause_three(self) -> None:
        result = check_eligibility(_order(NOW, category="laptops"), "return", NOW + timedelta(days=16))
        assert not result.allowed
        assert result.clause == "§3"
        assert "15-day" in result.reason

    def test_cancelled_order_is_not_eligible_again(self) -> None:
        assert not check_eligibility(_order(NOW, status="cancelled"), "cancel", NOW).allowed


class TestConfirmationParsing:
    @pytest.mark.parametrize("reply", ["yes", "Yes please!", "sure, go ahead", "ok place it", "confirm"])
    def test_affirmative_replies_confirm(self, reply: str) -> None:
        assert parse_confirmation(reply) == "confirm"

    @pytest.mark.parametrize("reply", ["no", "No thanks", "cancel it", "don't"])
    def test_negative_replies_cancel(self, reply: str) -> None:
        assert parse_confirmation(reply) == "cancel"

    @pytest.mark.parametrize("reply", ["hmm", "hmm, not sure", "what colour is it?", "yes... no wait"])
    def test_ambiguous_replies_are_unclear(self, reply: str) -> None:
        assert parse_confirmation(reply) == "unclear"


class TestGrounding:
    EVIDENCE = '- UltraBook 13 Air: $999.99 | 13.3" display, 8GB RAM, fanless, 1.1kg\n§5 Free over $50.00.'

    def test_misstated_spec_is_flagged(self) -> None:
        assert ungrounded_numbers("The UltraBook 13 Air weighs 1.3kg.", self.EVIDENCE) == ["1.3"]

    def test_invented_price_is_flagged(self) -> None:
        assert ungrounded_numbers("Only $1.00 today!", self.EVIDENCE) == ["1.00"]

    def test_clause_numbers_do_not_vouch_for_amounts(self) -> None:
        assert ungrounded_numbers("Now just $5!", "§5 Shipping is free.") == ["5"]

    def test_numbers_from_evidence_pass_in_any_format(self) -> None:
        answer = "The UltraBook 13 Air is $999.99, weighs 1.1kg, ships free over $50 [§5]."
        assert ungrounded_numbers(answer, self.EVIDENCE) == []


class TestDecisionSanitizing:
    def test_unknown_ids_and_filter_values_are_dropped(self) -> None:
        raw = RouteDecision(
            on_topic=True,
            skill="order",
            category="LAPTOPS",
            brand="Acme",
            max_price=-5,
            items=[
                OrderItem(product_id="probook-15", quantity=99),
                OrderItem(product_id="ghost", quantity=1),
            ],
            order_id="ord-1000; drop table",
        )
        clean = sanitize_decision(raw, load_catalog())
        assert clean["filters"]["category"] == "laptops"
        assert clean["filters"]["brand"] is None
        assert clean["filters"]["max_price_cents"] is None
        assert clean["items"] == [{"product_id": "probook-15", "quantity": 10}]
        assert clean["order_id"] is None


def test_keyword_query_or_joins_tokens_and_drops_punctuation() -> None:
    assert keyword_query("Wireless headphones, under $100!") == "wireless | headphones | under | 100"
