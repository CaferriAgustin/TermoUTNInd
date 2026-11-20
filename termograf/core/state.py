"""Estado termodinámico de una sustancia pura. Unidades internas: SI (K, Pa, J/kg)."""
from __future__ import annotations

from dataclasses import dataclass

from CoolProp.CoolProp import PropsSI

_VALID = {"T", "P", "H", "S", "Q", "D"}


@dataclass(frozen=True)
class State:
    fluid: str
    T: float  # K
    P: float  # Pa
    h: float  # J/kg
    s: float  # J/(kg K)
    x: float | None  # título; None si no es mezcla bifásica
    v: float  # volumen específico, m3/kg

    @classmethod
    def from_inputs(cls, fluid: str, in1: tuple[str, float], in2: tuple[str, float]) -> "State":
        """Crea el estado a partir de dos propiedades independientes.

        Claves: T [K], P [Pa], H [J/kg], S [J/(kg K)], Q (título, 0-1), D [kg/m3].
        Ejemplo: State.from_inputs("Water", ("P", 1e5), ("Q", 0))
        """
        (k1, v1), (k2, v2) = in1, in2
        k1, k2 = k1.upper(), k2.upper()
        if k1 == k2 or not {k1, k2} <= _VALID:
            raise ValueError(f"Par de propiedades inválido: {k1}, {k2}")

        T = PropsSI("T", k1, v1, k2, v2, fluid)
        P = PropsSI("P", k1, v1, k2, v2, fluid)
        h = PropsSI("H", k1, v1, k2, v2, fluid)
        s = PropsSI("S", k1, v1, k2, v2, fluid)
        v = 1.0 / PropsSI("D", k1, v1, k2, v2, fluid)

        if "Q" in (k1, k2):
            x = v1 if k1 == "Q" else v2
        elif P < PropsSI("Pcrit", fluid):
            hl = PropsSI("H", "P", P, "Q", 0, fluid)
            hv = PropsSI("H", "P", P, "Q", 1, fluid)
            x = (h - hl) / (hv - hl) if hl < h < hv else None
        else:
            x = None
        return cls(fluid, T, P, h, s, x, v)

    # Conveniencia en unidades de uso común
    @property
    def T_C(self) -> float:
        return self.T - 273.15

    @property
    def P_bar(self) -> float:
        return self.P / 1e5

    @property
    def h_kJ(self) -> float:
        return self.h / 1e3

    @property
    def s_kJ(self) -> float:
        return self.s / 1e3

    @property
    def rho(self) -> float:
        return 1.0 / self.v
