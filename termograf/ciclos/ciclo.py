"""Ciclos como secuencia de equipos, y construcción desde una tabla de pasos."""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from termograf.core.state import State
from termograf.equipos import procesos as pr


@dataclass
class Ciclo:
    nombre: str
    pasos: list[pr.Resultado]

    @property
    def estados(self) -> list[State]:
        return [self.pasos[0].entrada] + [p.salida for p in self.pasos]

    @property
    def w_neto(self) -> float:
        return sum(p.w for p in self.pasos)

    @property
    def q_entrada(self) -> float:
        return sum(p.q for p in self.pasos if p.q > 0)

    @property
    def q_salida(self) -> float:
        return -sum(p.q for p in self.pasos if p.q < 0)

    @property
    def eficiencia(self) -> float:
        return self.w_neto / self.q_entrada if self.q_entrada > 0 else math.nan

    def cierra(self) -> bool:
        a, b = self.estados[0], self.estados[-1]
        return abs(a.h - b.h) < 500 and abs(a.P - b.P) < 1e-4 * a.P


def trayectoria(res: pr.Resultado, n: int = 25) -> list[tuple[float, float, float, float]]:
    """Puntos (s kJ/kgK, T °C, h kJ/kg, P bar) para dibujar el paso en los diagramas."""
    a, b = res.entrada, res.salida
    pts = [(a.s_kJ, a.T_C, a.h_kJ, a.P_bar)]
    if abs(a.P - b.P) <= 1e-6 * a.P:  # isobárico: se muestrea el camino real
        for h in np.linspace(a.h, b.h, n)[1:-1]:
            try:
                e = State.from_inputs(a.fluid, ("P", a.P), ("H", float(h)))
                pts.append((e.s_kJ, e.T_C, e.h_kJ, e.P_bar))
            except ValueError:
                pass
    pts.append((b.s_kJ, b.T_C, b.h_kJ, b.P_bar))
    return pts


ISOBARICOS = ("Caldera", "Calentador", "Recalentador", "Condensador", "Enfriador")
ADIABATICOS = ("Turbina", "Bomba", "Compresor", "Válvula")
EQUIPOS = ISOBARICOS + ADIABATICOS
OBJ_ISOBARICO = {"T [°C]": ("T", lambda v: v + 273.15), "h [kJ/kg]": ("H", lambda v: v * 1e3), "x [-]": ("Q", float)}
OBJ_PSALIDA = "P salida [bar]"


def desde_tabla(inicio: State, filas: list[dict], nombre: str = "Ciclo personalizado") -> Ciclo:
    """Arma un ciclo desde filas {equipo, objetivo, valor, eta} (unidades de usuario: °C, bar, kJ/kg)."""
    if not filas:
        raise ValueError("Agregá al menos un paso")
    pasos, actual = [], inicio
    for i, f in enumerate(filas, start=1):
        eq, obj, val = f["equipo"], f["objetivo"], float(f["valor"])
        eta = f.get("eta")
        eta = 1.0 if eta is None or (isinstance(eta, float) and math.isnan(eta)) else float(eta)
        if eq in ISOBARICOS:
            if obj not in OBJ_ISOBARICO:
                raise ValueError(f"Paso {i} ({eq}): el objetivo debe ser T, h o x")
            clave, conv = OBJ_ISOBARICO[obj]
            res = pr.isobarico(actual, (clave, conv(val)), eq)
        elif eq in ADIABATICOS:
            if obj != OBJ_PSALIDA:
                raise ValueError(f"Paso {i} ({eq}): el objetivo debe ser P salida [bar]")
            if eq == "Turbina":
                res = pr.turbina(actual, val * 1e5, eta)
            elif eq in ("Bomba", "Compresor"):
                res = pr.bomba(actual, val * 1e5, eta, eq)
            else:
                res = pr.valvula(actual, val * 1e5)
        else:
            raise ValueError(f"Paso {i}: equipo desconocido ({eq})")
        pasos.append(res)
        actual = res.salida
    return Ciclo(nombre, pasos)
