"""Static model catalogue for OpenCode Go.

Why static instead of fetched at runtime?

- the UI must work offline, before any API call;
- a typo in a model id would otherwise only fail at generation time;
- pricing and capabilities are needed to display an estimate *before* the call.

The catalogue mirrors https://opencode.ai/v2/docs/console/go/ (prices in USD
per 1M tokens). Update it when the provider adds or removes models.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ModelInfo:
    id: str
    label: str
    note: str
    context_window: int
    max_output: int
    input_price: float
    output_price: float
    supports_temperature: bool = True
    tags: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_free(self) -> bool:
        return self.input_price == 0 and self.output_price == 0

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "label": self.label,
            "note": self.note,
            "context_window": self.context_window,
            "max_output": self.max_output,
            "pricing": {
                "input_per_million": self.input_price,
                "output_per_million": self.output_price,
            },
            "supports_temperature": self.supports_temperature,
            "free": self.is_free,
            "tags": list(self.tags),
        }


MODELS: tuple[ModelInfo, ...] = (
    ModelInfo(
        id="deepseek-v4.1-flash",
        label="DeepSeek V4.1 Flash",
        note="Rapide et très bon marché, à l’aise en français.",
        context_window=1_000_000,
        max_output=384_000,
        input_price=0.15,
        output_price=0.60,
        tags=("scoring", "letter", "economique"),
    ),
    ModelInfo(
        id="claude-haiku-5-5",
        label="Claude Haiku 5.5",
        note="Excellent rapport qualité/prix pour la rédaction.",
        context_window=1_000_000,
        max_output=128_000,
        input_price=0.10,
        output_price=0.50,
        supports_temperature=False,
        tags=("scoring", "letter", "recommandé"),
    ),
    ModelInfo(
        id="gpt-6-luna",
        label="GPT-6 Luna",
        note="Bon équilibre entre style et coût.",
        context_window=1_050_000,
        max_output=128_000,
        input_price=0.10,
        output_price=0.50,
        tags=("scoring", "letter"),
    ),
    ModelInfo(
        id="glm-5.3-flash",
        label="GLM-5.3-Flash",
        note="Très économique, correct pour le scoring.",
        context_window=1_000_000,
        max_output=131_072,
        input_price=0.15,
        output_price=0.50,
        tags=("scoring",),
    ),
    ModelInfo(
        id="minimax-m3.1-flash",
        label="MiniMax M3.1 Flash",
        note="Rapide, adapté aux jugements courts et structurés.",
        context_window=1_000_000,
        max_output=512_000,
        input_price=0.15,
        output_price=0.60,
        tags=("scoring",),
    ),
    ModelInfo(
        id="qwen3.7-plus",
        label="Qwen3.7 Plus",
        note="Bonne qualité rédactionnelle, tarif intermédiaire.",
        context_window=1_000_000,
        max_output=65_536,
        input_price=0.40,
        output_price=1.60,
        tags=("letter",),
    ),
    ModelInfo(
        id="deepseek-v4-pro",
        label="DeepSeek V4 Pro",
        note="Plus lent et plus cher, utile pour comparer les sorties.",
        context_window=1_000_000,
        max_output=384_000,
        input_price=0.66,
        output_price=1.98,
        tags=("letter",),
    ),
    ModelInfo(
        id="kimi-k3.1-pro",
        label="Kimi K3.1 Pro",
        note="Haut de gamme, à réserver aux lettres importantes.",
        context_window=1_048_576,
        max_output=131_072,
        input_price=2.00,
        output_price=10.00,
        supports_temperature=False,
        tags=("letter",),
    ),
    ModelInfo(
        id="gemini-4-argon",
        label="Gemini 4 Argon",
        note="Haut de gamme, bon sur les textes longs.",
        context_window=1_048_576,
        max_output=65_536,
        input_price=2.00,
        output_price=10.00,
        supports_temperature=False,
        tags=("letter",),
    ),
    ModelInfo(
        id="grok-4.7",
        label="Grok 4.7",
        note="Alternatif haut de gamme pour comparer le style.",
        context_window=500_000,
        max_output=500_000,
        input_price=2.00,
        output_price=6.00,
        tags=("letter",),
    ),
    ModelInfo(
        id="longcat-2.5-free",
        label="LongCat 2.5 Free",
        note="Gratuit et limité dans le temps : parfait pour les tests.",
        context_window=1_000_000,
        max_output=262_144,
        input_price=0.0,
        output_price=0.0,
        supports_temperature=False,
        tags=("scoring", "free"),
    ),
    ModelInfo(
        id="beam-free",
        label="Beam Free",
        note="Gratuit et limité dans le temps.",
        context_window=1_048_576,
        max_output=131_072,
        input_price=0.0,
        output_price=0.0,
        tags=("scoring", "free"),
    ),
)

MODELS_BY_ID: dict[str, ModelInfo] = {model.id: model for model in MODELS}


def get_model(model_id: str) -> ModelInfo | None:
    return MODELS_BY_ID.get(model_id)


def is_known_model(model_id: str) -> bool:
    return model_id in MODELS_BY_ID


def estimate_cost_usd(model_id: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Cost estimate in USD.

    Approximation: the provider bills cached reads and peak/off-peak rates
    differently. This is enough to spot an expensive configuration, not to
    reconcile an invoice.
    """
    model = get_model(model_id)
    if model is None:
        return 0.0
    return round(
        (prompt_tokens / 1_000_000) * model.input_price
        + (completion_tokens / 1_000_000) * model.output_price,
        8,
    )


def public_catalog() -> list[dict[str, object]]:
    return [model.to_dict() for model in MODELS]
