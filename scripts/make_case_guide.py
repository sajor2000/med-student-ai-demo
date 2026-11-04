# /// script
# requires-python = ">=3.10"
# dependencies = ["python-docx>=1.1"]
# ///
"""Build a FICTIONAL case-based self-study guide for practice.

The layout mirrors the common case-guide format used in integrated M1/M2
curricula (course director notes, case presentation with labs, then one
section per discipline with topics, objectives, notes, and self-study
questions). The school, course, faculty, and patient are invented. Nothing
here is copied from any real course.

    uv run scripts/make_case_guide.py [--out sample/curriculum/GUIDE]
"""

from __future__ import annotations

import argparse
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

SCHOOL = "Meridian College of Medicine (fictional)"
COURSE = "BMS 501"
COURSE_TITLE = "Foundations of Infection and Immunity"
CASE = "Case 2: Jordan Rivera"
FILENAME = "BMS 501 Self-Study Guide 02 Jordan Rivera (fictional sample).docx"
DISCLAIMER = (
    "FICTIONAL SAMPLE for practice with the Med Student AI Study Agent. "
    "Invented school, faculty, and patient. Not affiliated with any medical school."
)
NAVY = RGBColor(0x1F, 0x3A, 0x5F)


# ---------------------------------------------------------------- helpers
def shade(cell, hex_fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tc_pr.append(shd)


def para(doc, text: str = "", *, bold=False, italic=False, size=None, align=None, color=None):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold, run.italic = bold, italic
    if size:
        run.font.size = Pt(size)
    if color:
        run.font.color.rgb = color
    if align is not None:
        p.alignment = align
    return p


def bullets(doc, items: list[str], level: int = 0) -> None:
    style = "List Bullet" if level == 0 else "List Bullet 2"
    for item in items:
        doc.add_paragraph(item, style=style)


def boxed(doc, title: str, lines: list[str]) -> None:
    """One-cell shaded box, like the director-notes callouts."""
    table = doc.add_table(rows=1, cols=1)
    table.style = "Table Grid"
    cell = table.rows[0].cells[0]
    shade(cell, "E8EEF6")
    cell.paragraphs[0].add_run(title).bold = True
    for line in lines:
        cell.add_paragraph(line)
    doc.add_paragraph()


def grid(doc, header: list[str], rows: list[list[str]], fill="1F3A5F") -> None:
    width = max(i + 1 for r in [header, *rows] for i, c in enumerate(r) if c)
    header, rows = header[:width], [r[:width] for r in rows]
    table = doc.add_table(rows=1, cols=len(header))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for cell, text in zip(table.rows[0].cells, header):
        shade(cell, fill)
        run = cell.paragraphs[0].add_run(text)
        run.bold = True
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    for row in rows:
        cells = table.add_row().cells
        for cell, text in zip(cells, row):
            cell.text = text
    doc.add_paragraph()


def topics(doc, videos: list[str], slides: list[str], notes: str) -> None:
    doc.add_heading("Self-Study Topics:", level=2)
    doc.add_heading("Videos:", level=4)
    for v in videos:
        doc.add_heading(v, level=5)
    doc.add_heading("Slides:", level=4)
    for s in slides:
        doc.add_heading(s, level=5)
    doc.add_heading(f"Notes: {notes}", level=4)


def objectives(doc, items: list[str]) -> None:
    doc.add_heading("Learning Objectives:", level=2)
    for i, item in enumerate(items, 1):
        doc.add_paragraph(f"{i}. {item}")


def questions(doc, discipline: str, qs: list[tuple[str, list[str], str, str]]) -> None:
    doc.add_heading(f"{discipline}: Self-Study Questions", level=3)
    for n, (stem, options, _, _) in enumerate(qs, 1):
        para(doc, f"{n}. {stem}")
        for letter, opt in zip("ABCDE", options):
            doc.add_paragraph(f"{letter}. {opt}", style="List Bullet 2")
    doc.add_heading(f"{discipline}: Self-Study Questions + Answers", level=3)
    for n, (stem, options, answer, why) in enumerate(qs, 1):
        para(doc, f"{n}. {stem}")
        for letter, opt in zip("ABCDE", options):
            doc.add_paragraph(f"{letter}. {opt}", style="List Bullet 2")
        para(doc, f"Answer: {answer}", bold=True)
        para(doc, why, italic=True)


def faculty(doc, director: str, email: str, office: str) -> None:
    para(doc, director, bold=True)
    para(doc, email)
    para(doc, office)


def discipline_notes(doc, lines: list[str]) -> None:
    para(doc, "Discipline Director Notes:", bold=True)
    bullets(doc, lines)


def page_break(doc) -> None:
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


# ---------------------------------------------------------------- content
def build(out_dir: Path) -> Path:
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Inches(8.5), Inches(11)
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec, side, Inches(0.6))
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(10)
    doc.styles["Normal"].paragraph_format.space_after = Pt(3)
    for name, size in (("Heading 1", 16), ("Heading 2", 12), ("Heading 3", 12), ("Heading 4", 10.5), ("Heading 5", 10)):
        doc.styles[name].font.size = Pt(size)
        doc.styles[name].paragraph_format.space_before = Pt(6)
        doc.styles[name].paragraph_format.space_after = Pt(2)
    for level in range(1, 6):
        doc.styles[f"Heading {level}"].font.color.rgb = NAVY

    footer = sec.footer.paragraphs[0]
    footer.text = DISCLAIMER
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.runs[0].font.size = Pt(8)

    # Cover block
    para(doc, SCHOOL, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, color=NAVY)
    para(doc, COURSE, bold=True, size=28, align=WD_ALIGN_PARAGRAPH.CENTER, color=NAVY)
    para(doc, COURSE_TITLE, size=18, align=WD_ALIGN_PARAGRAPH.CENTER)
    para(doc, CASE, bold=True, size=22, align=WD_ALIGN_PARAGRAPH.CENTER)
    para(doc, "Self-Study Guide · Week 2", italic=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    para(doc, DISCLAIMER, italic=True, size=9, align=WD_ALIGN_PARAGRAPH.CENTER)

    doc.add_heading("TABLE OF CONTENTS", level=1)
    for line in [
        "Course Director Notes",
        "Case Presentation",
        "Immunology",
        "Microbiology",
        "Pharmacology",
    ]:
        doc.add_paragraph(line, style="List Number")
    page_break(doc)

    doc.add_heading("Course Director Notes", level=1)
    boxed(doc, "Welcome to Case 2", [
        "This week follows Jordan Rivera, a college athlete with a painful skin infection. "
        "The case connects innate immunity, the virulence of Staphylococcus aureus, and how "
        "we choose antibiotics when resistance is possible.",
        "Work through the case presentation first, then each discipline in order. "
        "Try every self-study question before you look at the answers.",
        "Small-group session: Thursday, 9:00-11:00 (fictional).",
        "This guide demonstrates AI-assisted study; follow your own school's AI policy for real course materials.",
    ])

    doc.add_heading("Case Presentation", level=1)
    para(doc, "Chief complaint", bold=True)
    para(doc, "“There’s a painful bump on my arm that keeps getting bigger.”")
    para(doc, "History of present illness", bold=True)
    para(doc, (
        "Jordan Rivera is a 19-year-old college wrestler who presents to student health with a "
        "4-day history of a red, swollen, painful lesion on the ulnar (medial) side of the right forearm. It began as what "
        "Jordan thought was a spider bite after practice. Over 48 hours it became firm and warm, "
        "and this morning it felt soft in the center. Jordan reports subjective fevers and "
        "fatigue. Two teammates had similar “boils” this season."
    ))
    para(doc, "Past history", bold=True)
    bullets(doc, [
        "No chronic illnesses; no prior hospitalizations",
        "Medications: none. Allergies: no known drug allergies",
        "Social: shares mats and towels at practice; no injection drug use",
    ])
    para(doc, "Vital signs", bold=True)
    grid(doc, ["Measure", "Value", "Reference"], [
        ["Temperature", "38.4 °C", "36.1-37.2 °C"],
        ["Heart rate", "104 /min", "60-100 /min"],
        ["Blood pressure", "118/72 mmHg", "<120/80 mmHg"],
        ["Respiratory rate", "16 /min", "12-20 /min"],
        ["SpO2", "99% room air", "≥95%"],
    ])
    para(doc, "Physical examination", bold=True)
    para(doc, (
        "A 4 cm erythematous, warm, tender nodule on the ulnar side of the right volar forearm with a fluctuant "
        "center and 2 cm of surrounding erythema. No lymphangitic streaking. Small, tender right "
        "epitrochlear node. The rest of the exam is normal."
    ))
    para(doc, "Laboratory results", bold=True)
    grid(doc, ["Test", "Result", "Flag", "Reference range", "Units"], [
        ["WBC", "14.2", "H", "4.0-11.0", "×10³/µL"],
        ["Neutrophils", "82", "H", "40-70", "%"],
        ["Band forms", "6", "H", "0-5", "%"],
        ["Lymphocytes", "11", "L", "20-40", "%"],
        ["Hemoglobin", "14.6", "", "13.5-17.5", "g/dL"],
        ["Platelets", "268", "", "150-400", "×10³/µL"],
        ["C-reactive protein", "48", "H", "<10", "mg/L"],
        ["Creatinine", "0.9", "", "0.7-1.3", "mg/dL"],
        ["Glucose (random)", "94", "", "70-125", "mg/dL"],
    ])
    para(doc, "Reference ranges are typical adult values (hemoglobin and creatinine shown for an adult male); they vary by laboratory.", italic=True, size=9)
    para(doc, "Procedure and microbiology", bold=True)
    para(doc, (
        "Bedside incision and drainage released 6 mL of thick yellow pus. Gram stain showed "
        "many neutrophils and gram-positive cocci in clusters. Culture grew large golden "
        "colonies with beta-hemolysis on blood agar."
    ))
    grid(doc, ["Test", "Result", "Interpretation", "", ""], [
        ["Catalase", "Positive", "Staphylococcus", "", ""],
        ["Coagulase", "Positive", "S. aureus", "", ""],
        ["Cefoxitin disk screen", "Resistant", "mecA / PBP2a likely (MRSA)", "", ""],
        ["Trimethoprim-sulfamethoxazole", "Susceptible", "", "", ""],
        ["Doxycycline", "Susceptible", "", "", ""],
        ["Clindamycin (D-test)", "Negative D-test; susceptible", "", "", ""],
    ])
    para(doc, (
        "Review the results above. Before reading on, write down: (1) the organism, "
        "(2) the host cells doing most of the work, and (3) what you would treat with and why."
    ), italic=True)

    # ---------------- Immunology
    doc.add_heading("Immunology", level=1)
    faculty(doc, "Discipline Director: Dr. Avery Lin (fictional)",
            "avery.lin@meridian.example", "Office hours: Tuesday 3:00-4:00 (fictional)")
    discipline_notes(doc, [
        "Focus on the first hours of infection: barriers, recognition, recruitment, and killing.",
        "Be able to trace a neutrophil from the bloodstream to the abscess.",
    ])
    topics(
        doc,
        ["Barriers and Pattern Recognition (LO-1101) (14:20)",
         "Neutrophil Recruitment and Extravasation (LO-1102) (12:05)",
         "Phagocytosis and Oxidative Killing (LO-1103) (10:42)"],
        ["Innate Immunity I: Barriers and Recognition (LO-1101)",
         "Innate Immunity II: Neutrophils (LO-1102, LO-1103)"],
        "See Below",
    )
    objectives(doc, [
        "Describe how skin acts as a physical, chemical, and microbial barrier.",
        "Explain how pattern recognition receptors (TLR2) detect gram-positive bacteria.",
        "Outline the steps of neutrophil recruitment: rolling, activation, adhesion, transmigration.",
        "Explain how neutrophils kill bacteria with the respiratory burst.",
        "Predict how S. aureus virulence factors interfere with each step.",
    ])
    doc.add_heading("Neutrophil Recruitment and Killing (LO-1102, LO-1103)", level=3)
    para(doc, "Recognition", bold=True)
    bullets(doc, [
        "Bacterial lipoproteins are the main ligands for TLR2 (with TLR1 or TLR6); whether lipoteichoic acid also signals through TLR2 is debated [PMID:18406368].",
        "Tissue macrophages release IL-1, TNF-α, and IL-8 (CXCL8).",
    ])
    para(doc, "Recruitment (the leukocyte adhesion cascade)", bold=True)
    grid(doc, ["Step", "Endothelial molecule", "Neutrophil molecule", "", ""], [
        ["Rolling", "E-selectin, P-selectin", "Sialyl-Lewis X", "", ""],
        ["Activation", "Chemokines (IL-8)", "Chemokine receptors", "", ""],
        ["Tight adhesion", "ICAM-1", "Integrins (LFA-1, Mac-1)", "", ""],
        ["Transmigration", "PECAM-1 (CD31)", "PECAM-1 (CD31)", "", ""],
    ])
    para(doc, "Killing", bold=True)
    bullets(doc, [
        "Opsonized bacteria (IgG, C3b) are phagocytosed and the phagosome fuses with lysosomes.",
        "NADPH oxidase produces superoxide (the respiratory burst); myeloperoxidase makes hypochlorite.",
        "Pus is mostly dead neutrophils, bacteria, and tissue debris.",
    ])
    para(doc, "Clinical correlation", bold=True)
    bullets(doc, [
        "Chronic granulomatous disease (NADPH oxidase defect): recurrent S. aureus, Aspergillus, and other infections. Often taught as 'catalase-positive organisms', but in a mouse model catalase-negative S. aureus was equally virulent [PMID:11997027].",
        "Leukocyte adhesion deficiency type 1 (CD18 defect): little or no pus with marked neutrophilia; delayed umbilical cord separation is classic but not universal.",
    ])
    questions(doc, "Immunology", [
        ("A neutrophil rolling along the endothelium near Jordan’s abscess is slowed by which endothelial molecule?",
         ["ICAM-1", "E-selectin", "PECAM-1", "VCAM-1", "MHC class II"], "B",
         "Selectins mediate rolling; ICAM-1 binding to integrins mediates tight adhesion."),
        ("A child has recurrent S. aureus abscesses and absent superoxide production on a nitroblue tetrazolium (NBT) test. Which enzyme is defective?",
         ["Myeloperoxidase", "NADPH oxidase", "Superoxide dismutase", "Catalase", "Lysozyme"], "B",
         "No superoxide on NBT = absent respiratory burst = chronic granulomatous disease (NADPH oxidase defect). Myeloperoxidase deficiency spares superoxide production."),
    ])

    # ---------------- Microbiology
    doc.add_heading("Microbiology", level=1)
    faculty(doc, "Discipline Director: Dr. Morgan Patel (fictional)",
            "morgan.patel@meridian.example", "Office hours: Wednesday 1:00-2:00 (fictional)")
    discipline_notes(doc, [
        "Know how to identify S. aureus in the lab and link each virulence factor to a disease.",
        "Practice the sample deck: sample/curriculum/MICRO/Staphylococcus aureus (sample lecture).pptx",
    ])
    topics(
        doc,
        ["Staphylococci: Identification (LO-1201) (9:40)",
         "S. aureus Virulence Factors and Toxins (LO-1202) (16:15)",
         "MRSA: Mechanism and Epidemiology (LO-1203) (8:30)"],
        ["Staphylococcus aureus (LO-1201, LO-1202, LO-1203)"],
        "See Below",
    )
    objectives(doc, [
        "Identify S. aureus using Gram stain, catalase, and coagulase.",
        "Match surface factors (protein A, capsule, coagulase) to how they evade the host.",
        "Distinguish toxin-mediated diseases: TSS, scalded skin syndrome, food poisoning.",
        "Explain the mechanism of methicillin resistance (mecA, PBP2a).",
        "Contrast community-associated and hospital-associated MRSA.",
    ])
    doc.add_heading("Staphylococcus aureus (LO-1201, LO-1202, LO-1203)", level=3)
    grid(doc, ["Factor", "Type", "Action", "Disease link", ""], [
        ["Protein A", "Surface", "Binds Fc of IgG; blocks opsonization", "Immune evasion", ""],
        ["Coagulase", "Enzyme", "Activates prothrombin, forming fibrin", "Fibrin wall around the abscess", ""],
        ["Panton-Valentine leukocidin", "Toxin", "Pore-forming; kills leukocytes", "Associated with CA-MRSA skin infection and necrotizing pneumonia (causal role debated)", ""],
        ["TSST-1", "Superantigen", "Cross-links MHC II and TCR", "Toxic shock syndrome", ""],
        ["Exfoliative toxin", "Protease", "Cleaves desmoglein-1", "Scalded skin syndrome", ""],
        ["Enterotoxin", "Superantigen; heat-stable", "Preformed toxin in food", "Vomiting 30 min-8 h after eating (mean about 3 h)", ""],
    ])
    para(doc, "Methicillin resistance", bold=True)
    bullets(doc, [
        "mecA (on SCCmec) encodes PBP2a, a penicillin-binding protein with low affinity for beta-lactams.",
        "MRSA is resistant to nearly all beta-lactams (exception: anti-MRSA cephalosporins such as ceftaroline).",
        "Community-associated strains often carry PVL (its role in virulence is debated) and cause skin abscesses "
        "in healthy young people, especially with shared equipment and skin contact (athletes, dormitories) "
        "[PMID:17146447][PMID:22759601].",
    ])
    questions(doc, "Microbiology", [
        ("Which test distinguishes S. aureus from coagulase-negative staphylococci?",
         ["Catalase", "Coagulase", "Optochin", "Bacitracin", "Bile solubility"], "B",
         "All staphylococci are catalase positive; among human isolates, S. aureus is the coagulase-positive species."),
        ("Jordan’s isolate is cefoxitin-resistant. What is the molecular basis?",
         ["Beta-lactamase hyperproduction", "Altered PBP (PBP2a) encoded by mecA",
          "Efflux pump", "D-Ala-D-Lac cell wall precursor", "Decreased porin expression"], "B",
         "PBP2a binds beta-lactams poorly, so cell-wall synthesis continues."),
    ])

    # ---------------- Pharmacology
    doc.add_heading("Pharmacology", level=1)
    faculty(doc, "Discipline Director: Dr. Riley Okafor (fictional)",
            "riley.okafor@meridian.example", "Office hours: Friday 10:00-11:00 (fictional)")
    discipline_notes(doc, [
        "Know how each anti-staphylococcal drug works and when MRSA changes the choice.",
        "Incision and drainage is the main treatment for an abscess. Jordan has fever and tachycardia "
        "(two SIRS criteria), so an MRSA-active antibiotic is indicated [PMID:24973422]. In a large trial, "
        "TMP-SMX after drainage also raised the cure rate of uncomplicated abscesses "
        "(80.5% vs 73.6% with placebo, modified intention-to-treat) [PMID:26962903].",
    ])
    para(doc, "Summary of Important Symbols and Parameters", bold=True)
    grid(doc, ["Symbol", "Meaning", "Formula", "", ""], [
        ["Vd", "Volume of distribution", "Dose / C0", "", ""],
        ["CL", "Clearance", "Rate of elimination / plasma concentration", "", ""],
        ["t½", "Half-life", "0.693 × Vd / CL", "", ""],
        ["Css", "Steady-state concentration", "Dosing rate / CL", "", ""],
        ["LD", "Loading dose", "Css × Vd / F", "", ""],
    ])
    topics(
        doc,
        ["Cell Wall Inhibitors I: Beta-lactams (LO-1301) (13:10)",
         "Cell Wall Inhibitors II: Vancomycin (LO-1302) (7:55)",
         "Folate Antagonists and Tetracyclines (LO-1303) (11:20)"],
        ["Antibiotics for Gram-Positive Infections (LO-1301, LO-1302, LO-1303)"],
        "No Written Notes",
    )
    objectives(doc, [
        "Explain how beta-lactams and vancomycin inhibit cell-wall synthesis, and why each fails against resistant organisms.",
        "Choose an oral agent for uncomplicated CA-MRSA skin infection and justify it.",
        "Name key adverse effects of vancomycin, TMP-SMX, and doxycycline.",
        "Calculate a loading dose from Vd and a target concentration.",
    ])
    grid(doc, ["Drug", "Target", "Covers MRSA?", "Key adverse effects", ""], [
        ["Nafcillin / oxacillin", "PBPs (beta-lactamase resistant)", "No", "Neutropenia; interstitial nephritis (rare)", ""],
        ["Cefazolin", "PBPs", "No", "Hypersensitivity", ""],
        ["Vancomycin", "Binds D-Ala-D-Ala", "Yes", "Nephrotoxicity; infusion reaction (flushing)", ""],
        ["TMP-SMX", "DHFR + dihydropteroate synthase", "Yes", "Hyperkalemia, rash, bone marrow suppression", ""],
        ["Doxycycline", "30S ribosome", "Yes", "Photosensitivity, esophagitis; avoid in pregnancy", ""],
    ])
    questions(doc, "Pharmacology", [
        ("After drainage, Jordan is sent home on an oral antibiotic. Which is most appropriate given the susceptibilities?",
         ["Dicloxacillin", "Cephalexin", "Trimethoprim-sulfamethoxazole", "Amoxicillin", "Penicillin V"], "C",
         "The isolate is MRSA and TMP-SMX susceptible; beta-lactams do not cover MRSA."),
        ("A drug has Vd = 50 L and target concentration 20 mg/L with F = 1. What loading dose is needed?",
         ["100 mg", "250 mg", "1,000 mg", "2,500 mg", "5,000 mg"], "C",
         "LD = Css × Vd / F = 20 mg/L × 50 L = 1,000 mg."),
    ])

    doc.add_heading("Selected References", level=1)
    para(doc, "Every reference below was checked in PubMed. A citation shows a source exists; open it to see whether it supports the claim.", italic=True)
    bullets(doc, [
        "Stevens DL, et al. IDSA practice guidelines for skin and soft tissue infections, 2014 update. [PMID:24973422]",
        "Talan DA, et al. Trimethoprim-sulfamethoxazole versus placebo for uncomplicated skin abscess. N Engl J Med 2016. [PMID:26962903]",
        "Malachowa N, Kobayashi SD, DeLeo FR. Community-associated MRSA and athletes. Phys Sportsmed 2012. [PMID:22759601]",
        "Amagai M, et al. Toxin in bullous impetigo and staphylococcal scalded-skin syndrome targets desmoglein 1. Nat Med 2000. [PMID:11062541]",
        "Boyle-Vavra S, Daum RS. Community-acquired MRSA: the role of Panton-Valentine leukocidin. Lab Invest 2007. [PMID:17146447]",
        "Zähringer U, et al. TLR2 - promiscuous or specific? Immunobiology 2008. [PMID:18406368]",
        "Messina CG, et al. Catalase negative S. aureus retain virulence in a mouse model of CGD. FEBS Lett 2002. [PMID:11997027]",
    ])

    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / FILENAME
    doc.save(out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=Path("sample/curriculum/GUIDE"))
    args = ap.parse_args()
    print(f"Saved {build(args.out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
