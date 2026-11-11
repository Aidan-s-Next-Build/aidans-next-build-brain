"""YouTube forecast plus leave-one-out backtest against a simple baseline.
Usage: python forecast_backtest.py VIDEOS_CSV IDEAS_JSON [--as-of YYYY-MM-DD] [--window-start YYYY-MM-DD]
Target: views of videos published in the window and at least 7 days old. Sheet views are window totals, so they are an upper
bound on first-7-day views. LinkedIn is never combined with YouTube; see linkedin_summary."""
import argparse, json
import numpy as np, pandas as pd
from ytlib import load_videos, load_aggregate


def cluster_pred(train, cluster):
    c = train[train["cluster"] == cluster]["views"]
    return c.mean() if len(c) else train["views"].median()


def backtest(m):
    base, model, actual = [], [], []
    for i in m.index:
        train = m.drop(index=i)
        base.append(train["views"].median())
        model.append(cluster_pred(train, m.loc[i, "cluster"]))
        actual.append(m.loc[i, "views"])
    actual = np.array(actual)
    return float(np.mean(np.abs(np.array(base) - actual))), float(np.mean(np.abs(np.array(model) - actual)))


def forecast(m, idea):
    c = m[m["cluster"] == idea["cluster"]]["views"]
    if len(c) >= 2:
        lo, hi, basis = c.min(), c.max(), "cluster range n=%d" % len(c)
    elif len(c) == 1:
        lo, hi, basis = 0.5 * c.iloc[0], 1.5 * c.iloc[0], "single comparable +/-50%"
    else:
        lo, hi, basis = m["views"].min(), m["views"].max(), "all mature videos range (no cluster comparable)"
    conf = "low" if len(m) < 10 else "medium"
    return int(round(lo)), int(round(hi)), basis, conf


def main():
    p = argparse.ArgumentParser()
    p.add_argument("videos"); p.add_argument("ideas"); p.add_argument("--aggregate")
    p.add_argument("--as-of", default=str(pd.Timestamp.today().date()))
    p.add_argument("--window-start", default="2026-10-15")
    a = p.parse_args()
    v = load_videos(a.videos, a.as_of, a.window_start)
    m = v[v["mature"]]
    print("YouTube comparables (published in window, age >= 7 days): n=%d" % len(m))
    print(m[["id", "cluster", "age_days", "views", "impressions", "ctr"]].to_string(index=False))
    if len(m) >= 3:
        b, c = backtest(m)
        print("LOO backtest MAE views: baseline median=%.1f, cluster mean=%.1f, n=%d" % (b, c, len(m)))
        print("Cluster model beats baseline: %s (provisional, tiny sample)" % (c < b))
    else:
        print("Backtest skipped: fewer than 3 mature videos")
    for idea in json.load(open(a.ideas)):
        lo, hi, basis, conf = forecast(m, idea)
        print("Idea %s YouTube 7-day views range %d-%d, %s, confidence %s" % (idea["id"], lo, hi, basis, conf))
    if a.aggregate:
        g = load_aggregate(a.aggregate)
        print("LinkedIn window aggregate (separate from YouTube): impressions=%s, members reached=%s; no per-post rows, so no per-idea comparables" % (g.get("impressions"), g.get("members reached")))


if __name__ == "__main__":
    main()
