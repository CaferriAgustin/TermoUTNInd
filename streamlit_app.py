"""Punto de entrada para Streamlit Community Cloud (y para `streamlit run streamlit_app.py`)."""
import runpy

runpy.run_module("termograf.ui.app", run_name="__main__")
