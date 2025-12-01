"""
ui.py
------
Streamlit UI components for IS 456 slab designer (one-way focused).
Deflection outputs removed.
"""

import streamlit as st
from .one_way import design_oneway_slab
# keep two-way placeholder to avoid import crash when two-way module missing/disabled
try:
    from .two_way import design_twoway_slab
except Exception:
    def design_twoway_slab(*args, **kwargs):
        return {"msg": "Two-way slab module not implemented."}

from .report import export_pdf, export_csv
from .reinforcement import recommend_bars

FCK_OPTIONS = [20, 25, 30, 35, 40]
FY_OPTIONS = [415, 500]

RECOMMENDED_COVER_BY_EXPOSURE = {
    "Mild": 20,
    "Moderate": 30,
    "Severe": 45,
    "Very Severe": 50,
    "Extreme": 75
}


def _format_candidates_text(candidates):
    lines = []
    for c in candidates:
        lines.append(f"- dia {c['bar_dia_mm']} mm: spacing {c['spacing_mm']} mm, provided Ast = {c['Ast_provided_mm2_per_m']:.2f} mm²/m, ok={c['ok']}, warnings={c['warnings']}")
    return "\n".join(lines)


def display_results(result: dict, show_detailed=False):
    st.subheader("Design Output")
    keys_to_show = {k: v for k, v in result.items() if k not in ("warnings", "detailed_steps")}
    st.table(keys_to_show)

    if result.get("warnings"):
        st.subheader("Warnings")
        for w in result["warnings"]:
            st.warning(w)
    else:
        st.success("No warnings.")

    if show_detailed and result.get("detailed_steps"):
        st.subheader("Detailed calculation steps")
        for step in result["detailed_steps"]:
            st.markdown(f"**{step.get('title', '')}**")
            st.text(step.get("body", ""))
            st.markdown("---")


def one_way_ui():
    st.header("One-Way Slab Design")
    st.markdown("Provide inputs below. 'Show detailed steps' toggle shows step-by-step calculations.")

    col0, _ = st.columns([1, 3])
    with col0:
        show_detailed = st.checkbox("Show detailed steps", value=True)

    col1, col2 = st.columns(2)

    with col1:
        clear_span = st.number_input("Clear Span (m) (Lc)", min_value=0.5, value=4.0, step=0.1)
        support_w = st.number_input("Support Width (m)", min_value=0.0, value=0.0, step=0.01)
        wall_thickness_mm = st.number_input("Wall thickness (mm)", min_value=0.0, value=115.0, step=1.0)
        Ld = st.number_input("Design L/d (for initial depth sizing)", min_value=12, max_value=40, value=20)

    with col2:
        cover = st.number_input("Nominal Cover (mm)", min_value=5, max_value=150, value=20)
        bar_dia = st.selectbox("Main Bar Diameter (mm)", options=[8, 10, 12, 16, 20, 25], index=1)
        fck = st.selectbox("Concrete grade, fck (MPa)", options=FCK_OPTIONS, index=1)
        fy = st.selectbox("Steel grade, fy (MPa)", options=FY_OPTIONS, index=1)

    st.subheader("Loads")
    col3, col4 = st.columns(2)

    with col3:
        LL = st.number_input("Live Load (kN/m²)", min_value=0.0, value=3.0, step=0.1)
        FF = st.number_input("Floor Finish (kN/m²)", min_value=0.0, value=0.5, step=0.1)
    with col4:
        partitions = st.number_input("Partition Load (kN/m) — leave 0 to auto-calc", min_value=0.0, value=0.0, step=0.1)
        exposure = st.selectbox("Exposure condition", options=["Mild", "Moderate", "Severe", "Very Severe", "Extreme"], index=1)

    recommended_cover = RECOMMENDED_COVER_BY_EXPOSURE.get(exposure)
    if recommended_cover is not None:
        st.info(f"IS-456 recommended nominal cover for exposure '{exposure}': {recommended_cover} mm. (This is a suggestion only — your entered cover {cover} mm will be used.)")

    # if partitions = 0, estimate based on wall thickness
    if partitions == 0 and wall_thickness_mm > 0:
        if wall_thickness_mm == 115:
            partitions_est = 3.5
        elif wall_thickness_mm == 100:
            partitions_est = 2.5
        elif wall_thickness_mm == 200:
            partitions_est = 6.0
        else:
            partitions_est = (wall_thickness_mm / 115.0) * 3.5
    else:
        partitions_est = partitions

    if st.button("Calculate One-Way Design"):
        result = design_oneway_slab(
            clear_span_m=clear_span,
            support_width_m=support_w,
            L_div_d=Ld,
            cover_mm=cover,
            bar_dia_mm=bar_dia,
            live_load_kN_m2=LL,
            floor_finish_kN_m2=FF,
            partitions_kN_per_m=partitions_est,
            fck=fck,
            fy=fy,
            exposure=exposure,
            wall_thickness_mm=wall_thickness_mm
        )
        display_results(result, show_detailed=show_detailed)

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
        st.info("Two-way module not updated yet. Use one-way for now.")
