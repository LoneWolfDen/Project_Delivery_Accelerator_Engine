"""NFR Gate Matrix — maps source NFRs to blocked stories in downstream epics."""

GATES = [
  # Phase 1 Foundation gates → Phase 2 Core Business
  {
    "gate_id": "G-101-01",
    "source_epic": "E-101",
    "source_app": "APP-010",
    "nfr": "MDM API response < 200ms p95",
    "nfr_category": "Performance",
    "gate_type": "story_start",
    "validation": "Load test report showing p95 < 200ms under 2x load",
    "blocks": [
      {"epic": "E-201", "story": "Migrate 12 E-Commerce microservices to ECS", "reason": "E-Commerce calls MDM for product/customer data — latency directly impacts page load"},
      {"epic": "E-202", "story": "Migrate Node.js microservices to EKS", "reason": "Loyalty reads master customer data — slow MDM = incorrect points calculation"},
      {"epic": "E-204", "story": "Migrate Trade Promo Spring Boot services to ECS", "reason": "Trade Promo validates promotions against MDM product catalogue"}
    ]
  },
  {
    "gate_id": "G-101-02",
    "source_epic": "E-101",
    "source_app": "APP-010",
    "nfr": "Zero data loss during MDM migration",
    "nfr_category": "Data Integrity",
    "gate_type": "epic_exit",
    "validation": "Row count + checksum match source vs target; signed off by Data Governance",
    "blocks": [
      {"epic": "E-104", "story": "End-to-end integration test execution", "reason": "Cannot validate integrations if master data is incomplete or corrupted"},
      {"epic": "E-201", "story": "Integrate OAuth 2.0 with Cognito", "reason": "User records in MDM must be complete before auth migration"}
    ]
  },
  {
    "gate_id": "G-101-03",
    "source_epic": "E-101",
    "source_app": "APP-010",
    "nfr": "Kafka topics replicated to MSK with zero message loss",
    "nfr_category": "Data Integrity",
    "gate_type": "story_start",
    "validation": "Event count reconciliation: source Kafka vs MSK over 24h period",
    "blocks": [
      {"epic": "E-102", "story": "Spark jobs migration to EMR", "reason": "CDP Spark jobs consume MDM events — must be on MSK first"},
      {"epic": "E-201", "story": "Migrate Redis sessions to ElastiCache", "reason": "Session invalidation events flow through Kafka — must be reliable"}
    ]
  },
  {
    "gate_id": "G-102-01",
    "source_epic": "E-102",
    "source_app": "APP-007",
    "nfr": "CDP event processing latency < 500ms p99",
    "nfr_category": "Performance",
    "gate_type": "story_start",
    "validation": "End-to-end latency monitoring showing p99 < 500ms for 7 consecutive days",
    "blocks": [
      {"epic": "E-202", "story": "Replace RabbitMQ with Amazon MQ", "reason": "Loyalty consumes CDP events — must meet latency before rewiring message broker"},
      {"epic": "E-205", "story": "Spark job optimization for EMR", "reason": "Analytics Spark jobs depend on CDP event stream timing"}
    ]
  },
  {
    "gate_id": "G-102-02",
    "source_epic": "E-102",
    "source_app": "APP-007",
    "nfr": "Handle 10x event volume spike without degradation",
    "nfr_category": "Scalability",
    "gate_type": "story_done",
    "validation": "Load test with 10x synthetic traffic — no errors, latency within SLA",
    "blocks": [
      {"epic": "E-206", "story": "Black Friday load simulation (5x)", "reason": "Cannot validate 5x E-Commerce load if CDP can't handle 10x events"}
    ]
  },
  {
    "gate_id": "G-104-01",
    "source_epic": "E-104",
    "source_app": "APP-010",
    "nfr": "DR drill successful — RTO < 30min achieved",
    "nfr_category": "RPO/RTO",
    "gate_type": "epic_exit",
    "validation": "DR drill report showing full recovery in < 30min; signed off by CTO",
    "blocks": [
      {"epic": "E-201", "story": "Configure auto-scaling to handle 5x peak", "reason": "Cannot deploy revenue-critical E-Commerce without proven DR capability"},
      {"epic": "E-202", "story": "Migrate Node.js microservices to EKS", "reason": "Loyalty is Tier 1 — requires DR proven before production migration"},
      {"epic": "E-203", "story": "Python/R forecasting models to EMR", "reason": "Demand Planning is Critical — DR must be validated first"}
    ]
  },
  # Phase 2 Core Business gates → Phase 3 Dependent
  {
    "gate_id": "G-201-01",
    "source_epic": "E-201",
    "source_app": "APP-001",
    "nfr": "PCI-DSS compliance validated",
    "nfr_category": "Security",
    "gate_type": "story_done",
    "validation": "QSA pre-assessment clean; penetration test passed; WAF rules validated",
    "blocks": [
      {"epic": "E-304", "story": "Scala/Python pricing engine to EKS", "reason": "Pricing feeds into checkout — must be PCI-compliant environment"},
      {"epic": "E-305", "story": "Node.js Procurement to ECS", "reason": "Procurement handles supplier payments — PCI environment required"}
    ]
  },
  {
    "gate_id": "G-201-02",
    "source_epic": "E-201",
    "source_app": "APP-001",
    "nfr": "Auto-scaling to 5x validated — zero 5xx errors",
    "nfr_category": "Scalability",
    "gate_type": "epic_exit",
    "validation": "2-hour sustained load test at 5x with zero 5xx; auto-scaling triggered and recovered",
    "blocks": [
      {"epic": "E-305", "story": "FastAPI Store Ops to ECS", "reason": "Store Ops dashboard depends on E-Commerce APIs — must handle peak"},
      {"epic": "E-304", "story": "Full catalogue repricing optimization", "reason": "Repricing triggers E-Commerce price updates — must handle burst"}
    ]
  },
  {
    "gate_id": "G-205-01",
    "source_epic": "E-205",
    "source_app": "APP-008",
    "nfr": "Data freshness < 1 hour from source update",
    "nfr_category": "Data Freshness",
    "gate_type": "story_start",
    "validation": "End-to-end data latency monitoring showing < 1h for 7 days",
    "blocks": [
      {"epic": "E-302", "story": "Spring Batch to AWS Batch migration", "reason": "FP&A batch jobs consume analytics data — must be fresh"},
      {"epic": "E-304", "story": "ML models to SageMaker deployment", "reason": "Pricing ML models train on analytics data — stale data = bad prices"}
    ]
  },
  {
    "gate_id": "G-206-01",
    "source_epic": "E-206",
    "source_app": "ALL",
    "nfr": "All Phase 2 integration tests green",
    "nfr_category": "Availability",
    "gate_type": "epic_exit",
    "validation": "Full regression suite green; incident drill successful; runbooks approved",
    "blocks": [
      {"epic": "E-301", "story": ".NET 6 services to ECS", "reason": "PLM integrates with E-Commerce and MDM — all must be stable"},
      {"epic": "E-302", "story": "Informatica to Glue ETL conversion", "reason": "FP&A pulls from Trade Promo and Analytics — must be validated"},
      {"epic": "E-303", "story": "Python/R optimization models migration", "reason": "Inventory depends on Demand Planning output — must be stable"}
    ]
  },
  # Phase 3 Dependent gates → Phase 4 Legacy
  {
    "gate_id": "G-301-01",
    "source_epic": "E-301",
    "source_app": "APP-006",
    "nfr": "SOAP→REST adapters built and validated for MES",
    "nfr_category": "Compatibility",
    "gate_type": "story_done",
    "validation": "Adapter load test passing; MES can call PLM via REST; response < 1s",
    "blocks": [
      {"epic": "E-403", "story": "Replace COM+/DCOM interfaces with REST/gRPC", "reason": "MES COM+ replacement depends on PLM REST adapters being available"},
      {"epic": "E-403", "story": "Containerise MES for ECS deployment", "reason": "Cannot containerise until all external interfaces are REST/gRPC"}
    ]
  },
  {
    "gate_id": "G-303-01",
    "source_epic": "E-303",
    "source_app": "APP-012",
    "nfr": "Optimization accuracy within ±3% of on-prem",
    "nfr_category": "Accuracy",
    "gate_type": "story_done",
    "validation": "A/B comparison report: AWS vs on-prem results within ±3%",
    "blocks": [
      {"epic": "E-401", "story": "Replace IBM MQ with SQS/SNS", "reason": "WMS receives inventory optimization results via MQ — must be accurate before rewiring"},
      {"epic": "E-401", "story": "Implement EDI gateway on AWS Transfer Family", "reason": "EDI orders depend on accurate inventory levels"}
    ]
  },
  {
    "gate_id": "G-306-01",
    "source_epic": "E-306",
    "source_app": "ALL",
    "nfr": "SOAP→REST adapters validated for all Phase 4 consumers",
    "nfr_category": "Compatibility",
    "gate_type": "epic_exit",
    "validation": "All legacy adapters load tested; Phase 4 apps can consume via REST",
    "blocks": [
      {"epic": "E-401", "story": "Migrate Java 8 codebase to Java 17", "reason": "WMS refactoring assumes REST interfaces to PLM/Inventory are available"},
      {"epic": "E-402", "story": "Legacy SOAP/FTP interface retirement", "reason": "Cannot retire SOAP until REST adapters proven"},
      {"epic": "E-403", "story": "Rewrite VB.NET components in C#/.NET 8", "reason": "MES rewrite assumes all dependencies are on REST/gRPC"}
    ]
  },
  {
    "gate_id": "G-302-01",
    "source_epic": "E-302",
    "source_app": "APP-011",
    "nfr": "SOX compliance validated for financial reporting",
    "nfr_category": "Compliance",
    "gate_type": "story_done",
    "validation": "SOX audit trail complete; CloudTrail integration verified; access controls reviewed",
    "blocks": [
      {"epic": "E-404", "story": "Extract data from ASP.NET 4.8 for SaaS migration", "reason": "HR payroll integrates with FP&A — SOX compliance must be proven before touching payroll data"}
    ]
  },
]
