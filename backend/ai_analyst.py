"""
IMPACT-X — Phase 9: AI Security Analyst
Takes an incident + its blast radius + risk score (Phases 5-7) and produces
a plain-language executive brief grounded in actual graph data.

UPDATED:
  - Prompt rewritten for a non-technical reader (exec/judge), not a SOC lead —
    shorter sentences, no jargon like "lateral movement" left unexplained.
  - In-process cache keyed on the numbers that actually determine the
    output, so re-viewing the same incident (or two people opening the
    same one) doesn't re-hit the API and doesn't feel slow.
  - No AI provider name appears anywhere in output or logs surfaced to
    the user — keep it that way; if you switch providers again later,
    nothing user-facing needs to change.
"""

import os
import time
import concurrent.futures
from functools import lru_cache
from dotenv import load_dotenv

_ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=_ENV_PATH)

MODEL = "llama-3.3-70b-versatile"
_client = None


def _get_client():
    global _client
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None
    if _client is None:
        try:
            from groq import Groq
            _client = Groq(api_key=api_key)
        except ImportError:
            return None
    return _client


def _build_prompt(incident, blast_radius, risk):
    """Plain-language prompt: write for someone who has never seen a SOC
    dashboard before, not a security analyst."""
    services = ", ".join(
        f"{s['label']} ({s['criticality']} priority)" for s in blast_radius.get("business_services_affected", [])
    ) or "no critical business services"

    top_path = None
    if blast_radius.get("business_services_affected"):
        top_path = blast_radius["business_services_affected"][0].get("attack_path")
    path_str = " → ".join(top_path) if top_path else "no direct route to a critical service"

    return f"""You are explaining a cybersecurity incident to a non-technical executive
who has 30 seconds to read this. Avoid jargon. If you must use a technical
term, briefly explain it in plain words the first time.

INCIDENT FACTS:
- Person involved: {incident['user_name']}, {incident['role']} in {incident['department']} (access level: {incident['privilege_level']})
- What happened: {incident['incident_type']}
- Risk score: {risk['score']}/100 ({risk['status']})
- Systems this account could reach: {blast_radius['reachable_count']} total, {blast_radius['critical_count']} of them sensitive
- Important services within reach: {services}
- Example path an attacker could take: {path_str}

Write exactly 3 short sections using markdown bold titles, plain sentences, no bullet lists:
**What Happened:** [1 simple sentence — who, and what triggered the alert]
**Why It Matters:** [1-2 plain sentences — what could have been reached and how serious that is, avoid technical terms like "lateral movement"]
**What To Do Now:** [1 direct, concrete action a non-technical reader could hand to IT]"""


def _fallback_explanation(incident, blast_radius, risk):
    """Deterministic plain-language template used when no AI backend is
    configured or the call fails — matches the same 3-section format."""
    services = blast_radius.get("business_services_affected", [])
    service_names = ", ".join(s["label"] for s in services) if services else "no critical systems"

    what_happened = (
        f"**What Happened:** {incident['user_name']} ({incident['role']}, {incident['department']}) "
        f"triggered a security alert: '{incident['incident_type']}'."
    )

    if risk["status"] in ("CRITICAL", "HIGH"):
        why = (
            f"**Why It Matters:** This account could reach {blast_radius['reachable_count']} systems in total, "
            f"including {blast_radius['critical_count']} that hold sensitive data. That puts {service_names} at risk "
            f"if the account is actually compromised."
        )
    else:
        why = (
            f"**Why It Matters:** This account's reach is limited — {blast_radius['reachable_count']} systems total, "
            f"only {blast_radius['critical_count']} sensitive — so the potential damage is low even in a worst case."
        )

    if risk["status"] == "CRITICAL":
        action = (
            f"**What To Do Now:** Disable '{incident['user_name']}''s account immediately, log them out of every "
            f"session, and have IT check the systems this account could reach for anything unusual."
        )
    elif risk["status"] == "HIGH":
        action = (
            f"**What To Do Now:** Temporarily suspend this account's access while IT confirms whether the activity "
            f"was legitimate."
        )
    elif risk["status"] == "MEDIUM":
        action = (
            f"**What To Do Now:** Have IT review this account's recent activity logs as part of normal checks — "
            f"no urgent action needed yet."
        )
    else:
        action = "**What To Do Now:** No action needed — this is logged for the record only."

    return f"{what_happened}\n\n{why}\n\n{action}"


def _call_groq(client, prompt):
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


@lru_cache(maxsize=256)
def _cached_call(cache_key, prompt):
    """The cache key is the incident id + risk score + reachable count —
    the exact things that determine the output. Same incident, same
    numbers, same viewer or a different one -> instant, no repeat API
    call. This is what actually addresses "the AI summary feels slow"."""
    client = _get_client()
    return _call_groq(client, prompt)


def explain_incident(incident, blast_radius, risk, max_retries=2, timeout_seconds=20):
    """
    Returns a dict: {"explanation": str, "source": "ai" | "template" | "cached", "error": optional_str}
    """
    client = _get_client()

    if client is None:
        return {"explanation": _fallback_explanation(incident, blast_radius, risk), "source": "template"}

    prompt = _build_prompt(incident, blast_radius, risk)
    cache_key = (incident["id"], risk["score"], blast_radius["reachable_count"], blast_radius["critical_count"])

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_cached_call, cache_key, prompt)
                text = future.result(timeout=timeout_seconds)
            return {"explanation": text, "source": "ai"}
        except concurrent.futures.TimeoutError:
            last_error = f"Timed out after {timeout_seconds}s waiting for a response."
            break
        except Exception as e:
            last_error = str(e)
            if attempt < max_retries and ("UNAVAILABLE" in last_error or "503" in last_error):
                time.sleep(1.5)
                continue
            break

    fallback = _fallback_explanation(incident, blast_radius, risk)
    return {"explanation": fallback, "source": "template", "error": last_error}


if __name__ == "__main__":
    from risk_engine import score_incident
    from incident_engine import get_all_incidents, simulate_incident
    from graph_engine import build_graph

    incidents = get_all_incidents()
    if not incidents:
        simulate_incident(privilege_level="admin")
        incidents = get_all_incidents()

    graph = build_graph()
    result = score_incident(incidents[0]["id"], graph=graph)

    print("=== Automated Incident Briefing Output ===")
    output = explain_incident(result["incident"], result["blast_radius"], result["risk"])
    print(f"[Source Mode: {output['source']}]")
    if "error" in output:
        print(f"[Error Details: {output['error']}]")
    print("\n" + output["explanation"])