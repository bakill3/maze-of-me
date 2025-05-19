import pytest
from utils.parsers import parse_height, parse_weight, parse_eu_date
from datetime import date

@pytest.mark.parametrize("inp,expected", [
    ("178", 178.00),
    ("1.78", 178.00),
    ("1,78m", 178.00),
    ("200cm", 200.00),
])
def test_parse_height_valid(inp, expected):
    assert parse_height(inp) == expected

@pytest.mark.parametrize("inp", ["2.5", "500", "29", "301"])
def test_parse_height_invalid(inp):
    with pytest.raises(ValueError):
        parse_height(inp)

@pytest.mark.parametrize("inp,expected", [
    ("70", 70.00),
    ("70kg", 70.00),
    ("70,5", 70.50),
])
def test_parse_weight_valid(inp, expected):
    assert parse_weight(inp) == expected

@pytest.mark.parametrize("inp", ["5", "600"])
def test_parse_weight_invalid(inp):
    with pytest.raises(ValueError):
        parse_weight(inp)

def test_parse_eu_date_valid():
    assert parse_eu_date("10-02-2000") == date(2000, 2, 10)

@pytest.mark.parametrize("inp", ["2000-02-10", "31-02-2000", "abc"])
def test_parse_eu_date_invalid(inp):
    with pytest.raises(ValueError):
        parse_eu_date(inp)
