"""Validate the GSS data behind plot.py.

Checks, in order:
  1. Value labels in the raw file mean what get_data.py assumes.
  2. Raw 2024 counts match NORC's published 2024 codebook (unweighted frequencies,
     Release 1, May 19 2025: SEX p.44, PARTYID p.57).
  3. Every raw respondent is accounted for in data/gss_gender_party.csv.
  4. Shares recomputed straight from the raw file, by a separate route, match
     the ones plot.py draws.
  5. Sensitivity: how much the gender gap moves with a different weight or none.

Run after get_data.py. Exits non-zero if any of checks 1-4 fails.
"""

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from pandas.io.stata import StataMissingValue

from plot import START, shares

warnings.filterwarnings("ignore", category=UnicodeWarning)

RAW = next(Path("data/raw").rglob("gss7224*.dta"))
CLEAN = Path("data/gss_gender_party.csv")

# NORC 2024 GSS codebook, unweighted frequencies.
CODEBOOK_2024 = {
    "sex": {1: 1467, 2: 1823, ".d": 7, ".n": 1, ".s": 11},
    "partyid": {0: 532, 1: 372, 2: 340, 3: 829, 4: 274, 5: 378, 6: 460, 7: 83, ".n": 41},
}
EXPECTED_LABELS = {
    "sex": {1: "male", 2: "female"},
    "partyid": {0: "strong democrat", 3: "independent (neither, no response)",
                6: "strong republican", 7: "other party"},
}

failures = []


def check(ok, msg):
    print(("  PASS  " if ok else "  FAIL  ") + msg)
    if not ok:
        failures.append(msg)


def main():
    reader = pd.io.stata.StataReader(RAW)
    labels = reader.value_labels()
    lblset = dict(zip(reader._varlist, reader._lbllist))
    raw = pd.read_stata(RAW, columns=["year", "sex", "partyid", "wtssps", "wtssnrps"],
                        convert_categoricals=False, convert_missing=True)

    print(f"1. Value labels ({RAW.name})")
    for var, want in EXPECTED_LABELS.items():
        got = labels[lblset[var]]
        for code, text in want.items():
            check(got.get(code) == text, f"{var}={code} is '{text}' (file says '{got.get(code)}')")

    print("\n2. 2024 counts vs NORC codebook")
    y24 = raw[raw["year"] == 2024]
    for var, want in CODEBOOK_2024.items():
        got = y24[var].astype(str).value_counts()
        for code, n in want.items():
            check(got.get(str(code), 0) == n, f"{var}={code}: {got.get(str(code), 0)} vs codebook {n}")
    check(len(y24) == 3309, f"2024 total: {len(y24)} vs codebook 3309")

    print("\n3. Raw file -> cleaned CSV")
    num = raw.map(lambda v: np.nan if isinstance(v, StataMissingValue) else v).astype(float)
    keep = num["partyid"].between(0, 6) & num["sex"].isin([1, 2])
    clean = pd.read_csv(CLEAN)
    dropped = {
        "other party (7)": (num["partyid"] == 7).sum(),
        "party ID missing": num["partyid"].isna().sum(),
        "sex missing (party valid)": (num["partyid"].between(0, 6) & num["sex"].isna()).sum(),
    }
    for why, n in dropped.items():
        print(f"        dropped {n:>5,}  {why}")
    check(len(clean) == keep.sum(), f"cleaned rows {len(clean):,} = raw valid rows {keep.sum():,}")
    check(len(raw) - keep.sum() == sum(dropped.values()),
          f"all {len(raw):,} raw rows accounted for")
    check(np.allclose(num.loc[keep].groupby("year")["wtssps"].mean(), 1, atol=0.05),
          "wtssps averages ~1 in every year (on valid rows)")

    print(f"\n4. Shares recomputed from raw, {START}-2024")
    r = num[keep & (num["year"] >= START)]
    dem = r["partyid"] <= 2
    rep = r["partyid"] >= 4
    indep = pd.DataFrame({"year": r["year"], "sex": r["sex"],
                          "d": dem * r["wtssps"], "r": rep * r["wtssps"], "w": r["wtssps"]})
    g = indep.groupby(["year", "sex"])[["d", "r", "w"]].sum()
    ours = shares(clean).set_index(["year", "gender"])
    for sex, gender in [(1, "Men"), (2, "Women")]:
        a = g.xs(sex, level="sex")
        b = ours.xs(gender, level="gender")
        diff = max((a.d / a.w * 100 - b.Democrat).abs().max(),
                   (a.r / a.w * 100 - b.Republican).abs().max())
        check(diff < 1e-9, f"{gender}: max difference {diff:.1e} points")

    print("\n5. Sensitivity of the gender gap (women minus men, net Dem ID, points)")
    def gap(weight):
        w = weight if weight is not None else pd.Series(1.0, index=r.index)
        net = ((dem.astype(float) - rep) * w).groupby([r["year"], r["sex"]]).sum() \
            / w.groupby([r["year"], r["sex"]]).sum() * 100
        net = net.unstack()
        return net[2] - net[1]
    sens = pd.DataFrame({"wtssps (used)": gap(r["wtssps"]),
                         "wtssnrps": gap(r["wtssnrps"]),
                         "unweighted": gap(None)})
    sens.index = sens.index.astype(int)
    print(sens.round(1).to_string())
    print(f"\n        mean |wtssps - unweighted| = {(sens.iloc[:, 0] - sens.iloc[:, 2]).abs().mean():.1f}")
    print(f"        mean |wtssps - wtssnrps|   = {(sens.iloc[:, 0] - sens.iloc[:, 1]).abs().mean():.1f}")

    print("\nAll checks passed." if not failures else f"\n{len(failures)} check(s) FAILED.")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
