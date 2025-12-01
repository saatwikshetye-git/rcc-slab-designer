"""
ui.py
------
Streamlit UI components for IS 456 slab designer (One-way + Two-way).
Fully cleaned, no deflection logic anywhere.
"""

import streamlit as st
from .one_way import design_oneway_slab
from .two_way import design_twoway_slab
from .report import export_pdf, export_csv

FCK_OPTIONS = [20, 25, 30, 35, 40]
FY_OPTIONS = [415, 500]

RECOMMENDED_COVER_BY_EXPOSURE = {
    "Mild": 20,
    "Moderate": 30,
    "Severe": 45,
    "Very Severe": 50,
    "Extreme": 75
}


# ---------------------------------------------------------
# DISPLAY RESULTS
# ---------------------------------------------------------
def display_results(result: dict, show_detailed=False):
    st.subheader("Design Output")

    keys_to_show = {k: v for k, v in result.items()
                    if k not in ("warnings", "detailed_steps")}

    st.table(keys_to_show)

    if result.get("warnings"):
        st.subheader("Warnings")
        for w in result["warnings"]:
            st.warning(w)
    else:
        st.success("No warnings.")

    if show_detailed and result.get("detailed_steps"):
        st.subheader("Detailed Calculation Steps")
        for step in result["detailed_steps"]:
            st.markdown(f"**{step.get('title', '')}**")
            st.text(step.get("body", ""))
            st.markdown("---")


# ---------------------------------------------------------
# ONE-WAY SLAB UI
# ---------------------------------------------------------
def one_way_ui():
    st.header("One-Way Slab Design")

    col0, _ = st.columns([1, 3])
    with col0:
        show_detailed = st.checkbox("Show detailed steps", value=True)

    col1, col2 = st.columns(2)

    with col1:
        clear_span = st.number_input("Clear Span Lc (m)", min_value=0.5, value=4.0, step=0.1)
    support_w = st.number_input("Support Width (m)", min_value=0.0, value=0.0, step=0.01)
    wall_thickness_mm = st.number_input("Wall Thickness (mm)", min_value=0.0, value=115.0, step=1.0)
    Ld = st.number_input("Design L/d (for depth sizing)", min_value=12, max_value=40, value=20)

    with col2:
        cover = st.number_input("Nominal Cover (mm)", min_value=5, max_value=150, value=20)
        bar_dia = st.selectbox("Main Bar Diameter (mm)", [8, 10, 12, 16, 20, 25], index=1)
        fck = st.selectbox("Concrete Grade fck (MPa)", FCK_OPTIONS, index=1)
        fy = st.selectbox("Steel Grade fy (MPa)", FY_OPTIONS, index=1)

    st.subheader("Loads")
    col3, col4 = st.columns(2)

    with col3:
        LL = st.number_input("Live Load (kN/m²)", min_value=0.0, value=3.0, step=0.1)
        FF = st.number_input("Floor Finish (kN/m²)", min_value=0.0, value=0.5, step=0.1)

    with col4:
        partitions = st.number_input("Partition Load (kN/m)", min_value=0.0, value=0.0, step=0.1)
        exposure = st.selectbox("Exposure Condition", list(RECOMMENDED_COVER_BY_EXPOSURE.keys()), index=1)

    recommended_cover = RECOMMENDED_COVER_BY_EXPOSURE.get(exposure)
    st.info(f"IS 456 Recommended cover for '{exposure}': {recommended_cover} mm (will not override user input)")

    # Auto-partition load
    if partitions == 0 and wall_thickness_mm > 0:
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


# ---------------------------------------------------------
# TWO-WAY SLAB UI
# ---------------------------------------------------------
def two_way_ui():
    st.header("Two-Way Slab Design (IS 456 – Table 27)")

    col0, _ = st.columns([1, 3])
    with col0:
        show_detailed = st.checkbox("Show detailed steps", value=True)

    col1, col2 = st.columns(2)

    with col1:
        Lx = st.number_input("Short Span Lx (m)", min_value=0.5, value=4.0, step=0.1)
        Ly = st.number_input("Long Span Ly (m)", min_value=0.5, value=5.0, step=0.1)
        wall_thickness_mm = st.number_input("Wall Thickness (mm)", min_value=0.0, value=115.0, step=1.0)
        Ld = st.number_input("Design L/d (for depth sizing)", min_value=12, max_value=40, value=20)

    with col2:
        cover = st.number_input("Cover (mm)", min_value=5, max_value=150, value=20)
        bar_x = st.selectbox("Bar Diameter X (mm)", [8, 10, 12, 16, 20, 25], index=1)
        bar_y = st.selectbox("Bar Diameter Y (mm)", [8, 10, 12, 16, 20, 25], index=1)
        fck = st.selectbox("Concrete fck (MPa)", FCK_OPTIONS, index=1)
        fy = st.selectbox("Steel fy (MPa)", FY_OPTIONS, index=1)

    # Exposure selector
    exposure = st.selectbox(
        "Exposure Condition (IS 456 – Table 16)",
        list(RECOMMENDED_COVER_BY_EXPOSURE.keys()),
        index=1
    )

    recommended_cover = RECOMMENDED_COVER_BY_EXPOSURE.get(exposure)
    st.info(
        f"IS 456 recommended nominal cover for '{exposure}': {recommended_cover} mm "
        f"(this does NOT override your entered cover of {cover} mm)."
    )

    st.subheader("Loads")
    col3, col4 = st.columns(2)

    with col3:
        LL = st.number_input("Live Load (kN/m²)", min_value=0.0, value=3.0, step=0.1)
        FF = st.number_input("Floor Finish (kN/m²)", min_value=0.0, value=0.5, step=0.1)

    with col4:
        partitions = st.number_input("Partition Load (kN/m)", min_value=0.0, value=0.0, step=0.1)

    if st.button("Calculate Two-Way Design"):
        result = design_twoway_slab(
            Lx_m=Lx,
            Ly_m=Ly,
            live_load_kN_m2=LL,
            floor_finish_kN_m2=FF,
            partitions_kN_per_m=partitions,
            wall_thickness_mm=wall_thickness_mm,
            cover_mm=cover,
            bar_dia_x_mm=bar_x,
            bar_dia_y_mm=bar_y,
            fck=fck,
            fy=fy,
            exposure=exposure    # <--- NEW
        )

        # add recommended cover to results table
        result["recommended_cover_mm"] = recommended_cover

        display_results(result, show_detailed=show_detailed)

        st.subheader("Export")
        pdf_file = export_pdf(result)
        csv_file = export_csv(result)
        st.download_button("Download PDF", data=open(pdf_file, "rb"), file_name=pdf_file)
        st.download_button("Download CSV", data=open(csv_file, "rb"), file_name=csv_file)



# ---------------------------------------------------------
# MAIN UI CONTROLLER
# ---------------------------------------------------------
def main_ui():
    st.sidebar.title("Slab Type")
    slab_mode = st.sidebar.radio("Select Mode", ["One-Way", "Two-Way"])

    if slab_mode == "One-Way":
        one_way_ui()
    else:
        two_way_ui()
