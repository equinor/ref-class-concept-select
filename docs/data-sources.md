# Data sources

What data the project has, what else is publicly available for Volve, and how
to retrieve it. Everything marked *verified* was checked on 2026-11-19.

## 1. Local data

Location: `../volve_data` relative to the repository root (74 files, 2.48 GB),
or wherever the `VOLVE_DATA` environment variable points. Described in
`docs/background.txt`. Every file is listed with size and SHA-256 in
`data/manifest.csv`; `make manifest-verify` checks a machine against it.

| ID | Path | Content | Measured |
|---|---|---|---|
| `pud2005` | `reports/Volve_PUD.pdf` | Plan for development and operation, Feb 2005, Norwegian | 53 pages, born-digital; about 22 figures and 33 tables |
| `pud2005` | `reports/Volve_PUD_cmt.pdf` | Same, with the user's highlights | 77 highlight annotations on 23 pages; otherwise identical text |
| `disc1993` | `reports/Discovery_report.pdf` | Discovery evaluation report, well 15/9-19 SR, Dec 1993, English | 194 pages, 300-dpi scan with OCR layer, 182 MB |
| `prod` | `production_data/Volve production data.xlsx` | Daily and monthly production per wellbore | Daily: 15 634 rows × 24 columns, 7 wellbores, 2007-09-01 to 2016-12-01. Monthly: 526 rows. Cumulative oil 10.04 MSm3, gas 1.475 GSm3, water 15.32 MSm3, water injection 30.33 MSm3 |
| `sim2016` | `eclipse_model/sim_model_PPA-eclipse/` | Eclipse 100 history-matched model with results | 108 × 100 × 63 grid, 183 545 active cells; 31 Dec 2007 to 1 Oct 2016; FOPT 9.98 MSm3; FOIP at start 21.97 MSm3 |

The three `.zip` files in `../volve_data` (581 MB) are the downloaded archives
of the extracted folders.

## 2. Public sources for Volve

### 2.1 Equinor Volve data village — *verified*

- Page: <https://www.equinor.com/energy/volve-data-sharing>
- About 40 000 files. Access is now through the Databricks Marketplace
  (provider "Equinor ASA"); the page links a user guide:
  <https://equinoropendata.blob.core.windows.net/userguides/Equinor%20open%20data%20-%20User%20Guide.pdf>
- Per `docs/background.txt` the full release covers production data, well
  design, completion string design, seismic, well logs (petrophysical and
  drilling), geological and stratigraphical data, static and dynamic models,
  surface and grid data. Marketplace installations expire after 90 days and can
  be reinstalled.
- Locally present so far: reports, production data and the Eclipse model.
- Retrieval: install the share in a Databricks workspace and export the wanted
  package. Not yet inventoried: the list and size of the remaining packages.

### 2.2 Norwegian Offshore Directorate (Sodir) FactPages — *verified*

- Field page: <https://factpages.sodir.no/en/field/PageView/All/3420717>
  (NPDID field 3420717; discovery wellbore 15/9-19 SR, wellbore page id 2105).
- A snapshot of the tables below, taken 2026-11-19, is in
  `data/sodir/20261119/`; `make sodir` takes a new one. The Volve values are in
  the fact register, `data/facts/sodir.csv`.
- Every FactPages table can be downloaded as CSV for the whole shelf without
  authentication:

```
https://factpages.sodir.no/public?/Factpages/external/tableview/<TABLE>&rs:Command=Render&rc:Toolbar=false&rc:Parameters=f&IpAddress=not_used&CultureCode=en&rs:Format=CSV&Top100=false
```

```bash
curl -s -o field_reserves.csv 'https://factpages.sodir.no/public?/Factpages/external/tableview/field_reserves&rs:Command=Render&rc:Toolbar=false&rc:Parameters=f&IpAddress=not_used&CultureCode=en&rs:Format=CSV&Top100=false'
```

| `<TABLE>` | Content | Volve rows | Size |
|---|---|---|---|
| `field_production_yearly` | Net oil, gas, NGL, condensate, o.e., produced water per year | 9 (2008–2016) | 0.1 MB |
| `field_production_monthly` | Same per month | 114 | 2.0 MB |
| `field_investment_yearly` | Investments per year, million NOK nominal | 17 | 0.1 MB |
| `field_reserves` | Recoverable and remaining volumes, one version per year-end, 2004–2025 | 21 (2005–2025) | 0.2 MB |
| `field_in_place_volumes` | In-place volumes, current estimate | 1 | <0.1 MB |
| `field_description` | Text descriptions | 7 | 0.2 MB |
| `field_activity_status_hst` | Status history | 3 | <0.1 MB |
| `field_licensee_hst` | Ownership history | 52 | 1.5 MB |
| `wellbore_development_all` | Development wellbores | 22 | 4.1 MB |

  Files start with a UTF-8 byte-order mark. The tables cover all fields, which
  makes them the base for the reference class as well (see
  `agents/rcf/README.md`).

  Units, as stated on the Sodir field page: oil and condensate in million Sm3,
  gas in billion Sm3, oil equivalents in million Sm3 o.e., investments in
  million NOK nominal. NGL is in million Sm3 in the production tables and in
  million tonnes in `field_reserves`.

Volve values from these tables:

| Quantity | Value |
|---|---|
| Oil produced 2008–2016 | 10.17 MSm3 (yearly: 1.770, 2.717, 1.699, 0.859, 0.587, 0.572, 0.760, 0.881, 0.327) |
| In-place oil, current estimate | 18.70 MSm3 |
| Recoverable oil, estimate by year-end | 2005: 11.90 · 2006: 12.42 · 2007: 12.49 · 2008: 13.58 · 2009: 8.79 · 2010: 8.15 · 2011: 8.51 · 2012: 8.68 · 2013: 9.54 · 2014: 9.68 · 2015: 10.34 · 2016 onward: 10.17 |
| Investments 2005–2016, nominal | 4 689 MNOK (2005–2009: 2 933; 2010–2011: 111; 2012–2014: 1 640; 2015–2016: 5) |

### 2.3 Archived NPD FactPages (Internet Archive) — *verified 2026-11-20*

The live Sodir tables carry only the current in-place estimate. Earlier
published values are in Internet Archive captures of the NPD FactPages (NPD is
Sodir's former name). Saved in `data/npd_archive/`:

| Capture | Content | Volve values |
|---|---|---|
| Feb 2007 | Field page, `www.npd.no/engelsk/cwi/pbl/en/field/all/3420717.htm` | Recoverable oil 11.90 as of 31.12.2005; no in-place shown |
| Oct 2014, Jun 2017, Oct 2020 | Field page, `factpages.npd.no/ReportServer…PageView/field…NpdId=3420717` | Oil in place 18.70 (31.12.2013, 31.12.2016), 19.00 (31.12.2019) |
| Apr 2021, Dec 2022, May 2023 | `field_in_place_volumes` table, all fields | Oil in place 18.70, 18.70, 19.00 |

To find captures: `http://web.archive.org/cdx/search/cdx?url=<url>&filter=statuscode:200&collapse=timestamp:6&fl=timestamp,length,original`.
To fetch one unchanged: `http://web.archive.org/web/<timestamp>id_/<url>`.
A domain-wide search of `npd.no` timed out; only the specific URLs above were
searched.

### 2.4 Norwegian Petroleum (norskpetroleum.no) — *verified*

- <https://www.norskpetroleum.no/en/facts/field/volve/>
- Short field description (development, reservoir, recovery strategy,
  transport, status) and charts of production and investments with data
  download. The numbers are Sodir's.

### 2.5 Price series — *verified 2026-11-20*

Used to put the PDO's assumptions and costs in context. Snapshots in
`data/public/`, taken with `make public`.

| Series | Source | Retrieval |
|---|---|---|
| Consumer price index, annual, 2015 = 100 | Statistics Norway, table 03014 | POST of a JSON query to `https://data.ssb.no/api/v0/en/table/03014` (in `syskit.public`) |
| Brent crude, annual average, USD per barrel | FRED series `DCOILBRENTEU` | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=DCOILBRENTEU&fq=Annual&fam=avg` |

No public source was found for the actual operating or lease costs of Volve;
Sodir publishes investments only.

### 2.6 Simulator and tooling references — *verified*

- OPM Flow reference manual, release 2026-04: <https://opm-project.org/?page_id=955>
- OPM Flow packages for Ubuntu 24.04: `ppa:opm/ppa` (`libopm-simulators-bin`
  2026.04); Python bindings `opm` 2026.4 on PyPI. Install command in
  `agents/sim/README.md`.
- `resdata` 7.0.0 and `res2df` 1.4.0 on PyPI.

### 2.7 Not yet checked

- Sodir wellbore pages for the Volve exploration and development wells, and the
  documents attached to them.
- Sodir open-data landing page (`sodir.no/en/about-us/open-data/`) — returned
  HTTP 403 to an automated request; the FactPages endpoints above work.
- The impact assessment (konsekvensutredning) and supporting documents that
  the PDO refers to.
- Operator and partner publications on the Volve development and its costs.

## 3. Retrieval practice

- Public tables are pulled with `make sodir` into `data/sodir/<YYYYMMDD>/`
  and analyses read the snapshot (`agents/sys/GUIDELINES.md` §3). To add a
  table, add its name to `TABLES` in `agents/sys/src/syskit/sodir.py`.
- Record the retrieval date with every value quoted from Sodir. The tables
  carry a synchronisation date (it equalled the retrieval date) and the
  reserve estimates get a new version each year.
