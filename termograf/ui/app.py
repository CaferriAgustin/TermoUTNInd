"""App Streamlit: definir estados, procesos y ciclos."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from CoolProp.CoolProp import PropsSI

from termograf.ciclos.ciclo import EQUIPOS, ISOBARICOS, OBJ_ISOBARICO, OBJ_PSALIDA, desde_tabla, trayectoria
from termograf.ciclos.rankine import rankine
from termograf.core.state import State
from termograf.equipos import procesos as pr

st.set_page_config(page_title="TermoGraf propio", layout="wide")

FLUIDOS = ["Water", "R134a", "Ammonia", "CO2"]
MAG = {"T [°C]": "T", "P [bar]": "P", "h [kJ/kg]": "H", "s [kJ/kg·K]": "S", "x [-]": "Q"}
# par -> (clave1, etiqueta1, valor inicial 1, clave2, etiqueta2, valor inicial 2)
PARES = {
    "T y P": ("T", "T [°C]", 20.0, "P", "P [bar]", 1.0),
    "P y x": ("P", "P [bar]", 1.0, "Q", "x [-]", 0.0),
    "T y x": ("T", "T [°C]", 100.0, "Q", "x [-]", 0.5),
    "P y h": ("P", "P [bar]", 1.0, "H", "h [kJ/kg]", 1500.0),
    "P y s": ("P", "P [bar]", 1.0, "S", "s [kJ/kg·K]", 6.0),
}
TIPOS = [
    "Caldera / calentador", "Condensador / enfriador", "Turbina", "Bomba / compresor",
    "Válvula (isoentálpica)", "Proceso simple (mantiene una propiedad)",
]

if "estados" not in st.session_state:
    st.session_state.estados = {}


def a_SI(clave: str, valor: float) -> float:
    return {"T": valor + 273.15, "P": valor * 1e5, "H": valor * 1e3, "S": valor * 1e3, "Q": valor, "D": valor}[clave]


@st.cache_data
def domo(fluido: str, tipo: str):
    T = np.linspace(PropsSI("Ttriple", fluido) + 1, PropsSI("Tcrit", fluido) - 0.01, 200)
    if tipo == "T-s":
        sl = [PropsSI("S", "T", t, "Q", 0, fluido) / 1e3 for t in T]
        sv = [PropsSI("S", "T", t, "Q", 1, fluido) / 1e3 for t in T]
        return sl, list(T - 273.15), sv, list(T - 273.15)
    P = [PropsSI("P", "T", t, "Q", 0, fluido) / 1e5 for t in T]
    hl = [PropsSI("H", "T", t, "Q", 0, fluido) / 1e3 for t in T]
    hv = [PropsSI("H", "T", t, "Q", 1, fluido) / 1e3 for t in T]
    return hl, P, hv, P


def figura(fluido, tipo, estados, caminos=()):
    xl, yl, xv, yv = domo(fluido, tipo)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xl, y=yl, name="Líquido sat.", line=dict(color="#3a9bb5")))
    fig.add_trace(go.Scatter(x=xv, y=yv, name="Vapor sat.", line=dict(color="#d68a2f")))
    ix, iy = (0, 1) if tipo == "T-s" else (2, 3)
    for cam in caminos:
        fig.add_trace(go.Scatter(x=[p[ix] for p in cam], y=[p[iy] for p in cam], mode="lines",
                                 line=dict(color="#888", width=2), showlegend=False, hoverinfo="skip"))
    if estados:
        xs = [e.s_kJ if tipo == "T-s" else e.h_kJ for e in estados.values()]
        ys = [e.T_C if tipo == "T-s" else e.P_bar for e in estados.values()]
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="markers+text", text=list(estados), textposition="top center",
                                 name="Estados", marker=dict(size=11, color="#c2527a")))
    fig.update_layout(title=f"Diagrama {tipo} · {fluido}", margin=dict(t=50, b=10),
                      xaxis_title="s [kJ/kg·K]" if tipo == "T-s" else "h [kJ/kg]",
                      yaxis_title="T [°C]" if tipo == "T-s" else "P [bar]")
    if tipo == "P-h":
        fig.update_yaxes(type="log")
    return fig


def tabla_estados(estados: dict) -> pd.DataFrame:
    return pd.DataFrame([{
        "Estado": n, "T [°C]": round(e.T_C, 2), "P [bar]": round(e.P_bar, 4), "h [kJ/kg]": round(e.h_kJ, 2),
        "s [kJ/kg·K]": round(e.s_kJ, 4), "x": None if e.x is None else round(e.x, 4),
        "v [m³/kg]": float(f"{e.v:.5g}"),
    } for n, e in estados.items()])


def sig_nombre() -> str:
    return str(len(st.session_state.estados) + 1)


def mostrar_ciclo(c, clave):
    if not c.cierra():
        st.warning("El ciclo no cierra: el último estado no coincide con el inicial.")
    m = st.columns(4)
    m[0].metric("w neto [kJ/kg]", f"{c.w_neto / 1e3:.1f}")
    m[1].metric("q entrada [kJ/kg]", f"{c.q_entrada / 1e3:.1f}")
    m[2].metric("q salida [kJ/kg]", f"{c.q_salida / 1e3:.1f}")
    m[3].metric("Rendimiento térmico", f"{c.eficiencia * 100:.2f} %")
    st.dataframe(pd.DataFrame([{
        "Paso": p.nombre, "q [kJ/kg]": round(p.q / 1e3, 2), "w [kJ/kg]": round(p.w / 1e3, 2),
        "Δh [kJ/kg]": round(p.dh / 1e3, 2), "Δs [kJ/kg·K]": round(p.ds / 1e3, 4),
    } for p in c.pasos]), hide_index=True)
    est = c.estados[:-1] if c.cierra() else c.estados
    nombres = {str(i + 1): e for i, e in enumerate(est)}
    tipo = st.radio("Diagrama", ["T-s", "P-h"], horizontal=True, key=f"{clave}-diag")
    st.plotly_chart(figura(est[0].fluid, tipo, nombres, [trayectoria(p) for p in c.pasos]), width="stretch")
    st.dataframe(tabla_estados(nombres), hide_index=True)
    pref = st.text_input("Prefijo para guardar los estados en la pestaña Estados", value="C", key=f"{clave}-pref")
    if st.button("Guardar estados del ciclo", key=f"{clave}-guardar"):
        for n, e in nombres.items():
            st.session_state.estados[f"{pref}{n}"] = e
        st.success(f"Guardados {len(nombres)} estados ({pref}1…{pref}{len(nombres)}).")


st.title("TermoGraf propio")
t1, t2, t3 = st.tabs(["Estados", "Procesos y equipos", "Ciclos"])

# ---------------------------------------------------------------- Estados
with t1:
    c_in, c_out = st.columns([1, 2])
    with c_in:
        fluido = st.selectbox("Fluido", FLUIDOS, key="e-fluido")
        par = st.selectbox("Propiedades conocidas", list(PARES), key="e-par")
        k1, e1, d1, k2, e2, d2 = PARES[par]
        v1 = st.number_input(e1, value=d1, key=f"e-{par}-1")
        v2 = st.number_input(e2, value=d2, key=f"e-{par}-2")
        nuevo = None
        try:
            nuevo = State.from_inputs(fluido, (k1, a_SI(k1, v1)), (k2, a_SI(k2, v2)))
            m = st.columns(2)
            m[0].metric("T [°C]", f"{nuevo.T_C:.2f}")
            m[1].metric("P [bar]", f"{nuevo.P_bar:.3f}")
            m[0].metric("h [kJ/kg]", f"{nuevo.h_kJ:.2f}")
            m[1].metric("s [kJ/kg·K]", f"{nuevo.s_kJ:.4f}")
            m[0].metric("x", "—" if nuevo.x is None else f"{nuevo.x:.3f}")
            m[1].metric("v [m³/kg]", f"{nuevo.v:.5g}")
        except Exception as e:
            st.error(f"No se pudo calcular el estado: {e}")
        nombre = st.text_input("Nombre del estado", value=sig_nombre(), key=f"e-nombre-{sig_nombre()}")
        if st.button("Guardar estado", disabled=nuevo is None):
            st.session_state.estados[nombre] = nuevo
            st.rerun()
    with c_out:
        guardados = st.session_state.estados
        tipo = st.radio("Diagrama", ["T-s", "P-h"], horizontal=True, key="e-diag")
        mostrar = dict(guardados)
        if nuevo is not None:
            mostrar["(nuevo)"] = nuevo
        st.plotly_chart(figura(fluido, tipo, {n: e for n, e in mostrar.items() if e.fluid == fluido}), width="stretch")
        if guardados:
            st.dataframe(tabla_estados(guardados), hide_index=True)
            b1, b2 = st.columns(2)
            borrar = b1.selectbox("Eliminar estado", list(guardados), key="e-borrar")
            if b1.button("Eliminar"):
                del st.session_state.estados[borrar]
                st.rerun()
            if b2.button("Vaciar todos"):
                st.session_state.estados = {}
                st.rerun()

# ---------------------------------------------------------------- Procesos
with t2:
    guardados = st.session_state.estados
    if not guardados:
        st.info("Primero guardá al menos un estado en la pestaña Estados.")
    else:
        c_in, c_out = st.columns([1, 2])
        with c_in:
            ent = st.selectbox("Estado de entrada", list(guardados), key="p-ent")
            e0 = guardados[ent]
            tipo_p = st.selectbox("Equipo o proceso", TIPOS, key="p-tipo")
            res = None
            try:
                if tipo_p.startswith(("Caldera", "Condensador")):
                    nom = "Caldera" if tipo_p.startswith("Caldera") else "Condensador"
                    et = st.selectbox("Estado final: propiedad conocida (P se mantiene)", list(OBJ_ISOBARICO), key=f"p-{nom}-et")
                    val = st.number_input(et, value=0.0 if nom == "Condensador" else e0.T_C + 100, key=f"p-{nom}-{et}")
                    res = pr.isobarico(e0, (MAG[et], a_SI(MAG[et], val)), nom)
                elif tipo_p.startswith(("Turbina", "Bomba")):
                    nom = "Turbina" if tipo_p.startswith("Turbina") else "Bomba"
                    P2 = st.number_input("P salida [bar]", value=max(e0.P_bar / 10, 0.05) if nom == "Turbina" else e0.P_bar * 10,
                                         key=f"p-{nom}-P")
                    eta = st.number_input("Rendimiento isoentrópico", 0.05, 1.0, 1.0, 0.05, key=f"p-{nom}-eta")
                    res = pr.turbina(e0, P2 * 1e5, eta) if nom == "Turbina" else pr.bomba(e0, P2 * 1e5, eta)
                elif tipo_p.startswith("Válvula"):
                    P2 = st.number_input("P salida [bar]", value=max(e0.P_bar / 10, 0.05), key="p-val-P")
                    res = pr.valvula(e0, P2 * 1e5)
                else:
                    mant = st.selectbox("Propiedad constante", ["P", "T", "H", "S", "D"], key="p-mant",
                                        format_func=lambda k: {"P": "P (isobárico)", "T": "T (isotérmico)", "H": "h (isoentálpico)",
                                                               "S": "s (isoentrópico)", "D": "ρ (isocórico)"}[k])
                    et = st.selectbox("Estado final: propiedad conocida", list(MAG), key="p-simple-et")
                    val = st.number_input(et, value=1.0, key=f"p-simple-{et}")
                    res = pr.proceso_simple(e0, mant, (MAG[et], a_SI(MAG[et], val)))
            except Exception as e:
                st.error(f"No se pudo calcular: {e}")
        with c_out:
            if res is not None:
                m = st.columns(4)
                m[0].metric("q [kJ/kg]", "—" if res.q is None else f"{res.q / 1e3:.2f}")
                m[1].metric("w [kJ/kg]", "—" if res.w is None else f"{res.w / 1e3:.2f}")
                m[2].metric("Δh [kJ/kg]", f"{res.dh / 1e3:.2f}")
                m[3].metric("Δs [kJ/kg·K]", f"{res.ds / 1e3:.4f}")
                st.caption("q: calor recibido por el fluido. w: trabajo entregado por el fluido. Flujo estacionario, por kg.")
                tipo = st.radio("Diagrama", ["T-s", "P-h"], horizontal=True, key="p-diag")
                st.plotly_chart(figura(e0.fluid, tipo, {ent: res.entrada, "(salida)": res.salida}, [trayectoria(res)]), width="stretch")
                n_out = st.text_input("Guardar el estado de salida como", value=sig_nombre(), key=f"p-nombre-{sig_nombre()}")
                if st.button("Guardar estado de salida"):
                    st.session_state.estados[n_out] = res.salida
                    st.rerun()

# ---------------------------------------------------------------- Ciclos
with t3:
    modo = st.radio("Ciclo", ["Rankine", "Personalizado"], horizontal=True, key="c-modo")
    if modo == "Rankine":
        c1, c2, c3 = st.columns(3)
        fl = c1.selectbox("Fluido", FLUIDOS, key="r-fl")
        Pa = c1.number_input("P caldera [bar]", value=30.0, key="r-Pa")
        Ta = c1.number_input("T entrada turbina [°C]", value=350.0, key="r-Ta")
        Pb = c2.number_input("P condensador [bar]", value=0.75, key="r-Pb")
        et_t = c2.number_input("η turbina", 0.05, 1.0, 1.0, 0.05, key="r-et")
        et_b = c2.number_input("η bomba", 0.05, 1.0, 1.0, 0.05, key="r-eb")
        rec = c3.checkbox("Con recalentamiento", key="r-rec")
        Pr = c3.number_input("P recalentamiento [bar]", value=5.0, disabled=not rec, key="r-Pr")
        Tr = c3.number_input("T recalentada [°C]", value=350.0, disabled=not rec, key="r-Tr")
        try:
            ciclo = rankine(fl, Pa * 1e5, Ta + 273.15, Pb * 1e5, et_t, et_b, (Pr * 1e5, Tr + 273.15) if rec else None)
            mostrar_ciclo(ciclo, "r")
        except Exception as e:
            st.error(f"No se pudo calcular el ciclo: {e}")
    else:
        guardados = st.session_state.estados
        if not guardados:
            st.info("Guardá un estado inicial en la pestaña Estados (por ejemplo, líquido saturado a la presión del condensador).")
        else:
            ini = st.selectbox("Estado inicial", list(guardados), key="c-ini")
            base = pd.DataFrame({
                "Equipo": ["Bomba", "Caldera", "Turbina", "Condensador"],
                "Objetivo": [OBJ_PSALIDA, "T [°C]", OBJ_PSALIDA, "x [-]"],
                "Valor": [30.0, 350.0, 0.75, 0.0],
                "η_s": [1.0, 1.0, 1.0, 1.0],
            })
            tabla = st.data_editor(base, num_rows="dynamic", key="c-tabla", column_config={
                "Equipo": st.column_config.SelectboxColumn(options=list(EQUIPOS), required=True),
                "Objetivo": st.column_config.SelectboxColumn(options=list(OBJ_ISOBARICO) + [OBJ_PSALIDA], required=True),
                "Valor": st.column_config.NumberColumn(required=True),
                "η_s": st.column_config.NumberColumn(min_value=0.05, max_value=1.0),
            })
            st.caption("Cada fila es un equipo que toma la salida del anterior. Caldera, Condensador, etc. mantienen P y fijan T, h o x; "
                       "Turbina, Bomba, Compresor y Válvula fijan la P de salida (η_s solo aplica a turbina, bomba y compresor).")
            try:
                filas = [{"equipo": r["Equipo"], "objetivo": r["Objetivo"], "valor": r["Valor"], "eta": r["η_s"]}
                         for _, r in tabla.iterrows()]
                mostrar_ciclo(desde_tabla(guardados[ini], filas), "c")
            except Exception as e:
                st.error(f"No se pudo calcular el ciclo: {e}")
