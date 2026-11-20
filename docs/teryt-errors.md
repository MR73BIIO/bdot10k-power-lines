# TERYT errors in BDOT10k OT_ADJA_A

Found 20.11.2026 while summing line lengths per voivodeship. The national total did not match
the sum of voivodeships. File: `OT_ADJA_A.parquet` from opendata.geoportal.gov.pl.
Reference: GUS TERYT register (eteryt.stat.gov.pl), search TERC.

| Unit | In BDOT10k (IDENTYFIKATORTERYTJEDNOSTKI / parent) | GUS TERYT | Change record |
|---|---|---|---|
| powiat nakielski | `1004` / `4` | 0410 / 04 | GK-KARTO.600.43.2024 |
| gmina Kcynia | `410013` / `410` | 0410013 / 0410 | |
| gmina Szubin | `410053` / `0410` | 0410053 / 0410 | |
| powiat ząbkowicki | `0224` / `2` | parent 02 | |
| powiat wołowski | `0222` / `2` | parent 02 | |
| powiat średzki | `0218` / `2` | parent 02 | |
| powiat lubiński | `0211` / `2` | parent 02 | |
| powiat polkowicki | `0216` / `2` | parent 02 | |

Code `1004` belongs to powiat łęczycki (łódzkie). In OT_ADJA_A both counties carry it, so any join
by TERYT puts powiat nakielski (kujawsko-pomorskie) into łódzkie.

The other rows look like codes stored as numbers somewhere on the way, which drops the leading zero.

## Check it yourself

```python
import geopandas as gpd
a = gpd.read_parquet("kraj/OT_ADJA_A.parquet")
k = ["RODZAJ", "NAZWA", "IDENTYFIKATORTERYTJEDNOSTKI", "IDTERYTJEDNOSTKINADRZEDNEJ", "OZNACZENIEZMIANY"]
t = a.IDENTYFIKATORTERYTJEDNOSTKI.astype(str)
print(a[t.str.startswith("1004")][k])
print(a[a.NAZWA.astype(str).str.contains("Kcyni|Szubin", case=False)][k])
print(a[a.IDTERYTJEDNOSTKINADRZEDNEJ.astype(str).str.len() == 1][k])
```

## Defensive pattern

Read TERYT as text, then check length: 2 (voivodeship), 4 (county), 7 (municipality with type).
Anything else is a data error, not a valid code.
