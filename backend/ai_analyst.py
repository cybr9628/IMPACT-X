"""
IMPACT-X — Phase 9: AI Security Analyst
Takes an incident + its blast radius + risk score (Phases 5-7) and produces
a plain-language executive brief grounded in actual graph data.

Uses Groq (free tier, no billing required, low latency) when GROQ_API_KEY is set.
Falls back seamlessly to a matching deterministic template if offline or if API calls fail.
"""

import os
import time
import concurrent.futures
from dotenv import load_dotenv

# Explicit path to .env file at project root
_ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=_ENV_PATH)

MODEL = "llama-3.3-70b-versatile"
_client = None


def _get_client():
    """Lazily creates the Groq client only if an API key is present."""
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
    """Builds a structured prompt forcing exact executive briefing formatting."""
    services = ", ".join(
        f"{s['label']} ({s['criticality']})" for s in blast_radius.get("business_services_affected", [])
    ) or "None monitored"

    top_path = None
    if blast_radius.get("business_services_affected"):
        top_path = blast_radius["business_services_affected"][0].get("attack_path")
    path_str = " → ".join(top_path) if top_path else "No direct attack path to critical services"

    return f"""You are a senior SOC lead briefing executive management on a security incident.
Provide a clear, structured assessment in exactly 3 sections using markdown bold titles.

INCIDENT METRICS:
- Identity: {incident['user_name']} ({incident['role']}, {incident['department']}) | Privilege: {incident['privilege_level']}
- Incident Event: {incident['incident_type']}
- Risk Rating: {risk['score']}/100 ({risk['status']})
- Reachable Assets: {blast_radius['reachable_count']} total ({blast_radius['critical_count']} critical)
- Critical Services Exposed: {services}
- Example Attack Path: {path_str}

Format your output EXACTLY as:
**Primary Threat:** [1 concise sentence on what occurred and who triggered it]
**Business Impact:** [1-2 sentences explaining reachable assets, critical service exposure, and lateral movement risk]
**Immediate Action:** [1 direct, actionable containment recommendation]"""


def _fallback_explanation(incident, blast_radius, risk):
    """Deterministic structured template matching the AI format when API key is unavailable."""
    services = blast_radius.get("business_services_affected", [])
    service_names = ", ".join(s["label"] for s in services) if services else "no monitored business services"

    top_path = services[0].get("attack_path") if services and services[0].get("attack_path") else []
    path_str = " → ".join(top_path) if top_path else "no direct path to critical business services"

    # Section 1: Primary Threat
    primary_threat = (
        f"**Primary Threat:** {incident['user_name']} ({incident['role']}, {incident['department']}, "
        f"{incident['privilege_level']} privilege) triggered a '{incident['incident_type']}' security alert."
    )

    # Section 2: Business Impact
    if risk["status"] in ("CRITICAL", "HIGH"):
        impact = (
            f"**Business Impact:** Identity can reach {blast_radius['reachable_count']} total assets "
            f"({blast_radius['critical_count']} critical), placing {service_names} at risk via path: {path_str}."
        )
    else:
        impact = (
            f"**Business Impact:** Threat reach is contained to {blast_radius['reachable_count']} total assets "
            f"({blast_radius['critical_count']} critical) with low risk to enterprise operations."
        )

    # Section 3: Immediate Action
    if risk["status"] == "CRITICAL":
        action = (
            f"**Immediate Action:** Disable user '{incident['user_name']}' immediately, revoke active sessions, "
            f"and perform forensic audits on all reachable critical systems."
        )
    elif risk["status"] == "HIGH":
        action = (
            f"**Immediate Action:** Suspend access privileges for '{incident['user_name']}' pending SOC triage "
            f"and isolate vulnerable target nodes."
        )
    elif risk["status"] == "MEDIUM":
        action = (
            f"**Immediate Action:** Review recent activity logs during standard triage to verify action authorization."
        )
    else:
        action = (
            f"**Immediate Action:** Log incident for operational record; no account suspension required."
        )

    return f"{primary_threat}\n\n{impact}\n\n{action}"


def _call_groq(client, prompt):
    """Runs the API call with strict formatting constraint parameters."""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


def explain_incident(incident, blast_radius, risk, max_retries=2, timeout_seconds=20):
    """
    Returns a dict: {"explanation": str, "source": "ai" | "template", "error": optional_str}
    """
    client = _get_client()

    if client is None:
        return {"explanation": _fallback_explanation(incident, blast_radius, risk), "source": "template"}

    prompt = _build_prompt(incident, blast_radius, risk)
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_call_groq, client, prompt)
                text = future.result(timeout=timeout_seconds)
            return {"explanation": text, "source": "ai"}
        except concurrent.futures.TimeoutError:
            last_error = f"Timed out after {timeout_seconds}s (no response from Groq)."
            break
        except Exception as e:
            last_error = str(e)
            if attempt < max_retries and ("UNAVAILABLE" in last_error or "503" in last_error):
                time.sleep(1.5)
                continue
            break

    # Fallback execution if API attempts fail
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