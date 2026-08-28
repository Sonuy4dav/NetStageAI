"""Streamlit Cloud launcher for the packaged application."""

import runpy


runpy.run_module("src.app", run_name="__main__")