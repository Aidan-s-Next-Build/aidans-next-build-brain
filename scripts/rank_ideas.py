"""Rule-based ranker. Usage: python rank_ideas.py VIDEOS_CSV IDEAS_JSON [--as-of YYYY-MM-DD] [--window-start YYYY-MM-DD]
Weights come from winning-patterns.md (specificity, hiring relevance, effort) plus cluster evidence from the sheet.
This is rule-based and not learned. Weights change only when a later PR shows evidence."""
import argparse, json
import pandas as pd
from ytlib import load_videos

W = {"hiring_relevance": 2.0, "specificity": 2.0, "effort": -1.0, "cluster_evidence": 1.0}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("videos"); p.add_argument("ideas")
    p.add_argument("--as-of", default=str(pd.Timestamp.today().date()))
    p.add_argument("--window-start", default="2026-10-15")
    a = p.parse_args()
    v = load_videos(a.videos, a.as_of, a.window_start)
    m = v[v["mature"]]
    overall = m["views"].median()
    rows = []
    for idea in json.load(open(a.ideas)):
        c = m[m["cluster"] == idea["cluster"]]["views"]
        evidence = (c.median() / overall) if len(c) else 1.0  # 1.0 = no cluster comparable
        score = sum(W[k] * (evidence if k == "cluster_evidence" else idea[k]) for k in W)
        rows.append({"id": idea["id"], "title": idea["title"], "cluster_n": int(len(c)), "evidence": round(float(evidence), 2), "score": round(float(score), 2)})
    out = pd.DataFrame(rows).sort_values("score", ascending=False)
    out["rank"] = range(1, len(out) + 1)
    print("RANKER (rule-based, not learned). mature comparables n=%d" % len(m))
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
