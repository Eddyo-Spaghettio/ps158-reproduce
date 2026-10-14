"""First look: party identification by gender, 1980-2024.

Reads the cleaned files written by get_data.py and saves figure.png
(and figure.pdf), styled as a black-and-white journal figure with a numbered caption
and a source note below.
Panel A: weighted share of men and women identifying as Democrats and as
Republicans (leaners counted with their party). Panel B: the gender gap in
net Democratic identification (% Dem - % Rep, women minus men).
"""

import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

START = 1980
OUT = Path("figure")

SOURCES = {"GSS": "data/gss_gender_party.csv", "ANES": "data/anes_gender_party.csv"}
SOURCE_NOTES = {
    "GSS": "General Social Survey cumulative file, 1972–2024 (NORC, Release 3a, July 2026)",
    "ANES": "American National Election Studies Time Series Cumulative Data File, "
            "1948–2024 (version 2026-02-05)",
}

# Black-and-white encoding: gender by line style, party by marker, survey by grey level.
LINE = {"Women": "-", "Men": "--"}
MARKER = {"Democrat": dict(marker="o", mfc="black"), "Republican": dict(marker="s", mfc="white")}
SHADE = {"GSS": "black", "ANES": "0.55"}

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
    "font.size": 9,
    "axes.linewidth": 0.6,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "xtick.direction": "out",
    "ytick.direction": "out",
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "legend.frameon": False,
    "savefig.dpi": 300,
})


def shares(df):
    """Weighted % Democrat and % Republican by year and gender."""
    df = df[df["year"] >= START]
    tot = df.groupby(["year", "gender"])["weight"].sum()
    by_party = df.groupby(["year", "gender", "party3"])["weight"].sum()
    pct = (by_party / tot * 100).unstack("party3")
    pct["net_dem"] = pct["Democrat"] - pct["Republican"]
    return pct.reset_index()


def main():
    data = {name: shares(pd.read_csv(p)) for name, p in SOURCES.items() if Path(p).exists()}
    tag = len(data) > 1  # only label the survey in legends when there is more than one

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.5, 4.6))

    for name, pct in data.items():
        color = SHADE[name]
        for gender, g in pct.groupby("gender"):
            for party, m in MARKER.items():
                ax1.plot(g.year, g[party], LINE[gender], color=color, lw=0.9, ms=3.2,
                         mec=color, mew=0.7, **m,
                         label=f"{gender}, {party}" + (f" ({name})" if tag else ""))

        wide = pct.pivot(index="year", columns="gender", values="net_dem")
        gap = wide["Women"] - wide["Men"]
        ax2.plot(gap.index, gap.values, "-", color=color, lw=0.9, marker="o", ms=3.2,
                 mfc=color, mec=color, label=name)

    ax1.set(ylabel="Percent identifying with party", xlabel="Survey year")
    ax1.set_title("A. Party identification by gender", loc="left", fontsize=9)

    ax2.axhline(0, color="black", lw=0.5, ls=":")
    ax2.set(ylabel="Gap in net Democratic ID (points)", xlabel="Survey year")
    ax2.set_title("B. Gender gap (women minus men)", loc="left", fontsize=9)
    if tag:
        ax2.legend(fontsize=7, loc="lower right")

    # Key below the panels so it never covers data.
    handles, labels = ax1.get_legend_handles_labels()
    fig.subplots_adjust(left=0.08, right=0.98, top=0.93, bottom=0.36, wspace=0.28)
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.255),
               ncol=4, fontsize=7.5, handlelength=2.6, columnspacing=1.6)

    for ax in (ax1, ax2):
        ax.set_xlim(START - 2, 2026)
        ax.set_xticks(range(START, 2030, 10))

    caption = (
        "Figure 1. Party identification of American men and women, "
        f"{START}–2024. Panel A shows the percentage of each gender identifying "
        "as Democrats and as Republicans; panel B shows the difference between women "
        "and men in net Democratic identification (percent Democrat minus percent "
        "Republican)."
    )
    note = (
        "Note: Estimates are weighted. Independents who lean toward a party are "
        "classified with that party; respondents not coded male or female are excluded. "
        "Source: " + "; ".join(SOURCE_NOTES[n] for n in data) + "."
    )
    fig.text(0.02, 0.165, textwrap.fill(caption, 118), ha="left", va="top", fontsize=9)
    fig.text(0.02, 0.055, textwrap.fill(note, 150), ha="left", va="top", fontsize=7.5,
             style="italic")

    for ext in ("png", "pdf"):
        fig.savefig(OUT.with_suffix(f".{ext}"), bbox_inches="tight", pad_inches=0.15)
    print("Saved figure.png and figure.pdf")

    for name, pct in data.items():
        wide = pct.pivot(index="year", columns="gender", values="net_dem")
        print(f"\n{name}: net Dem ID by gender, and gap (women - men)")
        print(wide.assign(gap=wide.Women - wide.Men).round(1).to_string())


if __name__ == "__main__":
    main()
