"""Equipos y procesos en flujo estacionario, por unidad de masa.

Convenciones (J/kg): q = calor RECIBIDO por el fluido, w = trabajo ENTREGADO por el fluido.
Balance de energía: q - w = h_salida - h_entrada.
"""
from __future__ import annotations

from dataclasses import dataclass

from termograf.core.state import State


@dataclass(frozen=True)
class Resultado:
    nombre: str
    entrada: State
    salida: State
    q: float | None = None  # None en procesos simples (no se define el balance)
    w: float | None = None

    @property
    def dh(self) -> float:
        return self.salida.h - self.entrada.h

    @property
    def ds(self) -> float:
        return self.salida.s - self.entrada.s


def isobarico(entrada: State, objetivo: tuple[str, float], nombre: str = "Calentador") -> Resultado:
    """Calentador/enfriador sin trabajo de eje. P se mantiene; objetivo = ("T"|"H"|"Q", valor SI)."""
    salida = State.from_inputs(entrada.fluid, ("P", entrada.P), objetivo)
    return Resultado(nombre, entrada, salida, q=salida.h - entrada.h, w=0.0)


def caldera(entrada: State, objetivo: tuple[str, float]) -> Resultado:
    return isobarico(entrada, objetivo, "Caldera")


def condensador(entrada: State, objetivo: tuple[str, float] = ("Q", 0.0)) -> Resultado:
    return isobarico(entrada, objetivo, "Condensador")


def _adiabatico(entrada: State, P_salida: float, eta: float, expansion: bool, nombre: str) -> Resultado:
    if not 0 < eta <= 1:
        raise ValueError("El rendimiento isoentrópico debe estar en (0, 1]")
    if expansion and P_salida >= entrada.P:
        raise ValueError(f"{nombre}: la presión de salida debe ser menor que la de entrada")
    if not expansion and P_salida <= entrada.P:
        raise ValueError(f"{nombre}: la presión de salida debe ser mayor que la de entrada")
    ideal = State.from_inputs(entrada.fluid, ("P", P_salida), ("S", entrada.s))
    if expansion:
        h2 = entrada.h - eta * (entrada.h - ideal.h)
    else:
        h2 = entrada.h + (ideal.h - entrada.h) / eta
    salida = State.from_inputs(entrada.fluid, ("P", P_salida), ("H", h2))
    return Resultado(nombre, entrada, salida, q=0.0, w=entrada.h - h2)


def turbina(entrada: State, P_salida: float, eta_s: float = 1.0, nombre: str = "Turbina") -> Resultado:
    return _adiabatico(entrada, P_salida, eta_s, True, nombre)


def bomba(entrada: State, P_salida: float, eta_s: float = 1.0, nombre: str = "Bomba") -> Resultado:
    """Bomba o compresor (w resulta negativo: se entrega trabajo al fluido)."""
    return _adiabatico(entrada, P_salida, eta_s, False, nombre)


def valvula(entrada: State, P_salida: float) -> Resultado:
    """Laminación isoentálpica."""
    if P_salida >= entrada.P:
        raise ValueError("Válvula: la presión de salida debe ser menor que la de entrada")
    salida = State.from_inputs(entrada.fluid, ("P", P_salida), ("H", entrada.h))
    return Resultado("Válvula", entrada, salida, q=0.0, w=0.0)


_MANTIENE = {"P": lambda e: e.P, "T": lambda e: e.T, "H": lambda e: e.h, "S": lambda e: e.s, "D": lambda e: e.rho}


def proceso_simple(entrada: State, mantiene: str, objetivo: tuple[str, float]) -> Resultado:
    """Proceso que mantiene una propiedad (P, T, H, S o D) y fija otra del estado final.

    Solo define el estado final y las variaciones dh y ds; no calcula q ni w.
    """
    mantiene = mantiene.upper()
    if mantiene not in _MANTIENE:
        raise ValueError(f"No se puede mantener constante: {mantiene}")
    salida = State.from_inputs(entrada.fluid, (mantiene, _MANTIENE[mantiene](entrada)), objetivo)
    nombres = {"P": "isobárico", "T": "isotérmico", "H": "isoentálpico", "S": "isoentrópico", "D": "isocórico"}
    return Resultado(f"Proceso {nombres[mantiene]}", entrada, salida)
