"""Generate realistic mock Canadian tax documents as PDFs for demo purposes.

Uses reportlab to create text-based PDFs resembling CRA slip layouts.
All data is fictional. Includes intentional anomalies for the analyzer to detect:
- T4: CPP contribution is slightly lower than expected
- No RRSP receipt despite having room (analyzer should flag this)

Usage:
    pip install reportlab
    python generate_samples.py
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


def _draw_header(c: canvas.Canvas, title: str, form_code: str, year: int):
    c.setFont("Helvetica-Bold", 14)
    c.drawString(0.75 * inch, 10.2 * inch, f"CANADA REVENUE AGENCY")
    c.setFont("Helvetica", 10)
    c.drawString(0.75 * inch, 10.0 * inch, f"Agence du revenu du Canada")
    c.setFont("Helvetica-Bold", 18)
    c.drawRightString(7.75 * inch, 10.2 * inch, form_code)
    c.setFont("Helvetica", 11)
    c.drawRightString(7.75 * inch, 10.0 * inch, f"Tax Year / Année d'imposition: {year}")
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(4.25 * inch, 9.7 * inch, title)
    c.line(0.75 * inch, 9.55 * inch, 7.75 * inch, 9.55 * inch)


def _draw_box(c: canvas.Canvas, x: float, y: float, label: str, value: str, box_num: str = ""):
    c.setFont("Helvetica", 7)
    if box_num:
        c.drawString(x, y + 0.28 * inch, f"Box {box_num}")
    c.setFont("Helvetica", 8)
    c.drawString(x, y + 0.15 * inch, label)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y, value)


def generate_t4():
    """T4 — Statement of Remuneration Paid. CPP is intentionally ~$50 low."""
    c = canvas.Canvas("sample_T4_maple_tech.pdf", pagesize=letter)
    _draw_header(c, "STATEMENT OF REMUNERATION PAID", "T4", 2024)

    y = 9.1 * inch
    c.setFont("Helvetica", 9)
    c.drawString(0.75 * inch, y, "Employer / Employeur:")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2.5 * inch, y, "Maple Tech Inc.")
    y -= 0.25 * inch
    c.setFont("Helvetica", 9)
    c.drawString(0.75 * inch, y, "Employer Address:")
    c.setFont("Helvetica", 10)
    c.drawString(2.5 * inch, y, "100 Innovation Drive, Toronto, ON M5V 1A1")

    y -= 0.4 * inch
    c.setFont("Helvetica", 9)
    c.drawString(0.75 * inch, y, "Employee / Employé:")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2.5 * inch, y, "Jordan A. Nguyen")
    y -= 0.25 * inch
    c.setFont("Helvetica", 9)
    c.drawString(0.75 * inch, y, "Social Insurance Number:")
    c.setFont("Helvetica", 10)
    c.drawString(2.5 * inch, y, "123-456-782")

    y -= 0.5 * inch
    col1, col2 = 0.75 * inch, 4.25 * inch

    _draw_box(c, col1, y, "Employment income", "$78,500.00", "14")
    _draw_box(c, col2, y, "Employee's CPP contributions", "$3,815.50", "16")

    y -= 0.55 * inch
    _draw_box(c, col1, y, "Employee's EI premiums", "$1,049.12", "18")
    _draw_box(c, col2, y, "Income tax deducted", "$15,420.00", "22")

    y -= 0.55 * inch
    _draw_box(c, col1, y, "RPP contributions", "$2,400.00", "20")
    _draw_box(c, col2, y, "Pension adjustment", "$4,800.00", "52")

    y -= 0.55 * inch
    _draw_box(c, col1, y, "Union dues", "$624.00", "44")
    _draw_box(c, col2, y, "Charitable donations", "$250.00", "46")

    c.save()
    print("Generated: sample_T4_maple_tech.pdf")


def generate_t5():
    """T5 — Statement of Investment Income."""
    c = canvas.Canvas("sample_T5_national_bank.pdf", pagesize=letter)
    _draw_header(c, "STATEMENT OF INVESTMENT INCOME", "T5", 2024)

    y = 9.1 * inch
    c.setFont("Helvetica", 9)
    c.drawString(0.75 * inch, y, "Payer / Payeur:")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2.5 * inch, y, "National Bank of Canada")

    y -= 0.3 * inch
    c.setFont("Helvetica", 9)
    c.drawString(0.75 * inch, y, "Recipient / Bénéficiaire:")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2.5 * inch, y, "Jordan A. Nguyen")
    y -= 0.25 * inch
    c.setFont("Helvetica", 9)
    c.drawString(0.75 * inch, y, "Social Insurance Number:")
    c.setFont("Helvetica", 10)
    c.drawString(2.5 * inch, y, "123-456-782")

    y -= 0.5 * inch
    col1, col2 = 0.75 * inch, 4.25 * inch

    _draw_box(c, col1, y, "Actual amount of eligible dividends", "$1,250.00", "10")
    _draw_box(c, col2, y, "Actual amount of dividends other than eligible", "$0.00", "11")

    y -= 0.55 * inch
    _draw_box(c, col1, y, "Interest from Canadian sources", "$342.67", "13")
    _draw_box(c, col2, y, "Foreign income", "$0.00", "15")

    y -= 0.55 * inch
    _draw_box(c, col1, y, "Capital gains dividends", "$0.00", "18")
    _draw_box(c, col2, y, "Taxable amount of eligible dividends", "$1,725.00", "24")

    y -= 0.55 * inch
    _draw_box(c, col1, y, "Dividend tax credit for eligible dividends", "$236.09", "26")

    c.save()
    print("Generated: sample_T5_national_bank.pdf")


def generate_t2202():
    """T2202 — Tuition and Enrolment Certificate."""
    c = canvas.Canvas("sample_T2202_university.pdf", pagesize=letter)
    _draw_header(c, "TUITION AND ENROLMENT CERTIFICATE", "T2202", 2024)

    y = 9.1 * inch
    c.setFont("Helvetica", 9)
    c.drawString(0.75 * inch, y, "Designated Educational Institution:")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(3.2 * inch, y, "University of Toronto")

    y -= 0.3 * inch
    c.setFont("Helvetica", 9)
    c.drawString(0.75 * inch, y, "Student / Étudiant:")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2.5 * inch, y, "Jordan A. Nguyen")
    y -= 0.25 * inch
    c.setFont("Helvetica", 9)
    c.drawString(0.75 * inch, y, "Social Insurance Number:")
    c.setFont("Helvetica", 10)
    c.drawString(2.5 * inch, y, "123-456-782")

    y -= 0.5 * inch
    col1, col2 = 0.75 * inch, 4.25 * inch

    _draw_box(c, col1, y, "Eligible tuition fees", "$7,850.00", "A")
    _draw_box(c, col2, y, "Number of months part-time", "0", "B")

    y -= 0.55 * inch
    _draw_box(c, col1, y, "Number of months full-time", "8", "C")

    c.save()
    print("Generated: sample_T2202_university.pdf")


def generate_rrsp():
    """RRSP Contribution Receipt."""
    c = canvas.Canvas("sample_RRSP_wealthsimple.pdf", pagesize=letter)
    _draw_header(c, "RRSP CONTRIBUTION RECEIPT", "RRSP", 2024)

    y = 9.1 * inch
    c.setFont("Helvetica", 9)
    c.drawString(0.75 * inch, y, "Issuer / Émetteur:")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2.5 * inch, y, "Wealthsimple Financial Corp.")

    y -= 0.3 * inch
    c.setFont("Helvetica", 9)
    c.drawString(0.75 * inch, y, "Contributor / Cotisant:")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2.5 * inch, y, "Jordan A. Nguyen")
    y -= 0.25 * inch
    c.setFont("Helvetica", 9)
    c.drawString(0.75 * inch, y, "Social Insurance Number:")
    c.setFont("Helvetica", 10)
    c.drawString(2.5 * inch, y, "123-456-782")

    y -= 0.5 * inch
    col1, col2 = 0.75 * inch, 4.25 * inch

    _draw_box(c, col1, y, "Contribution Amount", "$5,000.00", "")
    _draw_box(c, col2, y, "Date of Contribution", "2024-03-15", "")

    y -= 0.55 * inch
    _draw_box(c, col1, y, "First 60 days of following year?", "No", "")
    _draw_box(c, col2, y, "Tax year applicable", "2024", "")

    c.save()
    print("Generated: sample_RRSP_wealthsimple.pdf")


if __name__ == "__main__":
    generate_t4()
    generate_t5()
    generate_t2202()
    generate_rrsp()
    print("\nAll sample documents generated successfully.")
    print("Note: The T4 has CPP contribution ~$50 lower than expected — this is intentional")
    print("for the anomaly detector to flag.")
