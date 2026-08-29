"""
IMPACT-X — Phase 9: AI Security Analyst
Takes an incident + its blast radius + risk score (Phases 5-7) and produces
a plain-language explanation of why it matters, grounded in the actual
graph data — not a generic canned response.

Uses Google's Gemini API (free tier via Google AI Studio, no billing
required) when a GEMINI_API_KEY environment variable is set. If not set,
or if the API call fails for any reason, falls back to a deterministic
template built from the same data — so the demo never breaks without
internet/API access.
"""

import os
import time
import concurrent.futures
from dotenv import load_dotenv

# Loads variables from a .env file in the project root into the environment.
# We build an explicit path (rather than relying on load_dotenv()'s default
# search from the current working directory) so this works identically no
# matter how or from where the script is launched — terminal, VS Code's Run
# button, or main.py.
_ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=_ENV_PATH)

# gemini-3.6-flash is Google's current fast/free-tier model as of this
# writing. If Google retires this model too, the error message from a
# failed API call will name the current replacement — update here.
MODEL = "gemini-3.6-flash"

_client = None


def _get_client():
    """Lazily creates the Gemini client only if a key is present,
    so importing this module never fails when the SDK/key is missing."""
    global _client
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return None
    if _client is None:
        try:
            from google import genai
            _client = genai.Client(api_key=api_key)
        except ImportError:
            return None
    return _client


def _build_prompt(incident, blast_radius, risk):
    services = ", ".join(
        f"{s['label']} ({s['criticality']})" for s in blast_radius["business_services_affected"]
    ) or "none"

    top_path = None
    if blast_radius["business_services_affected"]:
        top_path = blast_radius["business_services_affected"][0]["attack_path"]
    path_str = " -> ".join(top_path) if top_path else "no path to a business service found"

    return f"""You are a security analyst assistant embedded in IMPACT-X, a cyber blast-radius
analysis platform. Explain the following incident to a SOC analyst in 3-4 concise sentences.
Be direct and specific, referencing the actual numbers given. Do not invent details not provided.

INCIDENT
- Type: {incident['incident_type']}
- Affected identity: {incident['user_name']} ({incident['role']}, {incident['department']})
- Privilege level: {incident['privilege_level']}

BLAST RADIUS
- Directly accessible assets: {blast_radius['direct_count']}
- Total reachable assets (all hops): {blast_radius['reachable_count']}
- Critical (high-sensitivity) assets reached: {blast_radius['critical_count']}
- Business services affected: {services}
- Example attack path: {path_str}

RISK SCORE
- Score: {risk['score']}/100
- Status: {risk['status']}

Explain why this incident is (or isn't) serious, referencing the specific reachable systems and
the attack path. End with one concrete recommended action for the analyst."""


def _fallback_explanation(incident, blast_radius, risk):
    """Deterministic template used when no API key is available."""
    services = blast_radius["business_services_affected"]
    service_names = ", ".join(s["label"] for s in services) if services else "no monitored business services"

    lines = []
    lines.append(
        f"{incident['user_name']} ({incident['role']}, {incident['department']}, "
        f"{incident['privilege_level']} privilege) triggered a '{incident['incident_type']}' alert."
    )

    if risk["status"] in ("CRITICAL", "HIGH"):
        lines.append(
            f"This identity can reach {blast_radius['reachable_count']} systems in total, including "
            f"{blast_radius['critical_count']} high-sensitivity asset(s), putting {service_names} at risk."
        )
    else:
        lines.append(
            f"This identity's reach is limited — {blast_radius['reachable_count']} systems total, "
            f"with {blast_radius['critical_count']} high-sensitivity asset(s) exposed."
        )

    if services and services[0]["attack_path"]:
        lines.append("Example attack path: " + " → ".join(services[0]["attack_path"]) + ".")

    if risk["status"] == "CRITICAL":
        lines.append(
            f"Risk score {risk['score']}/100 (CRITICAL). Recommended action: disable this identity "
            f"immediately, force credential rotation, and audit recent activity on all reachable systems."
        )
    elif risk["status"] == "HIGH":
        lines.append(
            f"Risk score {risk['score']}/100 (HIGH). Recommended action: investigate this identity's "
            f"recent activity now and consider temporary access suspension pending review."
        )
    elif risk["status"] == "MEDIUM":
        lines.append(
            f"Risk score {risk['score']}/100 (MEDIUM). Recommended action: review the alert during "
            f"normal triage and confirm the activity was legitimate."
        )
    else:
        lines.append(
            f"Risk score {risk['score']}/100 (LOW). Recommended action: log for audit purposes; "
            f"no immediate containment action required."
        )

    return " ".join(lines)


def _call_gemini(client, prompt):
    """Runs the actual API call — used inside a timeout wrapper below."""
    response = client.models.generate_content(model=MODEL, contents=prompt)
    return response.text.strip()


def explain_incident(incident, blast_radius, risk, max_retries=2, timeout_seconds=20):
    """
    Returns a dict: {"explanation": str, "source": "ai" | "template"}

    - incident: dict from INCIDENTS/USERS join (as produced by risk_engine.score_incident)
    - blast_radius: dict from blast_radius.calculate_blast_radius()
    - risk: dict from risk_engine.calculate_risk_score()
    - max_retries: number of extra attempts if Google's API is temporarily
      overloaded (503 UNAVAILABLE) before falling back to the template.
    - timeout_seconds: hard ceiling per attempt. If the network stalls (no
      response at all — not even an error), this ensures we never hang
      indefinitely and always fall back to the template within this time.
    """
    client = _get_client()

    if client is None:
        return {"explanation": _fallback_explanation(incident, blast_radius, risk), "source": "template"}

    prompt = _build_prompt(incident, blast_radius, risk)
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_call_gemini, client, prompt)
                text = future.result(timeout=timeout_seconds)
            return {"explanation": text, "source": "ai"}
        except concurrent.futures.TimeoutError:
            last_error = f"Timed out after {timeout_seconds}s (no response from Gemini)."
            break  # a stalled connection is unlikely to resolve on retry — go straight to fallback
        except Exception as e:
            last_error = str(e)
            if attempt < max_retries and "UNAVAILABLE" in last_error:
                time.sleep(1.5)  # brief pause before retrying an overloaded model
                continue
            break

    # All attempts failed — never let an API hiccup (quota, network, timeout) break the demo.
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

    print("=== AI Analyst (source will show 'template' unless GEMINI_API_KEY is set) ===")
    output = explain_incident(result["incident"], result["blast_radius"], result["risk"])
    print(f"[source: {output['source']}]\n")
    if "error" in output:
        print(f"[ERROR DETAIL: {output['error']}]\n")
    print(output["explanation"])