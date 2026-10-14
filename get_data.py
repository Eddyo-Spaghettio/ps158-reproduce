"""Download survey data on gender and party identification, 1980s-present.

Sources
-------
1. General Social Survey (GSS) cumulative file, 1972-2024 (NORC, Release 3a, July 2026).
   Downloaded automatically from gss.norc.org.
2. ANES Time Series Cumulative Data File, 1948-2024 (version 2026-02-05).
   electionstudies.org blocks scripted downloads, so get it by hand:
     https://electionstudies.org/data-center/anes-time-series-cumulative-data-file/
   Download the CSV, unzip it, and put the .csv in data/raw/. This script picks it up
   if it is there and skips ANES otherwise.

Output: data/gss_gender_party.csv and (if available) data/anes_gender_party.csv,
each with one row per respondent: year, gender, party (7-point), party3, weight.
"""

import io
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd

RAW = Path("data/raw")
OUT = Path("data")

GSS_URL = "https://gss.norc.org/content/dam/gss/get-the-data/documents/stata/GSS_stata.zip"

PARTY3 = {"Democrat": "Democrat", "Independent": "Independent", "Republican": "Republican"}


def download_gss():
    """Fetch the GSS Stata zip (~48 MB) unless it is already in data/raw."""
    dta = next(RAW.rglob("gss7224*.dta"), None)
    if dta:
        return dta
    print(f"Downloading {GSS_URL}")
    req = Request(GSS_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req) as resp:
        zf = zipfile.ZipFile(io.BytesIO(resp.read()))
    name = next(n for n in zf.namelist() if n.lower().endswith(".dta"))
    return Path(zf.extract(name, RAW))


def clean_gss(path):
    # partyid: 0 strong Dem, 1 not-very-strong Dem, 2 ind. near Dem, 3 independent,
    #          4 ind. near Rep, 5 not-very-strong Rep, 6 strong Rep, 7 other party.
    # sex: 1 male, 2 female. wtssps is NORC's recommended weight for the cumulative file.
    cols = ["year", "sex", "partyid", "wtssps"]
    df = pd.read_stata(path, columns=cols, convert_categoricals=False)
    df = df[df["partyid"].between(0, 6) & df["sex"].isin([1, 2])].copy()
    out = pd.DataFrame({
        "year": df["year"].astype(int),
        "gender": df["sex"].map({1: "Men", 2: "Women"}),
        "party": df["partyid"].astype(int) + 1,  # rescale to 1 (strong D) - 7 (strong R)
        "weight": df["wtssps"],
    })
    # Leaners counted with their party, the usual convention in the gender-gap literature.
    out["party3"] = pd.cut(out["party"], [0, 3, 4, 7], labels=list(PARTY3)).astype(str)
    return out


def clean_anes(path):
    # VCF0004 year; VCF0104 gender (1 male, 2 female, 3 other);
    # VCF0301 7-point party ID (1 strong D ... 7 strong R; 0 = DK/NA);
    # VCF0009z full-sample weight. Check names against the 2026-02-05 codebook.
    cols = ["VCF0004", "VCF0104", "VCF0301", "VCF0009z"]
    df = pd.read_csv(path, usecols=cols, low_memory=False)
    df = df.apply(pd.to_numeric, errors="coerce")
    df = df[df["VCF0301"].between(1, 7) & df["VCF0104"].isin([1, 2])]
    out = pd.DataFrame({
        "year": df["VCF0004"].astype(int),
        "gender": df["VCF0104"].map({1: "Men", 2: "Women"}),
        "party": df["VCF0301"].astype(int),
        "weight": df["VCF0009z"],
    })
    out["party3"] = pd.cut(out["party"], [0, 3, 4, 7], labels=list(PARTY3)).astype(str)
    return out


def main():
    RAW.mkdir(parents=True, exist_ok=True)

    gss = clean_gss(download_gss())
    gss.to_csv(OUT / "gss_gender_party.csv", index=False)
    print(f"GSS: {len(gss):,} respondents, {gss.year.min()}-{gss.year.max()}")

    anes_csv = next(RAW.rglob("anes_timeseries_cdf*.csv"), None)
    if anes_csv:
        anes = clean_anes(anes_csv)
        anes.to_csv(OUT / "anes_gender_party.csv", index=False)
        print(f"ANES: {len(anes):,} respondents, {anes.year.min()}-{anes.year.max()}")
    else:
        print("ANES: no CSV in data/raw/ - see the docstring for how to download it.")


if __name__ == "__main__":
    main()
