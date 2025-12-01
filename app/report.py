"""
report.py
---------
Utilities for exporting slab design results to:
- PDF (clean formatted)
- CSV (simple row output)
"""

from fpdf import FPDF
import csv
import os


# ---------------------------------------------------------
# PDF REPORT
# ---------------------------------------------------------

class PDFReport(FPDF):
    def header(self):
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, "IS 456 Slab Design Report", ln=True, align="C")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, "Generated using Streamlit Slab Designer", align="C")


def export_pdf(result_dict, filename="slab_design_report.pdf"):
    """
    Creates a simple PDF showing key results and warnings.
    result_dict: dictionary returned by one_way or two_way design modules.
    Returns the filename for Streamlit to download.
    """

    pdf = PDFReport()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font("Arial", size=12)

    # Section: Inputs/Results
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Design Summary", ln=True)
    pdf.set_font("Arial", size=11)

    for key, value in result_dict.items():
        if key == "warnings":
            continue  # handled separately
        pdf.cell(0, 8, f"{key}: {value}", ln=True)

    # Section: Warnings
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Warnings:", ln=True)
    pdf.set_font("Arial", size=11)

    if result_dict.get("warnings"):
        for w in result_dict["warnings"]:
            pdf.multi_cell(0, 8, f"- {w}")
    else:
        pdf.cell(0, 8, "No warnings.", ln=True)

    pdf.output(filename)
    return filename


# ---------------------------------------------------------
# CSV EXPORT
# ---------------------------------------------------------

def export_csv(result_dict, filename="slab_design_results.csv"):
    """
    Save result dictionary to CSV file.
    """
    with open(filename, mode="w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Parameter", "Value"])

        for key, value in result_dict.items():
            if key == "warnings":
                continue
            writer.writerow([key, value])

        # Add warnings at end
        if result_dict.get("warnings"):
            writer.writerow([])
            writer.writerow(["Warnings", ""])
            for w in result_dict["warnings"]:
                writer.writerow(["", w])

    return filename

