import streamlit as st

from .one_way import design_oneway_slab
from .two_way import design_twoway_slab
from .report import export_pdf, export_csv


# ---------------------------------------------------------
# Display result dictionary
# ---------------------------------------------------------

def display_results(result: dict):
    st.subheader("Design Output")

    keys_to_show = {k: v for k, v in result.items() if k != "warnings"}
    st.table(keys_to_show)

    # Warnings
    if result.get("warnings"):
        st.subheader("Warnings")
        for w in result["warnings"]:
            st.warning(w)
    else:
        st.success("No warnings.")

    # Detailed step-by-step
    if "detailed_steps" in result:
        with st.expander("Show step-by-step IS 456 calculation"):
            for step in result["detailed_steps"]:
                st.markdown(f"### {step['title']}")
                st.markdown(step["body"])


# ---------------------------------------------------------
# ONE-WAY SLAB UI
# ---------------------------------------------------------

def one_way_ui():
    st.header("One-Way Slab Design (IS 456)")

    col1, col2 = st.columns(2)

    with col1:
        span_m = st.number_input("Clear Span Lc (m)", min_value=0.5, value=4.0)
        support_w = st.number_input("Support Width (m)", min_value=0.0, value=0.0)
        wall_thickness = st.number_input("Wall thickness (mm)", min_value=0.0, value=115.0)
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

    exposure = st.selectbox(
        "Exposure Condition (for cracking & cover requirements)",
        ["Mild", "Moderate", "Severe", "Very Severe", "Extreme"],
        index=1
    )

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


# ---------------------------------------------------------
# TWO-WAY SLAB UI
# ---------------------------------------------------------

def two_way_ui():
    st.header("Two-Way Slab Design (IS 456 Table 27 Method)")

    col1, col2 = st.columns(2)

    with col1:
        Lx = st.number_input("Short Span Lx (m)", min_value=0.5, value=4.0)
        Ly = st.number_input("Long Span Ly (m)", min_value=0.5, value=5.0)
        wall_thickness = st.number_input("Wall thickness (mm)", min_value=0.0, value=115.0)

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


# ---------------------------------------------------------
# MAIN APP UI
# ---------------------------------------------------------

def main_ui():
    st.sidebar.title("Slab Type")
    slab_mode = st.sidebar.radio("Select Mode", ["One-Way", "Two-Way"])

    if slab_mode == "One-Way":
        one_way_ui()
    else:
        two_way_ui()
