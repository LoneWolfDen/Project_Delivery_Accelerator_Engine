"""Migration Dashboard — self-contained server that embeds data into HTML."""
import json, csv, os, re
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from project_manager import (
    list_projects, get_project, create_project, delete_project,
    update_project, list_files, save_file, delete_file, read_enabled_files,
    ARTIFACTS, LLM_BACKENDS,
)

try:
    import boto3
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

import sys
sys.path.insert(0, str(Path(__file__).parent))
from stories_data import STORIES
from gates_data import GATES as GATES_DATA

DATA_DIR = Path(__file__).parent
PORT = 8888

def load_csv_json(filepath):
    """Load CSV and return as JSON array."""
    if not filepath.exists():
        return []
    with open(filepath) as f:
        return list(csv.DictReader(f))

def load_csv_text(filepath):
    if not filepath.exists():
        return ""
    return filepath.read_text()

# Pre-load all data
EPICS = load_csv_json(DATA_DIR / "migration_epic_plan.csv")
RESOURCES = load_csv_json(DATA_DIR / "migration_resource_plan.csv")
TRACKING = load_csv_json(DATA_DIR / "migration_operational_tracking.csv")
NFRS = load_csv_json(DATA_DIR / "migration_nfr_requirements.csv")

# Gantt data: epic → roles with man-days and activities
GANTT = [
  {"epic_id":"E-001","epic":"Landing Zone & Network","phase":"Phase 0","start":1,"end":4,"roles":[
    {"role":"Cloud Solutions Architect","count":2,"man_days":40,"activities":["Design multi-account structure","Configure AWS Organizations","Design VPC topology & Transit Gateway","Establish Direct Connect / VPN","Define IAM roles & policies","Set up CloudTrail & Config"]},
    {"role":"DevOps / Platform Engineer","count":2,"man_days":30,"activities":["Provision accounts via IaC (Terraform/CDK)","Set up CI/CD pipelines","Configure CloudWatch dashboards","Deploy shared services (logging, monitoring)"]},
    {"role":"Network Engineer","count":1,"man_days":20,"activities":["Configure VPN tunnels","Set up Direct Connect","DNS configuration (Route 53)","Firewall rules & security groups","Hybrid connectivity testing"]},
    {"role":"Security Engineer","count":1,"man_days":15,"activities":["Define security baseline","Configure GuardDuty & Security Hub","Set up KMS keys","Establish encryption policies","IAM policy reviews"]}
  ]},
  {"epic_id":"E-002","epic":"Cloud Readiness & Training","phase":"Phase 0","start":1,"end":4,"roles":[
    {"role":"Change Manager / Training Lead","count":1,"man_days":20,"activities":["Develop training curriculum","Deliver AWS fundamentals training","Establish Cloud CoE charter","Define operating model","Create communication plan"]},
    {"role":"Migration Programme Manager","count":1,"man_days":15,"activities":["Stakeholder alignment","Define governance model","Establish reporting cadence","Risk register setup"]},
    {"role":"Scrum Master / Delivery Lead","count":1,"man_days":10,"activities":["Set up JIRA/Azure DevOps","Define sprint cadence","Establish ceremonies","Cross-team coordination model"]}
  ]},
  {"epic_id":"E-003","epic":"Migration Tooling & CI/CD","phase":"Phase 0","start":2,"end":4,"roles":[
    {"role":"DevOps / Platform Engineer","count":2,"man_days":24,"activities":["Set up DMS replication instances","Configure SCT for schema conversion","Build IaC modules (compute, DB, network)","CI/CD pipeline templates","Container registry setup"]},
    {"role":"Database Migration Specialist","count":2,"man_days":18,"activities":["Configure DMS endpoints","Test replication for each DB engine","Schema conversion validation","Build migration runbooks"]},
    {"role":"QA / Test Automation Engineer","count":1,"man_days":10,"activities":["Set up test frameworks","Build data validation scripts","Performance test baseline tooling"]}
  ]},
  {"epic_id":"E-004","epic":"Data Classification & Governance","phase":"Phase 0","start":2,"end":4,"roles":[
    {"role":"Data Engineer / Big Data Specialist","count":1,"man_days":12,"activities":["Catalogue all data stores","Classify data sensitivity levels","Establish data quality baseline metrics","Configure AWS Glue Data Catalog"]},
    {"role":"Security Engineer","count":1,"man_days":8,"activities":["Define data retention policies","Map PII/sensitive data","Configure AWS Config rules","Compliance framework mapping"]},
    {"role":"Business Analyst","count":1,"man_days":10,"activities":["Document data ownership","Map business data flows","Stakeholder interviews for classification","Retention policy sign-off"]}
  ]},
  {"epic_id":"E-101","epic":"MDM Migration (APP-010)","phase":"Phase 1","start":5,"end":10,"roles":[
    {"role":"Java/Spring Boot Developer","count":2,"man_days":48,"activities":["Migrate Spring Boot services to ECS","Refactor Oracle-specific queries for RDS","Kafka producer/consumer migration to MSK","REST API endpoint validation","Connection pooling configuration"]},
    {"role":"Database Migration Specialist","count":1,"man_days":24,"activities":["Oracle 19c → RDS migration via DMS","MongoDB → DocumentDB migration","Schema optimization for RDS","Data validation & integrity checks","Performance tuning"]},
    {"role":"Data Engineer / Big Data Specialist","count":1,"man_days":20,"activities":["Kafka topic migration to MSK","Event schema registry setup","Data pipeline reconfiguration","Data quality checks post-migration"]},
    {"role":"DevOps / Platform Engineer","count":1,"man_days":18,"activities":["ECS cluster provisioning","RDS Multi-AZ setup","MSK cluster configuration","Monitoring & alerting setup","Auto-scaling policies"]},
    {"role":"QA / Test Automation Engineer","count":1,"man_days":15,"activities":["Integration test suite","API contract testing","Data integrity validation","Performance baseline testing","DR failover testing"]}
  ]},
  {"epic_id":"E-102","epic":"CDP Migration (APP-007)","phase":"Phase 1","start":5,"end":10,"roles":[
    {"role":"Python / ML Engineer","count":2,"man_days":48,"activities":["Spark jobs migration to EMR","Python service containerisation","gRPC endpoint migration","Event processing pipeline refactoring","ML model serving setup"]},
    {"role":"Data Engineer / Big Data Specialist","count":2,"man_days":40,"activities":["Cassandra → Keyspaces migration","Elasticsearch → OpenSearch migration","Kafka consumer group migration","Data replication validation","Event stream testing"]},
    {"role":"DevOps / Platform Engineer","count":1,"man_days":18,"activities":["EMR cluster provisioning","OpenSearch domain setup","Keyspaces configuration","Monitoring dashboards","Auto-scaling policies"]},
    {"role":"QA / Test Automation Engineer","count":1,"man_days":15,"activities":["Event processing latency testing","Data consistency validation","Chaos engineering (AZ failure)","Load testing at 10x volume"]}
  ]},
  {"epic_id":"E-103","epic":"Big Data Pipeline (APP-019)","phase":"Phase 1","start":6,"end":10,"roles":[
    {"role":"Data Engineer / Big Data Specialist","count":2,"man_days":40,"activities":["Hadoop → EMR migration","NiFi → MWAA workflow migration","S3 data lake partitioning design","Spark job optimization for EMR","Data quality framework (Deequ/Great Expectations)"]},
    {"role":"Python / ML Engineer","count":1,"man_days":15,"activities":["Python ETL script migration","Airflow DAG conversion","Data transformation validation","Scheduling & orchestration testing"]},
    {"role":"DevOps / Platform Engineer","count":1,"man_days":12,"activities":["EMR fleet configuration","S3 bucket policies & lifecycle","MWAA environment setup","Cost optimization (spot instances)"]}
  ]},
  {"epic_id":"E-104","epic":"Foundation Integration Testing","phase":"Phase 1","start":9,"end":11,"roles":[
    {"role":"QA / Test Automation Engineer","count":2,"man_days":24,"activities":["End-to-end integration test execution","Performance baseline validation","DR drill execution & validation","Regression suite finalization","Test report & sign-off"]},
    {"role":"Senior DevOps / SRE","count":1,"man_days":12,"activities":["DR drill orchestration","Chaos engineering tests","Performance tuning","Monitoring validation","Runbook testing"]},
    {"role":"Cloud Solutions Architect","count":1,"man_days":8,"activities":["Architecture review","Performance assessment","Capacity planning validation","Sign-off on production readiness"]}
  ]},
  {"epic_id":"E-201","epic":"E-Commerce Migration (APP-001)","phase":"Phase 2","start":12,"end":17,"roles":[
    {"role":"Java/Spring Boot Developer","count":2,"man_days":48,"activities":["Spring Boot services → ECS","Redis session migration to ElastiCache","OAuth 2.0 integration","API gateway configuration","Connection pooling & caching optimization"]},
    {"role":"Node.js / React Developer","count":1,"man_days":24,"activities":["React frontend deployment to CloudFront","SSR configuration","Asset pipeline optimization","CDN cache strategy"]},
    {"role":"Database Migration Specialist","count":1,"man_days":20,"activities":["PostgreSQL 14 → RDS migration","Read replica setup","Performance tuning","Data validation"]},
    {"role":"DevOps / Platform Engineer","count":1,"man_days":20,"activities":["ECS service mesh setup","ALB + CloudFront configuration","Auto-scaling (5x capacity)","Blue-green deployment pipeline"]},
    {"role":"Security Engineer","count":1,"man_days":15,"activities":["PCI-DSS compliance validation","WAF rule configuration","Shield Advanced setup","Penetration testing","Encryption audit"]},
    {"role":"QA / Test Automation Engineer","count":1,"man_days":18,"activities":["Load testing (Black Friday simulation)","PCI compliance testing","API regression suite","Performance benchmarking"]}
  ]},
  {"epic_id":"E-202","epic":"Loyalty Engine Migration (APP-002)","phase":"Phase 2","start":12,"end":16,"roles":[
    {"role":"Node.js / React Developer","count":2,"man_days":40,"activities":["Node.js microservices → EKS","MongoDB queries → DocumentDB","RabbitMQ → Amazon MQ migration","Event-driven architecture validation","Points calculation accuracy testing"]},
    {"role":"Database Migration Specialist","count":1,"man_days":15,"activities":["MongoDB → DocumentDB migration","Index optimization","Data consistency validation","Replica set configuration"]},
    {"role":"DevOps / Platform Engineer","count":1,"man_days":12,"activities":["EKS cluster setup","Amazon MQ configuration","ElastiCache provisioning","HPA auto-scaling policies"]},
    {"role":"QA / Test Automation Engineer","count":1,"man_days":12,"activities":["Points accuracy validation (100%)","Event flow testing","Load testing","Reconciliation job validation"]}
  ]},
  {"epic_id":"E-203","epic":"Demand Planning Migration (APP-003)","phase":"Phase 2","start":12,"end":16,"roles":[
    {"role":"Python / ML Engineer","count":2,"man_days":40,"activities":["Python/R forecasting models → EMR","Airflow DAGs → MWAA","Spark job optimization","Model accuracy validation (±5%)","Scheduling & dependency management"]},
    {"role":"Vendor / Integration Specialist","count":1,"man_days":15,"activities":["Kinaxis cloud compatibility validation","Vendor API integration testing","License compliance verification","Support agreement update"]},
    {"role":"DevOps / Platform Engineer","count":1,"man_days":10,"activities":["MWAA environment configuration","EMR cluster policies","S3 data staging setup"]},
    {"role":"QA / Test Automation Engineer","count":1,"man_days":12,"activities":["Forecast accuracy A/B testing","DAG execution validation","Performance benchmarking","Data freshness testing"]}
  ]},
  {"epic_id":"E-204","epic":"Trade Promotion Migration (APP-005)","phase":"Phase 2","start":14,"end":17,"roles":[
    {"role":"Java/Spring Boot Developer","count":1,"man_days":16,"activities":["Spring Boot 2.7 services → ECS","Kafka producer migration to MSK","SFTP → Transfer Family","Financial calculation validation"]},
    {"role":"Database Migration Specialist","count":1,"man_days":12,"activities":["PostgreSQL 15 → RDS migration","Performance tuning","Financial data integrity validation"]},
    {"role":"DevOps / Platform Engineer","count":1,"man_days":8,"activities":["ECS service setup","MSK topic configuration","Transfer Family SFTP endpoint"]},
    {"role":"QA / Test Automation Engineer","count":1,"man_days":10,"activities":["Financial precision testing","Kafka stream validation","Integration testing with E-Commerce"]}
  ]},
  {"epic_id":"E-205","epic":"Retail Analytics Migration (APP-008)","phase":"Phase 2","start":14,"end":18,"roles":[
    {"role":"Data Engineer / Big Data Specialist","count":1,"man_days":20,"activities":["Hadoop/Spark → EMR migration","Hive → Athena conversion","S3 data lake integration","Data freshness pipeline"]},
    {"role":"Python / ML Engineer","count":1,"man_days":15,"activities":["Python analytics scripts migration","Spark job optimization","Dashboard data pipeline","Reporting query optimization"]},
    {"role":"DevOps / Platform Engineer","count":1,"man_days":10,"activities":["EMR cluster configuration","Athena workgroup setup","QuickSight provisioning","Cost optimization (spot)"]},
    {"role":"QA / Test Automation Engineer","count":1,"man_days":12,"activities":["Dashboard load testing (200 users)","Batch job timing validation","Data freshness < 1h testing","Regression suite"]}
  ]},
  {"epic_id":"E-206","epic":"Core Business Integration Testing","phase":"Phase 2","start":17,"end":19,"roles":[
    {"role":"QA / Test Automation Engineer","count":2,"man_days":24,"activities":["Full integration test execution","Black Friday load simulation (5x)","Cross-app dependency validation","Incident drill execution","Sign-off documentation"]},
    {"role":"Senior DevOps / SRE","count":1,"man_days":12,"activities":["Load test orchestration","Performance tuning","Auto-scaling validation","Runbook finalization","Chaos engineering"]},
    {"role":"Migration Programme Manager","count":1,"man_days":6,"activities":["Go/no-go decision coordination","Stakeholder sign-off","Risk assessment update"]}
  ]},
  {"epic_id":"E-301","epic":"PLM Migration (APP-006)","phase":"Phase 3","start":20,"end":24,"roles":[
    {"role":".NET / C# Developer","count":2,"man_days":40,"activities":[".NET 6 services → ECS","IIS → Kestrel/ECS migration","RabbitMQ → Amazon MQ","SOAP→REST adapter for MES","Vendor (Dassault) integration testing"]},
    {"role":"Database Migration Specialist","count":1,"man_days":15,"activities":["MS SQL 2019 → RDS migration","Performance tuning","Data validation"]},
    {"role":"Vendor / Integration Specialist","count":1,"man_days":15,"activities":["Dassault cloud certification","Vendor support validation","License compliance","Integration testing coordination"]},
    {"role":"QA / Test Automation Engineer","count":1,"man_days":12,"activities":["Product search performance testing","BOM generation validation","Vendor integration testing","SOAP adapter testing"]}
  ]},
  {"epic_id":"E-302","epic":"FP&A Migration (APP-011)","phase":"Phase 3","start":20,"end":23,"roles":[
    {"role":"Java/Spring Boot Developer","count":1,"man_days":16,"activities":["Spring Batch → AWS Batch migration","Informatica → Glue ETL conversion","SFTP → Transfer Family","Batch scheduling configuration"]},
    {"role":"Database Migration Specialist","count":1,"man_days":12,"activities":["MS SQL 2019 → RDS (shared with PLM)","Informatica metadata migration","Performance tuning"]},
    {"role":"Security Engineer","count":1,"man_days":8,"activities":["SOX compliance validation","Audit trail configuration","Access control review","CloudTrail integration"]},
    {"role":"QA / Test Automation Engineer","count":1,"man_days":10,"activities":["Month-end batch simulation","SOX compliance testing","Financial reconciliation","Performance benchmarking"]}
  ]},
  {"epic_id":"E-303","epic":"Inventory Optimisation (APP-012)","phase":"Phase 3","start":21,"end":24,"roles":[
    {"role":"Python / ML Engineer","count":1,"man_days":16,"activities":["Python/R optimization models migration","Airflow DAGs → MWAA","Pandas pipelines containerization","Model accuracy validation (±3%)"]},
    {"role":"Database Migration Specialist","count":1,"man_days":10,"activities":["MySQL 8.0 → RDS migration","Redis → ElastiCache","Data validation"]},
    {"role":"DevOps / Platform Engineer","count":1,"man_days":8,"activities":["ECS compute-optimized setup","MWAA configuration","ElastiCache provisioning"]},
    {"role":"QA / Test Automation Engineer","count":1,"man_days":10,"activities":["Optimization accuracy A/B testing","Full catalogue run timing","Airflow DAG validation"]}
  ]},
  {"epic_id":"E-304","epic":"Pricing Engine (APP-020)","phase":"Phase 3","start":21,"end":25,"roles":[
    {"role":"Python / ML Engineer","count":2,"man_days":40,"activities":["Scala/Python pricing engine → EKS","ML models → SageMaker deployment","Elasticsearch → OpenSearch migration","gRPC endpoint migration","Full catalogue repricing optimization"]},
    {"role":"Database Migration Specialist","count":1,"man_days":12,"activities":["PostgreSQL 15 → RDS","OpenSearch domain setup","Redis → ElastiCache","Data validation"]},
    {"role":"DevOps / Platform Engineer","count":1,"man_days":10,"activities":["EKS cluster setup","SageMaker endpoint configuration","OpenSearch provisioning","Auto-scaling policies"]},
    {"role":"QA / Test Automation Engineer","count":1,"man_days":12,"activities":["Pricing accuracy testing (±1%)","Full reprice timing (<1h)","Load testing","Shadow mode comparison"]}
  ]},
  {"epic_id":"E-305","epic":"QMS, Procurement, Store Ops","phase":"Phase 3","start":22,"end":26,"roles":[
    {"role":"Python / ML Engineer","count":1,"man_days":15,"activities":["Django QMS → ECS","FastAPI Store Ops → ECS","Celery workers containerization","WebSocket endpoint migration"]},
    {"role":"Node.js / React Developer","count":1,"man_days":15,"activities":["Node.js Procurement → ECS","React frontend deployment","MongoDB → DocumentDB","OAuth 2.0 integration"]},
    {"role":"Database Migration Specialist","count":1,"man_days":12,"activities":["PostgreSQL 15 → RDS (QMS, Store Ops)","MongoDB → DocumentDB (Procurement)","Redis → ElastiCache"]},
    {"role":"DevOps / Platform Engineer","count":1,"man_days":10,"activities":["ECS services provisioning","WebSocket via API Gateway","RabbitMQ → Amazon MQ"]},
    {"role":"QA / Test Automation Engineer","count":1,"man_days":12,"activities":["Integration testing (3 apps)","WebSocket real-time testing","OAuth flow validation","GxP audit trail testing (QMS)"]}
  ]},
  {"epic_id":"E-306","epic":"Dependent Phase Regression","phase":"Phase 3","start":25,"end":26,"roles":[
    {"role":"QA / Test Automation Engineer","count":2,"man_days":16,"activities":["Full regression execution","SOAP→REST adapter validation","Cost optimization review","Phase 4 readiness assessment"]},
    {"role":"Senior DevOps / SRE","count":1,"man_days":8,"activities":["Performance review","Cost analysis","Adapter load testing","Phase 4 infrastructure prep"]},
    {"role":"Cloud Solutions Architect","count":1,"man_days":6,"activities":["Architecture review","Legacy modernization pattern finalization","Phase 4 design sign-off"]}
  ]},
  {"epic_id":"E-401","epic":"WMS Refactoring (APP-004)","phase":"Phase 4","start":27,"end":34,"roles":[
    {"role":"Java/Spring Boot Developer","count":3,"man_days":96,"activities":["Java 8 → 17 migration","WebLogic → Spring Boot 3 refactoring","IBM MQ → SQS/SNS migration","EDI gateway implementation on AWS","Strangler Fig pattern implementation","Oracle 12c query refactoring"]},
    {"role":"Database Migration Specialist","count":1,"man_days":24,"activities":["Oracle 12c → 19c upgrade","Oracle 19c → RDS migration","Schema optimization","Zero-downtime cutover planning","Data validation"]},
    {"role":"Vendor / Integration Specialist","count":1,"man_days":20,"activities":["EDI partner communication","B2B gateway configuration","Partner connectivity testing","AWS Transfer Family setup","Cutover coordination with partners"]},
    {"role":"DevOps / Platform Engineer","count":1,"man_days":16,"activities":["ECS deployment pipeline","Blue-green deployment setup","SQS/SNS configuration","Monitoring & alerting"]},
    {"role":"QA / Test Automation Engineer","count":1,"man_days":20,"activities":["EDI partner end-to-end testing","Performance testing (<500ms)","Zero-downtime cutover rehearsal","Regression suite","Integration with Inventory & Demand Planning"]}
  ]},
  {"epic_id":"E-402","epic":"TMS Replacement (APP-009)","phase":"Phase 4","start":27,"end":34,"roles":[
    {"role":"Java/Spring Boot Developer","count":1,"man_days":24,"activities":["Legacy SOAP/FTP interface retirement","New REST API development (if rewrite)","Data access layer for new system","Integration with WMS & Demand Planning"]},
    {"role":"Vendor / Integration Specialist","count":1,"man_days":20,"activities":["SaaS vendor evaluation","RFP process management","Contract negotiation","SaaS implementation coordination","EDI partner migration"]},
    {"role":"Database Migration Specialist","count":1,"man_days":15,"activities":["MySQL 5.7 → 8.0 upgrade","Historical data migration","Data transformation for new system","Validation & reconciliation"]},
    {"role":"QA / Test Automation Engineer","count":1,"man_days":12,"activities":["Data migration validation","Integration testing","EDI flow testing","User acceptance coordination"]}
  ]},
  {"epic_id":"E-403","epic":"MES Replatforming (APP-015)","phase":"Phase 4","start":28,"end":35,"roles":[
    {"role":".NET / C# Developer","count":2,"man_days":64,"activities":["VB.NET → .NET 8 rewrite","COM+/DCOM → REST/gRPC replacement","MSMQ → SQS migration","IIS → ECS containerization","Shop floor interface modernization","Strangler Fig incremental migration"]},
    {"role":"Database Migration Specialist","count":1,"man_days":15,"activities":["MS SQL 2016 → 2019 upgrade","MS SQL 2019 → RDS migration","Stored procedure optimization","Data validation"]},
    {"role":"DevOps / Platform Engineer","count":1,"man_days":12,"activities":["ECS/.NET 8 deployment pipeline","SQS queue configuration","Service mesh setup","Monitoring for shop floor latency"]},
    {"role":"QA / Test Automation Engineer","count":1,"man_days":15,"activities":["Shop floor transaction testing (<1s)","COM+ interface replacement validation","Integration with PLM & Inventory","Load testing"]}
  ]},
  {"epic_id":"E-404","epic":"HR Platform Replacement (APP-017)","phase":"Phase 4","start":29,"end":34,"roles":[
    {"role":".NET / C# Developer","count":1,"man_days":18,"activities":["ASP.NET 4.8 data extraction","LDAP → Cognito/AD migration","Integration API development","Legacy system decommission prep"]},
    {"role":"Vendor / Integration Specialist","count":1,"man_days":20,"activities":["SaaS evaluation (Workday/SuccessFactors)","Vendor selection & contract","Implementation coordination","Data migration planning","Go-live support"]},
    {"role":"Security Engineer","count":1,"man_days":10,"activities":["GDPR compliance validation","Employee PII handling","Access control migration","Right to erasure implementation","Audit trail setup"]},
    {"role":"QA / Test Automation Engineer","count":1,"man_days":10,"activities":["Employee record migration validation","GDPR compliance testing","Integration testing with FP&A","UAT coordination"]}
  ]},
  {"epic_id":"E-405","epic":"Document Mgmt Retirement (APP-018)","phase":"Phase 4","start":30,"end":33,"roles":[
    {"role":"DevOps / Platform Engineer","count":1,"man_days":12,"activities":["S3 Glacier configuration","Object Lock & lifecycle policies","OpenSearch for metadata","Alfresco decommission"]},
    {"role":"Data Engineer / Big Data Specialist","count":1,"man_days":10,"activities":["Document extraction & migration to S3","Metadata indexing to OpenSearch","Retention policy automation","Data validation & count reconciliation"]},
    {"role":"QA / Test Automation Engineer","count":1,"man_days":6,"activities":["Document count validation","Metadata search testing","Retrieval time testing","Retention policy verification"]}
  ]},
  {"epic_id":"E-406","epic":"Decommission & Hypercare","phase":"Phase 4","start":34,"end":37,"roles":[
    {"role":"Senior DevOps / SRE","count":1,"man_days":16,"activities":["On-prem shutdown coordination","Final monitoring validation","Cost savings verification (44%)","Hypercare incident management","Knowledge transfer to BAU"]},
    {"role":"DevOps / Platform Engineer","count":2,"man_days":24,"activities":["Infrastructure decommission","DNS cutover finalization","Backup verification","Final security scan","Documentation handover"]},
    {"role":"Migration Programme Manager","count":1,"man_days":12,"activities":["Project closure report","Lessons learned","Final stakeholder presentation","Cost savings sign-off","Team offboarding coordination"]},
    {"role":"DBA (Production Support)","count":1,"man_days":12,"activities":["Legacy DB decommission","Final backup archival","RDS operational handover","Performance baseline documentation","BAU runbook finalization"]}
  ]}
]

# Merge stories into GANTT
for epic in GANTT:
    epic_stories = STORIES.get(epic["epic_id"], {})
    for role in epic["roles"]:
        role["stories"] = epic_stories.get(role["role"], [])

SYSTEM_PROMPT = """You are a Migration Assessment Assistant for AnyCompany's AWS cloud migration.
You have access to: 26 epics across 5 phases (37 weeks), 18 roles with staggered onboarding,
20 apps with prerequisites/outputs, and 61 NFRs.

Key facts:
- Phase 0: Mobilisation (W1-4) - Landing Zone, Training, Tooling, Data Classification
- Phase 1: Foundation (W5-11) - MDM, CDP, Big Data Pipeline
- Phase 2: Core Business (W12-19) - E-Commerce, Loyalty, Demand Planning, Trade Promo, Analytics
- Phase 3: Dependent (W20-26) - PLM, FP&A, Inventory, QMS, Procurement, Store Ops, Pricing
- Phase 4: Legacy/Modernise (W27-37) - WMS, TMS, MES, HR, Doc Mgmt
- Peak team: ~28 people (weeks 12-19)
- Cost savings target: 44% annually
- 651 instances total, 689TB storage

Answer concisely. Reference app IDs and epic IDs when relevant."""


def chat_with_bedrock(message, history, system_override=None):
    if not HAS_BOTO3:
        return "boto3 not available."
    client = boto3.client("bedrock-runtime", region_name="us-east-1")
    messages = [{"role": h["role"], "content": [{"text": h["content"]}]} for h in history]
    messages.append({"role": "user", "content": [{"text": message}]})
    try:
        resp = client.converse(
            modelId="amazon.nova-pro-v1:0",
            system=[{"text": system_override or SYSTEM_PROMPT}],
            messages=messages,
            inferenceConfig={"maxTokens": 4096, "temperature": 0.3},
        )
        return resp["output"]["message"]["content"][0]["text"]
    except Exception as e:
        return f"Error: {e}"


def chat_with_ollama(message, history, system_override=None):
    """Call local OLLAMA API (default: http://localhost:11434)."""
    import urllib.request
    ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    model = os.environ.get("OLLAMA_MODEL", "llama3")
    msgs = [{"role": "system", "content": system_override or SYSTEM_PROMPT}]
    for h in history:
        msgs.append({"role": h["role"], "content": h["content"]})
    msgs.append({"role": "user", "content": message})
    payload = json.dumps({"model": model, "messages": msgs, "stream": False}).encode()
    req = urllib.request.Request(
        f"{ollama_url}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read())
            return data.get("message", {}).get("content", "No response from OLLAMA.")
    except Exception as e:
        return f"OLLAMA error: {e}"


def generate_artifact(project_id: str, artifact: str, prompt: str) -> str:
    """Generate artifact content using the project's LLM backend + enabled files."""
    project = get_project(project_id)
    if not project:
        return json.dumps({"error": "Project not found"})

    backend = project["llm_backend"]
    file_context = read_enabled_files(project_id, artifact)

    system = (
        f"You are a project delivery assistant. Generate structured JSON data for the '{artifact}' "
        f"artifact of a project delivery dashboard. Return ONLY valid JSON, no markdown fences.\n"
        f"Use the provided project documents as the primary source of truth.\n"
        f"If documents are insufficient, use reasonable defaults."
    )
    if file_context:
        system += f"\n\nProject Documents:\n{file_context[:12000]}"

    user_prompt = prompt or f"Generate the {artifact} data for this project."

    if backend == "files_only":
        if not file_context:
            return json.dumps({"error": "No files enabled for this artifact. Please upload and enable files."})
        return chat_with_bedrock(user_prompt, [], system_override=system)
    elif backend == "bedrock":
        return chat_with_bedrock(user_prompt, [], system_override=system)
    elif backend == "ollama":
        return chat_with_ollama(user_prompt, [], system_override=system)
    elif backend == "files+ollama":
        return chat_with_ollama(user_prompt, [], system_override=system)
    return json.dumps({"error": f"Unknown backend: {backend}"})


def build_html():
    """Build complete HTML with embedded data."""
    epics_json = json.dumps(EPICS)
    resources_json = json.dumps(RESOURCES)
    tracking_json = json.dumps(TRACKING)
    nfrs_json = json.dumps(NFRS)
    gantt_json = json.dumps(GANTT)
    gates_json = json.dumps(GATES_DATA)
    artifacts_list = json.dumps(ARTIFACTS)
    # Load drawio XML files
    drawio_files = {}
    for name in ['migration_dependency_diagram', 'data_flow_diagram', 'operational_dependency_diagram']:
        fp = DATA_DIR / f"{name}.drawio"
        if fp.exists():
            drawio_files[name] = fp.read_text()
    drawio_json = json.dumps(drawio_files)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Migration Assessment Dashboard</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f5f7fa;color:#1a1a2e}}
.header{{background:linear-gradient(135deg,#1a1a2e,#16213e);color:#fff;padding:1rem 2rem;display:flex;justify-content:space-between;align-items:center}}
.header h1{{font-size:1.3rem}}
.nav{{display:flex;gap:.5rem;padding:.5rem 2rem;background:#fff;border-bottom:1px solid #e0e0e0;flex-wrap:wrap}}
.nav button{{padding:.5rem 1rem;border:1px solid #ddd;border-radius:6px;background:#fff;cursor:pointer;font-size:.85rem;transition:all .2s}}
.nav button.active{{background:#1a1a2e;color:#fff;border-color:#1a1a2e}}
.nav button:hover{{background:#e8eaf6}}
.content{{padding:1.5rem 2rem}}
.tab{{display:none}}.tab.active{{display:block}}
table{{width:100%;border-collapse:collapse;font-size:.78rem;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08)}}
th{{background:#1a1a2e;color:#fff;padding:.5rem;text-align:left;white-space:nowrap}}
td{{padding:.4rem .5rem;border-bottom:1px solid #eee;vertical-align:top;max-width:280px;word-wrap:break-word}}
tr:hover{{background:#f0f4ff}}
.table-wrap{{overflow-x:auto;max-height:72vh;overflow-y:auto}}
.summary-cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1rem;margin-bottom:1.5rem}}
.card{{background:#fff;border-radius:8px;padding:1rem;box-shadow:0 2px 8px rgba(0,0,0,.08);border-left:4px solid #1a1a2e}}
.card h3{{font-size:.85rem;color:#666;margin-bottom:.2rem}}.card .value{{font-size:1.6rem;font-weight:700}}
.card.green{{border-left-color:#4caf50}}.card.blue{{border-left-color:#2196f3}}.card.orange{{border-left-color:#ff9800}}.card.red{{border-left-color:#f44336}}
.chat-toggle{{position:fixed;bottom:20px;right:20px;width:56px;height:56px;border-radius:50%;background:#1a1a2e;color:#fff;border:none;font-size:1.5rem;cursor:pointer;box-shadow:0 4px 12px rgba(0,0,0,.3);z-index:1000}}
.chat-panel{{position:fixed;bottom:90px;right:20px;width:400px;height:500px;background:#fff;border-radius:12px;box-shadow:0 8px 32px rgba(0,0,0,.2);display:none;flex-direction:column;z-index:1000;overflow:hidden}}
.chat-panel.open{{display:flex}}
.chat-header{{background:#1a1a2e;color:#fff;padding:.7rem 1rem;font-weight:600;display:flex;justify-content:space-between;align-items:center}}
.chat-messages{{flex:1;overflow-y:auto;padding:.8rem;display:flex;flex-direction:column;gap:.4rem}}
.msg{{max-width:85%;padding:.5rem .7rem;border-radius:12px;font-size:.82rem;line-height:1.4;word-wrap:break-word;white-space:pre-wrap}}
.msg.user{{background:#1a1a2e;color:#fff;align-self:flex-end;border-bottom-right-radius:4px}}
.msg.bot{{background:#f0f4ff;color:#1a1a2e;align-self:flex-start;border-bottom-left-radius:4px}}
.chat-input{{display:flex;border-top:1px solid #eee;padding:.4rem}}
.chat-input input{{flex:1;border:1px solid #ddd;border-radius:20px;padding:.4rem .8rem;font-size:.82rem;outline:none}}
.chat-input button{{margin-left:.4rem;background:#1a1a2e;color:#fff;border:none;border-radius:50%;width:34px;height:34px;cursor:pointer}}
.timeline-bar{{display:flex;margin:1rem 0;border-radius:6px;overflow:hidden;height:36px}}
.timeline-bar div{{display:flex;align-items:center;justify-content:center;color:#fff;font-size:.7rem;font-weight:600}}
.gantt-wrap{{background:#fff;border-radius:8px;padding:1rem;box-shadow:0 2px 8px rgba(0,0,0,.08)}}
.g-epic{{border:1px solid #e0e0e0;border-radius:6px;margin:4px 0;overflow:hidden}}
.g-epic-hdr{{display:flex;align-items:center;cursor:pointer;padding:8px 10px;background:#fafafa;transition:background .2s;gap:8px}}
.g-epic-hdr:hover{{background:#f0f4ff}}
.g-epic-hdr .arr{{transition:transform .2s;font-size:.7rem}}.g-epic-hdr.open .arr{{transform:rotate(90deg)}}
.g-epic-hdr .bar-area{{flex:1;position:relative;height:20px;margin-left:8px}}
.g-epic-hdr .bar-area span{{position:absolute;height:20px;border-radius:3px;display:flex;align-items:center;padding:0 6px;font-size:.6rem;color:#fff;font-weight:600;white-space:nowrap}}
.g-epic-body{{display:none;padding:4px 12px 8px 28px}}.g-epic-body.open{{display:block}}
.g-role{{border-left:3px solid #ddd;margin:5px 0;padding:3px 0 3px 10px}}
.g-role-hdr{{cursor:pointer;display:flex;align-items:center;gap:6px;font-size:.78rem;font-weight:600}}.g-role-hdr:hover{{color:#1565c0}}
.g-role-hdr .arr{{font-size:.6rem;transition:transform .2s}}.g-role-hdr.open .arr{{transform:rotate(90deg)}}
.g-role-body{{display:none;padding:4px 0 4px 14px}}.g-role-body.open{{display:block}}
.g-story{{margin:3px 0;padding:5px 8px;background:#f8f9ff;border-radius:4px;font-size:.75rem;border-left:3px solid #ccc}}
.g-story-hdr{{display:flex;align-items:center;gap:6px;cursor:pointer}}.g-story-hdr:hover{{color:#1565c0}}
.g-story-hdr .arr{{font-size:.55rem;transition:transform .2s}}.g-story-hdr.open .arr{{transform:rotate(90deg)}}
.g-story-ac{{display:none;margin-top:3px;padding-left:14px;font-size:.7rem;color:#555}}.g-story-ac.open{{display:block}}
.sz{{display:inline-block;padding:1px 5px;border-radius:8px;font-size:.6rem;font-weight:700;color:#fff}}
.sz-XS{{background:#4caf50}}.sz-S{{background:#8bc34a}}.sz-M{{background:#ff9800}}.sz-L{{background:#f44336}}.sz-XL{{background:#9c27b0}}
.progress-bar{{height:6px;background:#e0e0e0;border-radius:3px;overflow:hidden;flex:1;margin:0 8px}}
.progress-bar .fill{{height:100%;border-radius:3px;transition:width .3s}}
.progress-bar .fill.green{{background:#4caf50}}.progress-bar .fill.orange{{background:#ff9800}}.progress-bar .fill.red{{background:#f44336}}
.story-edit{{display:inline-flex;align-items:center;gap:4px;margin-left:8px;font-size:.65rem}}
.story-edit input,.story-edit select{{padding:1px 4px;border:1px solid #ddd;border-radius:3px;font-size:.65rem;width:42px}}
.story-edit select{{width:auto}}
.status-badge{{padding:1px 5px;border-radius:8px;font-size:.6rem;font-weight:600}}
.status-ns{{background:#e0e0e0;color:#666}}.status-ip{{background:#fff3e0;color:#e65100}}.status-done{{background:#e8f5e9;color:#2e7d32}}
.actual-bar{{position:absolute;height:8px;border-radius:2px;bottom:2px;background:#1a1a2e;opacity:.7}}
.change-log{{background:#fff;border:1px solid #e0e0e0;border-radius:8px;margin-top:1rem;max-height:250px;overflow-y:auto;font-size:.72rem}}
.change-log-header{{display:flex;justify-content:space-between;align-items:center;padding:8px 12px;background:#f5f5f5;border-bottom:1px solid #e0e0e0;position:sticky;top:0}}
.change-entry{{padding:6px 12px;border-bottom:1px solid #f0f0f0;display:flex;gap:8px;align-items:flex-start}}
.change-entry.new{{background:#fff8e1}}.change-entry.accepted{{background:#f1f8e9}}.change-entry.pending{{background:#fff3e0}}
.change-badge{{padding:1px 5px;border-radius:8px;font-size:.6rem;font-weight:600;white-space:nowrap}}
.change-badge.new{{background:#ff9800;color:#fff}}.change-badge.accepted{{background:#4caf50;color:#fff}}.change-badge.pending{{background:#ff5722;color:#fff}}
.editable-text{{cursor:text;border-bottom:1px dashed #ccc;padding:1px 2px}}
.editable-text:hover{{background:#e3f2fd}}
.impact-box{{background:#fff;border:1px solid #e0e0e0;border-radius:8px;padding:12px;margin-top:.5rem;font-size:.75rem}}
.impact-item{{padding:4px 8px;margin:3px 0;border-radius:4px;display:flex;align-items:center;gap:6px}}
.diagram-container{{background:#fff;border-radius:8px;padding:1rem;box-shadow:0 2px 8px rgba(0,0,0,.08);position:relative;overflow:hidden}}
.diagram-controls{{display:flex;gap:.5rem;margin-bottom:.5rem;align-items:center}}
.diagram-controls button{{padding:4px 10px;border:1px solid #ddd;border-radius:4px;background:#fff;cursor:pointer;font-size:.8rem}}
.diagram-controls button:hover{{background:#e8eaf6}}
.diagram-svg{{width:100%;overflow:auto;border:1px solid #eee;border-radius:4px;min-height:500px}}
.diagram-svg svg{{transition:transform .2s}}
.node{{cursor:pointer;transition:opacity .2s,filter .2s}}.node:hover{{filter:brightness(1.1)}}
.node.dimmed{{opacity:.15}}.node.highlighted{{filter:brightness(1.1);stroke-width:3}}
.edge{{transition:opacity .2s,stroke-width .2s}}.edge.dimmed{{opacity:.08}}.edge.highlighted{{stroke-width:3;opacity:1}}
</style>
</head>
<body>
<div class="header">
  <h1>☁️ Project Delivery Accelerator</h1>
  <span style="font-size:.75rem;opacity:.7">Multi-LLM · File Upload · 5 Projects</span>
</div>
<div id="projectBar" style="background:#16213e;color:#fff;padding:.4rem 1.5rem;display:flex;align-items:center;gap:.6rem;flex-wrap:wrap;font-size:.8rem">
  <span style="opacity:.7">Project:</span>
  <div id="projectTabs" style="display:flex;gap:.4rem;flex-wrap:wrap"></div>
  <button onclick="showNewProjectDialog()" id="btnNewProject" style="padding:3px 10px;border:1px solid #4caf50;border-radius:12px;background:transparent;color:#4caf50;cursor:pointer;font-size:.75rem">+ New</button>
  <div style="margin-left:auto;display:flex;align-items:center;gap:.6rem">
    <span style="opacity:.7">LLM:</span>
    <select id="llmSelect" onchange="setLLMBackend(this.value)" style="padding:2px 6px;border-radius:4px;border:1px solid #444;background:#1a1a2e;color:#fff;font-size:.75rem">
      <option value="bedrock">☁️ Bedrock (Nova Pro)</option>
      <option value="ollama">🦙 OLLAMA (local)</option>
      <option value="files_only">📄 Files Only</option>
      <option value="files+ollama">📄+🦙 Files + OLLAMA</option>
    </select>
    <button onclick="toggleUploadPanel()" style="padding:3px 10px;border:1px solid #2196f3;border-radius:12px;background:transparent;color:#2196f3;cursor:pointer;font-size:.75rem">📁 Files</button>
  </div>
</div>
<div id="uploadPanel" style="display:none;background:#f0f4ff;border-bottom:2px solid #2196f3;padding:.8rem 1.5rem">
  <div style="display:flex;gap:1rem;flex-wrap:wrap;align-items:flex-start">
    <div style="flex:1;min-width:260px">
      <div style="font-weight:700;font-size:.82rem;margin-bottom:.4rem">📤 Upload Files (transcripts, SOW, presentations, artefacts…)</div>
      <input type="file" id="fileInput" multiple accept=".txt,.pdf,.csv,.docx,.pptx,.xlsx,.md,.json,.xml,.drawio" style="font-size:.78rem">
      <button onclick="uploadFiles()" style="margin-left:.5rem;padding:4px 12px;border:1px solid #1565c0;border-radius:4px;background:#1565c0;color:#fff;cursor:pointer;font-size:.78rem">Upload</button>
      <div id="uploadStatus" style="font-size:.72rem;color:#1565c0;margin-top:.3rem"></div>
    </div>
    <div style="flex:2;min-width:320px">
      <div style="font-weight:700;font-size:.82rem;margin-bottom:.4rem">📋 Project Files — Enable per Artifact</div>
      <div id="fileList" style="font-size:.75rem;color:#555">Select a project to see files.</div>
    </div>
  </div>
</div>
<div id="newProjectDialog" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.5);z-index:2000;display:none;align-items:center;justify-content:center">
  <div style="background:#fff;border-radius:10px;padding:1.5rem;min-width:320px;box-shadow:0 8px 32px rgba(0,0,0,.3)">
    <div style="font-weight:700;font-size:1rem;margin-bottom:.8rem">New Project</div>
    <input id="newProjectName" type="text" placeholder="Project name…" style="width:100%;padding:.4rem .6rem;border:1px solid #ddd;border-radius:4px;font-size:.85rem;margin-bottom:.6rem">
    <div style="display:flex;gap:.5rem;justify-content:flex-end">
      <button onclick="document.getElementById('newProjectDialog').style.display='none'" style="padding:5px 14px;border:1px solid #ddd;border-radius:4px;background:#fff;cursor:pointer">Cancel</button>
      <button onclick="createProject()" style="padding:5px 14px;border:none;border-radius:4px;background:#1a1a2e;color:#fff;cursor:pointer">Create</button>
    </div>
    <div id="newProjectError" style="color:#f44336;font-size:.75rem;margin-top:.4rem"></div>
  </div>
</div>
<div class="nav" id="navBar"></div>
<div class="content" id="contentArea"></div>
<button class="chat-toggle" onclick="toggleChat()">💬</button>
<div class="chat-panel" id="chatPanel">
  <div class="chat-header"><span>Migration Assistant</span><button onclick="toggleChat()" style="background:none;border:none;color:#fff;cursor:pointer;font-size:1.2rem">✕</button></div>
  <div class="chat-messages" id="chatMessages"><div class="msg bot">Hi! Ask me about phases, dependencies, resources, NFRs, timelines, or costs.</div></div>
  <div class="chat-input"><input id="chatInput" placeholder="Ask about the migration..." onkeydown="if(event.key==='Enter')sendChat()"><button onclick="sendChat()">➤</button></div>
</div>
<script>
const DATA={{
  epics:{epics_json},
  resources:{resources_json},
  tracking:{tracking_json},
  nfrs:{nfrs_json},
  gantt:{gantt_json},
  gates:{gates_json},
  drawio:{drawio_json}
}};
const TABS=[
  {{id:'overview',label:'Overview'}},
  {{id:'gantt',label:'📊 Gantt Chart'}},
  {{id:'gates',label:'🚦 NFR Gates ('+DATA.gates.length+')'}},
  {{id:'deps',label:'🔗 Dependencies'}},
  {{id:'dataflow',label:'💾 Data Flow'}},
  {{id:'diagrams',label:'✏️ Diagram Editor'}},
  {{id:'epics',label:'Epic Plan ('+DATA.epics.length+')'}},
  {{id:'resources',label:'Resources ('+DATA.resources.length+')'}},
  {{id:'tracking',label:'Tracking ('+DATA.tracking.length+')'}},
  {{id:'nfrs',label:'NFRs ('+DATA.nfrs.length+')'}}
];
let activeTab='overview';
function render(){{
  // Nav
  document.getElementById('navBar').innerHTML=TABS.map(t=>
    '<button class="'+(t.id===activeTab?'active':'')+'" onclick="showTab(\\''+t.id+'\\')">'+t.label+'</button>'
  ).join('');
  // Content
  let html='';
  TABS.forEach(t=>{{html+='<div class="tab '+(t.id===activeTab?'active':'')+'">'+renderTab(t.id)+'</div>'}});
  document.getElementById('contentArea').innerHTML=html;
}}
function showTab(id){{activeTab=id;render()}}
function renderTab(id){{
  if(id==='overview')return renderOverview();
  if(id==='gantt')return renderGantt();
  if(id==='gates')return renderGates();
  if(id==='deps')return renderDeps();
  if(id==='dataflow')return renderDataFlow();
  if(id==='diagrams')return renderDiagramEditor();
  if(id==='epics')return renderTable(DATA.epics);
  if(id==='resources')return renderTable(DATA.resources);
  if(id==='tracking')return renderTable(DATA.tracking);
  if(id==='nfrs')return renderTable(DATA.nfrs);
}}
const PHASE_COLORS={{'Phase 0':'#607d8b','Phase 1':'#4caf50','Phase 2':'#2196f3','Phase 3':'#ff9800','Phase 4':'#f44336'}};
const ROLE_COLORS={{'Cloud Solutions Architect':'#5c6bc0','Data Engineer / Big Data Specialist':'#26a69a','Database Migration Specialist':'#8e24aa','Java/Spring Boot Developer':'#e65100','Node.js / React Developer':'#2e7d32','.NET / C# Developer':'#c62828','Python / ML Engineer':'#1565c0','DevOps / Platform Engineer':'#4e342e','Senior DevOps / SRE':'#37474f','QA / Test Automation Engineer':'#00838f','Security Engineer':'#ad1457','Network Engineer':'#6d4c41','Migration Programme Manager':'#283593','Scrum Master / Delivery Lead':'#00695c','Business Analyst':'#4527a0','Change Manager / Training Lead':'#bf360c','Vendor / Integration Specialist':'#1b5e20','DBA (Production Support)':'#880e4f'}};
function getEpicActualBars(ei,epic){{
  // Collect actual start/end weeks from stories and color them green/amber/red
  const weeks=37;
  const bars=[];
  const plannedEnd=epic.end;
  epic.roles.forEach((r,ri)=>{{
    (r.stories||[]).forEach((s,si)=>{{
      const p=getStoryProgress(ei,ri,si);
      if(p.status==='done'&&p.actualStart&&p.actualEnd){{
        const aStart=parseInt(p.actualStart);
        const aEnd=parseInt(p.actualEnd);
        if(aStart&&aEnd){{
          const delay=aEnd-plannedEnd;
          const color=delay<=0?'#4caf50':delay<=2?'#ff9800':'#f44336';
          const left=((aStart-1)/weeks*100).toFixed(1);
          const width=((aEnd-aStart+1)/weeks*100).toFixed(1);
          bars.push({{left,width,color}});
        }}
      }}else if(p.status==='ip'&&p.actualStart){{
        const aStart=parseInt(p.actualStart);
        if(aStart){{
          const left=((aStart-1)/weeks*100).toFixed(1);
          const width=((Math.min(37,aStart+2)-aStart)/weeks*100).toFixed(1);
          bars.push({{left,width,color:'#2196f3'}});
        }}
      }}
    }});
  }});
  return bars;
}}
function renderGantt(){{
  const weeks=37;
  const baseDays=DATA.gantt.reduce((s,e)=>s+e.roles.reduce((s2,r)=>s2+r.man_days,0),0);
  const extraTotal=Object.values(EXTRA_DAYS).reduce((s,d)=>s+d,0);
  const totalManDays=baseDays+extraTotal;
  // Overall progress
  let allDone=0,allTotal=0;
  DATA.gantt.forEach((e,ei)=>{{const p=getEpicProgress(ei);allDone+=p.done;allTotal+=p.total}});
  const overallPct=allTotal?Math.round(allDone/allTotal*100):0;
  let h='<div class="summary-cards" style="margin-bottom:1rem">';
  h+='<div class="card blue"><h3>Total Man-Days</h3><div class="value">'+totalManDays+'</div>'+(extraTotal?'<div style="font-size:.6rem;color:#f44336">+'+extraTotal+'d from changes</div>':'')+'</div>';
  h+='<div class="card green"><h3>Overall Progress</h3><div class="value">'+overallPct+'%</div><div class="progress-bar" style="margin-top:4px"><div class="fill green" style="width:'+overallPct+'%"></div></div></div>';
  h+='<div class="card orange"><h3>Stories Done</h3><div class="value">'+allDone+'/'+allTotal+'</div></div>';
  h+='<div class="card red"><h3>T-Shirt Sizes</h3><div class="value" style="font-size:.75rem"><span class="sz sz-XS">XS</span>1-2d <span class="sz sz-S">S</span>3-5d <span class="sz sz-M">M</span>5-10d <span class="sz sz-L">L</span>10-20d <span class="sz sz-XL">XL</span>20+d</div></div>';
  h+='</div>';
  h+='<div style="display:flex;gap:.5rem;margin-bottom:.5rem;align-items:center"><button onclick="exportProgress()" style="padding:4px 10px;border:1px solid #ddd;border-radius:4px;background:#fff;cursor:pointer;font-size:.75rem">📥 Export Progress CSV</button><button onclick="expandAll()" style="padding:4px 10px;border:1px solid #ddd;border-radius:4px;background:#fff;cursor:pointer;font-size:.75rem">➕ Expand All</button><button onclick="collapseAll()" style="padding:4px 10px;border:1px solid #ddd;border-radius:4px;background:#fff;cursor:pointer;font-size:.75rem">➖ Collapse All</button><span style="font-size:.7rem;color:#888">Progress auto-saves to browser</span></div>';
  // Week-wise scope change impact
  if(extraTotal>0){{
    const weekImpacts={{}};
    CHANGELOG.filter(c=>c.status==='accepted'&&c.impact).forEach(c=>{{
      const wk=c.date?c.date.substring(0,10):'unknown';
      weekImpacts[wk]=(weekImpacts[wk]||0)+c.impact.extraDays;
    }});
    h+='<div style="background:#fff;border:1px solid #e0e0e0;border-radius:6px;padding:8px 12px;margin-bottom:.5rem;font-size:.7rem;display:flex;align-items:center;gap:12px;flex-wrap:wrap">';
    h+='<span style="font-weight:700">Scope Change Impact:</span>';
    h+='<span style="color:#f44336;font-weight:600">Overall: +'+extraTotal+'d to plan</span>';
    Object.entries(weekImpacts).sort().forEach(([wk,days])=>{{
      h+='<span style="padding:2px 6px;background:#fff3e0;border-radius:4px">'+wk+': <strong style="color:#e65100">+'+days+'d</strong></span>';
    }});
    h+='</div>';
  }}
  h+='<div class="gantt-wrap">';
  DATA.gantt.forEach((epic,ei)=>{{
    const color=PHASE_COLORS[epic.phase]||'#666';
    const left=((epic.start-1)/weeks*100).toFixed(1);
    const width=((epic.end-epic.start+1)/weeks*100).toFixed(1);
    const days=epic.roles.reduce((s,r)=>s+r.man_days,0);
    const prog=getEpicProgress(ei);
    const progColor=prog.pct===100?'green':prog.pct>0?'orange':'';
    h+='<div class="g-epic">';
    h+='<div class="g-epic-hdr'+(EXPANDED['e'+ei]?' open':'')+'" data-tog-id="e'+ei+'" onclick="tog(this)">';
    h+='<span class="arr">▶</span>';
    h+='<span style="font-size:.78rem;font-weight:700;min-width:180px">'+esc(epic.epic_id)+' '+esc(epic.epic)+'</span>';
    h+='<div class="progress-bar" style="max-width:80px"><div class="fill '+progColor+'" style="width:'+prog.pct+'%"></div></div>';
    h+='<span style="font-size:.62rem;color:#666;min-width:60px">'+prog.done+'/'+prog.total+'</span>';
    if(prog.totalActual)h+='<span style="font-size:.62rem;color:'+(prog.totalActual>prog.totalPlanned?'#f44336':'#4caf50')+'">'+prog.totalActual+'/'+prog.totalPlanned+'d</span>';
    h+='<div class="bar-area">';
    h+='<span style="left:'+left+'%;width:'+width+'%;background:'+color+'">W'+epic.start+'-'+epic.end+'</span>';
    // Actual progress overlay
    const actualBars=getEpicActualBars(ei,epic);
    actualBars.forEach(ab=>{{
      h+='<span style="left:'+ab.left+'%;width:'+ab.width+'%;background:'+ab.color+';height:8px;bottom:0;top:auto;border-radius:2px;opacity:.85;font-size:0"></span>';
    }});
    h+='</div>';
    h+='</div>';
    h+='<div class="g-epic-body'+(EXPANDED['e'+ei]?' open':'')+'">';
    epic.roles.forEach((role,ri)=>{{
      const rc=ROLE_COLORS[role.role]||'#666';
      h+='<div class="g-role" style="border-left-color:'+rc+'">';
      h+='<div class="g-role-hdr'+(EXPANDED['r'+ei+'-'+ri]?' open':'')+'" data-tog-id="r'+ei+'-'+ri+'" onclick="tog(this)">';
      h+='<span class="arr">▶</span>';
      h+='<span style="color:'+rc+'">'+esc(role.role)+'</span>';
      h+='<span style="font-size:.7rem;color:#888">(×'+role.count+' · '+role.man_days+' man-days)</span>';
      h+='</div>';
      h+='<div class="g-role-body'+(EXPANDED['r'+ei+'-'+ri]?' open':'')+'">';
      if(role.stories&&role.stories.length){{
        role.stories.forEach((s,si)=>{{
          const sc=s.size||'M';
          const gates=getGatesForStory(epic.epic_id,s.story);
          const gateIcon=gates.length?'<span title="Blocked by '+gates.length+' gate(s)" style="cursor:help">🚫</span> ':'';
          const prog=getStoryProgress(ei,ri,si);
          const statusCls=prog.status==='done'?'status-done':prog.status==='ip'?'status-ip':'status-ns';
          const statusLabel=prog.status==='done'?'Done':prog.status==='ip'?'In Progress':'Not Started';
          h+='<div class="g-story" style="border-left-color:'+rc+(gates.length?';background:#fff8f8':'')+(prog.status==='done'?';background:#f1f8e9;opacity:.8':'')+'">';
          h+='<div class="g-story-hdr'+(EXPANDED['s'+ei+'-'+ri+'-'+si]?' open':'')+'" data-tog-id="s'+ei+'-'+ri+'-'+si+'" onclick="markStoryViewed('+ei+','+ri+','+si+');tog(this)">';
          h+='<span class="arr">▶</span>';
          h+=gateIcon;
          h+='<span class="sz sz-'+sc+'">'+sc+'</span>';
          h+='<span class="status-badge '+statusCls+'">'+statusLabel+'</span>';
          if(isStoryNew(ei,ri,si))h+='<span class="change-badge new" style="margin-left:3px">NEW</span>';
          h+='<span'+(prog.status==='done'?' style="text-decoration:line-through;opacity:.7"':'')+' id="st-'+ei+'-'+ri+'-'+si+'" class="editable-text" ondblclick="editStory('+ei+','+ri+','+si+')">'+esc(getStoryText(ei,ri,si))+'</span>';
          h+='</div>';
          h+='<div class="g-story-ac'+(EXPANDED['s'+ei+'-'+ri+'-'+si]?' open':'')+'">';
          // Edit controls
          h+='<div class="story-edit" style="margin-bottom:6px;padding:4px 6px;background:#f5f5f5;border-radius:4px">';
          h+='<label>Status:</label><select onchange="updateStory('+ei+','+ri+','+si+',\\'status\\',this.value)">';
          h+='<option value="ns"'+(prog.status==='ns'?' selected':'')+'>Not Started</option>';
          h+='<option value="ip"'+(prog.status==='ip'?' selected':'')+'>In Progress</option>';
          h+='<option value="done"'+(prog.status==='done'?' selected':'')+'>Done</option></select>';
          h+='<label>Start W:</label><input type="number" min="1" max="37" value="'+esc(prog.actualStart)+'" onchange="updateStory('+ei+','+ri+','+si+',\\'actualStart\\',this.value)" placeholder="W">';
          h+='<label>End W:</label><input type="number" min="1" max="37" value="'+esc(prog.actualEnd)+'" onchange="updateStory('+ei+','+ri+','+si+',\\'actualEnd\\',this.value)" placeholder="W">';
          h+='<label>Hours:</label><input type="number" min="0" value="'+esc(prog.actualHours)+'" onchange="updateStory('+ei+','+ri+','+si+',\\'actualHours\\',this.value)" placeholder="hrs" style="width:50px">';
          h+='</div>';
          if(gates.length){{
            h+='<div style="margin-bottom:6px;padding:4px 6px;background:#ffebee;border-radius:4px;font-size:.68rem">';
            h+='<strong>⚠️ Gated by:</strong>';
            gates.forEach(g=>{{h+='<div style="margin:2px 0 2px 8px">• <strong>'+esc(g.gate_id)+'</strong>: '+esc(g.nfr)+' ('+esc(g.source_epic)+')</div>'}});
            h+='</div>';
          }}
          h+='<strong>Acceptance Criteria:</strong><ul style="margin:2px 0 0 12px">';
          (s.ac||[]).forEach(a=>{{h+='<li>'+esc(a)+'</li>'}});
          h+='</ul></div></div>';
        }});
      }}else{{
        h+='<div style="font-size:.72rem;color:#999;padding:2px 0">Activities: '+role.activities.map(a=>esc(a)).join(' · ')+'</div>';
      }}
      h+='</div></div>';
    }});
    h+='</div></div>';
  }});
  h+='</div>';
  h+=renderChangeLog();
  return h;
}}
function tog(el){{
  el.classList.toggle('open');
  const body=el.nextElementSibling;
  if(body)body.classList.toggle('open');
  // Save expand state
  const id=el.dataset.togId;
  if(id){{
    if(el.classList.contains('open'))EXPANDED[id]=true;
    else delete EXPANDED[id];
    localStorage.setItem('ganttExpanded',JSON.stringify(EXPANDED));
  }}
}}
let EXPANDED=JSON.parse(localStorage.getItem('ganttExpanded')||'{{}}');
// Build gate lookup: story text → gates that block it
const GATE_LOOKUP={{}};
DATA.gates.forEach(g=>{{
  g.blocks.forEach(b=>{{
    const key=b.epic+'|'+b.story;
    if(!GATE_LOOKUP[key])GATE_LOOKUP[key]=[];
    GATE_LOOKUP[key].push(g);
  }});
}});
function getGatesForStory(epicId,storyText){{
  return GATE_LOOKUP[epicId+'|'+storyText]||[];
}}
// === INTERACTIVE DIAGRAMS ===
const APPS=[
  {{id:'APP-010',name:'MDM',phase:1,x:400,y:80,deps:['APP-001','APP-005','APP-007','APP-008']}},
  {{id:'APP-007',name:'CDP',phase:1,x:200,y:80,deps:['APP-002','APP-010','APP-011']}},
  {{id:'APP-019',name:'Big Data Pipeline',phase:1,x:600,y:80,deps:['APP-007','APP-008','APP-010']}},
  {{id:'APP-001',name:'E-Commerce',phase:2,x:100,y:220,deps:['APP-002','APP-005','APP-010']}},
  {{id:'APP-002',name:'Loyalty',phase:2,x:300,y:220,deps:['APP-001','APP-007','APP-010']}},
  {{id:'APP-003',name:'Demand Planning',phase:2,x:500,y:220,deps:['APP-004','APP-009','APP-010']}},
  {{id:'APP-005',name:'Trade Promo',phase:2,x:700,y:220,deps:['APP-001','APP-010','APP-011']}},
  {{id:'APP-008',name:'Analytics',phase:2,x:150,y:340,deps:['APP-001','APP-002','APP-005','APP-007']}},
  {{id:'APP-006',name:'PLM',phase:3,x:100,y:460,deps:['APP-010','APP-012','APP-015']}},
  {{id:'APP-011',name:'FP&A',phase:3,x:300,y:460,deps:['APP-005','APP-008','APP-010']}},
  {{id:'APP-012',name:'Inventory',phase:3,x:500,y:460,deps:['APP-004','APP-008','APP-009']}},
  {{id:'APP-020',name:'Pricing',phase:3,x:700,y:460,deps:['APP-001','APP-005','APP-008']}},
  {{id:'APP-013',name:'QMS',phase:3,x:100,y:560,deps:['APP-006','APP-015']}},
  {{id:'APP-014',name:'Procurement',phase:3,x:300,y:560,deps:['APP-010','APP-011']}},
  {{id:'APP-016',name:'Store Ops',phase:3,x:500,y:560,deps:['APP-001','APP-008','APP-012']}},
  {{id:'APP-004',name:'WMS',phase:4,x:100,y:680,deps:['APP-003','APP-009','APP-012']}},
  {{id:'APP-009',name:'TMS',phase:4,x:300,y:680,deps:['APP-003','APP-004']}},
  {{id:'APP-015',name:'MES',phase:4,x:500,y:680,deps:['APP-006','APP-012']}},
  {{id:'APP-017',name:'HR',phase:4,x:700,y:680,deps:['APP-011']}},
  {{id:'APP-018',name:'Doc Mgmt',phase:4,x:500,y:760,deps:['APP-006','APP-013']}}
];
const DB_NODES=[
  {{id:'pg14',name:'PostgreSQL 14',x:80,y:500,apps:['APP-001','APP-008','APP-018']}},
  {{id:'pg15',name:'PostgreSQL 15',x:240,y:500,apps:['APP-005','APP-013','APP-016','APP-020']}},
  {{id:'ora19',name:'Oracle 19c',x:400,y:500,apps:['APP-003','APP-010']}},
  {{id:'mongo',name:'MongoDB 6.0',x:560,y:500,apps:['APP-002','APP-010','APP-014']}},
  {{id:'cassandra',name:'Cassandra 4.1',x:720,y:500,apps:['APP-007','APP-019']}},
  {{id:'redis',name:'Redis 7.x',x:80,y:600,apps:['APP-001','APP-002','APP-012','APP-013','APP-016','APP-020']}},
  {{id:'es',name:'Elasticsearch',x:240,y:600,apps:['APP-007','APP-020']}},
  {{id:'hadoop',name:'Hadoop/HDFS',x:400,y:600,apps:['APP-008','APP-019']}},
  {{id:'mssql',name:'MS SQL Server',x:560,y:600,apps:['APP-006','APP-011','APP-015','APP-017']}},
  {{id:'mysql',name:'MySQL',x:720,y:600,apps:['APP-009','APP-012']}}
];
let diagramZoom=1;
function zoomDiagram(id,delta){{
  diagramZoom=Math.max(0.5,Math.min(2,diagramZoom+delta));
  const svg=document.querySelector('#'+id+' svg');
  if(svg)svg.style.transform='scale('+diagramZoom+')';svg.style.transformOrigin='top left';
}}
function resetHighlight(containerId){{
  document.querySelectorAll('#'+containerId+' .node').forEach(n=>n.classList.remove('dimmed','highlighted'));
  document.querySelectorAll('#'+containerId+' .edge').forEach(e=>e.classList.remove('dimmed','highlighted'));
}}
function highlightNode(containerId,nodeId){{
  const container=document.getElementById(containerId);
  const allNodes=container.querySelectorAll('.node');
  const allEdges=container.querySelectorAll('.edge');
  const isAlreadyHighlighted=container.querySelector('.node.highlighted[data-id="'+nodeId+'"]');
  if(isAlreadyHighlighted){{resetHighlight(containerId);return}}
  allNodes.forEach(n=>n.classList.add('dimmed'));
  allNodes.forEach(n=>n.classList.remove('highlighted'));
  allEdges.forEach(e=>{{e.classList.add('dimmed');e.classList.remove('highlighted')}});
  // Highlight this node and connected nodes
  const node=container.querySelector('.node[data-id="'+nodeId+'"]');
  if(node){{node.classList.remove('dimmed');node.classList.add('highlighted')}}
  allEdges.forEach(e=>{{
    if(e.dataset.from===nodeId||e.dataset.to===nodeId){{
      e.classList.remove('dimmed');e.classList.add('highlighted');
      const other=e.dataset.from===nodeId?e.dataset.to:e.dataset.from;
      const otherNode=container.querySelector('.node[data-id="'+other+'"]');
      if(otherNode){{otherNode.classList.remove('dimmed');otherNode.classList.add('highlighted')}}
    }}
  }});
}}
function renderDeps(){{
  const w=850,h=820;
  const phaseColors={{1:'#4caf50',2:'#2196f3',3:'#ff9800',4:'#f44336'}};
  const phaseLabels={{1:'Phase 1: Foundation',2:'Phase 2: Core',3:'Phase 3: Dependent',4:'Phase 4: Legacy'}};
  // Build gate counts per app
  const appGates={{}};
  DATA.gates.forEach(g=>{{
    if(!appGates[g.source_app])appGates[g.source_app]=[];
    appGates[g.source_app].push(g);
    g.blocks.forEach(b=>{{
      const appId=b.epic.replace('E-1','APP-01').replace('E-2','APP-0').replace('E-3','APP-0').replace('E-4','APP-0');
    }});
  }});
  // Also count gates that BLOCK each app (by matching epic to app)
  const epicToApp={{'E-101':'APP-010','E-102':'APP-007','E-103':'APP-019','E-104':'APP-010','E-201':'APP-001','E-202':'APP-002','E-203':'APP-003','E-204':'APP-005','E-205':'APP-008','E-206':'ALL','E-301':'APP-006','E-302':'APP-011','E-303':'APP-012','E-304':'APP-020','E-305':'APP-013','E-306':'ALL','E-401':'APP-004','E-402':'APP-009','E-403':'APP-015','E-404':'APP-017','E-405':'APP-018','E-406':'ALL'}};
  const blockedByGates={{}};
  DATA.gates.forEach(g=>{{
    g.blocks.forEach(b=>{{
      const appId=epicToApp[b.epic];
      if(appId&&appId!=='ALL'){{
        if(!blockedByGates[appId])blockedByGates[appId]=[];
        blockedByGates[appId].push({{gate:g,story:b.story,reason:b.reason}});
      }}
    }});
  }});
  let svg='<svg width="'+w+'" height="'+h+'" style="font-family:sans-serif">';
  svg+='<rect x="0" y="40" width="'+w+'" height="130" fill="#4caf5010" stroke="#4caf50" stroke-dasharray="4"/>';
  svg+='<rect x="0" y="180" width="'+w+'" height="200" fill="#2196f310" stroke="#2196f3" stroke-dasharray="4"/>';
  svg+='<rect x="0" y="400" width="'+w+'" height="220" fill="#ff980010" stroke="#ff9800" stroke-dasharray="4"/>';
  svg+='<rect x="0" y="640" width="'+w+'" height="160" fill="#f4433610" stroke="#f44336" stroke-dasharray="4"/>';
  [1,2,3,4].forEach(p=>{{
    const y=p===1?55:p===2?195:p===3?415:655;
    svg+='<text x="10" y="'+y+'" font-size="11" fill="'+phaseColors[p]+'" font-weight="bold">'+phaseLabels[p]+'</text>';
  }});
  svg+='<defs><marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#999"/></marker></defs>';
  APPS.forEach(app=>{{
    app.deps.forEach(depId=>{{
      const dep=APPS.find(a=>a.id===depId);
      if(dep)svg+='<line class="edge" data-from="'+app.id+'" data-to="'+dep.id+'" x1="'+(app.x+60)+'" y1="'+(app.y+20)+'" x2="'+(dep.x+60)+'" y2="'+(dep.y+20)+'" stroke="#99999966" stroke-width="1.5" marker-end="url(#arrow)"/>';
    }});
  }});
  APPS.forEach(app=>{{
    const c=phaseColors[app.phase];
    const srcCount=(appGates[app.id]||[]).length;
    const blkCount=(blockedByGates[app.id]||[]).length;
    svg+='<g class="node" data-id="'+app.id+'" onclick="highlightNode(\\'depsDiagram\\',\\''+app.id+'\\');showAppGates(\\''+app.id+'\\')">';
    svg+='<rect x="'+app.x+'" y="'+app.y+'" width="120" height="40" rx="6" fill="'+c+'" opacity="0.85"/>';
    svg+='<text x="'+(app.x+60)+'" y="'+(app.y+16)+'" text-anchor="middle" font-size="9" fill="#fff" font-weight="bold">'+app.id+'</text>';
    svg+='<text x="'+(app.x+60)+'" y="'+(app.y+30)+'" text-anchor="middle" font-size="8" fill="#fff">'+app.name+'</text>';
    if(srcCount)svg+='<circle cx="'+(app.x+110)+'" cy="'+(app.y+5)+'" r="9" fill="#9c27b0"/><text x="'+(app.x+110)+'" y="'+(app.y+9)+'" text-anchor="middle" font-size="8" fill="#fff" font-weight="bold">'+srcCount+'</text>';
    if(blkCount)svg+='<circle cx="'+(app.x+10)+'" cy="'+(app.y+5)+'" r="9" fill="#f44336"/><text x="'+(app.x+10)+'" y="'+(app.y+9)+'" text-anchor="middle" font-size="8" fill="#fff" font-weight="bold">'+blkCount+'</text>';
    svg+='</g>';
  }});
  svg+='</svg>';
  let out='<div class="diagram-container">';
  out+='<div class="diagram-controls"><button onclick="zoomDiagram(\\'depsDiagram\\',0.2)">Zoom +</button><button onclick="zoomDiagram(\\'depsDiagram\\',-0.2)">Zoom -</button><button onclick="resetHighlight(\\'depsDiagram\\');diagramZoom=1;document.querySelector(\\'#depsDiagram svg\\').style.transform=\\'\\';document.getElementById(\\'gateDetail\\').innerHTML=\\'\\'">Reset</button>';
  out+='<span style="font-size:.72rem;color:#666;margin-left:1rem">Click app to highlight + show gates. <span style="color:#9c27b0;font-weight:600">●</span>=gates it produces <span style="color:#f44336;font-weight:600">●</span>=gates blocking it</span></div>';
  out+='<div class="diagram-svg" id="depsDiagram">'+svg+'</div>';
  out+='<div id="gateDetail" style="margin-top:.5rem"></div></div>';
  return out;
}}
function showAppGates(appId){{
  const srcGates=DATA.gates.filter(g=>g.source_app===appId);
  const epicToApp={{'E-101':'APP-010','E-102':'APP-007','E-103':'APP-019','E-201':'APP-001','E-202':'APP-002','E-203':'APP-003','E-204':'APP-005','E-205':'APP-008','E-301':'APP-006','E-302':'APP-011','E-303':'APP-012','E-304':'APP-020','E-401':'APP-004','E-402':'APP-009','E-403':'APP-015','E-404':'APP-017','E-405':'APP-018'}};
  const blkGates=[];
  DATA.gates.forEach(g=>g.blocks.forEach(b=>{{if(epicToApp[b.epic]===appId)blkGates.push({{gate:g,story:b.story,reason:b.reason}})}}));
  let h='<div style="background:#fff;border-radius:6px;padding:.8rem;border:1px solid #e0e0e0;font-size:.75rem">';
  h+='<strong style="font-size:.85rem">'+appId+' — NFR Gates</strong>';
  if(srcGates.length){{
    h+='<div style="margin-top:.5rem"><span style="color:#9c27b0;font-weight:700">Produces '+srcGates.length+' gate(s):</span>';
    srcGates.forEach(g=>{{
      h+='<div style="margin:3px 0 3px 10px;padding:4px 6px;background:#f3e5f5;border-radius:4px">';
      h+='<strong>'+esc(g.gate_id)+'</strong>: '+esc(g.nfr)+' → blocks '+g.blocks.length+' stories';
      h+='</div>';
    }});
    h+='</div>';
  }}
  if(blkGates.length){{
    h+='<div style="margin-top:.5rem"><span style="color:#f44336;font-weight:700">Blocked by '+blkGates.length+' gate(s):</span>';
    blkGates.forEach(b=>{{
      h+='<div style="margin:3px 0 3px 10px;padding:4px 6px;background:#ffebee;border-radius:4px">';
      h+='<strong>'+esc(b.gate.gate_id)+'</strong> ('+esc(b.gate.source_epic)+'): '+esc(b.gate.nfr);
      h+='<div style="color:#666;font-size:.68rem">↳ Story: '+esc(b.story)+'</div>';
      h+='</div>';
    }});
    h+='</div>';
  }}
  if(!srcGates.length&&!blkGates.length)h+='<div style="color:#888;margin-top:.3rem">No NFR gates linked to this app.</div>';
  h+='</div>';
  document.getElementById('gateDetail').innerHTML=h;
}}
function renderDataFlow(){{
  const w=850,h=680;
  const appY=60,dbY=420;
  const appNodes=APPS.slice(0,8);// Show main apps
  const appSpacing=w/(appNodes.length+1);
  let svg='<svg width="'+w+'" height="'+h+'" style="font-family:sans-serif">';
  svg+='<text x="10" y="20" font-size="12" font-weight="bold" fill="#1a1a2e">Applications</text>';
  svg+='<text x="10" y="410" font-size="12" font-weight="bold" fill="#1a1a2e">Data Stores</text>';
  svg+='<rect x="0" y="30" width="'+w+'" height="350" fill="#f8f9ff" rx="8"/>';
  svg+='<rect x="0" y="390" width="'+w+'" height="280" fill="#f5f5f5" rx="8"/>';
  // App nodes
  appNodes.forEach((app,i)=>{{
    const x=(i+1)*appSpacing-50;
    const c=PHASE_COLORS['Phase '+app.phase]||'#666';
    svg+='<g class="node" data-id="'+app.id+'" onclick="highlightNode(\\'dfDiagram\\',\\''+app.id+'\\')">';
    svg+='<rect x="'+x+'" y="'+appY+'" width="100" height="50" rx="6" fill="'+c+'" opacity="0.85"/>';
    svg+='<text x="'+(x+50)+'" y="'+(appY+20)+'" text-anchor="middle" font-size="8" fill="#fff" font-weight="bold">'+app.id+'</text>';
    svg+='<text x="'+(x+50)+'" y="'+(appY+36)+'" text-anchor="middle" font-size="7" fill="#fff">'+app.name+'</text>';
    svg+='</g>';
  }});
  // DB nodes
  const dbSpacing=w/(DB_NODES.length+1);
  DB_NODES.forEach((db,i)=>{{
    const x=(i+1)*dbSpacing-45;
    svg+='<g class="node" data-id="'+db.id+'" onclick="highlightNode(\\'dfDiagram\\',\\''+db.id+'\\')">';
    svg+='<ellipse cx="'+(x+45)+'" cy="'+(dbY+50)+'" rx="45" ry="28" fill="#e1d5e7" stroke="#9673a6"/>';
    svg+='<text x="'+(x+45)+'" y="'+(dbY+47)+'" text-anchor="middle" font-size="7" fill="#333" font-weight="bold">'+db.name+'</text>';
    svg+='<text x="'+(x+45)+'" y="'+(dbY+60)+'" text-anchor="middle" font-size="6" fill="#666">('+db.apps.length+' apps)</text>';
    svg+='</g>';
  }});
  // Edges: app → db
  DB_NODES.forEach((db,di)=>{{
    const dx=(di+1)*dbSpacing;
    db.apps.forEach(appId=>{{
      const ai=appNodes.findIndex(a=>a.id===appId);
      if(ai>=0){{
        const ax=(ai+1)*appSpacing;
        svg+='<line class="edge" data-from="'+appId+'" data-to="'+db.id+'" x1="'+ax+'" y1="'+(appY+50)+'" x2="'+dx+'" y2="'+(dbY+22)+'" stroke="#9673a650" stroke-width="1.5"/>';
      }}
    }});
  }});
  // App-to-app edges
  appNodes.forEach((app,i)=>{{
    const ax=(i+1)*appSpacing;
    app.deps.forEach(depId=>{{
      const di=appNodes.findIndex(a=>a.id===depId);
      if(di>=0){{
        const dx=(di+1)*appSpacing;
        svg+='<line class="edge" data-from="'+app.id+'" data-to="'+depId+'" x1="'+ax+'" y1="'+(appY+25)+'" x2="'+dx+'" y2="'+(appY+25)+'" stroke="#2196f330" stroke-width="1" stroke-dasharray="4"/>';
      }}
    }});
  }});
  svg+='</svg>';
  let out='<div class="diagram-container">';
  out+='<div class="diagram-controls"><button onclick="zoomDiagram(\\'dfDiagram\\',0.2)">Zoom +</button><button onclick="zoomDiagram(\\'dfDiagram\\',-0.2)">Zoom -</button><button onclick="resetHighlight(\\'dfDiagram\\');diagramZoom=1;document.querySelector(\\'#dfDiagram svg\\').style.transform=\\'\\'">Reset</button><span style="font-size:.75rem;color:#666;margin-left:1rem">Click any app or data store to highlight connections</span></div>';
  out+='<div class="diagram-svg" id="dfDiagram">'+svg+'</div></div>';
  return out;
}}
function renderDiagramEditor(){{
  const diagrams=[
    {{key:'migration_dependency_diagram',label:'Migration Phases & Dependencies'}},
    {{key:'data_flow_diagram',label:'Data Flow & Application Flow'}},
    {{key:'operational_dependency_diagram',label:'Operational Dependency & Ownership'}}
  ];
  let h='<p style="font-size:.82rem;color:#666;margin-bottom:.5rem">Select a diagram to open in the full draw.io editor. You can move blocks, add connections, edit text, and save changes.</p>';
  h+='<div style="display:flex;gap:.5rem;margin-bottom:.5rem;flex-wrap:wrap">';
  diagrams.forEach((d,i)=>{{
    h+='<button onclick="openDrawio(\\''+d.key+'\\',\\''+d.label+'\\' )" style="padding:6px 12px;border:1px solid #ddd;border-radius:6px;background:#fff;cursor:pointer;font-size:.8rem">✏️ '+d.label+'</button>';
  }});
  h+='</div>';
  h+='<div id="drawioContainer" style="width:100%;height:70vh;border:1px solid #ddd;border-radius:8px;overflow:hidden;background:#f9f9f9;display:flex;align-items:center;justify-content:center;color:#888;font-size:.9rem">Select a diagram above to open the editor</div>';
  return h;
}}
let drawioFrame=null;
let currentDiagramKey=null;
function openDrawio(key,label){{
  currentDiagramKey=key;
  const xml=DATA.drawio[key];
  if(!xml){{alert('Diagram not found: '+key);return}}
  const container=document.getElementById('drawioContainer');
  container.innerHTML='<iframe id="drawioIframe" style="width:100%;height:100%;border:none" src="https://embed.diagrams.net/?embed=1&proto=json&spin=1&libraries=1"></iframe>';
  drawioFrame=document.getElementById('drawioIframe');
  // Listen for messages from draw.io
  window.addEventListener('message',handleDrawioMessage);
  // Store XML to send once iframe is ready
  window._pendingDrawioXml=xml;
  window._pendingDrawioLabel=label;
}}
function handleDrawioMessage(evt){{
  if(!evt.data||typeof evt.data!=='string')return;
  try{{
    const msg=JSON.parse(evt.data);
    if(msg.event==='init'){{
      // Editor ready — load the diagram
      drawioFrame.contentWindow.postMessage(JSON.stringify({{
        action:'load',
        xml:window._pendingDrawioXml,
        title:window._pendingDrawioLabel
      }}),'*');
    }}else if(msg.event==='save'){{
      // User clicked save — store updated XML
      DATA.drawio[currentDiagramKey]=msg.xml;
      localStorage.setItem('drawio_'+currentDiagramKey,msg.xml);
      drawioFrame.contentWindow.postMessage(JSON.stringify({{action:'status',message:'Saved!',modified:false}}),'*');
    }}else if(msg.event==='exit'){{
      // User closed editor
      const container=document.getElementById('drawioContainer');
      container.innerHTML='<span style="color:#888;font-size:.9rem">Editor closed. Select a diagram to reopen.</span>';
      window.removeEventListener('message',handleDrawioMessage);
      drawioFrame=null;
    }}
  }}catch(e){{}}
}}
// Load any saved diagrams from localStorage on startup
Object.keys(DATA.drawio).forEach(k=>{{
  const saved=localStorage.getItem('drawio_'+k);
  if(saved)DATA.drawio[k]=saved;
}});
function renderGates(){{
  const typeColors={{'story_start':'#f44336','story_done':'#ff9800','epic_exit':'#9c27b0'}};
  const typeLabels={{'story_start':'🚫 Story Start Gate','story_done':'✅ Story Done Gate','epic_exit':'🏁 Epic Exit Gate'}};
  let h='<div style="display:flex;gap:.5rem;margin-bottom:.5rem;align-items:center">';
  h+='<button onclick="document.querySelectorAll(\\'#contentArea .g-epic-hdr\\').forEach(el=>{{if(!el.classList.contains(\\'open\\')){{el.classList.add(\\'open\\');el.nextElementSibling.classList.add(\\'open\\')}}}});" style="padding:4px 10px;border:1px solid #ddd;border-radius:4px;background:#fff;cursor:pointer;font-size:.75rem">➕ Expand All</button>';
  h+='<button onclick="document.querySelectorAll(\\'#contentArea .g-epic-hdr\\').forEach(el=>{{el.classList.remove(\\'open\\');el.nextElementSibling.classList.remove(\\'open\\')}});" style="padding:4px 10px;border:1px solid #ddd;border-radius:4px;background:#fff;cursor:pointer;font-size:.75rem">➖ Collapse All</button>';
  h+='<span style="font-size:.75rem;color:#666">NFR Gates define which requirements must be met before downstream stories can start or complete.</span></div>';
  h+='<div class="gantt-wrap">';
  DATA.gates.forEach((g,gi)=>{{
    const tc=typeColors[g.gate_type]||'#666';
    h+='<div class="g-epic" style="border-left:4px solid '+tc+'">';
    h+='<div class="g-epic-hdr" onclick="tog(this)">';
    h+='<span class="arr">▶</span>';
    h+='<span style="font-size:.75rem;font-weight:700">'+esc(g.gate_id)+'</span>';
    h+='<span style="font-size:.7rem;padding:2px 6px;border-radius:8px;background:'+tc+'20;color:'+tc+';font-weight:600">'+typeLabels[g.gate_type]+'</span>';
    h+='<span style="font-size:.72rem;flex:1;margin-left:8px">'+esc(g.nfr)+'</span>';
    h+='<span style="font-size:.65rem;color:#888">blocks '+g.blocks.length+' stories</span>';
    h+='</div>';
    h+='<div class="g-epic-body">';
    h+='<div style="padding:6px 0;font-size:.75rem"><strong>Source:</strong> '+esc(g.source_epic)+' ('+esc(g.source_app)+') | <strong>Category:</strong> '+esc(g.nfr_category)+'</div>';
    h+='<div style="padding:4px 0;font-size:.75rem;color:#1565c0"><strong>Validation:</strong> '+esc(g.validation)+'</div>';
    h+='<div style="padding:6px 0;font-size:.75rem;font-weight:600">Blocked Stories:</div>';
    g.blocks.forEach(b=>{{
      h+='<div style="margin:4px 0;padding:6px 8px;background:#fff3f3;border-radius:4px;border-left:3px solid '+tc+';font-size:.73rem">';
      h+='<div><strong>'+esc(b.epic)+'</strong> → '+esc(b.story)+'</div>';
      h+='<div style="color:#666;font-size:.68rem;margin-top:2px">↳ '+esc(b.reason)+'</div>';
      h+='</div>';
    }});
    h+='</div></div>';
  }});
  h+='</div>';
  return h;
}}
function renderOverview(){{
  let allDone=0,allTotal=0;
  DATA.gantt.forEach((e,ei)=>{{const p=getEpicProgress(ei);allDone+=p.done;allTotal+=p.total}});
  const overallPct=allTotal?Math.round(allDone/allTotal*100):0;
  let h='<div class="summary-cards">'+
    '<div class="card green"><h3>Duration</h3><div class="value">37 weeks</div></div>'+
    '<div class="card blue"><h3>Progress</h3><div class="value">'+overallPct+'%</div><div class="progress-bar" style="margin-top:4px"><div class="fill green" style="width:'+overallPct+'%"></div></div></div>'+
    '<div class="card orange"><h3>Stories</h3><div class="value">'+allDone+'/'+allTotal+'</div></div>'+
    '<div class="card red"><h3>Savings Target</h3><div class="value">44%</div></div>'+
  '</div>';
  h+='<h3 style="margin:.8rem 0 .5rem">Phase Timeline — click to expand</h3>';
  const phases=[
    {{name:'Phase 0: Mobilisation',weeks:'W1-4',color:'#607d8b',epics:DATA.gantt.filter(e=>e.phase==='Phase 0')}},
    {{name:'Phase 1: Foundation',weeks:'W5-11',color:'#4caf50',epics:DATA.gantt.filter(e=>e.phase==='Phase 1')}},
    {{name:'Phase 2: Core Business',weeks:'W12-19',color:'#2196f3',epics:DATA.gantt.filter(e=>e.phase==='Phase 2')}},
    {{name:'Phase 3: Dependent',weeks:'W20-26',color:'#ff9800',epics:DATA.gantt.filter(e=>e.phase==='Phase 3')}},
    {{name:'Phase 4: Legacy/Modernise',weeks:'W27-37',color:'#f44336',epics:DATA.gantt.filter(e=>e.phase==='Phase 4')}}
  ];
  // NFR gates grouped by source phase
  const gatesByPhase={{'Phase 0':[],'Phase 1':[],'Phase 2':[],'Phase 3':[],'Phase 4':[]}};
  DATA.gates.forEach(g=>{{
    const ep=DATA.gantt.find(e=>e.epic_id===g.source_epic);
    if(ep)gatesByPhase[ep.phase].push(g);
  }});
  h+='<div class="gantt-wrap">';
  phases.forEach((phase,pi)=>{{
    const phaseEpics=phase.epics;
    const phaseDone=phaseEpics.reduce((s,e,i)=>{{const idx=DATA.gantt.indexOf(e);return s+getEpicProgress(idx).done}},0);
    const phaseTotal=phaseEpics.reduce((s,e,i)=>{{const idx=DATA.gantt.indexOf(e);return s+getEpicProgress(idx).total}},0);
    const phasePct=phaseTotal?Math.round(phaseDone/phaseTotal*100):0;
    const phaseGates=gatesByPhase[phase.epics[0]?phase.epics[0].phase:'']||[];
    h+='<div class="g-epic" style="border-left:4px solid '+phase.color+'">';
    h+='<div class="g-epic-hdr" onclick="tog(this)" data-tog-id="ov-p'+pi+'">';
    h+='<span class="arr">▶</span>';
    h+='<span style="font-size:.85rem;font-weight:700;color:'+phase.color+'">'+phase.name+'</span>';
    h+='<span style="font-size:.7rem;color:#888;margin-left:8px">'+phase.weeks+' · '+phaseEpics.length+' epics</span>';
    h+='<div class="progress-bar" style="max-width:100px"><div class="fill '+(phasePct===100?'green':phasePct>0?'orange':'')+'" style="width:'+phasePct+'%"></div></div>';
    h+='<span style="font-size:.65rem;color:#666">'+phasePct+'%</span>';
    h+='</div>';
    h+='<div class="g-epic-body">';
    // Epics tree
    h+='<div style="font-size:.72rem;font-weight:700;color:#444;padding:4px 0">📋 Epics & Stories</div>';
    phaseEpics.forEach(epic=>{{
      const ei=DATA.gantt.indexOf(epic);
      const prog=getEpicProgress(ei);
      h+='<div style="margin:2px 0 2px 8px">';
      h+='<div class="g-epic-hdr" onclick="tog(this)" data-tog-id="ov-e'+ei+'" style="padding:4px 6px">';
      h+='<span class="arr">▶</span>';
      h+='<span style="font-size:.75rem;cursor:pointer;color:#1565c0;text-decoration:underline" onclick="event.stopPropagation();goToGanttEpic('+ei+')">'+esc(epic.epic_id)+'</span>';
      h+='<span style="font-size:.72rem;margin-left:4px">'+esc(epic.epic)+'</span>';
      h+='<span style="font-size:.62rem;color:#888;margin-left:6px">'+prog.done+'/'+prog.total+'</span>';
      h+='<div class="progress-bar" style="max-width:60px"><div class="fill '+(prog.pct===100?'green':prog.pct>0?'orange':'')+'" style="width:'+prog.pct+'%"></div></div>';
      h+='</div>';
      h+='<div class="g-epic-body" style="padding-left:20px">';
      epic.roles.forEach((r,ri)=>{{
        (r.stories||[]).forEach((s,si)=>{{
          const sp=getStoryProgress(ei,ri,si);
          const statusIcon=sp.status==='done'?'✅':sp.status==='ip'?'🔄':'⬜';
          h+='<div style="font-size:.68rem;padding:1px 0;display:flex;align-items:center;gap:4px;cursor:pointer" onclick="goToGanttStory('+ei+','+ri+','+si+')">';
          h+=statusIcon+' <span class="sz sz-'+(s.size||'M')+'">'+(s.size||'M')+'</span> ';
          h+='<span style="'+(sp.status==='done'?'text-decoration:line-through;opacity:.6':'')+'">'+esc(s.story.substring(0,60))+(s.story.length>60?'...':'')+'</span>';
          h+='</div>';
        }});
      }});
      h+='</div></div>';
    }});
    // NFR Gates tree
    if(phaseGates.length){{
      h+='<div style="font-size:.72rem;font-weight:700;color:#444;padding:6px 0 4px;margin-top:4px;border-top:1px solid #eee">🚦 NFR Gates ('+phaseGates.length+')</div>';
      phaseGates.forEach(g=>{{
        const typeIcon=g.gate_type==='story_start'?'🚫':g.gate_type==='story_done'?'✅':'🏁';
        h+='<div style="font-size:.68rem;padding:2px 0 2px 8px;display:flex;align-items:center;gap:4px;cursor:pointer" onclick="showTab(\\'gates\\')">';
        h+=typeIcon+' <strong>'+esc(g.gate_id)+'</strong>: '+esc(g.nfr.substring(0,50))+(g.nfr.length>50?'...':'')+' <span style="color:#888">(→'+g.blocks.length+' stories)</span>';
        h+='</div>';
      }});
    }}
    h+='</div></div>';
  }});
  h+='</div>';
  return h;
}}
function goToGanttEpic(ei){{
  EXPANDED['e'+ei]=true;
  localStorage.setItem('ganttExpanded',JSON.stringify(EXPANDED));
  showTab('gantt');
  setTimeout(()=>{{const el=document.querySelector('[data-tog-id="e'+ei+'"]');if(el)el.scrollIntoView({{behavior:'smooth',block:'center'}})}},100);
}}
function goToGanttStory(ei,ri,si){{
  EXPANDED['e'+ei]=true;
  EXPANDED['r'+ei+'-'+ri]=true;
  EXPANDED['s'+ei+'-'+ri+'-'+si]=true;
  localStorage.setItem('ganttExpanded',JSON.stringify(EXPANDED));
  showTab('gantt');
  setTimeout(()=>{{const el=document.querySelector('[data-tog-id="s'+ei+'-'+ri+'-'+si+'"]');if(el)el.scrollIntoView({{behavior:'smooth',block:'center'}})}},100);
}}
function expandAll(){{
  DATA.gantt.forEach((epic,ei)=>{{
    EXPANDED['e'+ei]=true;
    epic.roles.forEach((r,ri)=>{{
      EXPANDED['r'+ei+'-'+ri]=true;
      (r.stories||[]).forEach((s,si)=>{{EXPANDED['s'+ei+'-'+ri+'-'+si]=true}});
    }});
  }});
  localStorage.setItem('ganttExpanded',JSON.stringify(EXPANDED));
  render();
}}
function collapseAll(){{
  EXPANDED={{}};
  localStorage.setItem('ganttExpanded',JSON.stringify(EXPANDED));
  render();
}}
function renderTable(data){{
  if(!data||!data.length)return '<p>No data</p>';
  const keys=Object.keys(data[0]);
  let h='<div class="table-wrap"><table><thead><tr>'+keys.map(k=>'<th>'+esc(k)+'</th>').join('')+'</tr></thead><tbody>';
  data.forEach(row=>{{h+='<tr>'+keys.map(k=>'<td>'+esc(row[k]||'')+'</td>').join('')+'</tr>'}});
  h+='</tbody></table></div>';
  return h;
}}
function esc(s){{return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}}
// Chat
const chatHistory=[];
function toggleChat(){{document.getElementById('chatPanel').classList.toggle('open')}}
async function sendChat(){{
  const input=document.getElementById('chatInput');
  const msg=input.value.trim();if(!msg)return;
  input.value='';addMsg(msg,'user');
  chatHistory.push({{role:'user',content:msg}});
  const el=addMsg('Thinking...','bot');
  try{{
    const base=window.location.pathname.replace(/\\/$/,'');
    const url=base+'/api/chat?q='+encodeURIComponent(msg)+'&history='+encodeURIComponent(JSON.stringify(chatHistory.slice(-6)));
    const r=await fetch(url);
    const t=await r.text();
    el.remove();
    let reply;
    try{{const j=JSON.parse(t);reply=j.reply||j.error||t}}catch(e){{reply='Error: '+t.substring(0,150)}}
    addMsg(reply,'bot');
    chatHistory.push({{role:'assistant',content:reply}});
  }}catch(e){{el.remove();addMsg('Connection error: '+e.message,'bot')}}
}}
function addMsg(t,c){{const d=document.createElement('div');d.className='msg '+c;d.textContent=t;document.getElementById('chatMessages').appendChild(d);d.scrollIntoView({{behavior:'smooth'}});return d}}
// === CHANGE LOG & EDITABLE STORIES ===
let CHANGELOG=JSON.parse(localStorage.getItem('migrationChangeLog')||'[]');
let STORY_EDITS=JSON.parse(localStorage.getItem('migrationStoryEdits')||'{{}}');
let EXTRA_DAYS=JSON.parse(localStorage.getItem('migrationExtraDays')||'{{}}');
let NEW_STORIES=JSON.parse(localStorage.getItem('migrationNewStories')||'{{}}');
function saveChangeLog(){{localStorage.setItem('migrationChangeLog',JSON.stringify(CHANGELOG))}}
function saveStoryEdits(){{localStorage.setItem('migrationStoryEdits',JSON.stringify(STORY_EDITS))}}
function saveExtraDays(){{localStorage.setItem('migrationExtraDays',JSON.stringify(EXTRA_DAYS))}}
function saveNewStories(){{localStorage.setItem('migrationNewStories',JSON.stringify(NEW_STORIES))}}
function getStoryText(ei,ri,si){{return STORY_EDITS[ei+'-'+ri+'-'+si]||DATA.gantt[ei].roles[ri].stories[si].story}}
function getExtraDaysForEpic(ei){{return EXTRA_DAYS[ei]||0}}
function isStoryNew(ei,ri,si){{return !!NEW_STORIES[ei+'-'+ri+'-'+si]}}
function markStoryViewed(ei,ri,si){{const k=ei+'-'+ri+'-'+si;if(NEW_STORIES[k]){{delete NEW_STORIES[k];saveNewStories()}}}}
function editStory(ei,ri,si){{
  markStoryViewed(ei,ri,si);
  const key=ei+'-'+ri+'-'+si;const current=getStoryText(ei,ri,si);
  const el=document.getElementById('st-'+key);if(!el)return;
  el.innerHTML='<input type="text" value="'+esc(current).replace(/"/g,'&quot;')+'" style="width:100%;font-size:.73rem;padding:2px 4px;border:1px solid #2196f3;border-radius:3px" onkeydown="if(event.key===\\'Enter\\')saveOnlyChange('+ei+','+ri+','+si+',this.value,0)" id="st-input-'+key+'"><button onclick="saveOnlyChange('+ei+','+ri+','+si+',document.getElementById(\\'st-input-'+key+'\\').value,0)" style="margin-left:4px;padding:2px 6px;font-size:.65rem;border:1px solid #4caf50;border-radius:3px;background:#e8f5e9;cursor:pointer">Save Save</button><button onclick="reviewImpact('+ei+','+ri+','+si+',document.getElementById(\\'st-input-'+key+'\\').value)" style="margin-left:2px;padding:2px 6px;font-size:.65rem;border:1px solid #ff9800;border-radius:3px;background:#fff3e0;cursor:pointer">Review Review Impact</button>';
  document.getElementById('st-input-'+key).focus();
}}
function reviewImpact(ei,ri,si,newText){{
  const epic=DATA.gantt[ei];const role=epic.roles[ri];const oldText=role.stories[si].story;
  const impacts=[];const nw=newText.toLowerCase();let extraDays=0;
  if(nw.includes('testing')||nw.includes('test')){{impacts.push({{msg:'Environment availability needed for testing',days:2}});extraDays+=2}}
  if(nw.includes('performance')){{impacts.push({{msg:'Performance testing requires dedicated load window',days:3}});extraDays+=3}}
  if(nw.includes('security')||nw.includes('pen test')){{impacts.push({{msg:'Security review/pen test adds lead time',days:5}});extraDays+=5}}
  if(nw.includes('partner')||nw.includes('vendor')){{impacts.push({{msg:'External dependency - vendor/partner coordination',days:3}});extraDays+=3}}
  if(nw.includes('migration')||nw.includes('data')){{impacts.push({{msg:'Data migration scope change - validation effort increases',days:2}});extraDays+=2}}
  if(newText!==oldText&&impacts.length===0){{impacts.push({{msg:'Scope change - review with team',days:1}});extraDays+=1}}
  const impactId='impact-'+ei+'-'+ri+'-'+si;
  let h='<div class="impact-box" id="'+impactId+'">';
  h+='<div style="font-weight:700;margin-bottom:6px">Review Change Impact Analysis</div>';
  h+='<div style="font-size:.7rem;color:#666;margin-bottom:6px"><strong>Change:</strong> '+esc(oldText.substring(0,40))+'... -> '+esc(newText.substring(0,40))+'...</div>';
  impacts.forEach(imp=>{{const color=imp.days>=5?'#f44336':'#ff9800';h+='<div class="impact-item" style="background:'+color+'10;border-left:3px solid '+color+'"><span style="font-weight:600;color:'+color+'">+'+imp.days+'d</span> '+esc(imp.msg)+'</div>'}});
  h+='<div style="margin-top:8px;padding:6px;background:#e3f2fd;border-radius:4px"><strong>Timeline:</strong> ';
  if(extraDays>5)h+='WARNING Plan right-shifts by ~'+extraDays+'d. '+epic.epic_id+' may extend to W'+(epic.end+Math.ceil(extraDays/5));
  else h+='Minor (+'+extraDays+'d). Absorbable within buffer.';
  h+='</div><div style="margin-top:8px;display:flex;gap:6px">';
  h+='<button onclick="acceptChange('+ei+','+ri+','+si+',this.closest(\\'.impact-box\\').previousElementSibling.querySelector(\\'input\\').value,'+extraDays+')" style="padding:4px 10px;border:1px solid #4caf50;border-radius:4px;background:#e8f5e9;cursor:pointer;font-size:.72rem">OK Accept (+'+extraDays+'d)</button>';
  h+='<button onclick="saveOnlyChange('+ei+','+ri+','+si+',this.closest(\\'.impact-box\\').previousElementSibling.querySelector(\\'input\\').value,'+extraDays+')" style="padding:4px 10px;border:1px solid #ff9800;border-radius:4px;background:#fff3e0;cursor:pointer;font-size:.72rem">Save Save Only</button>';
  h+='<button onclick="document.getElementById(\\''+impactId+'\\').remove()" style="padding:4px 10px;border:1px solid #ddd;border-radius:4px;background:#fff;cursor:pointer;font-size:.72rem">X Cancel</button>';
  h+='</div></div>';
  const stEl=document.getElementById('st-'+ei+'-'+ri+'-'+si);
  if(stEl)stEl.insertAdjacentHTML('afterend',h);
}}
function acceptChange(ei,ri,si,newText,extraDays){{
  const key=ei+'-'+ri+'-'+si;
  STORY_EDITS[key]=newText;NEW_STORIES[key]=true;saveStoryEdits();saveNewStories();
  EXTRA_DAYS[ei]=(EXTRA_DAYS[ei]||0)+extraDays;saveExtraDays();
  CHANGELOG.unshift({{id:Date.now(),date:new Date().toISOString().slice(0,16).replace('T',' '),epic:DATA.gantt[ei].epic_id,epicIdx:ei,role:DATA.gantt[ei].roles[ri].role,storyKey:key,type:'scope_change',oldText:DATA.gantt[ei].roles[ri].stories[si].story,newText:newText,status:'accepted',impact:{{extraDays:extraDays,shift:extraDays>5?'right-shift +'+extraDays+'d':'minor (+'+extraDays+'d)'}}}});
  saveChangeLog();refreshGantt();
}}
function saveOnlyChange(ei,ri,si,newText,extraDays){{
  const key=ei+'-'+ri+'-'+si;const oldText=DATA.gantt[ei].roles[ri].stories[si].story;
  if(newText!==oldText){{STORY_EDITS[key]=newText;NEW_STORIES[key]=true;saveStoryEdits();saveNewStories()}}
  CHANGELOG.unshift({{id:Date.now(),date:new Date().toISOString().slice(0,16).replace('T',' '),epic:DATA.gantt[ei].epic_id,epicIdx:ei,role:DATA.gantt[ei].roles[ri].role,storyKey:key,type:'edit',oldText:oldText,newText:newText,status:'pending',impact:extraDays?{{extraDays:extraDays,shift:'pending (+'+extraDays+'d potential)'}}:null}});
  saveChangeLog();refreshGantt();
}}
function refreshGantt(){{
  if(activeTab==='gantt'){{
    const content=document.getElementById('contentArea');
    content.querySelectorAll('.tab').forEach(t=>{{if(t.classList.contains('active'))t.innerHTML=renderGantt()}});
    Object.keys(EXPANDED).forEach(id=>{{const el=document.querySelector('[data-tog-id="'+id+'"]');if(el){{el.classList.add('open');const b=el.nextElementSibling;if(b)b.classList.add('open')}}}});
  }}
}}
let clFilter='all';
function renderChangeLog(){{
  if(!CHANGELOG.length)return '<div class="change-log"><div class="change-log-header"><span>LOG Change Log</span></div><div style="padding:12px;color:#888;text-align:center">No changes yet. Double-click a story to edit.</div></div>';
  const groups={{}};
  CHANGELOG.forEach(c=>{{const gKey=c.epic+'|'+(c.storyKey||'x');if(!groups[gKey])groups[gKey]={{epic:c.epic,entries:[]}};groups[gKey].entries.push(c)}});
  const filtered=clFilter==='all'?CHANGELOG:CHANGELOG.filter(c=>c.status===clFilter);
  const pendingN=CHANGELOG.filter(c=>c.status==='pending').length;
  const acceptedN=CHANGELOG.filter(c=>c.status==='accepted').length;
  let h='<div class="change-log"><div class="change-log-header">';
  h+='<span>LOG Change Log ('+CHANGELOG.length+(pendingN?' - <span style="color:#f44336;font-weight:700">'+pendingN+' pending</span>':'')+')</span>';
  h+='<div style="display:flex;gap:4px">';
  h+='<button onclick="clFilter=\\'all\\';refreshGantt()" style="padding:2px 6px;border:1px solid '+(clFilter==='all'?'#1a1a2e':'#ddd')+';border-radius:3px;background:'+(clFilter==='all'?'#1a1a2e':'#fff')+';color:'+(clFilter==='all'?'#fff':'#333')+';cursor:pointer;font-size:.6rem">All</button>';
  h+='<button onclick="clFilter=\\'pending\\';refreshGantt()" style="padding:2px 6px;border:1px solid '+(clFilter==='pending'?'#ff5722':'#ddd')+';border-radius:3px;background:'+(clFilter==='pending'?'#ff5722':'#fff')+';color:'+(clFilter==='pending'?'#fff':'#333')+';cursor:pointer;font-size:.6rem">Pending ('+pendingN+')</button>';
  h+='<button onclick="clFilter=\\'accepted\\';refreshGantt()" style="padding:2px 6px;border:1px solid '+(clFilter==='accepted'?'#4caf50':'#ddd')+';border-radius:3px;background:'+(clFilter==='accepted'?'#4caf50':'#fff')+';color:'+(clFilter==='accepted'?'#fff':'#333')+';cursor:pointer;font-size:.6rem">Accepted ('+acceptedN+')</button>';
  h+='</div></div>';
  Object.values(groups).forEach(grp=>{{
    const gf=grp.entries.filter(c=>clFilter==='all'||c.status===clFilter);if(!gf.length)return;
    const storyName=gf[0].newText?gf[0].newText.substring(0,45):'';
    h+='<div style="border-bottom:1px solid #e0e0e0">';
    h+='<div style="padding:4px 12px;background:#f9f9f9;font-size:.7rem;font-weight:600;cursor:pointer;display:flex;align-items:center;gap:6px" onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display===\\'none\\'?\\'block\\':\\'none\\'">';
    h+='> <strong>'+esc(grp.epic)+'</strong> <span style="color:#1565c0">'+esc(storyName)+'</span> - '+gf.length+' change(s)';
    h+=' <span class="change-badge '+gf[0].status+'">'+gf[0].status.toUpperCase()+'</span>';
    if(gf[0].impact)h+=' <span style="font-size:.6rem;color:#f44336">'+esc(gf[0].impact.shift)+'</span>';
    h+='</div><div>';
    gf.forEach((c,ci)=>{{
      h+='<div class="change-entry '+c.status+'" title="OLD: '+(esc(c.oldText||''))+'&#10;NEW: '+(esc(c.newText||''))+'">';
      h+='<span class="change-badge '+c.status+'">'+c.status.toUpperCase()+'</span>';
      h+='<span style="color:#888;min-width:85px;font-size:.62rem">'+c.date+'</span>';
      h+='<span style="font-size:.62rem;color:#555;min-width:50px">#'+(c.storyKey||'-')+'</span>';
      h+='<div style="flex:1;font-size:.65rem;overflow:hidden"><div style="color:#c62828;text-decoration:line-through;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'+esc((c.oldText||'').substring(0,50))+'</div>';
      h+='<div style="color:#2e7d32;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'+esc((c.newText||'').substring(0,50))+'</div></div>';
      if(c.impact)h+='<span style="font-size:.6rem;color:'+(c.impact.extraDays>5?'#f44336':'#ff9800')+';white-space:nowrap">'+esc(c.impact.shift)+'</span>';
      h+='</div>';
    }});
    h+='</div></div>';
  }});
  h+='</div>';
  return h;
}}

// === PROGRESS TRACKING ===
let PROGRESS=JSON.parse(localStorage.getItem('migrationProgress')||'{{}}');
function saveProgress(){{localStorage.setItem('migrationProgress',JSON.stringify(PROGRESS))}}
function getStoryKey(ei,ri,si){{return ei+'-'+ri+'-'+si}}
function getStoryProgress(ei,ri,si){{
  return PROGRESS[getStoryKey(ei,ri,si)]||{{status:'ns',actualStart:'',actualEnd:'',actualHours:''}}
}}
function updateStory(ei,ri,si,field,value){{
  const key=getStoryKey(ei,ri,si);
  if(!PROGRESS[key])PROGRESS[key]={{status:'ns',actualStart:'',actualEnd:'',actualHours:''}};
  PROGRESS[key][field]=value;
  if(field==='status'&&value==='done'&&!PROGRESS[key].actualEnd)PROGRESS[key].actualEnd=PROGRESS[key].actualStart||'';
  saveProgress();
  // Re-render only the gantt tab content without losing expand state
  if(activeTab==='gantt'){{
    const content=document.getElementById('contentArea');
    const tabs=content.querySelectorAll('.tab');
    tabs.forEach(t=>{{if(t.classList.contains('active'))t.innerHTML=renderGantt()}});
    // Restore expanded state
    Object.keys(EXPANDED).forEach(id=>{{
      const el=document.querySelector('[data-tog-id="'+id+'"]');
      if(el){{el.classList.add('open');const b=el.nextElementSibling;if(b)b.classList.add('open')}}
    }});
  }}
}}
function getEpicProgress(ei){{
  const epic=DATA.gantt[ei];
  let total=0,done=0,inProgress=0,totalPlanned=0,totalActual=0;
  epic.roles.forEach((r,ri)=>{{
    (r.stories||[]).forEach((s,si)=>{{
      total++;
      const p=getStoryProgress(ei,ri,si);
      if(p.status==='done')done++;
      if(p.status==='ip')inProgress++;
      totalPlanned+=r.man_days/(r.stories||[]).length;
      if(p.actualHours)totalActual+=parseFloat(p.actualHours)/8;
    }});
    if(!(r.stories&&r.stories.length)){{total++;totalPlanned+=r.man_days}}
  }});
  return {{total,done,inProgress,pct:total?Math.round(done/total*100):0,totalPlanned:Math.round(totalPlanned),totalActual:Math.round(totalActual)}};
}}
function exportProgress(){{
  const rows=[['Epic','Role','Story','Size','Status','Planned_Days','Actual_Start_Week','Actual_End_Week','Actual_Hours']];
  DATA.gantt.forEach((epic,ei)=>{{
    epic.roles.forEach((r,ri)=>{{
      (r.stories||[]).forEach((s,si)=>{{
        const p=getStoryProgress(ei,ri,si);
        const planned=Math.round(r.man_days/(r.stories.length));
        rows.push([epic.epic_id,r.role,s.story,s.size||'M',p.status,planned,p.actualStart,p.actualEnd,p.actualHours]);
      }});
    }});
  }});
  const csv=rows.map(r=>r.map(c=>String(c).replace(/,/g,';')).join(',')).join(String.fromCharCode(10));
  const blob=new Blob([csv],{{type:'text/csv'}});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='migration_progress.csv';a.click();
}}
// === PROJECT MANAGEMENT ===
const ARTIFACTS_LIST = {artifacts_list};
let currentProject = null;
let allProjects = [];

async function loadProjects() {{
  const r = await fetch('/api/projects');
  allProjects = await r.json();
  renderProjectBar();
  if (allProjects.length > 0 && !currentProject) {{
    await selectProject(allProjects[0].id);
  }}
}}

function renderProjectBar() {{
  const tabs = document.getElementById('projectTabs');
  if (!tabs) return;
  tabs.innerHTML = allProjects.map(p =>
    '<button onclick="selectProject(\\''+p.id+'\\')" style="padding:3px 10px;border-radius:12px;border:1px solid '+(currentProject&&currentProject.id===p.id?'#fff':'#555')+';background:'+(currentProject&&currentProject.id===p.id?'#fff':'transparent')+';color:'+(currentProject&&currentProject.id===p.id?'#1a1a2e':'#ccc')+';cursor:pointer;font-size:.75rem;display:inline-flex;align-items:center;gap:4px">'+
    escHtml(p.name)+
    '<span onclick="event.stopPropagation();deleteProject(\\''+p.id+'\\')" style="margin-left:4px;opacity:.6;font-size:.65rem" title="Delete">✕</span></button>'
  ).join('');
  const btn = document.getElementById('btnNewProject');
  if (btn) btn.style.display = allProjects.length >= 5 ? 'none' : '';
}}

async function selectProject(pid) {{
  const r = await fetch('/api/projects');
  allProjects = await r.json();
  currentProject = allProjects.find(p => p.id === pid) || null;
  renderProjectBar();
  if (currentProject) {{
    const sel = document.getElementById('llmSelect');
    if (sel) sel.value = currentProject.llm_backend || 'bedrock';
    await refreshFileList();
  }}
}}

async function createProject() {{
  const name = document.getElementById('newProjectName').value.trim();
  if (!name) return;
  const r = await fetch('/api/projects', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{name}})}});
  const data = await r.json();
  if (data.error) {{ document.getElementById('newProjectError').textContent = data.error; return; }}
  document.getElementById('newProjectDialog').style.display = 'none';
  document.getElementById('newProjectName').value = '';
  await selectProject(data.id);
}}

async function deleteProject(pid) {{
  if (!confirm('Delete this project and all its files?')) return;
  await fetch('/api/projects/'+pid, {{method:'DELETE'}});
  if (currentProject && currentProject.id === pid) currentProject = null;
  await loadProjects();
}}

async function setLLMBackend(backend) {{
  if (!currentProject) return;
  await fetch('/api/projects/'+currentProject.id, {{method:'PATCH', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{llm_backend:backend}})}});
  currentProject.llm_backend = backend;
}}

function showNewProjectDialog() {{
  document.getElementById('newProjectError').textContent = '';
  document.getElementById('newProjectName').value = '';
  document.getElementById('newProjectDialog').style.display = 'flex';
  setTimeout(()=>document.getElementById('newProjectName').focus(), 50);
}}

function toggleUploadPanel() {{
  const p = document.getElementById('uploadPanel');
  p.style.display = p.style.display === 'none' ? 'block' : 'none';
  if (p.style.display === 'block') refreshFileList();
}}

async function uploadFiles() {{
  if (!currentProject) {{ alert('Select or create a project first.'); return; }}
  const input = document.getElementById('fileInput');
  if (!input.files.length) return;
  const status = document.getElementById('uploadStatus');
  status.textContent = 'Uploading\u2026';
  const fd = new FormData();
  for (const f of input.files) fd.append('files', f);
  const r = await fetch('/api/upload/'+currentProject.id, {{method:'POST', body:fd}});
  const data = await r.json();
  status.textContent = data.uploaded ? 'Uploaded: '+data.uploaded.join(', ') : (data.error||'Error');
  input.value = '';
  await refreshFileList();
}}

async function refreshFileList() {{
  if (!currentProject) return;
  const r = await fetch('/api/projects/'+currentProject.id);
  currentProject = await r.json();
  const files = currentProject._files || [];
  const toggles = currentProject.artifact_toggles || {{}};
  const el = document.getElementById('fileList');
  if (!el) return;
  if (!files.length) {{ el.innerHTML = '<span style="color:#999">No files uploaded yet.</span>'; return; }}
  let h = '<div style="overflow-x:auto"><table style="border-collapse:collapse;font-size:.7rem;width:auto">';
  h += '<tr><th style="text-align:left;padding:2px 6px;background:#e8eaf6">File</th>';
  ARTIFACTS_LIST.forEach(a => {{ h += '<th style="padding:2px 4px;background:#e8eaf6;font-size:.6rem;white-space:nowrap">'+a+'</th>'; }});
  h += '<th style="background:#e8eaf6"></th></tr>';
  files.forEach(fname => {{
    h += '<tr><td style="padding:2px 6px;white-space:nowrap;max-width:180px;overflow:hidden;text-overflow:ellipsis" title="'+escHtml(fname)+'">'+escHtml(fname)+'</td>';
    ARTIFACTS_LIST.forEach(a => {{
      const enabled = (toggles[a]||[]).includes(fname);
      h += '<td style="text-align:center;padding:2px 4px"><input type="checkbox" '+(enabled?'checked':'')+
           ' onchange="toggleFile(\\''+escHtml(fname)+'\\',\\''+a+'\\',this.checked)" title="Enable for '+a+'"></td>';
    }});
    h += '<td style="padding:2px 4px"><span onclick="deleteFile(\\''+escHtml(fname)+'\\')" style="cursor:pointer;color:#f44336;font-size:.65rem" title="Delete file">🗑</span></td>';
    h += '</tr>';
  }});
  h += '</table></div>';
  el.innerHTML = h;
}}

async function toggleFile(fname, artifact, enabled) {{
  if (!currentProject) return;
  const toggles = currentProject.artifact_toggles || {{}};
  let list = [...(toggles[artifact]||[])];
  if (enabled) {{ if (!list.includes(fname)) list.push(fname); }}
  else {{ list = list.filter(f => f !== fname); }}
  const patch = {{artifact_toggles: {{[artifact]: list}}}};
  await fetch('/api/projects/'+currentProject.id, {{method:'PATCH', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify(patch)}});
  if (!currentProject.artifact_toggles) currentProject.artifact_toggles = {{}};
  currentProject.artifact_toggles[artifact] = list;
}}

async function deleteFile(fname) {{
  if (!currentProject) return;
  if (!confirm('Delete '+fname+'?')) return;
  await fetch('/api/files/'+currentProject.id+'/'+encodeURIComponent(fname), {{method:'DELETE'}});
  await refreshFileList();
}}

function escHtml(s) {{ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }}

async function generateTab(artifact) {{
  if (!currentProject) {{ alert('Select a project first.'); return; }}
  const btn = document.getElementById('gen-btn-'+artifact);
  if (btn) {{ btn.textContent = '\u23f3 Generating\u2026'; btn.disabled = true; }}
  try {{
    const r = await fetch('/api/generate', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{project_id: currentProject.id, artifact, prompt: ''}})
    }});
    const data = await r.json();
    if (data.error) {{ alert('Generation error: '+data.error); }}
    else {{ alert('Generated successfully! The data has been returned by the LLM.'); }}
  }} catch(e) {{ alert('Error: '+e.message); }}
  finally {{ if (btn) {{ btn.textContent = '\u23f3 Generating\u2026'; btn.disabled = false; }} }}
}}

loadProjects();
render();
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def _json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        query = urlparse(self.path).query

        # --- Projects list ---
        if path == "/api/projects":
            projects = list_projects()
            for p in projects:
                p["_files"] = list_files(p["id"])
            return self._json(projects)

        # --- Single project ---
        m = re.match(r"^/api/projects/([a-f0-9]+)$", path)
        if m:
            p = get_project(m.group(1))
            if not p:
                return self._json({"error": "Not found"}, 404)
            p["_files"] = list_files(p["id"])
            return self._json(p)

        # --- Chat ---
        if "/api/chat" in path or (query and "chat=" in query):
            from urllib.parse import parse_qs, unquote
            params = parse_qs(query, keep_blank_values=True)
            message = params.get("chat", params.get("q", [""]))[0]
            message = unquote(message).strip()
            if not message:
                return self._json({"reply": "Please type a question."})
            history_str = params.get("history", ["[]"])[0]
            try:
                history = json.loads(unquote(history_str))
            except Exception:
                history = []
            reply = chat_with_bedrock(message, history)
            return self._json({"reply": reply})

        # --- Default: serve HTML ---
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.end_headers()
        self.wfile.write(build_html().encode())

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))

        # --- Create project ---
        if path == "/api/projects":
            body = json.loads(self.rfile.read(length))
            p = create_project(body.get("name", "Untitled"))
            if p is None:
                return self._json({"error": "Maximum 5 projects reached."}, 400)
            return self._json(p)

        # --- File upload ---
        m = re.match(r"^/api/upload/([a-f0-9]+)$", path)
        if m:
            pid = m.group(1)
            if not get_project(pid):
                return self._json({"error": "Project not found"}, 404)
            content_type = self.headers.get("Content-Type", "")
            boundary = None
            for part in content_type.split(";"):
                part = part.strip()
                if part.startswith("boundary="):
                    boundary = part[9:].strip('"')
            if not boundary:
                return self._json({"error": "No boundary in multipart"}, 400)
            raw = self.rfile.read(length)
            uploaded = _parse_multipart(raw, boundary, pid)
            return self._json({"uploaded": uploaded})

        # --- Generate artifact ---
        if path == "/api/generate":
            body = json.loads(self.rfile.read(length))
            result = generate_artifact(
                body.get("project_id", ""),
                body.get("artifact", ""),
                body.get("prompt", ""),
            )
            try:
                return self._json(json.loads(result))
            except Exception:
                return self._json({"result": result})

        # --- Legacy chat POST ---
        body = json.loads(self.rfile.read(length) if length else b"{}")
        reply = chat_with_bedrock(body.get("message", ""), body.get("history", []))
        return self._json({"reply": reply})

    def do_PATCH(self):
        path = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        m = re.match(r"^/api/projects/([a-f0-9]+)$", path)
        if m:
            body = json.loads(self.rfile.read(length))
            p = update_project(m.group(1), body)
            if not p:
                return self._json({"error": "Not found"}, 404)
            return self._json(p)
        self._json({"error": "Not found"}, 404)

    def do_DELETE(self):
        path = urlparse(self.path).path

        # --- Delete project ---
        m = re.match(r"^/api/projects/([a-f0-9]+)$", path)
        if m:
            ok = delete_project(m.group(1))
            return self._json({"ok": ok})

        # --- Delete file ---
        m = re.match(r"^/api/files/([a-f0-9]+)/(.+)$", path)
        if m:
            from urllib.parse import unquote
            pid, fname = m.group(1), unquote(m.group(2))
            ok = delete_file(pid, fname)
            return self._json({"ok": ok})

        self._json({"error": "Not found"}, 404)

    def log_message(self, format, *args):
        pass


def _parse_multipart(raw: bytes, boundary: str, pid: str) -> list:
    """Minimal multipart/form-data parser — extracts files and saves them."""
    uploaded = []
    sep = ("--" + boundary).encode()
    parts = raw.split(sep)
    for part in parts[1:]:
        if part.strip() in (b"", b"--", b"--\r\n"):
            continue
        # Split headers from body
        if b"\r\n\r\n" in part:
            headers_raw, body = part.split(b"\r\n\r\n", 1)
        elif b"\n\n" in part:
            headers_raw, body = part.split(b"\n\n", 1)
        else:
            continue
        # Strip trailing boundary marker
        body = body.rstrip(b"\r\n")
        if body.endswith(b"--"):
            body = body[:-2].rstrip(b"\r\n")
        headers_text = headers_raw.decode("utf-8", errors="replace")
        # Extract filename
        fn_match = re.search(r'filename="([^"]+)"', headers_text)
        if not fn_match:
            continue
        filename = fn_match.group(1)
        saved = save_file(pid, filename, body)
        uploaded.append(saved)
    return uploaded


def main():
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"\n  Migration Dashboard: http://localhost:{PORT}")
    print(f"  Chat: Amazon Nova Pro ({'available' if HAS_BOTO3 else 'UNAVAILABLE'})")
    print(f"  Press Ctrl+C to stop\n")
    server.serve_forever()

if __name__ == "__main__":
    main()
