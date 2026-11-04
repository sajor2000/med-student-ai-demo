# mnemonic-art reference

## Prompt patterns

The script builds: `Illustrate the concept "<concept>" as a memory aid. Scene: <scene>. <style suffix>`.
The style suffix asks for a simple cartoon with no text labels, no real people, and no patients. Image models
garble lettering, so the caption is the only text, added afterwards by the script.

Good scenes are one concrete picture with one hook:
- Sound-alike pun: "a staph bubble wearing a golden crown (aureus = golden)".
- Mechanism as action: "a pair of scissors cutting the threads between skin cells" for a protein that cleaves a
  cell-adhesion link.
- Contrast pair: "two doors, one with a catalase fountain, one dry" for a lab test that splits two organisms.

Keep scenes about objects and cartoon characters. Skip anatomy accuracy claims; the picture is a hook, not a figure.
Use `/visualize` for an accurate, cited diagram.

## What the script refuses

Before any network call (after the student's own review, on concept and scene together) it refuses:

- numbers with 6 or more digits, "MRN"/"DOB"/"date of birth"/"medical record", dates, birth years, and a name next
  to an age ("Name, 45"; "45-year-old named")
- email addresses; US phone numbers ("(312) 555-0100", "312-555-0100", "312.555.0100", "+1 312 555 0100")
- street addresses (a number plus a street word: St, Ave, Rd, Blvd, Dr, Lane, Court, Way ...)
- ZIP and ZIP+4 codes; SSN-like patterns (123-45-6789)
- MRN-like identifiers ("#48213", "chart/account/patient number 4821")
- URLs with a query string
- titles followed by a name (Mr, Mrs, Ms, Miss, Dr, Patient + Capitalized word)
- likely personal names: two or more Title-Case words in a row, none of which is on a built-in allowlist of medical
  and common terms (Graves, Hashimoto, Cushing, Lyme, Staphylococcus, Gram, Type, Vitamin ...). "John Smith"
  is refused; "Graves disease" and "Type 2 diabetes" pass.

A refusal tells the student to describe the idea without people's names or contact details and offers a generic
rephrase ("a patient", "a farmer"). The gate is heuristic and fail-closed: it will miss some identifiers (a lone first
name, a city) and refuse some harmless text (a five-digit count reads as a ZIP). The student's confirmation in step 2
is the real control; the script's check is a second safeguard.

## Key, cost, and privacy

- The student uses their own key: create it at openrouter.ai, set a spend limit on it, and
  `export OPENROUTER_API_KEY=...`. The script never prints, logs, or stores it.
- One image usually costs a few cents; the model is `google/gemini-2.5-flash-image` unless `--model` or
  `MSAD_IMAGE_MODEL` says otherwise. Check the model's current price on openrouter.ai.
- Requests set `provider.data_collection: "deny"`, so OpenRouter routes only to providers that do not train on or
  retain prompts. The prompt still leaves the machine, which is why the student confirms it first.
- Output: `output/<case>/art/<slug>-<hash>.png` (slug plus a short hash of the full concept, so similar names never collide; an image of a different concept is never overwritten) with the caption "AI illustration — not a reference" in a bottom band,
  and `<slug>.json` holding prompt, model, and timestamp.

## OpenRouter privacy settings (ZDR)

Requests ask for `data_collection: "deny"`, and the student's account can also enforce zero-data-retention (ZDR) or
a data policy at https://openrouter.ai/settings/privacy. Many image endpoints keep data, so these settings can
leave a model with no allowed image endpoint. The script then gets an error naming ZDR, a data policy, or a
guardrail, and prints a one-line hint.

On that error the student enables an image-capable endpoint (or turns off zero-data-retention for image models)
in the privacy settings and retries ONCE. Do not cycle through other models: every retry sends the prompt again
to a third party.

## School AI policy

Generated images may be restricted by a course or school AI policy. Check the policy before putting an image in a
shared deck or submitted work. Keep these images in personal study material, and cite the notes for facts.
`check.py` reports any citation pointing into `output/<case>/art/` as unresolved.
