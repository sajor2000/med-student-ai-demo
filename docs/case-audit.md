# Case audit: BMS 501 Case 2, Jordan Rivera (fictional)

Audit of every factual claim in `scripts/make_case_guide.py` (case data, lab values, mechanisms, tables,
formulas, and all six self-study questions). Run for the 2026-11-04 class demo. The patient, school, and faculty are invented;
only the medicine is checked against real sources.

**Tools:** PubMed MCP (`pubmed_fetch_articles`, `pubmed_search_articles`), Paperclip MCP (`evidence`), Tavily MCP
(`tavily_search`, `tavily_extract`; it was rate limited for part of the run). Every PMID below came from a tool call in this run and is
verified by `scripts/check.py`. Paperclip identifiers beginning `PMC` are open-access papers it returned.

**Verdict counts (45 rows):** supported 29, corrected 12, removed 0, not independently verified 2, not a factual claim 2.

**Rule applied:** a source has to state the claim. Where it states something narrower, the guide text was narrowed. The "uncertain" list is at the bottom.

| # | Claim | Verdict | Source | Tool |
|---|---|---|---|---|
| 1 | Case: 19-y wrestler, shared mats/towels, teammates with 'boils', spider-bite belief; CA-MRSA skin abscess in athletes | supported | PMID 22759601 (CA-MRSA and athletes review) | PubMed MCP |
| 2 | HPI: lesion on volar forearm with a tender epitrochlear node | corrected: lesion moved to the ulnar side (epitrochlear nodes drain the ulnar forearm/hand) | PMID 6821845 (ulnar distribution is the classic epitrochlear drainage); Paperclip evidence run | Paperclip MCP + PubMed MCP |
| 3 | Vitals: T 38.4 C, HR 104, RR 16, SpO2 99%, references 36.1-37.2 C, 60-100, 12-20, >=95% | supported (sources vary by about 0.3 C and 2-4 breaths/min) | Cleveland Clinic and Johns Hopkins vital-sign pages | Tavily MCP |
| 4 | Vitals: BP 122/74 against reference <120/80 | corrected: value changed to 118/72 so the table has no unflagged out-of-range value | Cleveland Clinic adult BP 90/60-120/80 | Tavily MCP |
| 5 | Labs: WBC 4.0-11.0, platelets 150-400, Hb 13.5-17.5 (male) | supported (NBME lists WBC 4.5-11.0; ranges are lab-dependent, note added) | NBME Laboratory Reference Values (2026) | Tavily MCP |
| 6 | Labs: neutrophils 40-70%, bands 0-5%, lymphocytes 20-40% | supported as typical clinical-lab ranges (NBME lists mean-type ranges: segs 54-62, bands 3-5, lymphs 25-33); note added | NBME Laboratory Reference Values | Tavily MCP |
| 7 | Labs: creatinine 0.7-1.3 mg/dL (male) | supported | MedlinePlus range quoted by HealthMatters; kidneyhypertension.net | Tavily MCP |
| 8 | Labs: CRP <10 mg/L; glucose reference | supported / corrected: CRP cutoffs vary by lab (8-10 mg/L upper limit common; healthy adults usually <3 mg/L), so <10 mg/L stands and 48 mg/L is clearly elevated. Glucose relabelled "random" with 70-125 mg/dL, because 70-99 mg/dL is the fasting range and a clinic visit is non-fasting | https://medlineplus.gov/ency/article/003356.htm ; https://www.testing.com/tests/c-reactive-protein-crp ; https://medlineplus.gov/ency/article/003482.htm | Tavily MCP |
| 9 | Lab interpretation: bandemia and left shift, lymphopenia as stress response in bacterial infection | not independently verified (descriptive; no numeric claim) | none | none (reasoning only) |
| 10 | Procedure: I&D, 6 mL pus, Gram stain cocci in clusters, golden beta-hemolytic colonies | supported (standard S. aureus identification) | Foster, Medical Microbiology (NCBI Bookshelf NBK8448) | Tavily MCP |
| 11 | Catalase + / coagulase + identify S. aureus; coagulase separates S. aureus from coagulase-negative staph | supported; Q explanation corrected: 'only S. aureus' became 'among human isolates' (S. intermedius group is also coagulase positive) | NBK8448 | Tavily MCP |
| 12 | Cefoxitin-resistant means mecA/PBP2a (MRSA) | supported | PMID 9164468 (mechanisms of methicillin resistance); Brakstad and Maeland | PubMed MCP |
| 13 | mecA on SCCmec encodes PBP2a with low beta-lactam affinity | supported (abstract read: PBP2a, low beta-lactam affinity, encoded by mecA in the mec region) | PMID 9164468 | PubMed MCP |
| 14 | MRSA resistant to nearly all beta-lactams (exception ceftaroline) | corrected: 'anti-MRSA cephalosporins such as ceftaroline' | FDA ceftaroline (Teflaro) review, NDA 200327 | Tavily MCP |
| 15 | Clindamycin D-test negative and susceptible; TMP-SMX and doxycycline susceptible | n/a (fictional susceptibility data; internally consistent) | none; fictional susceptibility data | none (reasoning only) |
| 16 | Skin is a physical, chemical, and microbial barrier | not independently verified (textbook statement) | none | none (reasoning only) |
| 17 | TLR2 (with TLR1/TLR6) senses bacterial lipoproteins; LTA role debated | supported (wording kept; citation added) | PMID 18406368 | Paperclip MCP + PubMed MCP |
| 18 | Macrophages release IL-1, TNF-alpha, IL-8 (CXCL8) to recruit neutrophils | supported | PMC13124807, PMC9728535 via Paperclip evidence | Paperclip MCP |
| 19 | Rolling by E/P-selectin and sialyl-Lewis X; tight adhesion by ICAM-1 with LFA-1/Mac-1; PECAM-1 for transmigration; IL-8 activates integrins | supported | PMC9728535 (Blood 2021 review), PMC13124807 | Paperclip MCP |
| 20 | Q1 stem: 'binds which ligand on the endothelium' (E-selectin) | corrected: reworded to 'slowed by which endothelial molecule' (single best answer: E-selectin; P-selectin not offered) | PMC9728535 | Paperclip MCP |
| 21 | Opsonized bacteria phagocytosed; NADPH oxidase makes superoxide; MPO makes hypochlorite | supported (textbook; consistent with MPO-dependent chlorination described in the CGD paper) | PMID 11997027 | PubMed MCP |
| 22 | CGD: recurrent S. aureus and Aspergillus infections; 'catalase-positive' teaching is overstated | supported (caveat retained from first pass) | PMID 11997027 | PubMed MCP |
| 23 | LAD-1 (CD18 defect): no pus and delayed cord separation | corrected: 'little or no pus with marked neutrophilia; delayed cord separation classic but not universal' | PMC7772426 (supports), PMC10997710 (cord separation not a hallmark); PMC6749021 | Paperclip MCP |
| 24 | Q2: negative dihydrorhodamine test with recurrent S. aureus abscesses means NADPH oxidase defect (option A: myeloperoxidase) | corrected: DHR oxidation also needs MPO, so MPO deficiency can read as abnormal; stem now uses an NBT test (superoxide-dependent) | PMID 27301573; PMC5946934; PMC7383027 | Paperclip MCP |
| 25 | Q2 explanation: 'catalase-positive organisms escape killing' | corrected: removed (contradicted the guide's own CGD caveat); replaced with respiratory-burst explanation and MPO note | PMID 11997027 | PubMed MCP |
| 26 | Protein A binds IgG Fc and blocks opsonization/phagocytosis | supported | PMC9882747, PMC4693167 | Paperclip MCP |
| 27 | Coagulase converts fibrinogen to fibrin | corrected: coagulase activates prothrombin, which then makes fibrin; table says 'Activates prothrombin, forming fibrin' | PMC3257306 (Coa and vWbp are prothrombin activators); PubMed 2744851 | Tavily MCP |
| 28 | PVL: pore-forming leukotoxin linked to CA-MRSA skin infection and necrotizing pneumonia | corrected: now 'associated with ... (causal role debated)'; PMID added to the MRSA bullet | PMID 17146447 | PubMed MCP |
| 29 | TSST-1 superantigen cross-links MHC II and the TCR (Vbeta), toxic shock syndrome | supported (TSST-1 is Vbeta2-specific; 'cross-links' kept at teaching level) | PMC7572075, PMC3153290, PMC3417409 | Paperclip MCP |
| 30 | Exfoliative toxin cleaves desmoglein-1 (scalded skin) | supported | PMID 11062541 (exfoliative toxin A) | PubMed MCP |
| 31 | Enterotoxin: preformed, heat-stable; vomiting 2-8 h after eating | corrected: 30 min-8 h, mean about 3 h (CDC); lecture deck's 1-6 h is a typical core, flagged as a discrepancy in the demo | CDC staph food poisoning page; CDC MMWR 6250a2 | Tavily MCP |
| 32 | CA-MRSA causes abscesses in healthy young people with shared equipment and skin contact | supported (PVL qualifier added) | PMID 22759601; PMID 17146447 | PubMed MCP |
| 33 | Antibiotic indicated after I&D when SIRS is present (fever >38, HR >90); MRSA-active agent | supported; text now says 'two SIRS criteria' and 'MRSA-active' | PMID 24973422; IDSA guideline text (idsociety.org) | PubMed MCP + Tavily MCP |
| 34 | TMP-SMX after drainage: cure 80.5% vs 73.6% | supported; qualifier 'modified intention-to-treat' added (per-protocol was 92.9% vs 85.7%) | PMID 26962903 | PubMed MCP |
| 35 | Beta-lactams (nafcillin, cefazolin) do not cover MRSA | supported | PMID 9164468 | PubMed MCP |
| 36 | Nafcillin AEs: neutropenia, interstitial nephritis (rare) | supported (first-pass fix confirmed against label) | FDA nafcillin label, NDA 050655 | Tavily MCP |
| 37 | Vancomycin binds D-Ala-D-Ala; AEs nephrotoxicity and infusion reaction | supported | FDA vancomycin labels (NDA 209481, 211962); PMC9414505 | Tavily MCP + Paperclip MCP |
| 38 | TMP-SMX targets DHFR and dihydropteroate synthase; AEs hyperkalemia, rash, marrow suppression | supported | DailyMed sulfamethoxazole/trimethoprim label; PMC8069106 | Tavily MCP + Paperclip MCP |
| 39 | Doxycycline binds 30S; photosensitivity, esophagitis, avoid in pregnancy | supported (label: tooth discoloration in late pregnancy and childhood) | FDA doxycycline labels (NDA 050795, 050582) | Tavily MCP |
| 40 | Formulas: Vd = Dose/C0; CL = elimination rate/concentration; t1/2 = 0.693 Vd/CL; Css = dosing rate/CL; LD = Css x Vd / F | supported | StatPearls NBK557418, NBK553132, NBK557852 | Tavily MCP |
| 41 | Pharm Q2: 20 mg/L x 50 L = 1,000 mg (answer C) | supported (single correct option) | StatPearls NBK553132 | Tavily MCP |
| 42 | Pharm Q1: oral agent after MRSA abscess drainage is TMP-SMX (answer C); beta-lactams wrong | supported (single defensible answer among options) | PMID 24973422; PMID 26962903 | PubMed MCP |
| 43 | Micro Q2: cefoxitin resistance is due to altered PBP (mecA); D-Ala-D-Lac is VRE; beta-lactamase hyperproduction stays cefoxitin-susceptible | supported (single defensible answer) | PMID 9164468; PMC8069106 | PubMed MCP + Paperclip MCP |
| 44 | Reference list: author/title/journal for 22759601, 11062541, 11997027, 24973422, 26962903 | corrected: 22759601 authors completed (Malachowa, Kobayashi, DeLeo); the rest matched PubMed; two references added (17146447, 18406368) | PMIDs 22759601, 11062541, 11997027, 24973422, 26962903, 17146447, 18406368 | PubMed MCP |
| 45 | Policy line: 'follow your own school's AI policy' added to Course Director Notes | n/a (new text, not a factual claim) | docs/RESPONSIBLE-USE.md | none (reasoning only) |

## Each question has exactly one defensible answer

| Question | Answer | Why the distractors fail |
|---|---|---|
| Immuno 1 (rolling) | B, E-selectin | ICAM-1 holds adhesion, PECAM-1 drives transmigration, VCAM-1 is VLA-4 mediated and not the neutrophil rolling step, MHC II is irrelevant |
| Immuno 2 (NBT negative) | B, NADPH oxidase | MPO deficiency spares superoxide (NBT positive), SOD and catalase deficiencies are not CGD, lysozyme is not a burst enzyme |
| Micro 1 (coagulase) | B | Catalase is positive in all staphylococci; optochin, bacitracin, and bile solubility are streptococcal tests |
| Micro 2 (cefoxitin-resistant) | B, mecA PBP2a | Beta-lactamase hyperproduction stays cefoxitin-susceptible, D-Ala-D-Lac is vancomycin resistance, efflux and porins are not the mechanism |
| Pharm 1 (oral agent) | C, TMP-SMX | Dicloxacillin, cephalexin, amoxicillin, and penicillin V do not cover MRSA |
| Pharm 2 (loading dose) | C, 1,000 mg | 20 x 50 = 1,000; the other options are distractor arithmetic |

## Uncertain or left alone

- Wrestling-specific CA-MRSA data: PMID 22759601 is a general CA-MRSA and athletes review; it supports the setting, not any single number.
- CRP and glucose ranges were confirmed afterwards with Tavily (MedlinePlus); glucose was relabelled as a random value.
- The sample lecture (`MICRO/Staphylococcus aureus (sample lecture)`) says enterotoxin onset 1-6 h; the guide now says 30 min-8 h (CDC). Both stay in the repo on purpose as a demo "Discrepancy". The lecture is shared with other branches and was not edited here.
- The TLR2 statement keeps "debated": one review (PMID 18406368) says only lipoproteins are sensed at physiologic concentrations, an older review says LTA signals through TLR2.
- The Paperclip "refute" hits on protein A, the superantigen mechanism, and selectin/integrin rolling were about mouse strains, structural detail, and LFA-1's role in rolling, and do not contradict the teaching-level statements.
- PMID 9164468's abstract was read afterwards and supports rows 12, 13, 35, and 43. PMID 37982596 (a virulence review) did not directly support row 13 and was dropped as its source.
