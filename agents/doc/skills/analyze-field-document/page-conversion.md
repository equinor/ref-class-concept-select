# Converting one page to Markdown

Rules for turning a page of a source document into Markdown that a person or
a language model can use in place of the original. They apply to every page of
every document.

## What you are given

| Input | Content |
|---|---|
| Page image | The page as it looks |
| Text aid | The text extracted from the page, in reading order. `**…**` marks text the user highlighted in the source |
| Figure list | For documents with cut-out figures: file name, page and figure number of each cut-out |

For a document that was created digitally, the text aid has the exact
characters; use it for wording and digits, and the image for layout, tables
and figures. For a scanned document the text aid is machine-read and contains
errors; the image decides, and the text aid is only a help.

## What you write

One file per page, `page_NNN.md`.

1. **First line:** `<!-- page N -->`.
2. **Second line:** `<!-- type: T -->`, where T is one of `text`, `table`,
   `figure`, `mixed`, `contents`, `cover`, `blank`.
3. **Everything on the page, in reading order, and nothing else.** Do not
   summarise, shorten, explain, correct or add. Leave out running headers and
   footers, page numbers, stamps and library marks.
4. **English.** Translate other languages faithfully, in the technical
   register of the source. Keep proper names as written (fields, formations,
   wells, vessels, companies, licences). Use the glossary below so that terms
   are the same on every page.

## Numbers

- Copy every number exactly. Never round, convert units or recompute.
- Write decimal commas as decimal points (`19,9` → `19.9`). Write thousands
  with a space (`92 500`). If you cannot tell whether a separator marks
  decimals or thousands, keep it as printed.
- Keep units as printed.
- If a digit cannot be read with confidence, write the best reading followed
  by `[?]`. If nothing can be read, write `[illegible]`. Do not guess.

## Structure

- **Headings.** Numbered headings keep their number: `##` for a chapter
  (`## 3 Geological evaluation`), `###` for a section (`### 3.1 …`), `####`
  for a subsection. Unnumbered headings are `###`.
- **Paragraphs.** One paragraph per source paragraph. Join words split by a
  line-end hyphen. On a two-column page, read the left column before the right
  one within each band between full-width elements.
- **Lists** become Markdown lists.
- **Bold is reserved for the user's highlights.** Make bold exactly the text
  that corresponds to highlighted source text, even when it starts or ends in
  mid-sentence. Use bold for nothing else; emphasis in the source is not
  reproduced.
- **Tables.** A caption line in italics, then a Markdown table:

  ```
  *Table 3.4 – Results of the uncertainty study (CV is coefficient of variation)*

  | | Base (million Sm3) | Mean (million Sm3) | … |
  |---|---|---|---|
  | East | 19.9 | 19.2 | … |
  ```

  Keep every row, column and cell. Put units in the header. Leave empty cells
  empty. Text printed under a table as a note follows it as a paragraph. A
  layout that cannot be a Markdown table goes in a fenced code block that
  keeps the alignment.
- **Figures.** One line with the image and the caption, then one line
  describing what is visible:

  ```
  ![Figure 4.2 – Volve oil rate and cumulative production](../figs/Volve_PUD_cmt_p023_fig4-2.png)

  Figure content: line chart; x-axis years 2007–2017; left axis Sm3/d (oil rate), right axis million Sm3 (cumulative oil).
  ```

  Take the file name from the figure list (same page and number). For a
  scanned page that is a figure, the file is `<document>_pNNN.jpg`. The
  "Figure content" line names the kind of figure, axes, series and labels. It
  does not interpret, and it does not read values off curves. Text inside a
  figure is not transcribed otherwise. If a caption has no figure in the
  source or in the list, write the caption in italics followed by
  `[figure not present in the source]`.
- **Contents pages** become a nested list of headings with page numbers.

## Before you finish a page

- Every number on the page is in your Markdown, with the same digits.
- Every highlighted passage is bold, and nothing else is.
- Every table and figure caption on the page is present.
- Nothing is in the Markdown that is not on the page.

## Glossary, Norwegian to English

| Norwegian | English |
|---|---|
| plan for utbygging og drift (PUD) | plan for development and operation (PDO) |
| utvinningstillatelse | production licence |
| rettighetshaver | licensee |
| myndighetene | the authorities |
| Olje- og energidepartementet | Ministry of Petroleum and Energy |
| Oljedirektoratet | Norwegian Petroleum Directorate |
| konsekvensutredning | impact assessment |
| funn; funnbrønn | discovery; discovery well |
| letebrønn; avgrensningsbrønn | exploration well; appraisal well |
| tilstedeværende (olje, volum) | (oil, volume) in place |
| utvinnbare; reserver | recoverable; reserves |
| utvinningsgrad | recovery factor |
| snitt; forventning | mean; expected |
| usikkerhet; usikkerhetsanalyse | uncertainty; uncertainty analysis |
| lukning; forkastning | closure; fault |
| olje-vann-kontakt (OVK) | oil-water contact (OWC) |
| brutto/netto bergartsvolum | gross/net rock volume |
| hydrokarbonporevolum | hydrocarbon pore volume |
| produksjonsstrategi; dreneringsstrategi | production strategy; drainage strategy |
| produsent; vanninjektor | producer; water injector |
| trykkstøtte; vanninjeksjon; gassløft | pressure support; water injection; gas lift |
| platå; produksjonsprognose | plateau; production forecast |
| rikgass | rich gas |
| utbyggingsløsning; utbyggingskonsept | development solution; development concept |
| oppjekkbar plattform (rigg) | jack-up platform (rig) |
| lagerskip | storage vessel |
| brønnhode; ventiltre; stigerør | wellhead; Christmas tree; riser |
| boring; komplettering; sandkontroll | drilling; completion; sand control |
| borekaks; borevæske | drill cuttings; drilling fluid |
| drift og vedlikehold | operation and maintenance |
| helse, miljø og sikkerhet (HMS) | health, safety and environment (HSE) |
| avslutningsplan; fjerning | decommissioning plan; removal |
| investeringer; driftskostnader | investments; operating costs |
| leie; leiekostnader | lease; lease costs |
| nåverdi; internrente | net present value; internal rate of return |
| nullpunktspris; balansepris | break-even price |
| før/etter skatt | before/after tax |
| lønnsomhet | profitability |
| områdevurdering | area evaluation |
| mill.; mrd. | million; billion |
| fat | barrel |
| årsverk | man-years |
