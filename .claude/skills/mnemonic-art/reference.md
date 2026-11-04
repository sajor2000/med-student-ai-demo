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

Before any network call it refuses numbers with 6 or more digits, "MRN"/"DOB"/"date of birth", dates, birth years,
and a name next to an age ("Name, 45"; "45-year-old named"). A refusal means: rewrite the scene without patient
details. The check is a second safeguard; the student review in step 2 is the first.

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
