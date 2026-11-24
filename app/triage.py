import json
import urllib.request
from .config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

def _template(evidence):
    return {
      "summary": f"{evidence.get('partner_id','Partner')} feed: {evidence.get('rejected',0)} rejected, "
                 f"{evidence.get('duplicates',0)} duplicates, discrepancy {evidence.get('discrepancy',0)}.",
      "recommended_next_step": "Review rejected rows and reconcile the source file with the partner before reprocessing.",
      "needs_human_review": True,
      "source": "template_fallback"
    }

def generate_triage(evidence):
    fallback = _template(evidence)
    if not LLM_API_KEY:
        return fallback
    prompt = (
      "Use only this evidence. Return JSON with keys summary (max 3 short lines), "
      "recommended_next_step, needs_human_review (boolean). Do not invent causes. "
      + json.dumps(evidence)
    )
    body = json.dumps({
      "model": LLM_MODEL,
      "messages": [{"role":"user","content":prompt}],
      "response_format": {"type":"json_object"},
      "temperature": 0
    }).encode()
    req = urllib.request.Request(
      LLM_BASE_URL.rstrip("/") + "/chat/completions", data=body,
      headers={"Authorization":"Bearer "+LLM_API_KEY, "Content-Type":"application/json"}
    )
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=12) as response:
                raw = json.loads(response.read().decode())
            content = raw["choices"][0]["message"]["content"]
            obj = json.loads(content)
            if not isinstance(obj.get("summary"), str) or not isinstance(obj.get("recommended_next_step"), str) or not isinstance(obj.get("needs_human_review"), bool):
                raise ValueError("Invalid triage schema")
            obj["source"] = "llm"
            return obj
        except Exception:
            if attempt == 1:
                return fallback
    return fallback
