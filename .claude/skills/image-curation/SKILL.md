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
├── candidates/<word-key>/<id>.jpg
├── manifest.json
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

Keep the full-size originals - the page shows downscaled previews, but the
originals are what eventually reach the deck.

## Step 2 - write the manifest

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
- `pick` may be `null` when you propose no image.
- `file` paths are relative to the manifest.
- `reason` is one line explaining *why this picture means this word*, not what
  is depicted. The owner reads it to decide whether to trust the pick.

## Step 3 - generate the page

```bash
python tools/image_review.py <manifest.json>
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

For each entry:

- `keep` - copy the **original** candidate file (never the preview embedded
  in the page) to `<images root>/<source>/<word>.jpg`. That folder is the
  inbox the deck generator prefers over its own search.
- `none` - write nothing. The word deliberately has no picture.
- `more` - start a fresh search round with *different* queries. Repeating the
  same queries wastes a cycle; the owner already saw those results and
  rejected them.

Writing into the owner's notes or vault needs their approval first - show
what will be written where, then wait.

Finally delete the temporary candidates folder, the manifest, the page and
`choices.json`. What survives is exactly the confirmed images.

## Failure modes worth remembering

| Symptom | Cause |
|---|---|
| Deck still shows the old picture | The file name does not match the source word exactly |
| Image looks soft in the deck | The downscaled preview was copied instead of the original |
| Same bad candidates come back | A `more` round reused the previous queries |
| Owner cannot find the page | The manifest folder path was never reported |
