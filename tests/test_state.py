import pytest

from termograf.core.state import State


def test_liquido_saturado_1bar():
    st = State.from_inputs("Water", ("P", 1e5), ("Q", 0))
    assert st.T_C == pytest.approx(99.61, abs=0.05)
    assert st.h_kJ == pytest.approx(417.5, abs=0.5)
    assert st.x == 0


def test_vapor_saturado_1bar():
    st = State.from_inputs("Water", ("P", 1e5), ("Q", 1))
    assert st.h_kJ == pytest.approx(2675.0, abs=1.0)
    assert st.s_kJ == pytest.approx(7.359, abs=0.01)


def test_vapor_sobrecalentado_10MPa_500C():
    st = State.from_inputs("Water", ("P", 10e6), ("T", 500 + 273.15))
    assert st.h_kJ == pytest.approx(3375.1, abs=1.0)
    assert st.s_kJ == pytest.approx(6.5995, abs=0.01)
    assert st.x is None


def test_mezcla_bifasica_desde_P_y_h():
    st = State.from_inputs("Water", ("P", 1e5), ("H", 1500e3))
    assert 0 < st.x < 1
    assert st.T_C == pytest.approx(99.61, abs=0.05)


def test_entradas_invalidas():
    with pytest.raises(ValueError):
        State.from_inputs("Water", ("P", 1e5), ("P", 2e5))
