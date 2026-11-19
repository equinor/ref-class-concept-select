# doc — document conversion, extraction and reporting

## Role

doc turns source documents into text and numbers that people and other agents
can use, analyses them on request, and produces the communication artifacts
(reports, web pages) for the project.

## Rules set by the user

1. **Convert to Markdown.** Each source document (`.pdf`, `.docx`, …) is
   converted to a `.md` file with the same file name, placed in an `md/` folder
   in the same directory as the original.
2. **Figures.** Cut-outs of the figures in a document go in a `figs/` folder in
   the same directory as the original, named so they can be matched to the
   document and figure. For plot graphs, the corresponding data table goes with
   the cut-out.
3. **Graph data to Excel.** The data of all graphs (production profiles and
   similar) in a document is exported to an Excel file with the same name as
   the original document.
4. **Highlights.** If a file name carries the `cmt` tag, text highlighted in
   the source is made bold in the Markdown.
5. **Analysis documents.** When an analysis is requested, the result goes in a
   separate document with the source's file name plus `_anlz`.
6. **Communication.** doc produces the HTML pages that present and summarise
   the data found in the documents.

## Conventions proposed by this charter (pending approval)

- Figure files: `<stem>_fig<NN>_<slug>.png`; plot data beside it as
  `<stem>_fig<NN>_<slug>.csv`. `<NN>` follows the document's own numbering
  (`fig04-5` for Figur 4.5).
- The Excel file of rule 3 is placed in the `md/` folder, one sheet per figure,
  plus an index sheet listing figure, page, axis units and extraction method.
- Translated documents: the Markdown is in English; each section keeps its page
  reference so the original wording can be checked.
- `_anlz` documents and HTML reports go in `agents/doc/out/`.
- Page anchors: every page of the source starts with a marker
  (`<!-- page 25 -->`) so facts can cite pages.

## Inputs

| Source | Characteristics (measured 2026-11-19) |
|---|---|
| `reports/Volve_PUD.pdf` | 53 pages, Norwegian, born-digital (Feb 2005), about 22 figure and 33 table captions. Plots are partly vector graphics (e.g. Figur 4.5), partly raster images |
| `reports/Volve_PUD_cmt.pdf` | Same document with 77 highlight annotations on 23 pages; the highlighted text can be read programmatically |
| `reports/Discovery_report.pdf` | 194 pages, English, 300-dpi scan with an OCR layer (Dec 1993), 182 MB. OCR is usable on prose pages and not on figure pages |

## Outputs and consumers

See `agents/sys/GUIDELINES.md` §6. Facts follow the fields in §5 of the
guidelines; until the fact register exists they are given as tables in the
`_anlz` document.

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

## First step

Defined in `docs/startup-assessment.md` §7. The detailed task is specified by
the user after the foundation is approved.

## Procedures

Procedures that prove themselves are written up as `GUIDELINE_<topic>.md` in
this folder so the next batch of documents starts from them.
