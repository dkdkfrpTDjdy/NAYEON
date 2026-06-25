from src.approval import calculate_supply_amount, calculate_weight_95


def test_calculate_weight_95_round():
    assert calculate_weight_95(9649, "round") == 9167


def test_calculate_weight_95_floor():
    assert calculate_weight_95(9649, "floor") == 9166


def test_calculate_supply_amount():
    assert calculate_supply_amount(9649, 180) == 1736820
