# TermoGraf propio

Simulador termodinámico didáctico (estados, procesos y ciclos) en Python, inspirado en TermoGraf (Unizar).

## Instalación (PowerShell)
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Uso
```powershell
pytest                              # validar contra tablas de vapor y ciclos de referencia
streamlit run termograf/ui/app.py   # abrir la app
```

## La app
- **Estados**: definí un estado con dos propiedades (T-P, P-x, T-x, P-h, P-s), guardalo con un nombre y verlo en T-s o P-h.
- **Procesos y equipos**: tomá un estado guardado y aplicale caldera, condensador, turbina, bomba/compresor, válvula o un proceso simple (isobárico, isotérmico, isoentálpico, isoentrópico, isocórico). Guarda la salida como estado nuevo.
- **Ciclos**: Rankine (simple o con recalentamiento, con rendimientos de turbina y bomba) o ciclo personalizado armando una tabla de equipos.

Convención: q = calor recibido por el fluido, w = trabajo entregado por el fluido (J/kg, flujo estacionario).

## Estructura
- `termograf/core`: `State` (SI internamente)
- `termograf/equipos`: `procesos.py` (caldera, condensador, turbina, bomba, válvula, proceso simple)
- `termograf/ciclos`: `ciclo.py` (clase `Ciclo`, ciclo desde tabla) y `rankine.py`
- `termograf/ui`: app Streamlit
- `tests`: validación
