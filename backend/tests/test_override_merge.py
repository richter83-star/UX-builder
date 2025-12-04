from decimal import Decimal
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.watchlist import merge_effective_rules
from app.models.schemas import UserRules, WatchlistOverride


def test_merge_uses_override_when_present():
    rules = UserRules(user_id="u1", alerts_enabled_default=True, edge_threshold_default=Decimal("0.03"))
    override = WatchlistOverride(
        user_id="u1",
        market_ticker="A",
        alerts_enabled=False,
        edge_threshold=Decimal("0.05"),
        min_liquidity=None,
    )
    effective = merge_effective_rules(rules, override)
    assert effective["alerts_enabled"] is False
    assert effective["edge_threshold"] == 0.05


def test_merge_falls_back_to_defaults():
    rules = UserRules(user_id="u1", alerts_enabled_default=True, edge_threshold_default=Decimal("0.04"), channels_json={"email": True})
    effective = merge_effective_rules(rules, None)
    assert effective["alerts_enabled"] is True
    assert effective["edge_threshold"] == 0.04
    assert effective["channels"] == {"email": True}
