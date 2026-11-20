# Oil in place: PDO, Sodir and the simulation model

Prepared 2026-11-20 in the sys role. All values are in the fact register
(`data/facts/pud2005.csv`, `sim2016.csv`, `sodir.csv`, `npd_archive.csv`).
Percentiles follow the PDO's convention: P90 is the low case.

## Comparison at three points in time

Oil originally in place, MSm3. "As of" is the date of the knowledge behind
each number.

| Point in time | PDO (operator) | Sodir (then NPD) | Eclipse model |
|---|---|---|---|
| **PDO delivery, Feb 2005** | Volve closure: mean **27.5**, P90 20.9, P50 26.7, P10 35.2; base case 24.5 (East 19.9 + West 4.6) | Not published. Only recoverable oil: 11.90 as of 31.12.2005 | None in the dataset. The PDO's simulation model was not released |
| **Production start, Feb 2008** | No update in the dataset | No record found. Recoverable oil 12.49 (31.12.2007), 13.58 (31.12.2008) | **21.97** in the model at 31 Dec 2007, but this is the model as history-matched in 2016. The Dec 2010 version of the model: 20.6, against 18.7 in the geological model |
| **End of production, 2016** | — | **18.70** as of 31.12.2016; unchanged from 31.12.2013 to today | **21.97** originally in place (main structure 20.23, north-west segment 1.73); 11.99 remaining on 1 Oct 2016 after 9.98 produced |

## What the numbers show

1. **The outcome is below the PDO's low case.** Sodir's 18.70 is 32 % below
   the PDO mean and 11 % below its P90. The simulation model's 21.97 is 20 %
   below the mean and just above P90.
2. **Sodir's figure is the operator's geological model.** The model
   presentation of Dec 2010 gives 18.7 MSm3 for the geological model of "Volve
   field including North West segment" — the value Sodir carries from at least
   year-end 2013.
3. **The simulation model holds more oil than the geological model, by
   design.** The same slide gives 20.6 MSm3 in the simulation model "to obtain
   the match"; the 2016 deck has 21.97, 17 % above Sodir. The deck multiplies
   pore volume in several areas for the history match.
4. **In-place fell and was then held; recoverable volume kept moving.** The
   in-place estimate went from 27.5 (2005) to 18.7 (by Dec 2010) and has been
   held since; no estimate in between is in the data. Sodir's recoverable oil
   went 11.90 (2005) → 13.58 (2008) → 8.15 (2010) → 10.17 (final).
5. **Recovery factor moved the other way.** Recoverable over in-place: PDO
   mean 11.40 / 27.5 = 41 %; Sodir final 10.17 / 18.70 = 54 %; simulation model
   9.98 / 21.97 = 45 %. Recovered oil ended 11 % below the PDO mean although
   in-place ended 32 % below.

## Detail

**PDO, February 2005** (`pud2005`, pages 19 and 25, tables 3.3, 3.4, 4.5):

| Area | Base | Mean | P90 | P50 | P10 | Std. dev. |
|---|---|---|---|---|---|---|
| East | 19.9 | 19.2 | 15.9 | 19.1 | 22.8 | 2.6 |
| West | 4.6 | 8.3 | 3.4 | 7.5 | 14.6 | 4.3 |
| Volve closure | 24.5 | 27.5 | 20.9 | 26.7 | 35.2 | 5.5 |
| Prospects | 6.3 | 13.8 | 5.0 | 9.9 | 30.0 | 11.6 |
| Closure and prospects | 30.8 | 41.3 | 27.2 | 36.4 | 64.7 | 15.8 |

Reserves from the same study: mean 11.40, P90 9.0, P50 11.35, P10 15.31.

**Sodir / NPD** (`sodir` snapshot 2026-11-19; `npd_archive` captures):

| As of | Oil in place | Associated gas in place (GSm3) | Recoverable oil | Source |
|---|---|---|---|---|
| 31.12.2005 | not shown | not shown | 11.90 | Field page captured Feb 2007 |
| 31.12.2013 | 18.70 | 2.80 | 9.54 | Field page captured Oct 2014 |
| 31.12.2016 | 18.70 | 2.80 | 10.17 | Field page captured Jun 2017 |
| 31.12.2019 | 19.00 | 3.00 | 10.17 | Field page captured Oct 2020 |
| 31.12.2020, 2021 | 18.70 | 2.80 | 10.17 | In-place table captured 2021, 2022 |
| 31.12.2022 | 19.00 | 3.00 | 10.17 | In-place table captured May 2023 |
| 31.12.2025 | 18.70 | 2.80 | 10.17 | Snapshot 2026-11-19 |

The 19.00 and 3.00 entries look like the same estimate shown rounded.
Recoverable oil is from the `field_reserves` table; the 2014 and 2017 field
pages show it to one decimal (9.50, 10.20).

**Eclipse model** (`sim2016`, `VOLVE_2016.PRT`, balance at 0 days, 31 Dec
2007; region labels from the `EQUIL` comments in the deck):

| Regions | Label | Oil in place (MSm3) |
|---|---|---|
| 1, 2, 4, 8 | Main structure: north-west, north, east, south-west | 16.99 |
| 3, 11 | Main structure, "purged water" regions | 3.25 |
| 6, 10 | Prospect North West | 1.73 |
| 5, 7, 9 | Prospect North, aquifer west | 0 (water) |
| All | | 21.97 |

Dissolved gas in place 3.04 GSm3; no free gas.

## Limits

- **Scope is not reconciled.** The PDO figure is for the "Volve closure" (East
  and West). The later figures are for the "Volve field including North West
  segment". Whether the PDO's West area and the later North West segment are
  the same volume is not established from the documents read so far.
- **Only three in-place estimates exist** in the data: PDO 2005, the Dec 2010
  slide, and the 2016 deck. The first Sodir in-place value found is for
  31.12.2013; none was published with the 2005 reserves. The web archive was
  searched for the field page and the in-place table only.
- **The model value at production start is hindsight.** It is the initial
  state of the 2016 model, not an estimate made in 2008.
- The PDO was read from its text layer and checked by the tables' internal
  sums; it has not yet been converted and reviewed as a whole.
