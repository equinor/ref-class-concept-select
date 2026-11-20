# doc — document conversion, extraction and reporting

## Role

doc turns source documents into text and numbers that people and other agents
can use, analyses them on request, and produces the communication artifacts
(reports, web pages) for the project.

## Rules set by the user

1. **Convert to Markdown.** Each source document (`.pdf`, `.docx`, …) is
   converted to a `.md` file with the same file name, placed in an `md/`
   folder.
2. **Figures.** Cut-outs of the figures in a document go in a `figs/` folder,
   named so they can be matched to the document and figure. For plot graphs,
   the corresponding data table goes with the cut-out.
3. **Graph data to Excel.** The data of all graphs (production profiles and
   similar) in a document is exported to an Excel file with the same name as
   the original document.
4. **Highlights.** If a file name carries the `cmt` tag, text highlighted in
   the source is made bold in the Markdown.
5. **Analysis documents.** When an analysis is requested, the result goes in a
   separate document with the source's file name plus `_anlz`.
6. **Communication.** doc produces the HTML pages that present and summarise
   the data found in the documents.

## Where the converted files go

Approved 2026-11-19: the `md/` and `figs/` folders are kept in the repository
under `data/volve/`, at the mirrored location of the original, so they are
versioned. Nothing is written to `$VOLVE_DATA`.

| Original | Converted |
|---|---|
| `$VOLVE_DATA/reports/Volve_PUD_cmt.pdf` | `data/volve/reports/md/Volve_PUD_cmt.md` |
| | `data/volve/reports/md/Volve_PUD_cmt.xlsx` |
| | `data/volve/reports/figs/Volve_PUD_cmt_p025_fig4-5.png`, plot data `..._fig4-5_<series>.csv` |
| `$VOLVE_DATA/reports/Discovery_report.pdf` | `data/volve/reports/md/Discovery_report.md` |
| | `data/volve/reports/figs/Discovery_report_p<NNN>.jpg` (whole figure pages of the scan) |

## Conventions

Settled in the first doc task (2026-11-20).

- Figure files: `<stem>_p<NNN>_fig<n>.png`, with the page number first so the
  files sort in document order and `<n>` following the document's own
  numbering (`fig4-5` for Figur 4.5). Figure pages of a scan are kept whole as
  `<stem>_p<NNN>.jpg`.
- Plot data: one CSV per series beside the cut-out,
  `<stem>_p<NNN>_fig<n>_<series>.csv`. The Excel file of rule 3 is in the
  `md/` folder, one sheet per figure, plus an index sheet listing figure,
  page, units and extraction method.
- Page anchors: every page of the source starts with a marker
  (`<!-- page 25 -->`) so facts can cite pages.
- Translated documents: the Markdown is in English; the page markers let the
  original wording be checked.
- Bold is used only for text highlighted in the source (rule 4). Captions are
  in italics.
- `_anlz` documents and HTML reports go in `agents/doc/out/`.

## Inputs

| Source | Characteristics (measured 2026-11-19) |
|---|---|
| `reports/Volve_PUD.pdf` | 53 pages, Norwegian, born-digital (Feb 2005), about 22 figure and 33 table captions. Plots are partly vector graphics (e.g. Figur 4.5), partly raster images |
| `reports/Volve_PUD_cmt.pdf` | Same document with 77 highlight annotations on 23 pages; the highlighted text can be read programmatically |
| `reports/Discovery_report.pdf` | 194 pages, English, 300-dpi scan with an OCR layer (Dec 1993), 182 MB. OCR is usable on prose pages and not on figure pages |

## Outputs and consumers

See `agents/sys/GUIDELINES.md` §6. Every value extracted for use by another
domain is a row in `data/facts/pud2005.csv` or `data/facts/disc1993.csv`, with
the columns of guidelines §5; `make facts-validate` checks them.

## Environment

`uv sync --group doc` installs PyMuPDF, openpyxl, pandas, matplotlib, Pillow
and plotly. Other tools are added with `uv add --group doc <package>` once a
trial shows they are needed.

## Skill

The procedure for converting and analysing a field document is the skill
[`skills/analyze-field-document/SKILL.md`](skills/analyze-field-document/SKILL.md),
with the page rules for sub-agents in `page-conversion.md` beside it. It is
linked from `.github/skills/` so Copilot CLI loads it. Start the next batch of
documents from it, and add to it what that batch teaches.

## Code

The `dockit` package in `src/`. The first group is general; the modules named
`pud_` and `disc_` hold what is specific to those two documents.

| Module | Purpose |
|---|---|
| `dockit.pdf` | Page text in reading order with highlights marked; page images |
| `dockit.figures` | Figure cut-outs located from captions and drawings |
| `dockit.plots` | Axis calibration and curve tracing for raster and vector plots |
| `dockit.assemble` | Join page files into one document; check form, digits and highlights against the source text |
| `dockit.pud_plots` | Plot data of the PDO figures to CSV and Excel, with checks against its tables |
| `dockit.pud_facts`, `dockit.disc_facts` | The values registered from the two documents |
| `dockit.pud_data` | Plan and outcome series used by the analysis and the report |
| `dockit.pud_redraw`, `dockit.pud_report` | Redrawn charts; the HTML report |

`make doc-volve` reruns everything that is generated from data. The
translation and transcription are LLM work and are not rerun by it.

## Results so far

| Output | Content |
|---|---|
| `data/volve/reports/md/Volve_PUD_cmt.md` | The PDO in English, 53 pages, highlights in bold |
| `data/volve/reports/md/Discovery_report.md` | The discovery report, 194 pages |
| `out/Volve_PUD_cmt_anlz.md` | Concept selection, production strategy with redrawn forecasts, uncertainties |
| `out/Discovery_report_anlz.md` | The same lines, where the discovery report has content |
| `out/volve-pdo-vs-actual/index.html` | The plan against the outcome: production, schedule, wells, investments |
| `data/facts/pud2005.csv`, `data/facts/disc1993.csv` | Values registered from the two documents |

## Method

- Use a deterministic extraction layer first (text with page positions,
  annotations, embedded images, vector paths), then LLM and vision passes for
  what parsers cannot do: translation, tables in scanned pages, reading of
  figures.
- Plots: where the curves are vector graphics, recover them from the drawing
  paths; where they are raster, digitise with recorded axis calibration.
  Always compare against a table of the same data if the document has one.
- Report only what the source states. Where a document gives no alternatives,
  no pros and cons or no probabilities, say so.

## Quality checks

`agents/sys/GUIDELINES.md` §7: converted document, extracted table, digitised
plot, translation.

## Open points

- The tables of the discovery report other than Table 10.1 were read once from
  the scan and not checked a second time.
- The PDO refers to a concept screening report (20.11.2003), a concept
  selection report (04.11.2004) and a Volume 2; none is in the dataset, so the
  reasons for rejecting the other concepts are not available.
- No public source gives the actual operating or lease costs of the field.
