---
name: image-curation
description: Collect image candidates for vocabulary words, propose the best one per word, and hand the owner a local review page to confirm or override before the images reach the deck. Use whenever the user asks for pictures or illustrations for words, cards or a chapter, wants to replace pictures the generator picked automatically, or complains that the current images are random or off-topic - even when they never mention a review page.
---

# Image Curation Loop

## Why this loop exists

The automatic image search queries the bare word and keeps the first result
that downloads. That works for concrete nouns and fails for abstract ones:
the failure is in the *query*, not in the ranking, so no amount of scoring
rescues a result set where nothing fits. Rewriting the query is judgement
work, and judging whether the picture actually evokes the meaning is the
owner's call, not yours.

So the split is: you do the searching and propose a pick with a reason; the
owner confirms or overrides in one pass on a local page; confirmed images
land in the inbox the deck generator already reads.

## The loop

1. **Collect** several candidates per word.
2. **Propose** one pick per word, with a one-line reason.
3. **Generate** the review page and hand it to the owner.
4. **Wait** for the owner to adjust and save their choices.
5. **Write back** the confirmed images, then clean up.

Do not compress this: skipping step 3 and asking about words in chat costs a
round trip per word, which is exactly the friction this loop removes.

## Where the working folder goes

Build everything for one round in `image-review/<source>/` inside the
repository (git-ignored), not in a temp directory: browsers refuse File
System Access writes into system locations such as `AppData\Local\Temp`, so
the owner would be unable to save their choices back next to the page.

```
image-review/<source>/
├── spec.json                       # your queries / no-image decisions
├── candidates/<word-key>/<id>.jpg
├── manifest.json                   # written by collect_candidates.py
└── review.html
```

## Step 1 - collect candidates

Show **four or five** candidates per word - enough to compare at a glance in
a single row, few enough that the owner is not scrolling through near
duplicates. Search more widely than that, then keep the best five; the point
of the page is a quick decision, not an exhaustive gallery.

Two kinds of words need two different approaches:

- **Concrete nouns** (`schematics`, `prosthetic`) - the word itself is a fine
  query. Do not over-think these; the plain search usually wins.
- **Abstract words** (`parochial`, `marginal`, `on the verge of`) - query a
  *scene* that evokes the meaning, not the word: "person standing on cliff
  edge" for *on the verge of*, "green seedling sprouting" for *viable*.
  Etymology often supplies the scene (viable / vita = life).

When a word has no plausible picture at all, propose **no image**. An
irrelevant picture is worse than none: it competes with the meaning during
recall. Saying so honestly is a valid, expected outcome.

### Words not to search blind

Real vocabulary lists contain words whose image search should not be run at
face value:

- **Explicit or vulgar slang** - an image search on the literal phrase
  returns pornography or nothing usable. Do not run it.
- **Clinical and surgical terms** (wound debridement, tissue necrosis,
  amputation) - the honest results are graphic medical photographs. They are
  not what someone wants on a flashcard they will see hundreds of times.
- **Anything where a plausible query would return disturbing results.** If
  you can predict that before searching, that prediction is the answer.

For these, send the word to the page with an empty candidate list, `pick`
set to `null`, and the `reason` stating why nothing was collected - for
example "explicit slang, not searched on purpose" or "clinical imagery
only". The page renders that reason in place of the thumbnails, so the owner
sees a decision with its justification instead of an empty row, and can
still override it with *Need more options* if they disagree.

This is a judgement call you make before spending a search, not a filter you
apply to results.

### When the search quota runs out

Keyed image search is metered. Google Custom Search, the usual backend here,
allows about a hundred queries per day for free, and one round costs roughly
a query per word plus every re-query for words that needed a second angle -
so a chapter re-run or two exhausts a day's budget. The API answers `403` or
`429` once it is spent.

Do not stop, and do not quietly hand over a page with fewer candidates.
The collector (Step 2) already falls back to keyless sources automatically
once Google answers `403`/`429`; these are what it switches to:

- **Openverse** (`api.openverse.org`) - aggregates openly licensed photos;
  good general coverage, weaker on staged conceptual scenes.
- **Wikimedia Commons** (`commons.wikimedia.org/w/api.php`) - encyclopedic
  and reliable for concrete nouns, objects, places and diagrams.

Two things to keep in mind when switching. Coverage differs, so a query that
worked against one backend may return nothing against another - rephrase
rather than concluding the word has no image. And a network can be
restricted in ways that make a source look broken: check that the host is
actually reachable before deciding it is unusable.

Tell the owner which source the candidates came from when it is not the
usual one. Licences differ between backends, and they may care.

Keep the full-size originals - the page shows downscaled previews, but the
originals are what eventually reach the deck.

## Step 2 - author the spec and collect

You make the judgement calls; a tool does the fetching. Write a **spec** -
one entry per word carrying the query (or queries) you designed, or
`no_image: true` for a word you decided not to search - then let the collector
query the backends, validate the downloads, dedupe and assemble the manifest:

```bash
python .claude/skills/image-curation/tools/collect_candidates.py <spec.json> [--per-word 5] [--providers google,openverse,wikimedia]
```

A spec entry is `word` (byte-for-byte the source word), optional `translation`,
`example` and `reason`, and either `queries: [...]` or `no_image: true`. The
collector writes `manifest.json` and downloads the originals into
`candidates/<word-key>/`; it tries Google first (keys from `config.properties`)
and falls back to Openverse then Wikimedia on quota, so you never hand over a
thinner page. Run it with `--help` for all flags. Do not hand-fetch images or
hand-write the manifest - that is exactly the repeat work this tool removes.

The manifest it produces is the contract the review page reads:

```json
{
  "source": "chapter-file-name-without-extension",
  "words": [
    {
      "word": "On the verge of",
      "translation": "На грани",
      "example": "...had been on the verge of war...",
      "pick": "c5",
      "reason": "A rock ledge over a canyon - literally on the edge",
      "candidates": [
        {"id": "a1", "file": "candidates/verge/a1.jpg", "query": "on the verge of"},
        {"id": "c5", "file": "candidates/verge/c5.jpg", "query": "person standing on cliff edge"}
      ]
    }
  ]
}
```

- `word` must match the source word list **byte for byte** - it becomes the
  image file name later, and a near-miss means the deck silently keeps the
  old picture.
- `pick` defaults to the first candidate; it is `null` when you proposed no
  image, and `candidates` is empty when the word was not searched at all - the
  `reason` then carries the explanation shown on the page.
- `file` paths are relative to the manifest.
- `reason` is one line explaining *why this picture means this word*, not what
  is depicted. Set it in the spec; refine any pick or reason directly in the
  manifest before generating the page.

## Step 3 - generate the page

```bash
python .claude/skills/image-curation/tools/image_review.py <manifest.json>
```

This writes a self-contained `review.html` next to the manifest. Tell the
owner the path, and state plainly what they are looking at: their word list,
your proposal preselected, the alternatives beside it, and two extra choices
per word - *No image* and *Need more options*.

*Need more options* is the important one to mention. Without it the owner
settles for the least bad candidate and you never learn the set was
unusable; with it you get a precise instruction to search again.

## Step 4 - wait

The page saves `choices.json` through the browser's file picker; when the
browser refuses, it shows the same JSON in a dialog to copy or download. Look
for the file next to the page first, then in the downloads folder, and ask
where it landed rather than searching the disk blindly. Do not guess at the
owner's intent while waiting - the whole point is that this decision is
theirs.

```json
{
  "source": "chapter-file-name-without-extension",
  "choices": {
    "Parochial": {"action": "keep", "pick": "c3"},
    "Marginal": {"action": "none", "pick": null},
    "Viable": {"action": "more", "pick": null}
  }
}
```

## Step 5 - write back and clean up

`apply_choices.py` reads the manifest and `choices.json` and copies the
confirmed **originals** into the inbox for you:

```bash
python .claude/skills/image-curation/tools/apply_choices.py <manifest.json> <choices.json> --dry-run   # show the plan
python .claude/skills/image-curation/tools/apply_choices.py <manifest.json> <choices.json>             # copy them
```

It resolves the inbox as `<images root>/<source>/` (`IMAGES_ROOT` from
`config.properties`, or the project `images/` folder), names each file
`<word><ext>`, and handles the three actions:

- `keep` - copies the original candidate (never the page preview) into the
  inbox the deck generator prefers over its own search.
- `none` - writes nothing. The word deliberately has no picture.
- `more` - left for you to run a fresh search round with *different* queries
  (repeating the rejected ones wastes a cycle), then apply that round's
  choices too.

Writing into the owner's vault needs their approval first: run `--dry-run`,
show what will be written where, then wait.

Finally delete the temporary candidates folder, the manifest, the page and
`choices.json`. What survives is exactly the confirmed images.

## Failure modes worth remembering

| Symptom | Cause |
|---|---|
| Deck still shows the old picture | The file name does not match the source word exactly |
| Image looks soft in the deck | The downscaled preview was copied instead of the original |
| Same bad candidates come back | A `more` round reused the previous queries |
| Owner cannot find the page | The manifest folder path was never reported |
