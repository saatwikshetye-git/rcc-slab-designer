"""
ui.py
------
Streamlit UI components for IS 456 slab designer.

This version:
- Adds fck/fy dropdowns
- Adds inputs required by the college procedure for one-way slabs
- Adds a collapsible "Detailed Calculation Steps" panel that prints
  step-by-step intermediate values returned by design_oneway_slab.
- Calls the two-way design as before (two_way not changed here).
"""

import streamlit as st
from .one_way import design_oneway_slab
from .two_way import design_twoway_slab
from .report import export_pdf, export_csv
from .reinforcement import recommend_bars

# Choices for material grades
FCK_OPTIONS = [20, 25, 30, 35, 40]
FY_OPTIONS = [415, 500]


def display_results(result: dict, show_detailed=False):
    st.subheader("Design Output")
    # Show main results (exclude large 'detailed_steps' if present)
    keys_to_show = {k: v for k, v in result.items() if k not in ("warnings", "detailed_steps")}
    st.table(keys_to_show)

    # Show useful metrics for two-way slabs (if present)
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

    # Detailed step-by-step section (collapsible)
    if show_detailed and result.get("detailed_steps"):
        st.subheader("Detailed calculation steps")
        for step in result["detailed_steps"]:
            # step is (title, text) pairs
            title = step.get("title", "")
            body = step.get("body", "")
            st.markdown(f"**{title}**")
            st.text(body)
            st.markdown("---")


# ---------------------------------------------------------
# ONE-WAY UI
# ---------------------------------------------------------

def one_way_ui():
    st.header("One-Way Slab Design")

    st.markdown("Provide inputs below. Use the 'Show detailed steps' toggle to view step-by-step calculations.")

    col0, _ = st.columns([1, 3])
    with col0:
        show_detailed = st.checkbox("Show detailed steps", value=True)

    col1, col2 = st.columns(2)

    with col1:
        clear_span = st.number_input("Clear Span (m) (Lc)", min_value=0.5, value=4.0, step=0.1)
        support_w = st.number_input("Support Width (m)", min_value=0.0, value=0.0, step=0.01)
        # wall thickness used to estimate partition load; user can directly input partitions too
        wall_thickness_mm = st.selectbox("Wall thickness (mm)", options=[0, 100, 115, 200], index=2,
                                         help="Used to estimate partition (line) load if Partition Load left as 0")
        Ld = st.number_input("Design L/d (use recommended values)", min_value=12, max_value=40, value=20)

    with col2:
        cover = st.number_input("Nominal Cover (mm)", min_value=5, max_value=100, value=20)
        bar_dia = st.selectbox("Main Bar Diameter (mm)", options=[8, 10, 12, 16, 20, 25], index=1)
        # material grades
        fck = st.selectbox("Concrete grade, fck (MPa)", options=FCK_OPTIONS, index=1)
        fy = st.selectbox("Steel grade, fy (MPa)", options=FY_OPTIONS, index=1)

    st.subheader("Loads")
    col3, col4 = st.columns(2)

    with col3:
        LL = st.number_input("Live Load (kN/m²)", min_value=0.0, value=3.0, step=0.1)
        FF = st.number_input("Floor Finish (kN/m²)", min_value=0.0, value=0.5, step=0.1)
    with col4:
        partitions = st.number_input("Partition Load (kN/m) — leave 0 to auto-calc", min_value=0.0, value=0.0, step=0.1)
        exposure = st.selectbox("Exposure condition", options=["Moderate", "Severe", "Very Severe"], index=0,
                                help="Used for recommending nominal cover and durability checks")

    # if user left partitions = 0 try estimate from wall thickness & typical density
    if partitions == 0 and wall_thickness_mm > 0:
        # quick estimate (conservative): brick wall 115mm ~ 3.5 kN/m, 100mm block ~ 2.5 kN/m
        if wall_thickness_mm == 115:
            partitions_est = 3.5
        elif wall_thickness_mm == 100:
            partitions_est = 2.5
        elif wall_thickness_mm == 200:
            partitions_est = 6.0
        else:
            partitions_est = 0.0
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
            exposure=exposure
        )
        display_results(result, show_detailed=show_detailed)

        st.subheader("Export")
        pdf_file = export_pdf(result)
        csv_file = export_csv(result)
        st.download_button("Download PDF", data=open(pdf_file, "rb"), file_name=pdf_file)
        st.download_button("Download CSV", data=open(csv_file, "rb"), file_name=csv_file)


# ---------------------------------------------------------
# TWO-WAY UI
# ---------------------------------------------------------

def two_way_ui():
    st.header("Two-Way Slab Design")

    col1, col2 = st.columns(2)

    with col1:
        Lx = st.number_input("Short Span Lx (m)", min_value=0.5, value=4.0, step=0.1)
        Ly = st.number_input("Long Span Ly (m)", min_value=0.5, value=5.0, step=0.1)

    with col2:
        cover = st.number_input("Nominal Cover (mm)", min_value=5, max_value=100, value=20)
        fck = st.selectbox("Concrete grade, fck (MPa)", options=FCK_OPTIONS, index=1)
        fy = st.selectbox("Steel grade, fy (MPa)", options=FY_OPTIONS, index=1)

    st.subheader("Reinforcement")
    col3, col4 = st.columns(2)

    with col3:
        bar_x = st.selectbox("Bar Dia (X-direction)", options=[8, 10, 12, 16, 20, 25], index=1)
    with col4:
        bar_y = st.selectbox("Bar Dia (Y-direction)", options=[8, 10, 12, 16, 20, 25], index=1)

    st.subheader("Loads")
    col5, col6 = st.columns(2)

    with col5:
        LL = st.number_input("Live Load (kN/m²)", min_value=0.0, value=3.0, step=0.1)
    with col6:
        FF = st.number_input("Floor Finish (kN/m²)", min_value=0.0, value=0.5, step=0.1)

    partitions = st.number_input("Partition Load (kN/m)", min_value=0.0, value=0.0, step=0.1)

    if st.button("Calculate Two-Way Design"):
        result = design_twoway_slab(
            Lx_m=Lx,
            Ly_m=Ly,
            cover_mm=cover,
            bar_dia_x_mm=bar_x,
            bar_dia_y_mm=bar_y,
            live_load_kN_m2=LL,
            floor_finish_kN_m2=FF,
            partitions_kN_per_m=partitions,
            fck=fck,
            fy=fy
        )
        display_results(result, show_detailed=False)

        st.subheader("Export")
        pdf_file = export_pdf(result)
        csv_file = export_csv(result)
        st.download_button("Download PDF", data=open(pdf_file, "rb"), file_name=pdf_file)
        st.download_button("Download CSV", data=open(csv_file, "rb"), file_name=csv_file)


# ---------------------------------------------------------
# MAIN UI ROUTER
# ---------------------------------------------------------

def main_ui():
    st.sidebar.title("Slab Type")
    slab_mode = st.sidebar.radio("Select Mode", ["One-Way", "Two-Way"])

    if slab_mode == "One-Way":
        one_way_ui()
    else:
        two_way_ui()
