"""YouTube forecast (point estimate + tight range), leave-one-out backtest with hit/miss scoring, baseline comparison.
Usage: python forecast_backtest.py REAL_VIDEOS_CSV IDEAS_JSON [--synthetic SYNTHETIC_CSV] [--aggregate AGG_CSV] [--as-of YYYY-MM-DD] [--window-start YYYY-MM-DD]
Point estimate: closest real comparable, or cluster median when 2+. Range: cluster min-max or +/-30% of point, whichever is narrower.
Confidence: medium with a direct real cluster comparable, else low. Synthetic comparables are reported on a separate line and never raise confidence.
Sheet views are window totals, an upper bound on first-7-day views. LinkedIn is never combined with YouTube. Contains no data."""
import argparse, json
import numpy as np, pandas as pd
from ytlib import load_videos, load_aggregate


def forecast_from(series, fallback):
    """series: cluster views (real). fallback: all-mature views. Returns point, lo, hi, basis, confidence."""
    if len(series) >= 1:
        p = float(series.median()); basis = "cluster median n=%d" % len(series) if len(series) >= 2 else "single closest comparable"
        lo, hi = 0.7 * p, 1.3 * p
        if len(series) >= 2:
            lo, hi = max(lo, float(series.min())), min(hi, float(series.max()))
        return p, lo, hi, basis, "medium"
    p = float(fallback.median())
    return p, 0.7 * p, 1.3 * p, "overall median, no cluster comparable", "low"


def backtest(m):
    rows = []
    for i in m.index:
        train = m.drop(index=i)
        p, lo, hi, basis, conf = forecast_from(train[train["cluster"] == m.loc[i, "cluster"]]["views"], train["views"])
        a = float(m.loc[i, "views"]); base = float(train["views"].median())
        rows.append(dict(id=m.loc[i, "id"], cluster=m.loc[i, "cluster"], actual=a, point=p, lo=lo, hi=hi, hit=bool(lo <= a <= hi),
                         model_err=abs(p - a), base_err=abs(base - a), miss_size=0.0 if lo <= a <= hi else min(abs(a - lo), abs(a - hi))))
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("videos"); ap.add_argument("ideas"); ap.add_argument("--synthetic"); ap.add_argument("--aggregate")
    ap.add_argument("--as-of", default=str(pd.Timestamp.today().date())); ap.add_argument("--window-start", default="2026-10-15")
    a = ap.parse_args()
    v = load_videos(a.videos, a.as_of, a.window_start); m = v[v["mature"]]
    print("SAMPLE: real mature n=%d" % len(m), end="")
    syn = None
    if a.synthetic:
        syn = load_videos(a.synthetic, a.as_of, a.window_start, require_window=False); syn = syn[syn["mature"]]
        print("; synthetic (assumed) n=%d" % len(syn))
    else:
        print()
    print(m[["id", "cluster", "age_days", "views", "impressions", "ctr"]].to_string(index=False))
    if len(m) >= 3:
        bt = backtest(m)
        print("LOO BACKTEST (real, n=%d)" % len(bt)); print(bt.round(1).to_string(index=False))
        print("MAE views: model point=%.1f, median baseline=%.1f. Model beats baseline: %s" % (bt.model_err.mean(), bt.base_err.mean(), bt.model_err.mean() < bt.base_err.mean()))
        print("Range hits: %d of %d; mean miss size on misses=%.1f views" % (bt.hit.sum(), len(bt), bt[~bt.hit].miss_size.mean() if (~bt.hit).any() else 0.0))
    else:
        print("Backtest skipped: fewer than 3 mature videos")
    for idea in json.load(open(a.ideas)):
        c = m[m["cluster"] == idea["cluster"]]["views"]
        p, lo, hi, basis, conf = forecast_from(c, m["views"])
        print("Idea %s YouTube first-7-day views (upper bound, measured comparables): point %d, range %d-%d, %s, confidence %s" % (idea["id"], round(p), round(lo), round(hi), basis, conf))
        if len(c): print("   real comparables:", ", ".join("%s=%d" % (r.id, r.views) for r in m[m["cluster"] == idea["cluster"]].itertuples()))
        if syn is not None:
            sc = syn[syn["cluster"] == idea["cluster"]]["views"]
            print("   synthetic (assumed) comparables: n=%d%s" % (len(sc), (", median %d, min %d, max %d" % (sc.median(), sc.min(), sc.max())) if len(sc) else ""))
    if a.aggregate:
        g = load_aggregate(a.aggregate)
        print("LINKEDIN window aggregate (measured, separate from YouTube): impressions=%s, members reached=%s; no per-post rows, so no per-idea comparables" % (g.get("impressions"), g.get("members reached")))


if __name__ == "__main__":
    main()
