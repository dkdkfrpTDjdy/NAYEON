from src.parser import normalize_date, normalize_number, extract_weight_candidates, choose_real_weight, extract_real_weight, extract_weight_95


def test_normalize_date():
    assert normalize_date("2025.03.04") == "2025-03-04"
    assert normalize_date("25-03-04") == "2025-03-04"


def test_normalize_number():
    assert normalize_number("9,649 kg") == 9649


def test_extract_weight_candidates():
    values = extract_weight_candidates("실중량 9,649 kg 95% 9,167 kg")
    assert 9649 in values
    assert 9167 in values


def test_choose_real_weight_default_first_plausible():
    assert choose_real_weight([9649, 9167]) == 9649


def test_labeled_weights():
    text = "실중량 9,649 kg 95% 중량 9,167 kg"
    values = extract_weight_candidates(text)
    assert extract_real_weight(text, values) == 9649
    assert extract_weight_95(text) == 9167
