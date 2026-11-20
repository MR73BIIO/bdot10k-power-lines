# -*- coding: utf-8 -*-
"""
linie_bdot_005.py - ile linii energetycznych, budynkow i dzialek pod pasem (BDOT10k + ULDK)

Etapy:

  0) kraj         - km linii (SN/WN/NN) dla kazdego wojewodztwa i powiatu; potrzebne tylko dwa pliki
                    krajowe GeoParquet: OT_SULN_L.parquet i OT_ADJA_A.parquet.


  1) rozpoznanie  - co jest w BDOT10k: pola i wartosci warstwy linii napowietrznych (OT_SULN_L).
                    Z tego ustalasz FILTR, czyli jak w tym powiecie opisano linie SN.
  2) powiat       - km linii (wg FILTRA), km przez tereny zabudowy, budynki w pasie 12 m
                    (w tym mieszkalne). Tylko BDOT10k, bez internetu, kilka sekund.
  3) gmina        - dla jednej gminy: dzialki pod pasem z ULDK (wolne: ok. 1 zapytanie na dzialke,
                    z pamiecia - mozna przerwac i wznowic), udzial dzialek zabudowanych,
                    szacunkowe kwoty (ten sam wzor co kalkulator).

Dane: BDOT10k dla powiatu (GML/SHP/GPKG) rozpakowane do jednego katalogu (Geoportal -> Pobierz dane),
albo pliki krajowe GeoParquet jednej klasy, np. OT_SULN_L.parquet (cala Polska) - wtedy
etap 'rozpoznanie' daje km linii dla calego kraju.

Przyklady (WSL):
  python3 linie_bdot_001.py rozpoznanie --bdot ~/dane/bdot_0403
  python3 linie_bdot_001.py powiat --bdot ~/dane/bdot_0403 --filtr "średni"
  python3 linie_bdot_001.py gmina  --bdot ~/dane/bdot_0403 --filtr "średni" --gmina 040301

Raporty: Downloads/linie_bdot_001_<etap>.txt (+ .gpkg / .csv przy etapach powiat i gmina).
"""

import argparse
import csv
import json
import math
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely import wkt as shp_wkt
from shapely.geometry import LineString, Point
from shapely.ops import unary_union
from shapely.strtree import STRtree

NR = "005"
CRS = "EPSG:2180"
PAS = {"o": 3.5, "s": 6.0}                 # pol szerokosci pasa SN [m]: operator / szeroki
K, U = 0.49, 0.05                          # wzor: sluzebnosc = PSP*Wg*k, rocznie = PSP*Wg*u*k
K_GRUNT = {"budowlana": 0.49, "rolna": 0.49, "lesna": 0.8}   # las: przecinka, ingerencja niemal pelna (orientacyjnie)
CENY = {"budowlana": 270, "rolna": 7, "lesna": 5}   # zl/m2 - zmien dla innej gminy
ULDK = "https://uldk.gugik.gov.pl/"


def downloads():
    for p in (Path("/mnt/c/Users/PC/Downloads"), Path.home() / "Downloads"):
        if p.exists():
            return p
    p = Path.home() / "Downloads"
    p.mkdir(parents=True, exist_ok=True)
    return p


OUT = downloads()


# ---------------- wczytywanie BDOT10k ----------------
def warstwa(katalog: Path, klasa: str):
    """wczytuje klase BDOT10k (np. OT_SULN_L) z GML/SHP/GPKG w katalogu; None gdy brak"""
    pliki = [p for p in katalog.rglob("*") if klasa.upper() in p.name.upper()
             and p.suffix.lower() in (".xml", ".gml", ".shp", ".gpkg", ".parquet")]
    if not pliki:
        return None
    czesci = []
    for p in pliki:
        try:
            g = gpd.read_parquet(p) if p.suffix.lower() == ".parquet" else gpd.read_file(p)
        except Exception as e:
            print(f"  ! nie wczytano {p.name}: {e}")
            continue
        if g.geometry.name != "geometry":          # np. krajowy GeoParquet ma kolumne 'geom'
            g = g.rename_geometry("geometry")
        if g.crs is None:
            g = g.set_crs(CRS)
        czesci.append(g.to_crs(CRS))
    if not czesci:
        return None
    return gpd.GeoDataFrame(pd.concat(czesci, ignore_index=True), geometry="geometry", crs=CRS)


def tekst_kolumny(g):
    return [c for c in g.columns if c != "geometry"
            and (g[c].dtype == object or pd.api.types.is_string_dtype(g[c]))]


def filtruj(g, filtr: str | None):
    """zostawia obiekty, w ktorych dowolne pole tekstowe zawiera filtr (bez wielkosci liter)"""
    if not filtr:
        return g
    wz = re.compile(filtr, re.I)
    maska = pd.Series(False, index=g.index)
    for c in tekst_kolumny(g):
        maska |= g[c].astype(str).str.contains(wz, na=False)
    return g[maska]


def zapisz(nazwa, tekst):
    p = OUT / f"linie_bdot_{NR}_{nazwa}.txt"
    p.write_text(tekst, encoding="utf-8")
    print(tekst)
    print(f"\nZapisano: {p}")


# ---------------- 1) rozpoznanie ----------------
def rozpoznanie(a):
    kat = Path(a.bdot).expanduser()
    r = [f"ROZPOZNANIE BDOT10k - {datetime.now():%Y-%m-%d %H:%M}", f"Katalog: {kat}", ""]
    for klasa in ("OT_SULN_L", "OT_BUBD_A", "OT_PTZB_A", "OT_PTLZ_A", "OT_PTWP_A", "OT_PTKM_A", "OT_ADJA_A"):
        g = warstwa(kat, klasa)
        r.append(f"== {klasa}: " + ("BRAK" if g is None else f"{len(g)} obiektow"))
        if g is None or klasa != "OT_SULN_L":
            if g is not None and klasa == "OT_ADJA_A":
                for c in tekst_kolumny(g):
                    r.append(f"   pole {c}: " + ", ".join(map(str, g[c].dropna().unique()[:12])))
            continue
        r.append(f"   dlugosc razem: {g.length.sum() / 1000:.1f} km")
        for c in tekst_kolumny(g):
            vc = g.groupby(g[c].astype(str)).apply(lambda x: (len(x), x.length.sum() / 1000))
            if 1 < len(vc) <= 40:
                r.append(f"   pole {c}:")
                for wart, (n, km) in sorted(vc.items(), key=lambda t: -t[1][1]):
                    r.append(f"      {wart[:60]:<60} {n:>6} ob. {km:>9.1f} km")
    r += ["", "Dalej: wybierz z wartosci powyzej slowo, ktore oznacza linie SN (np. 'średni' albo '15'),",
          "i uruchom etap 'powiat' z --filtr. Jesli linii SN nie ma w BDOT10k, napisz - uzyjemy innego zrodla."]
    zapisz("rozpoznanie", "\n".join(r))


# ---------------- 0) kraj ----------------
def _adja(kat, rodzaj):
    a = warstwa(kat, "OT_ADJA_A")
    if a is None:
        sys.exit("Brak OT_ADJA_A (granice) - pobierz OT_ADJA_A.parquet.")
    col_r = "RODZAJ" if "RODZAJ" in a.columns else next((c for c in a.columns if c.lower() == "rodzaj"), None)
    col_t = next((c for c in a.columns if c.upper() == "IDENTYFIKATORTERYTJEDNOSTKI"), None)
    col_n = next((c for c in a.columns if c.upper() == "NAZWA"), None)
    if not (col_r and col_t and col_n):
        sys.exit(f"Nie rozpoznaje pol w OT_ADJA_A: {list(a.columns)}")
    a = a[a[col_r].astype(str) == rodzaj].copy()
    a["teryt"], a["nazwa"] = a[col_t].astype(str), a[col_n].astype(str)
    # BDOT10k dostarcza granice kawalkami (np. wojewodztwo pociete na powiaty) - sklejamy po TERYT i nazwie
    a = a[["teryt", "nazwa", "geometry"]].dissolve(by=["teryt", "nazwa"]).reset_index()
    return a


def _km_w(poly_df, lin):
    """km linii (wg kolumny 'typ') w kazdym poligonie"""
    idx = lin.sindex
    out = []
    for _, p in poly_df.iterrows():
        kand = lin.iloc[idx.query(p.geometry, predicate="intersects")]
        rec = {"teryt": p.teryt, "nazwa": p.nazwa, "pow_km2": p.geometry.area / 1e6}
        if len(kand):
            dl = kand.geometry.intersection(p.geometry).length
            for typ, km in (dl.groupby(kand["typ"].values).sum() / 1000).items():
                rec[typ] = km
        out.append(rec)
    return pd.DataFrame(out).fillna(0)


def kraj(a):
    kat = Path(a.bdot).expanduser()
    lin = warstwa(kat, "OT_SULN_L")
    col = next((c for c in lin.columns if c.upper() == "RODZAJ"), None)
    typ = lin[col].astype(str).str.lower() if col else pd.Series("", index=lin.index)
    lin["typ"] = "inne"
    lin.loc[typ.str.contains("średni"), "typ"] = "SN"
    lin.loc[typ.str.contains("wysokiego"), "typ"] = "WN"
    lin.loc[typ.str.contains("najwyższ"), "typ"] = "NN"
    print("Licze wojewodztwa...")
    woj = _km_w(_adja(kat, "województwo"), lin)
    print("Licze powiaty (to potrwa kilka minut)...")
    pw = _km_w(_adja(kat, "powiat"), lin)
    for d in (woj, pw):
        for t in ("SN", "WN", "NN"):
            if t not in d:
                d[t] = 0.0
        d["SN_na_100km2"] = 100 * d.SN / d.pow_km2
        d["pas12_SN_km2"] = d.SN * 0.012
    woj = woj.sort_values("SN", ascending=False)
    r = [f"LINIE NAPOWIETRZNE WG WOJEWODZTW I POWIATOW - BDOT10k ({datetime.now():%Y-%m-%d %H:%M})",
         "km linii; pas 12 m = km SN x 12 m (bez odejmowania nakladania sie pasow)", "",
         f"{'wojewodztwo':<22}{'SN km':>10}{'WN km':>9}{'NN km':>8}{'SN/100km2':>11}{'pas12 SN km2':>14}"]
    for _, x in woj.iterrows():
        r.append(f"{x.nazwa:<22}{x.SN:>10,.0f}{x.WN:>9,.0f}{x.NN:>8,.0f}{x.SN_na_100km2:>11.1f}{x.pas12_SN_km2:>14.1f}".replace(",", " "))
    r.append(f"{'POLSKA':<22}{woj.SN.sum():>10,.0f}{woj.WN.sum():>9,.0f}{woj.NN.sum():>8,.0f}".replace(",", " "))
    r += ["", "Powiaty z najwieksza dlugoscia linii SN (top 15):"]
    for _, x in pw.sort_values("SN", ascending=False).head(15).iterrows():
        r.append(f"  {x.teryt} {x.nazwa:<28}{x.SN:>8,.0f} km SN  ({x.SN_na_100km2:.0f} km/100 km2)".replace(",", " "))
    if True:
        moj = pw[pw.teryt == (a.powiat or "0403")]
        for _, x in moj.iterrows():
            f0 = lambda v: f"{v:,.0f}".replace(",", " ")
            r += ["", f"Powiat {x.nazwa} ({x.teryt}): SN {f0(x.SN)} km, WN {f0(x.WN)} km, NN {f0(x.NN)} km,",
                  f"  gestosc SN {x.SN_na_100km2:.0f} km/100 km2, pas 12 m SN ok. {x.pas12_SN_km2:.1f} km2"]
    r += ["", "Uwaga: linie lezace na granicy jednostek licza sie do obu; suma powiatow moze sie roznic od sumy kraju."]
    zapisz("kraj", "\n".join(r))
    csv_p = OUT / f"linie_bdot_{NR}_kraj_powiaty.csv"
    pw.sort_values("teryt").to_csv(csv_p, sep=";", index=False, decimal=",", float_format="%.1f", encoding="utf-8-sig")
    print(f"Tabela powiatow: {csv_p}")


# ---------------- 2) powiat ----------------
def powiat(a):
    kat = Path(a.bdot).expanduser()
    lin = warstwa(kat, "OT_SULN_L")
    if lin is None:
        sys.exit("Brak OT_SULN_L w katalogu BDOT10k.")
    lin = filtruj(lin, a.filtr)
    if lin.empty:
        sys.exit(f"Filtr '{a.filtr}' nie pasuje do zadnej linii - sprawdz etap rozpoznanie.")
    bud = warstwa(kat, "OT_BUBD_A")
    ptzb = warstwa(kat, "OT_PTZB_A")
    os_ = unary_union(lin.geometry.values)
    pas = os_.buffer(PAS["s"])
    km = lin.length.sum() / 1000
    r = [f"LINIE NAD TERENEM - POWIAT ({datetime.now():%Y-%m-%d %H:%M})",
         f"Zrodlo: BDOT10k ({kat.name}), filtr linii: '{a.filtr}'", "",
         f"Linie napowietrzne wg filtra:        {km:10.1f} km ({len(lin)} odcinkow)",
         f"Pas {2 * PAS['s']:.0f} m wzdluz linii:              {pas.area / 10000:10.1f} ha"]
    if ptzb is not None:
        zab = unary_union(ptzb.geometry.values)
        km_zab = os_.intersection(zab).length / 1000
        r.append(f"Linii przez tereny zabudowy (PTZB):   {km_zab:10.1f} km ({100 * km_zab / km:.0f}%)")
    if bud is not None:
        w_pasie = bud[bud.intersects(pas)]
        mieszk = filtruj(w_pasie, "mieszk")
        r.append(f"Budynki w pasie {2 * PAS['s']:.0f} m:                 {len(w_pasie):10d}")
        r.append(f"  w tym mieszkalne (wg opisu BDOT):   {len(mieszk):10d}")
        r.append(f"Budynki w pasie {2 * PAS['o']:.0f} m:                  {int(bud.intersects(os_.buffer(PAS['o'])).sum()):10d}")
    r += ["", "Uwaga: BDOT10k ma dokladnosc mapy 1:10 000; przebieg linii moze odbiegac o kilka metrow.",
          "Liczba budynkow w pasie to nie liczba wlascicieli ani roszczen - to skala zjawiska."]
    zapisz("powiat", "\n".join(r))
    gp = OUT / f"linie_bdot_{NR}_powiat.gpkg"
    lin.to_file(gp, layer="linie", driver="GPKG")
    gpd.GeoDataFrame(geometry=[pas], crs=CRS).to_file(gp, layer="pas", driver="GPKG")
    if bud is not None:
        w_pasie.to_file(gp, layer="budynki_w_pasie", driver="GPKG")
    print(f"Warstwy do QGIS: {gp}")


# ---------------- 3) gmina (ULDK) ----------------
_kol = {"k": None}


def uldk_xy(x, y, offline=False):
    if offline:            # atrapa do testu: siatka dzialek 20 x 30 m
        cx, cy = math.floor(x / 20) * 20, math.floor(y / 30) * 30
        from shapely.geometry import box
        return f"999999_9.0001.{int(cx)}_{int(cy)}", box(cx, cy, cx + 20, cy + 30)
    pt = Point(x, y)
    for k in ([_kol["k"]] if _kol["k"] else ["xy", "yx"]):
        a_, b_ = (x, y) if k == "xy" else (y, x)
        url = f"{ULDK}?request=GetParcelByXY&xy={a_:.2f},{b_:.2f},2180&result=geom_wkt,teryt"
        for proba in range(3):
            try:
                txt = urllib.request.urlopen(url, timeout=30).read().decode("utf-8").strip()
                break
            except Exception:
                time.sleep(2 + 3 * proba)
        else:
            return None
        time.sleep(0.1)
        ls = txt.splitlines()
        if len(ls) < 2 or ls[0].startswith("-1"):
            continue
        cz = ls[1].split("|")
        w = cz[0].split(";", 1)[1] if cz[0].upper().startswith("SRID") else cz[0]
        g = shp_wkt.loads(w)
        if g.is_empty or not g.buffer(0.01).contains(pt):
            continue
        _kol["k"] = k
        return (cz[1].strip() if len(cz) > 1 else "?"), g
    return None


def punkty_wzdluz(linia: LineString, krok=4.0, odsuniecia=(-4.5, 0.0, 4.5)):
    n = max(int(linia.length // krok), 1)
    for i in range(n + 1):
        d = min(i * krok, linia.length)
        p = linia.interpolate(d)
        q = linia.interpolate(min(d + 0.5, linia.length)) if d < linia.length else linia.interpolate(d - 0.5)
        dx, dy = q.x - p.x, q.y - p.y
        dl = math.hypot(dx, dy) or 1
        nx, ny = -dy / dl, dx / dl
        for o in odsuniecia:
            yield p.x + nx * o, p.y + ny * o


def gmina(a):
    kat = Path(a.bdot).expanduser()
    lin = filtruj(warstwa(kat, "OT_SULN_L"), a.filtr)
    adja = warstwa(kat, "OT_ADJA_A")
    granica = None
    if adja is not None and a.gmina:
        kol_t = next((c for c in adja.columns if c.upper() == "IDENTYFIKATORTERYTJEDNOSTKI"), None)
        kol_r = next((c for c in adja.columns if c.upper() == "RODZAJ"), None)
        if kol_t and kol_r:
            trafione = adja[(adja[kol_r].astype(str) == "gmina") & adja[kol_t].astype(str).str.startswith(a.gmina)]
        else:
            trafione = filtruj(adja, re.escape(a.gmina))
        if not trafione.empty:
            granica = unary_union(trafione.geometry.values)
    if granica is None and a.bbox:
        from shapely.geometry import box
        granica = box(*map(float, a.bbox.split(",")))
    if granica is None:
        sys.exit("Nie znalazlem granicy gminy w OT_ADJA_A - podaj --bbox minx,miny,maxx,maxy (EPSG:2180).")
    os_ = unary_union(lin.geometry.values).intersection(granica)
    linie = [os_] if os_.geom_type == "LineString" else [g for g in getattr(os_, "geoms", []) if g.geom_type == "LineString"]
    print(f"Linie w gminie: {os_.length / 1000:.1f} km, {len(linie)} odcinkow. Pobieram dzialki z ULDK...")

    cache_p = OUT / f"linie_bdot_{NR}_gmina_{a.gmina or 'bbox'}_cache.jsonl"
    dzialki = {}
    if cache_p.exists():
        for ln in cache_p.read_text(encoding="utf-8").splitlines():
            d = json.loads(ln)
            dzialki[d["teryt"]] = shp_wkt.loads(d["wkt"])
        print(f"  wczytano z pamieci: {len(dzialki)} dzialek")
    geoms = list(dzialki.values())
    drzewo = STRtree(geoms) if geoms else None
    nowe_od_przebudowy = []
    zap, start = 0, time.time()
    with open(cache_p, "a", encoding="utf-8") as cache:
        for ln_ in linie:
            for x, y in punkty_wzdluz(ln_):
                pt = Point(x, y)
                if drzewo is not None and any(geoms[i].contains(pt) for i in drzewo.query(pt)):
                    continue
                if any(g.contains(pt) for g in nowe_od_przebudowy):
                    continue
                if zap >= a.limit:
                    break
                zap += 1
                w = uldk_xy(x, y, a.offline)
                if not w or w[0] in dzialki:
                    continue
                dzialki[w[0]] = w[1]
                nowe_od_przebudowy.append(w[1])
                cache.write(json.dumps({"teryt": w[0], "wkt": w[1].wkt}) + "\n")
                if len(nowe_od_przebudowy) >= 200:
                    geoms = list(dzialki.values())
                    drzewo = STRtree(geoms)
                    nowe_od_przebudowy = []
                    cache.flush()
                    print(f"  {len(dzialki)} dzialek, {zap} zapytan, {time.time() - start:.0f} s")
    if zap >= a.limit:
        print(f"UWAGA: limit {a.limit} zapytan - uruchom ponownie, skrypt dokonczy od miejsca przerwania.")

    bud = warstwa(kat, "OT_BUBD_A")
    ptzb = warstwa(kat, "OT_PTZB_A")
    ptlz = warstwa(kat, "OT_PTLZ_A")
    ptwp = warstwa(kat, "OT_PTWP_A")
    ptkm = warstwa(kat, "OT_PTKM_A")
    woda = unary_union(ptwp.geometry.values) if ptwp is not None else None
    komun = unary_union(ptkm.geometry.values) if ptkm is not None else None
    zab = unary_union(ptzb.geometry.values) if ptzb is not None else None
    las = unary_union(ptlz.geometry.values) if ptlz is not None else None
    bud_tree = STRtree(list(bud.geometry.values)) if bud is not None else None
    os_all = unary_union(linie)
    pas_o, pas_s = os_all.buffer(PAS["o"]), os_all.buffer(PAS["s"])
    wiersze = []
    for teryt, g in dzialki.items():
        ps = g.intersection(pas_s).area
        if ps < 1:
            continue
        po = g.intersection(pas_o).area
        n_bud = int(sum(1 for i in bud_tree.query(g) if bud.geometry.values[i].intersects(g))) if bud_tree else 0
        if zab is not None and g.intersects(zab) or n_bud:
            grunt = "budowlana"
        elif las is not None and g.intersection(las).area > 0.5 * g.area:
            grunt = "lesna"
        else:
            grunt = "rolna"
        zwarta = 4 * math.pi * g.area / (g.length ** 2) if g.length else 0
        uw = "waska - droga/row?" if zwarta < 0.12 and not n_bud else ""
        if woda is not None and g.intersection(woda).area > 0.5 * g.area:
            uw = "woda - zwykle Skarb Panstwa"
        elif komun is not None and g.intersection(komun).area > 0.5 * g.area and not n_bud:
            uw = "droga/kolej - zwykle gmina/SP"
        cena = CENY[grunt]
        k = K_GRUNT[grunt]
        wiersze.append(dict(teryt=teryt, nr=teryt.split(".")[-1], pow=g.area, pas7=po, pas12=ps,
                            proc=100 * ps / g.area, budynki=n_bud, grunt=grunt, cena=cena,
                            sluz_o=po * cena * k, sluz_s=ps * cena * k, rok_s=ps * cena * U * k,
                            uwagi=uw, geom=g))
    df = pd.DataFrame(wiersze)
    if df.empty:
        sys.exit("Brak dzialek pod pasem.")
    wlasc = df[df.uwagi == ""]
    S = lambda d, k: d[k].sum()
    r = [f"DZIALKI POD LINIA - GMINA {a.gmina or a.bbox} ({datetime.now():%Y-%m-%d %H:%M})",
         f"Zrodla: BDOT10k (linie, budynki, tereny zabudowy, lasy), ULDK (dzialki). Filtr linii: '{a.filtr}'",
         f"Ceny gruntu [zl/m2]: {CENY}; k: {K_GRUNT}; wzor: pas x cena x k (sluzebnosc), x {U} rocznie", "",
         f"Linie w gminie:                          {os_.length / 1000:8.1f} km",
         f"Dzialki pod pasem 12 m (wszystkie):      {len(df):8d}",
         f"  pominiete (drogi, rowy, wody):         {len(df) - len(wlasc):8d}",
         f"Dzialki do analizy:                      {len(wlasc):8d}",
         f"  z budynkiem:                           {int((wlasc.budynki > 0).sum()):8d}",
         f"  budowlane / rolne / lesne:             {int((wlasc.grunt == 'budowlana').sum())} / "
         f"{int((wlasc.grunt == 'rolna').sum())} / {int((wlasc.grunt == 'lesna').sum())}",
         f"Pas 12 m w tych dzialkach:               {S(wlasc, 'pas12') / 10000:8.2f} ha",
         f"Pas 7 m w tych dzialkach:                {S(wlasc, 'pas7') / 10000:8.2f} ha",
         f"Mediana udzialu pasa w dzialce:          {wlasc.proc.median():8.1f} %", "",
         f"Szacunek sluzebnosci razem: {S(wlasc, 'sluz_o') / 1e6:.2f} mln zl (pas 7 m) - "
         f"{S(wlasc, 'sluz_s') / 1e6:.2f} mln zl (pas 12 m)",
         f"Szacunek 6 lat wstecz razem (pas 12 m): {6 * S(wlasc, 'rok_s') / 1e6:.2f} mln zl",
         f"Mediana na dzialke budowlana (pas 12 m): "
         f"{wlasc[wlasc.grunt == 'budowlana'].sluz_s.median() if (wlasc.grunt == 'budowlana').any() else 0:,.0f} zl".replace(",", " "),
         "", "To skala, nie roszczenia: nie wiadomo, ile dzialek ma juz uregulowany stan prawny (sluzebnosc w KW,",
         "decyzja, umowa). Dane BDOT10k maja dokladnosc rzedu kilku metrow."]
    zapisz(f"gmina_{a.gmina or 'bbox'}", "\n".join(r))
    csv_p = OUT / f"linie_bdot_{NR}_gmina_{a.gmina or 'bbox'}.csv"
    with open(csv_p, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["dzialka", "teryt", "pow m2", "pas 7 m m2", "pas 12 m m2", "% dzialki", "budynki",
                    "grunt", "cena zl/m2", "sluzebnosc 7 m zl", "sluzebnosc 12 m zl", "uwagi"])
        for _, x in df.sort_values("pas12", ascending=False).iterrows():
            w.writerow([x.nr, x.teryt, f"{x['pow']:.0f}", f"{x.pas7:.0f}", f"{x.pas12:.0f}",
                        f"{x.proc:.1f}".replace(".", ","), x.budynki, x.grunt, x.cena,
                        f"{x.sluz_o:.0f}", f"{x.sluz_s:.0f}", x.uwagi])
    gdf = gpd.GeoDataFrame(df.drop(columns=["geom"]), geometry=list(df.geom), crs=CRS)
    gp = OUT / f"linie_bdot_{NR}_gmina_{a.gmina or 'bbox'}.gpkg"
    gdf.to_file(gp, layer="dzialki", driver="GPKG")
    gpd.GeoDataFrame(geometry=[pas_s], crs=CRS).to_file(gp, layer="pas12", driver="GPKG")
    print(f"Tabela: {csv_p}\nWarstwy do QGIS: {gp}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Linie energetyczne z BDOT10k: km, budynki, dzialki pod pasem")
    ap.add_argument("etap", choices=["kraj", "rozpoznanie", "powiat", "gmina"])
    ap.add_argument("--powiat", default="0403", help="TERYT powiatu wyrozniony w etapie kraj")
    ap.add_argument("--bdot", required=True, help="katalog z rozpakowanym BDOT10k powiatu")
    ap.add_argument("--filtr", help="slowo/regex oznaczajace linie SN w polach OT_SULN_L (z etapu rozpoznanie)")
    ap.add_argument("--gmina", help="TERYT gminy, np. 040301 (szukany w OT_ADJA_A)")
    ap.add_argument("--bbox", help="zamiast gminy: minx,miny,maxx,maxy w EPSG:2180")
    ap.add_argument("--limit", type=int, default=20000, help="max zapytan ULDK w jednym uruchomieniu")
    ap.add_argument("--offline", action="store_true", help="test bez internetu (dzialki-atrapy)")
    a = ap.parse_args()
    {"kraj": kraj, "rozpoznanie": rozpoznanie, "powiat": powiat, "gmina": gmina}[a.etap](a)
