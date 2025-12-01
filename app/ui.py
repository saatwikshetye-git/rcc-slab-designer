"""
ui.py
------
Streamlit UI components for IS 456 slab designer.
Shows alpha coefficients and ly/lx ratio for two-way (Table 27).
"""

import streamlit as st
from .one_way import design_oneway_slab
from .two_way import design_twoway_slab
from .report import export_pdf, export_csv
from .reinforcement import recommend_bars


def display_results(result: dict):
    st.subheader("Design Output")
    # Show main results (exclude warnings)
    keys_to_show = {k: v for k, v in result.items() if k != "warnings"}
    st.table(keys_to_show)

    # show some key values in columns for clarity
    if result.get("slab_type", "").lower().startswith("two-way"):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("ly/lx ratio", result.get("ly_lx_ratio", "N/A"))
            st.metric("alpha (short)", result.get("alpha_short", "N/A"))
        with col2:
            st.metric("alpha (long)", result.get("alpha_long", "N/A"))
            st.metric("wu (kN/m)", result.get("wu_kN_per_m", "N/A"))
        with col3:
            st.metric("L short (m)", result.get("L_short_m", "N/A"))
            st.metric("L long (m)", result.get("L_long_m", "N/A"))

    # Warnings
    if result.get("warnings"):
        st.subheader("Warnings")
        for w in result["warnings"]:
            st.warning(w)
    else:
        st.success("No warnings.")


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


def two_way_ui():
    st.header("Two-Way Slab Design (IS 456 Table 27 - Simply Supported on 4 sides)")
    st.markdown("Two-way design uses IS 456 Table 27 (annex) coefficients interpolated for ly/lx ratio.")

    col1, col2 = st.columns(2)

    with col1:
        Lx = st.number_input("Short Span Lx (m)", min_value=1.0, value=4.0)
        Ly = st.number_input("Long Span Ly (m)", min_value=1.0, value=5.0)

    with col2:
        cover = st.number_input("Effective Cover (mm)", min_value=10, max_value=40, value=20)
        st.info("Using Table 27 (ly/lx interpolation). Other panel cases (Table 26) can be added later.")

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


def main_ui():
    st.sidebar.title("Slab Type")
    slab_mode = st.sidebar.radio("Select Mode", ["One-Way", "Two-Way"])

    if slab_mode == "One-Way":
        one_way_ui()
    else:
        two_way_ui()
