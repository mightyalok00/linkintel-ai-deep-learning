FEATURE_COLUMNS = [
    "referring_domains", "outbound_link_ratio", "content_relevance",
    "domain_age_years", "anchor_diversity", "thin_content_ratio",
]

def validate_feature_row(row: dict) -> dict:
    missing = [column for column in FEATURE_COLUMNS if row.get(column) is None]
    if missing:
        raise ValueError("Missing ML features: " + ", ".join(missing))
    clean = {}
    for column in FEATURE_COLUMNS:
        value = float(row[column])
        if not (value == value and abs(value) != float("inf")):
            raise ValueError(f"Invalid non-finite feature: {column}")
        clean[column] = value
    return clean
