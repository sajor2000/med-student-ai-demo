# /// script
# requires-python = ">=3.11"
# dependencies = ["python-pptx>=1.0"]
# ///
"""Build sample/curriculum/MICRO/Staphylococcus aureus (sample lecture).pptx.

Original, synthetic teaching text written for this demo (not from any school),
so the repo can be cloned and run without real course files.
"""
from pathlib import Path
from pptx import Presentation

SLIDES = [
    ("Staphylococcus aureus (sample lecture)", ["Synthetic demo lecture for med-student-ai-demo", "Learning objectives: (1) identify S. aureus in the lab; (2) link virulence factors to disease; (3) explain methicillin resistance"]),
    ("Lab identification", ["Gram-positive cocci in clusters", "Catalase positive (separates staphylococci from streptococci)", "Coagulase positive (separates S. aureus from most other staphylococci)", "Beta-hemolytic, golden colonies on blood agar"]),
    ("Surface virulence factors", ["Protein A binds the Fc region of IgG, blocking opsonization and phagocytosis", "Capsule (polysaccharide) resists phagocytosis", "Clumping factor binds fibrinogen"]),
    ("Toxins and toxin-mediated disease", ["TSST-1 is a superantigen: cross-links MHC II and T-cell receptors outside the peptide groove, causing massive cytokine release (toxic shock syndrome)", "Exfoliative toxins cleave desmoglein-1, causing staphylococcal scalded skin syndrome", "Preformed heat-stable enterotoxins cause rapid-onset vomiting (food poisoning, 1-6 h)", "Panton-Valentine leukocidin (PVL) kills leukocytes; associated with necrotizing skin infection and pneumonia"]),
    ("Clinical spectrum", ["Skin and soft tissue: impetigo, furuncles, abscesses, cellulitis", "Invasive: bacteremia, endocarditis (often tricuspid valve in people who inject drugs), osteomyelitis, septic arthritis", "Abscess formation is driven by neutrophil recruitment"]),
    ("Methicillin resistance (MRSA)", ["mecA gene encodes PBP2a, a penicillin-binding protein with low affinity for beta-lactams", "mecA is carried on a mobile element, SCCmec", "Result: resistance to almost all beta-lactams", "Options for serious MRSA infection include vancomycin or daptomycin (daptomycin not for pneumonia: inactivated by surfactant)"]),
]

prs = Presentation()
for title, bullets in SLIDES:
    s = prs.slides.add_slide(prs.slide_layouts[1])
    s.shapes.title.text = title
    tf = s.placeholders[1].text_frame
    tf.text = bullets[0]
    for b in bullets[1:]:
        tf.add_paragraph().text = b
out = Path("sample/curriculum/MICRO/Staphylococcus aureus (sample lecture).pptx")
out.parent.mkdir(parents=True, exist_ok=True)
prs.save(out)
print(out)
