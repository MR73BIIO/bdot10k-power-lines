# Value of landowners' claims under medium-voltage lines in Poland (November 2026)

A model estimate, not a valuation of any individual claim and not legal advice.

## Question

Overhead medium-voltage (MV, 15–30 kV) lines cross private land. Under the Polish Civil Code the owner
can ask for a paid transmission easement (art. 305² § 2 k.c.) and for payment for past use without
a contract (art. 224–225 k.c., in general up to 6 years back). How much could these claims be worth
across the country?

## Data

- BDOT10k OT_SULN_L (GUGiK): MV line geometry, 222 098 km.
- PRG address points (GUGiK): 340 277 addresses closer than 25 m to an MV line.
- Rejestr Cen Nieruchomości (RCN, GUGiK): land transaction prices, cleaned (free market, undeveloped
  land, full ownership), median and quartiles per municipality, county and voivodeship.
- ULDK (GUGiK): plot geometry, used plot by plot in the calibration municipalities.

## Method

1. Private part of a 12 m corridor along MV lines, split into building land (estimated from address
   density) and agricultural land.
2. Value of the corridor = area × local price per m²; easement = 0.49 × corridor value;
   past use = 5–6% of the easement value per year for about 6.9 years.
3. Calibration on 8 municipalities computed plot by plot (ULDK + BDOT10k + local transaction prices):
   Białe Błota, Dobrcz, Nowa Wieś Wielka, Osielsko, Sicienko, Piaseczno, Marki, Ząbki.
   In total the model is about 6% below the plot-by-plot result; in single municipalities the
   difference is up to ±20%. Building-land area per address follows 484 × density^-0.33
   (density = addresses per km of line).
4. Expected value: the potential is multiplied by working probabilities (to be confirmed with
   lawyers on a sample of plots):

| Factor | Working value |
|---|---:|
| line exists and is still overhead | 0.91 |
| operator has no legal title | 0.60 |
| no adverse possession: (1 − 0.85) + 0.85 × P(court applies TK P 10/16 = 0.5) | 0.575 |
| operator has not paid yet | 0.95 |
| **multiplier** | **0.298** |

## Result (MV overhead lines only)

| | bn PLN |
|---|---:|
| potential (easement + past use), midpoint | 21.15 |
| range | 7.91–30.90 |
| expected value with the factors above | 6.31 |
| expected value if courts never apply TK P 10/16 | 1.65 |
| expected value if courts always apply it | 10.97 |

Not included: low-voltage lines, 110 kV, 220/400 kV, underground cables, gas, water, heat, oil,
telecom.

## Legal context (as of 22.11.2026)

- Constitutional Tribunal, P 10/16 (2.12.2025): acquiring by adverse possession, before 3.08.2008,
  an easement equal in content to a transmission easement is unconstitutional where no expropriation
  decision was issued (1958 act art. 35, 1985 act art. 70, real estate act art. 124). Not published.
- Supreme Court, three chambers, III CZP 41/26 (18.11.2026): rulings of the Tribunal bind without
  publication; the resolution is disputed by the Minister of Justice.

## What the operators report

Provisions for landowners' claims in their own financial statements for 2025:

| Company | Provision | Source |
|---|---:|---|
| Enea Group | 562.8 m PLN (31.03.2026) | condensed consolidated FS Q1 2026, notes 18 and 25.3 |
| PSE | 116.8 m PLN | FS 2025, table 43 |
| Stoen Operator | 54.3 m PLN | FS 2025, p. 24 |
| Polska Spółka Gazownictwa | 46.3 m PLN | FS 2025, note 27.3 |
| Tauron Dystrybucja | 38.2 m PLN | FS 2025, pp. 46–47 |
| PGE Dystrybucja | 11.3 m PLN | FS 2025, note 17.2 |
| **total** | **about 830 m PLN** | |

Different dates and categories; not a like-for-like comparison. PGE Dystrybucja (p. 56) and Tauron
Dystrybucja (p. 57) state in almost the same words that they do not value potential claims that
owners have not filed. Energa-Operator does not show land claims separately.

A provision and a model potential are different things. The gap between them is not a hidden debt.

## Limits

- BDOT10k can be older than the terrain: some lines are now underground cables.
- The legal title of the operator is not known plot by plot; the factors above are working values.
- Court cases can take many years.

Marcin Ruszczak · MR73BIIO · ORCID 0009-0004-0170-4277
