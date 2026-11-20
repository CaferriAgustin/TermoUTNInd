"""Ciclo Rankine simple y con recalentamiento."""
from __future__ import annotations

from termograf.ciclos.ciclo import Ciclo
from termograf.core.state import State
from termograf.equipos import procesos as pr


def rankine(
    fluido: str = "Water",
    P_alta: float = 3e6,
    T_alta: float = 623.15,
    P_baja: float = 75e3,
    eta_turbina: float = 1.0,
    eta_bomba: float = 1.0,
    recalentamiento: tuple[float, float] | None = None,
) -> Ciclo:
    """Unidades SI (Pa, K). recalentamiento = (P_intermedia [Pa], T_recalentada [K])."""
    e1 = State.from_inputs(fluido, ("P", P_baja), ("Q", 0))
    pasos = [pr.bomba(e1, P_alta, eta_bomba)]
    pasos.append(pr.caldera(pasos[-1].salida, ("T", T_alta)))
    if recalentamiento:
        P_rec, T_rec = recalentamiento
        pasos.append(pr.turbina(pasos[-1].salida, P_rec, eta_turbina, "Turbina AP"))
        pasos.append(pr.isobarico(pasos[-1].salida, ("T", T_rec), "Recalentador"))
        pasos.append(pr.turbina(pasos[-1].salida, P_baja, eta_turbina, "Turbina BP"))
    else:
        pasos.append(pr.turbina(pasos[-1].salida, P_baja, eta_turbina))
    pasos.append(pr.condensador(pasos[-1].salida, ("Q", 0.0)))
    return Ciclo("Rankine con recalentamiento" if recalentamiento else "Rankine simple", pasos)
