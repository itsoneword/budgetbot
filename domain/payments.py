"""
Invoice payload codec for the AI-access paywall (T-023). Pure functions.

The invoice_payload string encodes the terms as sold ('ai:30' = 30-day pass,
'ai:perp' = perpetual), so a stale invoice paid after a config change still
grants exactly what its message advertised — the successful_payment handler
trusts the payload, never the current env config.
"""
from dataclasses import dataclass
from typing import Optional

_PREFIX = "ai:"
_PERPETUAL = "perp"


@dataclass(frozen=True)
class AIPurchaseTerms:
    """Terms sold with one invoice. duration_days=None = perpetual."""
    duration_days: Optional[int]


def encode_ai_payload(duration_days: Optional[int]) -> str:
    """Terms -> invoice_payload. None or 0 days sells perpetual access."""
    if not duration_days:
        return _PREFIX + _PERPETUAL
    if duration_days < 0:
        raise ValueError(f"duration_days must be >= 0, got {duration_days}")
    return f"{_PREFIX}{duration_days}"


def parse_ai_payload(payload: str) -> Optional[AIPurchaseTerms]:
    """invoice_payload -> terms, or None if the payload is not a valid
    AI-access payload (pre-checkout must then decline the purchase)."""
    if not isinstance(payload, str) or not payload.startswith(_PREFIX):
        return None
    terms = payload[len(_PREFIX):]
    if terms == _PERPETUAL:
        return AIPurchaseTerms(duration_days=None)
    if terms.isdigit() and int(terms) > 0:
        return AIPurchaseTerms(duration_days=int(terms))
    return None
