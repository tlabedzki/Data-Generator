import numpy as np
import pytest

import func.data as d
import func.format as f
from func.customer import make_unique_emails


def test_probabilities_are_normalized():
    values, probabilities = d.get_param_list_and_normalized_probabilities({"a": 2, "b": 6})
    assert values == ["a", "b"]
    np.testing.assert_allclose(probabilities, [0.25, 0.75])


def test_probabilities_must_be_positive():
    with pytest.raises(ValueError):
        d.get_param_list_and_normalized_probabilities({"a": 0, "b": 0})


@pytest.mark.parametrize("price, expected", [(123.4, 129), (120, 129), (129, 129), (5, 9), (999.6, 1009)])
def test_round_to_9(price, expected):
    assert d.round_to_9(price) == expected


def test_remove_polish_accents():
    assert d.remove_polish_accents("Łukasz Żółć ąęśń") == "Lukasz Zolc aesn"


def test_make_unique_emails_adds_numbers_to_repeats():
    emails = ["jan.nowak@example.com", "jan.nowak@example.com", "jan.nowak2@example.com", "jan.nowak@example.com"]
    unique = make_unique_emails(emails)
    assert len(set(unique)) == len(unique)
    assert unique[0] == "jan.nowak@example.com"
    assert unique[1] == "jan.nowak3@example.com"
    assert unique[2] == "jan.nowak2@example.com"


def test_format_number():
    assert f.format_number(1234567) == "1 234 567"
    with pytest.raises(ValueError):
        f.format_number("12")
