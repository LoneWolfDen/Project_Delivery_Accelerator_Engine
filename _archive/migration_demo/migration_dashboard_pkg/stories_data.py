"""Stories with t-shirt sizing based on AWS migration learnings.

T-shirt sizes (AWS MAP experience):
  XS (1-2d): Config/parameter change, DNS switch, simple lift-and-shift
  S  (3-5d): Standard managed service migration, minor code change
  M  (5-10d): Moderate refactoring, schema adaptation, integration rewiring
  L  (10-20d): Major refactoring, protocol replacement, vendor coordination
  XL (20+d): Full rewrite, platform change, multi-partner coordination
"""

STORIES = {
  "E-001": {
    "Cloud Solutions Architect": [
      {"story": "Design multi-account structure with OU hierarchy", "size": "M", "ac": ["4+ accounts created (shared-services, dev, staging, prod)", "OU structure documented and approved", "SCPs applied to prevent drift"]},
      {"story": "Design VPC topology with Transit Gateway for cross-account connectivity", "size": "M", "ac": ["VPC CIDR ranges non-overlapping", "Transit Gateway routing validated", "Network diagram approved by security"]},
      {"story": "Establish Direct Connect / VPN hybrid connectivity", "size": "L", "ac": ["Latency < 10ms on-prem to AWS", "Failover tested (VPN backup for DX)", "Bandwidth sufficient for migration traffic"]},
    ],
    "DevOps / Platform Engineer": [
      {"story": "Provision all accounts via Terraform/CDK with state management", "size": "M", "ac": ["All accounts provisioned via IaC", "No manual console changes", "State files in S3 with DynamoDB locking"]},
      {"story": "Set up CI/CD pipeline templates for all deployment patterns", "size": "M", "ac": ["Pipeline deploys to dev in < 10 min", "Automated testing gate before promotion", "Rollback capability demonstrated"]},
    ],
    "Network Engineer": [
      {"story": "Configure hybrid DNS resolution (Route 53 Resolver)", "size": "S", "ac": ["Route 53 resolver rules configured", "On-prem DNS forwarding validated", "Split-horizon DNS working"]},
      {"story": "Validate network throughput for migration data transfer", "size": "S", "ac": ["Throughput > 1Gbps sustained", "No packet loss under load", "MTU configured correctly for DX"]},
    ],
    "Security Engineer": [
      {"story": "Establish encryption-at-rest policies with KMS", "size": "S", "ac": ["KMS keys created per account/service", "Default EBS/S3 encryption enabled", "TLS 1.2+ enforced on all endpoints"]},
      {"story": "Configure detective controls (GuardDuty, Security Hub, CloudTrail)", "size": "S", "ac": ["GuardDuty enabled all regions", "Security Hub aggregating findings", "CloudTrail to centralised S3"]},
    ],
  },
  "E-002": {
    "Change Manager / Training Lead": [
      {"story": "Develop and deliver AWS fundamentals training for all teams", "size": "L", "ac": ["All team members complete training", "Hands-on labs completed", "Assessment scores > 80%"]},
      {"story": "Establish Cloud CoE charter and operating model", "size": "M", "ac": ["Charter signed by leadership", "Roles and responsibilities defined", "Escalation paths documented"]},
    ],
    "Migration Programme Manager": [
      {"story": "Define governance model and reporting cadence", "size": "S", "ac": ["Weekly SteerCo format agreed", "RAID log established", "Dashboard reporting automated"]},
    ],
    "Scrum Master / Delivery Lead": [
      {"story": "Set up delivery tooling and sprint cadence", "size": "S", "ac": ["JIRA project configured", "Sprint cadence agreed (2-week)", "Ceremonies scheduled"]},
    ],
  },
  "E-003": {
    "DevOps / Platform Engineer": [
      {"story": "Set up DMS replication instances and test connectivity", "size": "M", "ac": ["DMS instances provisioned in each AZ", "Source/target endpoints validated", "Replication latency < 1s"]},
      {"story": "Build reusable IaC modules for compute, DB, and networking", "size": "L", "ac": ["Modules for ECS, RDS, ElastiCache, MSK", "Parameterised for all environments", "Tested in dev account"]},
    ],
    "Database Migration Specialist": [
      {"story": "Configure and test DMS for each database engine", "size": "M", "ac": ["Oracle, PostgreSQL, SQL Server, MySQL, MongoDB tested", "Full load + CDC validated", "Error handling documented"]},
      {"story": "Build migration runbooks with rollback procedures", "size": "S", "ac": ["Runbook per DB engine", "Rollback tested", "Timing estimates validated"]},
    ],
    "QA / Test Automation Engineer": [
      {"story": "Build data validation framework for migration verification", "size": "M", "ac": ["Row count comparison automated", "Checksum validation scripts", "Sample data verification tool"]},
    ],
  },
  "E-004": {
    "Data Engineer / Big Data Specialist": [
      {"story": "Catalogue all data stores in AWS Glue Data Catalog", "size": "M", "ac": ["All 14 data stores catalogued", "Schema metadata captured", "Lineage documented"]},
    ],
    "Security Engineer": [
      {"story": "Map PII/sensitive data and define retention policies", "size": "M", "ac": ["PII fields identified across all DBs", "Retention policies per data class", "AWS Config rules enforcing policies"]},
    ],
    "Business Analyst": [
      {"story": "Document data ownership and business data flows", "size": "M", "ac": ["Owner assigned per data store", "Data flow diagrams approved", "Retention sign-off from legal"]},
    ],
  },
  "E-101": {
    "Java/Spring Boot Developer": [
      {"story": "Containerise MDM Spring Boot services for ECS", "size": "M", "ac": ["Docker images in ECR", "Health checks passing", "Start time < 30s", "CPU/memory limits set"]},
      {"story": "Migrate Kafka producers/consumers to MSK", "size": "L", "ac": ["All topics on MSK", "Consumer lag < 100ms", "No message loss during switchover", "DLQ configured"]},
      {"story": "Refactor Oracle-specific SQL for RDS PostgreSQL compatibility", "size": "L", "ac": ["All stored procedures converted", "Performance within 10% of baseline", "No Oracle-specific syntax remaining"]},
    ],
    "Database Migration Specialist": [
      {"story": "Migrate Oracle 19c to RDS via DMS (full load + CDC)", "size": "XL", "ac": ["Zero data loss", "Row counts match", "Checksums validated", "Replication lag < 5s at cutover"]},
      {"story": "Migrate MongoDB to DocumentDB", "size": "L", "ac": ["All collections migrated", "Indexes recreated", "Query performance within 15%", "Connection strings updated"]},
    ],
    "Data Engineer / Big Data Specialist": [
      {"story": "Migrate Kafka topics and consumer groups to MSK", "size": "M", "ac": ["Topics with correct partitioning", "Retention policies matched", "Consumer groups migrated", "Monitoring live"]},
      {"story": "Implement automated data quality checks post-migration", "size": "M", "ac": ["DQ score > 98%", "No nulls in required fields", "Referential integrity maintained"]},
    ],
    "DevOps / Platform Engineer": [
      {"story": "Provision ECS cluster with auto-scaling and Multi-AZ", "size": "M", "ac": ["Auto-scale 2-10 tasks", "CPU tracking at 70%", "Multi-AZ confirmed", "Rolling deployment"]},
      {"story": "Set up monitoring, alerting, and dashboards", "size": "S", "ac": ["Alarms for p95 > 200ms", "Error rate > 1% alarm", "PagerDuty integration", "Key metrics dashboard"]},
    ],
    "QA / Test Automation Engineer": [
      {"story": "Validate data integrity (row counts, checksums, spot checks)", "size": "M", "ac": ["100% table row count match", "Checksum validation", "1000 record spot-check", "No corruption"]},
      {"story": "Run performance tests to validate SLAs on AWS", "size": "M", "ac": ["API < 200ms p95 under load", "Throughput matches baseline", "No errors at 2x load", "Results signed off"]},
    ],
  },
  "E-201": {
    "Java/Spring Boot Developer": [
      {"story": "Migrate 12 E-Commerce microservices to ECS", "size": "XL", "ac": ["All services containerised", "Health checks passing", "Service discovery configured", "Graceful shutdown"]},
      {"story": "Migrate Redis sessions to ElastiCache", "size": "M", "ac": ["Session data migrated", "TTL maintained", "Failover tested", "No drops during deploy"]},
      {"story": "Integrate OAuth 2.0 with Cognito", "size": "M", "ac": ["All OAuth flows working", "Token refresh working", "Existing users can log in", "MFA functional"]},
    ],
    "Node.js / React Developer": [
      {"story": "Deploy React SPA to CloudFront with cache strategy", "size": "S", "ac": ["Page load < 2s", "Cache hit > 80%", "Asset versioning working", "404 handling"]},
      {"story": "Configure SSR for SEO-critical pages", "size": "M", "ac": ["SSR renders < 500ms", "Meta tags in source", "No indexing issues"]},
    ],
    "Security Engineer": [
      {"story": "Achieve PCI-DSS compliance on AWS", "size": "XL", "ac": ["WAF blocking OWASP Top 10", "Cardholder data AES-256 encrypted", "Network segmentation validated", "Pen test passed", "QSA pre-assessment clean"]},
      {"story": "Configure Shield Advanced for DDoS protection", "size": "S", "ac": ["Shield on ALB + CloudFront", "DRT contactable", "Rate limiting configured"]},
    ],
    "Database Migration Specialist": [
      {"story": "Migrate PostgreSQL 14 to RDS with read replicas", "size": "L", "ac": ["Zero data loss", "Read replicas configured", "PgBouncer working", "Performance within 5%"]},
    ],
    "DevOps / Platform Engineer": [
      {"story": "Configure auto-scaling to handle 5x peak (Black Friday)", "size": "L", "ac": ["ECS scales to 5x in 3 min", "RDS replicas handle reads", "ElastiCache scales", "No 5xx at 5x"]},
      {"story": "Set up blue-green deployment for zero-downtime releases", "size": "M", "ac": ["Switch < 60s", "Rollback < 60s", "Health check gates", "DB migrations backward-compatible"]},
    ],
    "QA / Test Automation Engineer": [
      {"story": "Run Black Friday load simulation at 5x traffic", "size": "L", "ac": ["5x sustained 2 hours", "p95 < 2s throughout", "Zero 5xx", "Auto-scaling triggered", "Cost at peak documented"]},
    ],
  },
  "E-202": {
    "Node.js / React Developer": [
      {"story": "Migrate Node.js microservices to EKS", "size": "L", "ac": ["All services on EKS", "HPA configured", "Health checks passing", "Rolling updates working"]},
      {"story": "Migrate MongoDB queries to DocumentDB syntax", "size": "M", "ac": ["All queries compatible", "Aggregation pipelines working", "Performance within 15%"]},
      {"story": "Replace RabbitMQ with Amazon MQ", "size": "M", "ac": ["All queues migrated", "Message patterns preserved", "No message loss", "Monitoring configured"]},
    ],
    "Database Migration Specialist": [
      {"story": "Migrate MongoDB to DocumentDB with index optimization", "size": "L", "ac": ["All collections migrated", "Indexes optimized", "Consistency validated", "Replica set configured"]},
    ],
    "QA / Test Automation Engineer": [
      {"story": "Validate points calculation accuracy (must be 100%)", "size": "M", "ac": ["10,000 transaction sample validated", "Edge cases tested", "Reconciliation job passing", "No rounding errors"]},
    ],
  },
  "E-401": {
    "Java/Spring Boot Developer": [
      {"story": "Migrate Java 8 codebase to Java 17", "size": "XL", "ac": ["All deprecated APIs replaced", "Unit tests passing", "No reflection warnings", "Performance equal or better"]},
      {"story": "Replace WebLogic with Spring Boot 3", "size": "XL", "ac": ["All EJBs → Spring services", "JNDI → Spring config", "Transaction management migrated", "Startup < 30s"]},
      {"story": "Replace IBM MQ with SQS/SNS", "size": "L", "ac": ["Queue patterns → SQS", "Pub/sub → SNS", "Message ordering preserved", "DLQ configured", "No loss at cutover"]},
      {"story": "Implement EDI gateway on AWS Transfer Family", "size": "L", "ac": ["All EDI doc types supported", "SFTP endpoints live", "15 partners tested", "Validation rules migrated"]},
    ],
    "Database Migration Specialist": [
      {"story": "Upgrade Oracle 12c → 19c → RDS with zero-downtime cutover", "size": "XL", "ac": ["12c→19c upgrade successful", "19c→RDS via DMS complete", "Zero data loss", "Performance within 10%", "Cutover < 4h"]},
    ],
    "Vendor / Integration Specialist": [
      {"story": "Validate all 15 EDI partners end-to-end post-migration", "size": "XL", "ac": ["All partners tested both directions", "Document exchange successful", "SLAs updated", "Rollback plan per partner"]},
      {"story": "Configure AWS Transfer Family for SFTP/FTP partners", "size": "M", "ac": ["SFTP endpoints provisioned", "SSH keys configured", "IP whitelisting applied", "Monitoring live"]},
    ],
    "DevOps / Platform Engineer": [
      {"story": "Set up blue-green deployment for zero-downtime WMS cutover", "size": "L", "ac": ["Blue-green infra provisioned", "DB sync between environments", "DNS switch < 60s", "Rollback tested"]},
    ],
    "QA / Test Automation Engineer": [
      {"story": "Validate EDI end-to-end with all 15 trading partners", "size": "XL", "ac": ["All partners exchange test docs", "Validation passes", "Response times within SLA", "Error handling tested"]},
      {"story": "Perform cutover rehearsal within 4h maintenance window", "size": "L", "ac": ["Rehearsal completes in 4h", "All systems functional", "Rollback executed", "Timing documented"]},
    ],
  },
  "E-403": {
    ".NET / C# Developer": [
      {"story": "Rewrite VB.NET components in C#/.NET 8", "size": "XL", "ac": ["All VB.NET modules rewritten", "Unit test coverage > 80%", "Functionality parity", "Performance equal or better"]},
      {"story": "Replace COM+/DCOM interfaces with REST/gRPC", "size": "XL", "ac": ["All interfaces mapped", "Contract tests passing", "Backward compat during transition", "No shop floor disruption"]},
      {"story": "Replace MSMQ with SQS", "size": "L", "ac": ["All queue patterns migrated", "Ordering preserved", "Poison message handling", "Throughput matches baseline"]},
      {"story": "Containerise MES for ECS deployment", "size": "L", "ac": ["Docker images built", "Health checks configured", "Shop floor latency < 1s", "Graceful shutdown for in-flight txns"]},
    ],
    "Database Migration Specialist": [
      {"story": "Upgrade SQL Server 2016 → 2019 → RDS", "size": "L", "ac": ["Upgrade path validated", "Stored procedures compatible", "Performance within 10%", "Backup/restore tested"]},
    ],
    "DevOps / Platform Engineer": [
      {"story": "Configure SQS with latency monitoring for shop floor SLA", "size": "M", "ac": ["Queues provisioned", "Alarms for > 500ms", "Auto-scale on queue depth", "DLQ alerting"]},
    ],
    "QA / Test Automation Engineer": [
      {"story": "Validate shop floor transactions under production load", "size": "L", "ac": ["Response < 1s at peak", "No data loss under stress", "AZ failover tested", "24h soak test passed"]},
    ],
  },
  "E-404": {
    ".NET / C# Developer": [
      {"story": "Extract data from ASP.NET 4.8 for SaaS migration", "size": "L", "ac": ["All employee data exported", "Data format compatible with target SaaS", "Historical records preserved"]},
      {"story": "Migrate LDAP authentication to Cognito/AD", "size": "M", "ac": ["All users migrated", "Groups/roles mapped", "SSO working", "Legacy LDAP decommissioned"]},
    ],
    "Vendor / Integration Specialist": [
      {"story": "Evaluate and select HR SaaS (Workday/SuccessFactors)", "size": "L", "ac": ["RFP completed", "Vendor selected", "Contract signed", "Implementation timeline agreed"]},
      {"story": "Coordinate SaaS implementation and data migration", "size": "XL", "ac": ["All employee records migrated", "Integrations with FP&A working", "UAT passed", "Go-live successful"]},
    ],
    "Security Engineer": [
      {"story": "Validate GDPR compliance for employee PII migration", "size": "M", "ac": ["DPA signed with SaaS vendor", "PII encrypted in transit", "Right to erasure implemented", "Audit trail configured"]},
    ],
    "QA / Test Automation Engineer": [
      {"story": "Validate 100% employee record accuracy post-migration", "size": "M", "ac": ["Record-by-record comparison", "No missing fields", "Historical data accessible", "Payroll integration tested"]},
    ],
  },
}
