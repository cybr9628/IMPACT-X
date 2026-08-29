# IMPACT-X

### Incident-to-Impact Cybersecurity Intelligence

> **"An alert tells you something happened. IMPACT-X shows what it could potentially affect."**

IMPACT-X is a cybersecurity platform that analyzes security incidents across interconnected enterprise identities, applications, APIs, databases, infrastructure, and business services.

Instead of treating an incident as an isolated alert, IMPACT-X maps the affected entity through an enterprise relationship graph to identify **potential attack paths, blast radius, critical assets, and business impact**.

## ⚡ How It Works

```text
Security Incident
       ↓
Affected User / Asset
       ↓
Enterprise Security Graph
       ↓
Attack-Path Analysis
       ↓
Blast-Radius Analysis
       ↓
Risk Score
       ↓
Security Recommendation

🔥 Key Features
- 🕸️ Enterprise Relationship Graph — Maps users, applications, databases, APIs, infrastructure and business services.
- 🎯 Attack-Path Analysis — Identifies potential paths from an affected entity to critical resources.
- 💥 Blast-Radius Analysis — Estimates the potential scope of an incident.
- 📊 Risk Prioritization — Produces explainable risk scores based on privilege, criticality, sensitivity and reachability.
- 🧠 Pattern Analysis — Compares incidents with historical security events to identify recurring patterns.
- 🛡️ Security Recommendations — Suggests controls that may reduce future exposure.
- 📈 Interactive Dashboard — Provides a visual view of incidents, relationships, risk and potential impact.
🏢 Environment
IMPACT-X currently uses NovaTech Corporation, a synthetic enterprise environment containing users, applications, databases, APIs, servers, cloud resources and business services.
Using synthetic data allows realistic security scenarios to be tested without exposing real organizational infrastructure or sensitive information.
🛠️ Tech Stack
Frontend: React / Next.js · TypeScript · Tailwind CSS
Backend: Python · FastAPI
Security Engine: NetworkX · Custom Risk Engine
Database: SQLite / PostgreSQL
Visualization: Interactive Security Graph
🎯 Why IMPACT-X?
Traditional alerts answer:
"What happened?"

IMPACT-X focuses on:
"What could this incident potentially affect, how significant is it, and what should we investigate next?"

🚧 Project Status
Active Development
Currently developing the graph-based attack-path, blast-radius, risk-analysis and historical-pattern engines.
🔐 Disclaimer
IMPACT-X is intended for authorized defensive security analysis, research and educational use only.
