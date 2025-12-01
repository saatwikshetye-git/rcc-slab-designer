"""
ui.py
Final Streamlit UI for IS 456 Slab Designer.
Presents a clean summary at top + an expander showing full step-by-step IS calculations.
"""

import streamlit as st
from .one_way import design_oneway_slab
from .two_way import design_twoway_slab
from .report import export_pdf, export_csv


def scalar_summary(result: dict) -> dict:
    """
    Build a small dict of simple scalar outputs for the compact summary view.
    Prioritises typical final outputs.
    """
    keys_preferred = [
        "slab_type",
        "effective_span_m", "d_mm", "D_mm",
        "wu_kN_per_m", "Mu_kN_m_per_m",
        "Ast_required_mm2_per_m", "Ast_provided_mm2_per_m",
        "spacing_mm", "bar_dia_mm",
        # Two-way keys (if present)
        "L_short_m", "L_long_m", "Mx_kN_m_per_m", "My_kN_m_per_m",
        "Ast_short_req_mm2_per_m", "Ast_short_prov_mm2_per_m",
        "spacing_short_mm", "Ast_long_req_mm2_per_m", "Ast_long_prov_mm2_per_m",
        "spacing_long_mm", "deflection_check"
    ]

    summary = {}
    for k in keys_preferred:
        if k in result:
            v = result[k]
            # round floats for neat display
            if isinstance(v, float):
                summary[k] = round(v, 4)
            else:
                summary[k] = v
    # fallback: include any other simple scalars
    for k, v in result.items():
        if k not in summary and isinstance(v, (int, float, str, bool)):
            if isinstance(v, float):
                summary[k] = round(v, 4)
            else:
                summary[k] = v
    return summary


def show_summary_block(summary: dict):
    if not summary:
        st.write("No scalar summary available.")
        return

    st.subheader("Summary (final values)")
    # render keys in two columns for readability
    keys = list(summary.keys())
    half = (len(keys) + 1) // 2
    col1_keys = keys[:half]
    col2_keys = keys[half:]

    col1, col2 = st.columns(2)
    with col1:
        for k in col1_keys:
            st.markdown(f"**{k}**")
            st.write(summary[k])
    with col2:
        for k in col2_keys:
            st.markdown(f"**{k}**")
            st.write(summary[k])


def display_results(result: dict):
    """
    Clean summary + step-by-step expander.
    """
    st.subheader("Design Output")

    # Simple scalar summary first
    summary = scalar_summary(result)
    show_summary_block(summary)

    # Warnings
    if result.get("warnings"):
        st.subheader("Warnings")
        for w in result["warnings"]:
            st.warning(w)
    else:
        st.success("No warnings.")

    # Detailed step-by-step (plain text, preformatted)
    if result.get("detailed_steps"):
        with st.expander("Show detailed IS-456 calculation steps"):
            for step in result["detailed_steps"]:
                title = step.get("title", "")
                body = step.get("body", "")
                st.markdown(f"### {title}")
                st.text(body)

    # Raw JSON (debug) at user's discretion
    if st.checkbox("Show raw result JSON (debug)", value=False):
        st.json(result)


# ----------------- One-way UI -----------------
def one_way_ui():
    st.header("One-Way Slab Design (IS 456)")

    col1, col2 = st.columns(2)
    with col1:
        span_m = st.number_input("Clear Span Lc (m)", min_value=0.5, value=4.0, step=0.1)
        support_w = st.number_input("Support Width (m)", min_value=0.0, value=0.0, step=0.05)
        wall_thickness = st.number_input("Wall thickness (mm)", min_value=0.0, value=115.0, step=5.0)
        Ld = st.number_input("Design L/d", min_value=12, max_value=30, value=20)
    with col2:
        cover = st.number_input("Nominal Cover (mm)", min_value=10, max_value=40, value=20)
        bar_dia = st.number_input("Main Bar Diameter (mm)", min_value=8, max_value=25, value=10)
        fck = st.selectbox("Concrete grade fck (MPa)", [20, 25, 30, 35, 40], index=1)
        fy = st.selectbox("Steel grade fy (MPa)", [415, 500], index=1)

    st.subheader("Loads")
    col3, col4 = st.columns(2)
    with col3:
        LL = st.number_input("Live Load (kN/m²)", min_value=0.0, value=3.0)
        FF = st.number_input("Floor Finish (kN/m²)", min_value=0.0, value=0.5)
    with col4:
        partitions = st.number_input("Partition Load (kN/m)", min_value=0.0, value=0.0)
        exposure = st.selectbox("Exposure Condition", ["Mild", "Moderate", "Severe", "Very Severe", "Extreme"], index=1)

    if st.button("Calculate One-Way Design"):
        result = design_oneway_slab(
            span_m=span_m,
            support_width_m=support_w,
            wall_thickness_mm=wall_thickness,
            L_div_d=Ld,
            cover_mm=cover,
            bar_dia_mm=bar_dia,
            live_load_kN_m2=LL,
            floor_finish_kN_m2=FF,
            partitions_kN_per_m=partitions,
            fck=fck,
            fy=fy,
            exposure=exposure
        )
        display_results(result)

        st.subheader("Export")
        pdf_file = export_pdf(result)
        csv_file = export_csv(result)
        st.download_button("Download PDF", data=open(pdf_file, "rb"), file_name=pdf_file)
        st.download_button("Download CSV", data=open(csv_file, "rb"), file_name=csv_file)


# ----------------- Two-way UI -----------------
def two_way_ui():
    st.header("Two-Way Slab Design (IS 456 Table 27 method)")

    col1, col2 = st.columns(2)
    with col1:
        Lx = st.number_input("Short Span Lx (m)", min_value=0.5, value=4.0, step=0.1)
        Ly = st.number_input("Long Span Ly (m)", min_value=0.5, value=5.0, step=0.1)
        wall_thickness = st.number_input("Wall thickness (mm)", min_value=0.0, value=115.0, step=5.0)
    with col2:
        cover = st.number_input("Effective Cover (mm)", min_value=10, max_value=40, value=20)
        fck = st.selectbox("Concrete grade fck (MPa)", [20, 25, 30, 35, 40], index=1)
        fy = st.selectbox("Steel grade fy (MPa)", [415, 500], index=1)

    st.subheader("Loads")
    col3, col4 = st.columns(2)
    with col3:
        live_load = st.number_input("Live Load (kN/m²)", min_value=0.0, value=3.0)
        floor_finish = st.number_input("Floor Finish (kN/m²)", min_value=0.0, value=0.5)
    with col4:
        partitions = st.number_input("Partition Load (kN/m)", min_value=0.0, value=0.0)

    col5, col6 = st.columns(2)
    with col5:
        bar_x = st.number_input("Bar Diameter (X-direction)", min_value=8, max_value=25, value=10)
    with col6:
        bar_y = st.number_input("Bar Diameter (Y-direction)", min_value=8, max_value=25, value=10)

    if st.button("Calculate Two-Way Design"):
        result = design_twoway_slab(
            Lx_m=Lx,
            Ly_m=Ly,
            wall_thickness_mm=wall_thickness,
            live_load_kN_m2=live_load,
            floor_finish_kN_m2=floor_finish,
            partitions_kN_per_m=partitions,
            cover_mm=cover,
            bar_dia_x_mm=bar_x,
            bar_dia_y_mm=bar_y,
            fck=fck,
            fy=fy
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
