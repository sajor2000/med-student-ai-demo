# anki-sync reference

## What *owned* means

A note is owned when all of these hold:
- it carries the tags `msad` and `msad-id::<id>`;
- every one of its cards sits in the deck `AI Study::<case>` or its subdeck `AI Study::<case>::misses`.

Cards whose `tags` include `miss` (made from missed vignette, teach-back or quiz questions) go to `AI Study::<case>::misses`;
all other cards go to `AI Study::<case>`. Re-syncing updates notes in place and never moves them.

`<id>` is `msad-<sha1[:12]>` of the card front (flashcards, same as `export.py`) or of `slug:label-id` (diagram labels).
The script writes and updates only owned notes. A tagged note with a card in another deck is skipped and counted.
A student's own notes, and the `AI Study::<case>::diagrams-offline` subdeck from `diagrams.apkg`, are never touched.

Adoption: a note in the owned deck with the `msad` tag (`export.py` adds it to every row of the `.anki.txt` files) but
no `msad-id` tag, whose Front or Text hashes to a CSV card's id, was imported by hand from those files. The script tags
it and updates it in place instead of adding a duplicate. A note with the same front but no `msad` tag is the student's
own: it is skipped, counted, and left untouched (`skip: same front as a generated card but not created by this repo`).

## Install AnkiConnect

1. Anki desktop: Tools, Add-ons, Get Add-ons.
2. Paste code `2055492159`, then restart Anki.
3. Keep Anki open while syncing. The add-on listens on `http://127.0.0.1:8765` (loopback only; the script refuses other hosts).

## Image Occlusion cards

Anki creates the "Image Occlusion" note type the first time its editor opens: Add, then choose Image Occlusion, once.
Without it the script skips diagram notes and prints that hint. Alternative: import `output/<case>/diagrams.apkg`
(portable masked cards). Use one path per diagram.

## Flags

`--csv`, `--diagrams`, `--threshold N` (lapses that count as a weak spot, default 3), `--url` (loopback only).
Weak spots append to `output/<case>/weak-spots.md` once per card; ids already written are in `output/<case>/.weak-spots-synced.json`.

## Troubleshooting

- `not reachable`: Anki is closed, or the add-on is missing. Open Anki and retry.
- `API version`: update the add-on (Tools, Add-ons, check for updates).
- `skipped` above 0: read the printed hint. Foreign-deck skips are deliberate.
- A card shows twice: it was imported into a different deck first; move or delete the stray copy in Anki.
