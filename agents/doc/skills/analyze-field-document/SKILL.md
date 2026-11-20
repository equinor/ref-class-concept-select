---
name: analyze-field-document
description: "Convert a field-development document (PDF, scanned or digital, any language) to English Markdown with figure cut-outs and plot data, register its facts, and analyse it for concept selection, production strategy and uncertainties. Use for any new source document in the doc domain."
---

# Analyse a field-development document

The core procedure of the doc domain. It turns a source document into
material that people and other agents can rely on, then answers set questions
about it. It was worked out on the Volve PDO (digital, Norwegian) and the
Discovery report (scanned, English); both remain as worked examples.

Read first: `agents/doc/README.md` (charter) and
`agents/sys/GUIDELINES.md` (locations, provenance, quality gates).

## What you deliver

For a source `<dir>/<stem>.pdf` under `$VOLVE_DATA`:

| Deliverable | Location |
|---|---|
| Markdown conversion, English, one page marker per page | `data/volve/<dir>/md/<stem>.md` |
| Figure cut-outs; plot data as CSV beside them | `data/volve/<dir>/figs/<stem>_pNNN_fig<number>.png`, `…csv` |
| Plot data workbook (if the document has production or cost charts) | `data/volve/<dir>/md/<stem>.xlsx` |
| Facts | `data/facts/<source-id>.csv` |
| Analysis | `agents/doc/out/<stem>_anlz.md` |
| Report, if asked for | `agents/doc/out/<name>/index.html` |

If the file name carries `cmt`, text the user highlighted is bold in the
Markdown, and nothing else is.

## Procedure

### 1. Register and profile

1. Give the source an ID in `data/sources.csv`; run `make manifest` if the
   file is new in `$VOLVE_DATA`.
2. Profile it before choosing a method: pages, language, whether pages have a
   real text layer or are scans, highlight annotations, how many pages are
   prose, tables or figures, and whether plots are vector or embedded
   pictures. Thirty lines of probing save hours.

### 2. Deterministic layer

```bash
uv run python -m dockit.pdf prepare <pdf> agents/doc/work/<id> --dpi 150 [--format jpg]
uv run python -m dockit.figures cut <pdf> data/volve/<dir>/figs --word Figur
```

This writes, per page, the text in reading order (highlights marked `**…**`)
and an image, and cuts out captioned figures. Look at a contact sheet of the
cut-outs; fix the cropping rules if a crop is wrong, never the image by hand.
For a scan, the cut-out of a figure, table or mixed page is the whole page
(`<stem>_pNNN.jpg`, about 110 dpi), made after the pages are typed in step 3.

### 3. Convert page by page

Each page becomes `page_NNN.md` under the rules in
[`page-conversion.md`](page-conversion.md). Translation and the reading of
scanned pages are language-model work:

- Split the pages into ranges of 10 (dense, translated) to 30 (scanned) and
  give each range to a sub-agent. Give every sub-agent the same rules file,
  the paths of its inputs, and the notes specific to the document. Ask each
  for a short list of oddities in the source and of anything it was unsure of.
- For a digital document the text layer has the exact digits; the image gives
  layout. For a scan the image decides; the machine-read text is only an aid.
- Never accept a sub-agent's own statement that its pages are correct. Check
  in step 4.

### 4. Assemble and check

```bash
uv run python -m dockit.assemble agents/doc/work/<id>/md data/volve/<dir>/md/<stem>.md \
    --title "…" --source "<stem>.pdf" --pages N [--text-dir agents/doc/work/<id>/text --ignore "<header digits>"]
```

With `--text-dir` (digital documents) every page's digits and highlights are
compared with the source text. Explain every difference it reports; typical
harmless ones are degree signs and superscripts read as digits, and axis
numbers of charts. For a scan, check the tables that carry the document's key
numbers yourself against the page image, digit by digit, and say which tables
were checked.

### 5. Plot data

Only for charts whose data matters (production profiles, costs).

- **Find out what the chart is.** An embedded picture is traced by colour
  (`dockit.plots.plot_area`, `trace`, `despike`); a vector chart is read from
  its shapes. Printed data labels are simply read.
- **Calibrate from the chart itself:** gridlines for the value axis, the plot
  frame for the time axis. Record the resolution (value per pixel).
- **Check against a table of the same data** wherever the document has one,
  and report the differences. A table that stops at an economic cut-off will
  differ from the chart in its last year; that is not an error.
- Digitised values are labelled digitised everywhere they appear.

`dockit.pud_plots` is the worked example.

### 6. Facts

Put every number that another domain may use into one script
(`dockit.pud_facts`, `dockit.disc_facts`) that writes
`data/facts/<source-id>.csv`. Analysis and reports import the numbers from
that script, so each number is defined once. Set `method` honestly (`read`,
`vision`, `digitised`, `translated`) and lower `confidence` for anything read
once from a scan. Run `make facts-validate`.

### 7. Analyse

Write `<stem>_anlz.md`. Answer the questions asked; the standing ones are
below. For each, give what the document says with the page, in tables where
the content is tabular, and **state plainly what the document does not
give**. Do not fill gaps and do not speculate about reasons.

| Question | What to extract | Where it usually is |
|---|---|---|
| **Concept selection** | The chosen solution; every alternative listed; reasons, advantages and drawbacks as stated; documents referred to for the evaluation | Summary; "development solution" chapter; economics; area evaluation |
| **Production strategy** | The drainage strategy in plain terms and the reason for each element; constraints and assumptions; forecasts redrawn and tables remade | Reservoir chapter; production technology |
| **Uncertainties** | For volumes in place, for the production strategy and for the plan: what is uncertain, how large the document says it is, what mitigation it states | Geology (uncertainty study); reservoir sensitivities; economics sensitivities |

Also record inconsistencies inside the document (summary against tables,
different bases for the same cost, numbering slips), and end with how the
analysis was made and what was not done.

If a question does not apply to the document (a discovery report has no
concept selection), say so and give what the document has instead.

### 8. Compare with outcomes, if asked

Plan against outcome goes in a self-contained web page built by a script
(`dockit.pud_report` is the example): numbers computed in code, never typed
into the text; every chart with a caption that says what it shows and how the
data was obtained; a section on what the comparison cannot show; a table of
sources. Render it in a headless browser and look at it before calling it
done.

### 9. Finish

`make check`; write what was verified and what was not; add anything learned
to this skill; commit with a `doc:` subject.

## Things that went wrong the first time

- **Bold means highlight.** Captions and source emphasis must not be bold, or
  the user's highlights are lost among them.
- **Text layers drop superscripts and fractions.** `Sm3` arrives as `Sm`,
  `8½"` as `8"`, `110°C` as `1100 C`. The page image has them.
- **Decimal comma and thousands point.** Norwegian `9.000` is nine thousand
  and `19,9` is 19.9. Compare digits, not formatted numbers.
- **Percentiles.** Norwegian documents use P90 for the low case. State the
  convention wherever percentiles are quoted.
- **A table can be cut where a chart is not.** The PDO's table of annual oil
  stops at the economic limit; its chart continues. Both are right.
- **One caption can cover two figures,** and a caption can stand under a
  figure that is missing from the file.
- **Traced curves carry stray pixels.** Filter single-column spikes and
  compare yearly totals with stated values.
- **Element ids in a web page must be unique.** A chart with the same id as
  its section is drawn in the wrong place, and only a rendered check shows it.
- **Money has a basis.** The same total appears in money of a base year and in
  nominal money a few pages apart. Carry the basis with every amount.
- **Leased facilities move cost out of "investments".** Public investment
  figures then cover only part of what a plan calls cost.
