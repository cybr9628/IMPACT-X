"""
IMPACT-X — Phase 2: Simulated Organization Generator
Builds a fictional company (NovaTech Corporation) with users, applications,
databases, servers, APIs, cloud resources, business services, and the
relationships that connect them.

This module does NOT touch the database — it only produces Python data
structures. Phase 3 (database.py) will consume this to populate SQLite.
"""

import random

random.seed(42)  # reproducible demo data

COMPANY_NAME = "NovaTech Corporation"

DEPARTMENTS = [
    "Finance", "HR", "Engineering", "Sales", "Marketing",
    "IT", "Legal", "Operations", "Customer Support", "Executive"
]

ROLES_BY_DEPT = {
    "Finance": ["Finance Manager", "Accountant", "Payroll Specialist", "CFO"],
    "HR": ["HR Manager", "Recruiter", "HR Generalist"],
    "Engineering": ["Software Engineer", "DevOps Engineer", "Engineering Manager", "QA Engineer"],
    "Sales": ["Sales Rep", "Sales Manager", "Account Executive"],
    "Marketing": ["Marketing Manager", "Content Specialist", "SEO Analyst"],
    "IT": ["IT Admin", "System Administrator", "Security Analyst", "IT Support"],
    "Legal": ["Legal Counsel", "Compliance Officer"],
    "Operations": ["Operations Manager", "Logistics Coordinator"],
    "Customer Support": ["Support Agent", "Support Team Lead"],
    "Executive": ["CEO", "COO", "CISO"],
}

PRIVILEGE_LEVELS = ["standard", "elevated", "admin"]

FIRST_NAMES = ["Alex", "Jordan", "Taylor", "Morgan", "Sam", "Casey", "Riley", "Jamie",
               "Avery", "Cameron", "Drew", "Quinn", "Reese", "Rowan", "Skyler", "Emerson",
               "Blake", "Hayden", "Parker", "Dakota", "Elliot", "Finley", "Harper", "Jesse",
               "Kendall", "Logan", "Micah", "Nico", "Oakley", "Peyton"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
              "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
              "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
              "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson"]

APP_TEMPLATES = {
    "Finance": ["Finance Application", "Payroll System", "Expense Manager"],
    "HR": ["HR Portal", "Recruiting Platform"],
    "Engineering": ["CI/CD Platform", "Internal Dev Portal", "Monitoring Dashboard"],
    "Sales": ["CRM Application", "Sales Analytics Tool"],
    "Marketing": ["Marketing Automation Suite", "Campaign Manager"],
    "IT": ["Identity & Access Manager", "Endpoint Management Console"],
    "Legal": ["Contract Management System"],
    "Operations": ["Supply Chain Tracker", "Inventory System"],
    "Customer Support": ["Ticketing System", "Customer Portal"],
    "Executive": ["Executive Reporting Dashboard"],
}

CLOUD_PROVIDERS = ["AWS", "Azure", "GCP"]


def _full_name():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def generate_users(count=70):
    users = []
    for i in range(1, count + 1):
        dept = random.choice(DEPARTMENTS)
        role = random.choice(ROLES_BY_DEPT[dept])
        if dept == "Executive" or "Manager" in role or "Admin" in role or "CISO" in role:
            privilege = random.choices(PRIVILEGE_LEVELS, weights=[1, 3, 6])[0]
        else:
            privilege = random.choices(PRIVILEGE_LEVELS, weights=[7, 2, 1])[0]
        users.append({
            "id": f"U{i:03d}",
            "name": _full_name(),
            "department": dept,
            "role": role,
            "privilege_level": privilege,
        })
    return users


def generate_applications():
    apps = []
    app_id = 1
    for dept, templates in APP_TEMPLATES.items():
        for name in templates:
            apps.append({
                "id": f"APP{app_id:03d}",
                "name": name,
                "owner_department": dept,
            })
            app_id += 1
    return apps


def generate_databases(apps):
    databases = []
    for i, app in enumerate(apps, start=1):
        sensitivity = "high" if app["owner_department"] in ("Finance", "HR", "Legal", "Executive") else \
                      random.choice(["medium", "low"])
        databases.append({
            "id": f"DB{i:03d}",
            "name": f"{app['name'].replace(' Application', '').replace(' System', '')} Database",
            "linked_app": app["id"],
            "data_sensitivity": sensitivity,
        })
    return databases


def generate_apis(apps):
    apis = []
    for i, app in enumerate(apps, start=1):
        apis.append({
            "id": f"API{i:03d}",
            "name": f"{app['name'].split(' ')[0]} API",
            "linked_app": app["id"],
        })
    return apis


def generate_servers(count=20):
    return [{"id": f"SRV{i:03d}", "name": f"App-Server-{i:02d}",
             "hosts_app": None} for i in range(1, count + 1)]


def generate_cloud_resources(count=15):
    return [{"id": f"CLD{i:03d}",
             "name": f"{random.choice(CLOUD_PROVIDERS)}-Resource-{i:02d}",
             "provider": random.choice(CLOUD_PROVIDERS)} for i in range(1, count + 1)]


def generate_business_services():
    return [
        {"id": "SVC001", "name": "Payment Service", "criticality": "critical"},
        {"id": "SVC002", "name": "Payroll Service", "criticality": "critical"},
        {"id": "SVC003", "name": "Customer Data Service", "criticality": "high"},
        {"id": "SVC004", "name": "Employee Records Service", "criticality": "high"},
        {"id": "SVC005", "name": "Reporting Service", "criticality": "medium"},
        {"id": "SVC006", "name": "Support Operations Service", "criticality": "medium"},
    ]


def generate_relationships(users, apps, databases, apis, servers, cloud_resources, services):
    """Builds the edges of the graph: HAS_ACCESS, CONNECTS_TO, DEPENDS_ON, HOSTS, SUPPORTS, OWNS."""
    relationships = []

    apps_by_dept = {}
    for app in apps:
        apps_by_dept.setdefault(app["owner_department"], []).append(app)

    # USER -> APPLICATION (HAS_ACCESS)
    for user in users:
        dept_apps = apps_by_dept.get(user["department"], [])
        if not dept_apps:
            continue
        n_apps = 1 if user["privilege_level"] == "standard" else random.randint(1, 3)
        for app in random.sample(dept_apps, min(n_apps, len(dept_apps))):
            relationships.append({"from": user["id"], "to": app["id"], "type": "HAS_ACCESS"})
        if random.random() < 0.1:
            other_app = random.choice(apps)
            relationships.append({"from": user["id"], "to": other_app["id"], "type": "HAS_ACCESS"})

    # APPLICATION -> DATABASE (CONNECTS_TO)
    for db in databases:
        relationships.append({"from": db["linked_app"], "to": db["id"], "type": "CONNECTS_TO"})

    # APPLICATION -> API (DEPENDS_ON)
    for api in apis:
        relationships.append({"from": api["linked_app"], "to": api["id"], "type": "DEPENDS_ON"})

    # SERVER -> APPLICATION (HOSTS)
    apps_pool = apps.copy()
    for server in servers:
        if not apps_pool:
            apps_pool = apps.copy()
        app = random.choice(apps_pool)
        server["hosts_app"] = app["id"]
        relationships.append({"from": server["id"], "to": app["id"], "type": "HOSTS"})

    # CLOUD_RESOURCE -> DATABASE (HOSTS)
    for cloud in cloud_resources:
        db = random.choice(databases)
        relationships.append({"from": cloud["id"], "to": db["id"], "type": "HOSTS"})

    # DATABASE -> BUSINESS SERVICE (SUPPORTS)
    dept_to_service = {
        "Finance": "SVC001", "HR": "SVC002", "Sales": "SVC003",
        "Customer Support": "SVC006", "Legal": "SVC004", "Executive": "SVC005",
        "Engineering": "SVC005", "IT": "SVC005", "Marketing": "SVC003", "Operations": "SVC006",
    }
    app_dept_map = {a["id"]: a["owner_department"] for a in apps}
    for db in databases:
        dept = app_dept_map.get(db["linked_app"], "Operations")
        service_id = dept_to_service.get(dept, "SVC005")
        relationships.append({"from": db["id"], "to": service_id, "type": "SUPPORTS"})

    # DEPARTMENT MANAGERS -> OWNS APPLICATION
    for app in apps:
        managers = [u for u in users if u["department"] == app["owner_department"]
                    and "Manager" in u["role"] or u["role"] in ("CEO", "CFO", "COO", "CISO")]
        if managers:
            relationships.append({"from": random.choice(managers)["id"], "to": app["id"], "type": "OWNS"})

    return relationships


def build_organization():
    users = generate_users(70)
    apps = generate_applications()
    databases = generate_databases(apps)
    apis = generate_apis(apps)
    servers = generate_servers(20)
    cloud_resources = generate_cloud_resources(15)
    services = generate_business_services()
    relationships = generate_relationships(users, apps, databases, apis, servers, cloud_resources, services)

    return {
        "company": COMPANY_NAME,
        "users": users,
        "applications": apps,
        "databases": databases,
        "apis": apis,
        "servers": servers,
        "cloud_resources": cloud_resources,
        "business_services": services,
        "relationships": relationships,
    }


if __name__ == "__main__":
    org = build_organization()
    print(f"Company: {org['company']}")
    for key in ["users", "applications", "databases", "apis", "servers", "cloud_resources", "business_services", "relationships"]:
        print(f"{key}: {len(org[key])}")