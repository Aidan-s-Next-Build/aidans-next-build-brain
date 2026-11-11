"""Shared loaders for the YouTube and LinkedIn sheet CSV exports. Contains no analytics data."""
import pandas as pd

ALIASES = {
    "id": ["Content", "Bv4uPCMWbzlHERQ2"],
    "title": ["Video title", "itoPB-fBIGPI3sMv"],
    "published": ["Video publish time", "YsTcrHel39hiHhCz"],
    "duration_s": ["Duration", "47PeOrtzg1KQq5jZ"],
    "views": ["Views", "S1Z6V5gIf2wiFQpF"],
    "watch_hours": ["Watch time (hours)", "4Rhr0LBdExZx3_sl"],
    "subs": ["Subscribers", "7vxEDTL51oD5uV63"],
    "impressions": ["Thumbnail impressions", "O0EPIoRQnXfmjiH3"],
    "ctr": ["Thumbnail click-through rate (%)", "Zx7sUBkpzutW3F8R"],
}
NUMERIC = ["duration_s", "views", "watch_hours", "subs", "impressions", "ctr"]
MIN_AGE_DAYS = 7  # a video needs 7 days of age before its views count as a 7-day comparable

CLUSTER_RULES = [
    ("hiring_howto", ["hired", "hiring", "job"]),
    ("market_take", ["cooked"]),
    ("systems_build", ["build systems", "systems."]),
    ("crypto_ai_verification", ["abc", "crypto", "oracle", "ai systems", "gh systems", "aml"]),
]


def topic_cluster(title):
    t = str(title).lower()
    for name, keys in CLUSTER_RULES:
        if any(k in t for k in keys):
            return name
    return "other"


def load_videos(path, as_of, window_start):
    df = pd.read_csv(path)
    rename = {}
    for key, names in ALIASES.items():
        for n in names:
            if n in df.columns:
                rename[n] = key
                break
    df = df.rename(columns=rename)
    df = df[df["id"].astype(str).str.lower() != "total"].copy()
    for c in NUMERIC:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["published"] = pd.to_datetime(df["published"], errors="coerce")
    df["age_days"] = (pd.Timestamp(as_of) - df["published"]).dt.days
    df["in_window"] = df["published"] >= pd.Timestamp(window_start)
    df["mature"] = df["in_window"] & (df["age_days"] >= MIN_AGE_DAYS) & df["views"].notna()
    df["cluster"] = df["title"].map(topic_cluster)
    return df


def load_aggregate(path):
    df = pd.read_csv(path)
    cols = [c for c in df.columns if c != "row_id"]
    out = {}
    for _, r in df.iterrows():
        out[str(r[cols[0]]).strip().lower()] = pd.to_numeric(r[cols[1]], errors="coerce")
    return out
