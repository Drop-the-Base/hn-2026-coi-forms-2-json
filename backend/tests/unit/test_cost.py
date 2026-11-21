import pytest

from forms2json.domain.cost import CostRates


def test_cost_from_tokens_rates_and_gpu_time() -> None:
    rates = CostRates(per_1m_input_tokens=0.15, per_1m_output_tokens=0.60, per_gpu_second=0.01)

    # 0.15 * 2 + 0.60 * 0.5 + 0.01 * 10
    assert rates.total(2_000_000, 500_000, 10.0) == pytest.approx(0.7)


def test_zero_rates_cost_nothing() -> None:
    assert CostRates().total(10_000, 5_000, 3.0) == 0.0
