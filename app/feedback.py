import json
import os
from datetime import datetime, timezone

from app.config import settings
from app.models import FeedbackRequest


def save_feedback(feedback: FeedbackRequest):
    record = feedback.model_dump()
    record["timestamp"] = datetime.now(timezone.utc).isoformat()

    os.makedirs(os.path.dirname(os.path.abspath(settings.FEEDBACK_LOG_PATH)), exist_ok=True)
    with open(settings.FEEDBACK_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    return record


def feedback_stats() -> dict:
    path = settings.FEEDBACK_LOG_PATH
    if not os.path.exists(path):
        return {"total": 0, "up": 0, "down": 0, "avg_confidence": 0.0}

    total = up = down = 0
    conf_sum = 0.0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            total += 1
            conf_sum += rec.get("confidence", 0.0)
            if rec.get("rating") == "up":
                up += 1
            elif rec.get("rating") == "down":
                down += 1

    return {
        "total": total,
        "up": up,
        "down": down,
        "avg_confidence": round(conf_sum / total, 4) if total else 0.0,
    }
