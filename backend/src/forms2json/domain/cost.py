from dataclasses import dataclass


@dataclass(frozen=True)
class CostRates:
    """Prices from config (NFR-13); a 0 rate means that part is not counted."""

    per_1m_input_tokens: float = 0.0
    per_1m_output_tokens: float = 0.0
    # Local models cost compute time, not an invoice (architecture §7).
    per_gpu_second: float = 0.0
    currency: str = "USD"

    def input_cost(self, tokens: int) -> float:
        return tokens * self.per_1m_input_tokens / 1_000_000

    def output_cost(self, tokens: int) -> float:
        return tokens * self.per_1m_output_tokens / 1_000_000

    def total(self, input_tokens: int, output_tokens: int, seconds: float) -> float:
        return (
            self.input_cost(input_tokens)
            + self.output_cost(output_tokens)
            + seconds * self.per_gpu_second
        )
