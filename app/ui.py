"""
ui.py
------
Streamlit UI components for IS 456 slab designer.
This module only handles inputs + clean display of outputs.
"""

import streamlit as st
from .one_way import design_oneway_slab
from .two_way import design_twoway_slab
from .report import export_pdf, export_csv


# ---------------------------------------------------------
# UTILITY: Display results dictionary nicely
# ---------------------------------------------------------

def display_results(result: dict):
    st.subheader("Design Output")

    clean_dict = {k: v for k, v in result.items() if k != "warnings"}
    st.table(clean_dict)

    # Warnings
    if result.get("warnings"):
        st.subheader("Warnings")
        for w in result["warnings"]:
            st.warning(w)
    else:
        st.success("No warnings.")


# ---------------------------------------------------------
# ONE-WAY SLAB UI
# ---------------------------------------------------------

def one_way_ui():
    st.header("One-Way Slab Design (IS 456)")

    col1, col2 = st.columns(2)

    with col1:
        span_m = st.number_input("Clear Span L (m)", min_value=1.0, value=4.0)
        support_w = st.number_input("Support Width (m)", min_value=0.0, value=0.0)
        Ld = st.number_input("L/d Ratio", min_value=12, max_value=30, value=20)

    with col2:
        cover = st.number_input("Effective Cover (mm)", min_value=10, max_value=40, value=20)
        bar_dia = st.number_input("Main Bar Diameter (mm)", min_value=8, max_value=25, value=10)

    st.subheader("Loads")
    col3, col4 = st.columns(2)

    with col3:
        LL = st.number_input("Live Load (kN/m²)", min_value=0.0, value=3.0)
        FF = st.number_input("Floor Finish (kN/m²)", min_value=0.0, value=0.5)
    with col4:
        partitions = st.number_input("Partition Load (kN/m)", min_value=0.0, value=0.0)

    if st.button("Calculate One-Way Design"):
        result = design_oneway_slab(
            span_m=span_m,
            support_width_m=support_w,
            L_div_d=Ld,
            cover_mm=cover,
            bar_dia_mm=bar_dia,
            live_load_kN_m2=LL,
            floor_finish_kN_m2=FF,
            partitions_kN_per_m=partitions
        )
        display_results(result)

        st.subheader("Export")
        pdf_file = export_pdf(result)
        csv_file = export_csv(result)
        st.download_button("Download PDF", data=open(pdf_file, "rb"), file_name=pdf_file)
        st.download_button("Download CSV", data=open(csv_file, "rb"), file_name=csv_file)


# ---------------------------------------------------------
# TWO-WAY SLAB UI
# ---------------------------------------------------------

def two_way_ui():
    st.header("Two-Way Slab Design (IS 456)")

    col1, col2 = st.columns(2)

    with col1:
        Lx = st.number_input("Short Span Lx (m)", min_value=1.0, value=4.0)
        Ly = st.number_input("Long Span Ly (m)", min_value=1.0, value=5.0)

    with col2:
        cover = st.number_input("Effective Cover (mm)", min_value=10, max_value=40, value=20)
        case = st.selectbox("Panel Case", ["Interior", "Edge", "Corner"])
    
    st.subheader("Reinforcement")
    col3, col4 = st.columns(2)

    with col3:
        bar_x = st.number_input("Bar Dia (X-direction)", min_value=8, max_value=25, value=10)
    with col4:
        bar_y = st.number_input("Bar Dia (Y-direction)", min_value=8, max_value=25, value=10)

    st.subheader("Loads")
    col5, col6 = st.columns(2)

    with col5:
        LL = st.number_input("Live Load (kN/m²)", min_value=0.0, value=3.0)
    with col6:
        FF = st.number_input("Floor Finish (kN/m²)", min_value=0.0, value=0.5)

    partitions = st.number_input("Partition Load (kN/m)", min_value=0.0, value=0.0)

    if st.button("Calculate Two-Way Design"):
        result = design_twoway_slab(
            Lx_m=Lx, 
            Ly_m=Ly,
            panel_case=case.lower(),
            cover_mm=cover,
            bar_dia_x_mm=bar_x,
            bar_dia_y_mm=bar_y,
            live_load_kN_m2=LL,
            floor_finish_kN_m2=FF,
            partitions_kN_per_m=partitions
        )
        display_results(result)

        st.subheader("Export")
        pdf_file = export_pdf(result)
        csv_file = export_csv(result)
        st.download_button("Download PDF", data=open(pdf_file, "rb"), file_name=pdf_file)
        st.download_button("Download CSV", data=open(csv_file, "rb"), file_name=csv_file)


# ---------------------------------------------------------
# MAIN UI SELECTOR
# ---------------------------------------------------------

def main_ui():
    st.sidebar.title("Slab Type")
    slab_mode = st.sidebar.radio("Select Mode", ["One-Way", "Two-Way"])

    if slab_mode == "One-Way":
        one_way_ui()
    else:
        two_way_ui()

