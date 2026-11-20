import pytest

from termograf.ciclos.ciclo import desde_tabla
from termograf.ciclos.rankine import rankine
from termograf.core.state import State
from termograf.equipos import procesos as pr


def test_turbina_isoentropica():
    e1 = State.from_inputs("Water", ("P", 10e6), ("T", 773.15))
    r = pr.turbina(e1, 1e5, 1.0)
    assert r.salida.s == pytest.approx(e1.s, rel=1e-6)
    assert r.w == pytest.approx(e1.h - r.salida.h)
    assert r.w > 0


def test_turbina_con_rendimiento():
    e1 = State.from_inputs("Water", ("P", 10e6), ("T", 773.15))
    ideal, real = pr.turbina(e1, 1e5, 1.0), pr.turbina(e1, 1e5, 0.8)
    assert real.w == pytest.approx(0.8 * ideal.w, rel=1e-6)
    assert real.salida.s > e1.s


def test_bomba_trabajo_aprox_v_dP():
    e1 = State.from_inputs("Water", ("P", 1e5), ("Q", 0))
    r = pr.bomba(e1, 10e5)
    assert r.w == pytest.approx(-e1.v * 9e5, rel=0.05)


def test_valvula_isoentalpica():
    e1 = State.from_inputs("Water", ("P", 10e5), ("Q", 0))
    r = pr.valvula(e1, 1e5)
    assert r.salida.h == pytest.approx(e1.h, rel=1e-9)
    assert r.salida.x is not None and 0 < r.salida.x < 1


def test_proceso_isocorico():
    e1 = State.from_inputs("Water", ("T", 400.0), ("P", 1e5))
    r = pr.proceso_simple(e1, "D", ("T", 500.0))
    assert r.salida.v == pytest.approx(e1.v, rel=1e-6)
    assert r.salida.T == pytest.approx(500.0)


def test_rankine_ideal_3MPa_350C_75kPa():
    c = rankine("Water", 3e6, 623.15, 75e3)
    assert c.cierra()
    assert c.eficiencia == pytest.approx(0.26, abs=0.01)
    assert c.w_neto == pytest.approx(c.q_entrada - c.q_salida, rel=1e-6)


def test_rankine_irreversibilidades_bajan_eficiencia():
    ideal = rankine("Water", 3e6, 623.15, 75e3)
    real = rankine("Water", 3e6, 623.15, 75e3, eta_turbina=0.85, eta_bomba=0.8)
    assert real.eficiencia < ideal.eficiencia


def test_rankine_recalentamiento_da_mas_trabajo():
    simple = rankine("Water", 10e6, 773.15, 10e3)
    rec = rankine("Water", 10e6, 773.15, 10e3, recalentamiento=(2e6, 773.15))
    assert rec.cierra() and rec.w_neto > simple.w_neto


def test_ciclo_desde_tabla_igual_a_rankine():
    e1 = State.from_inputs("Water", ("P", 75e3), ("Q", 0))
    filas = [
        {"equipo": "Bomba", "objetivo": "P salida [bar]", "valor": 30.0, "eta": 1.0},
        {"equipo": "Caldera", "objetivo": "T [°C]", "valor": 350.0, "eta": 1.0},
        {"equipo": "Turbina", "objetivo": "P salida [bar]", "valor": 0.75, "eta": 1.0},
        {"equipo": "Condensador", "objetivo": "x [-]", "valor": 0.0, "eta": 1.0},
    ]
    c = desde_tabla(e1, filas)
    assert c.eficiencia == pytest.approx(rankine("Water", 3e6, 623.15, 75e3).eficiencia, rel=1e-6)


def test_desde_tabla_errores():
    e1 = State.from_inputs("Water", ("P", 75e3), ("Q", 0))
    with pytest.raises(ValueError):
        desde_tabla(e1, [{"equipo": "Turbina", "objetivo": "T [°C]", "valor": 100, "eta": 1}])
