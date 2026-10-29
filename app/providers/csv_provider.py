import csv
import io
from app.schemas import ProspectInput

def parse_prospects_csv(content: bytes) -> list[ProspectInput]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV must be UTF-8 encoded.") from exc
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or "domain" not in reader.fieldnames:
        raise ValueError("CSV must include a 'domain' column.")
    bool_fields = {"mandatory_purchase", "paid_plan_required",
                   "free_submission_available", "terms_verified"}
    numeric_fields = {"authority_score", "backlink_quality", "spam_risk",
                      "relevance", "placement_fee", "submission_fee"}
    results = []
    for row in reader:
        values = {k: v for k, v in row.items() if k}
        for key in bool_fields:
            if values.get(key, "") == "":
                values[key] = None if key in {"mandatory_purchase", "paid_plan_required"} else False
            else:
                val = values[key].strip().lower()
                if val not in {"true", "false", "1", "0", "yes", "no"}:
                    raise ValueError(f"Invalid boolean value for {key}.")
                values[key] = val in {"true", "1", "yes"}
        for key in numeric_fields:
            if values.get(key, "") == "":
                values[key] = None
            else:
                values[key] = float(values[key])
        results.append(ProspectInput(**values))
    return results
