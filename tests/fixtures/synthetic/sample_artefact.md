# Technical Assessment: Payment Gateway Modernisation

## Executive Summary

The current payment gateway is a .NET Framework 4.6 monolith processing approximately 50,000 transactions daily. It requires modernisation to support PCI-DSS v4.0 requirements effective March 2025 and to enable horizontal scaling for peak periods.

## Current Architecture

- Runtime: .NET Framework 4.6.2 on Windows Server 2019
- Database: SQL Server 2017 Enterprise (single instance, 2TB)
- Message Queue: IBM MQ 9.1
- Authentication: Custom LDAP integration
- Deployment: Manual via RDP + xcopy

## Recommended Target State

- Runtime: .NET 8 on Linux containers (EKS)
- Database: Aurora PostgreSQL (multi-AZ) with read replicas
- Message Queue: Amazon MSK (Kafka managed)
- Authentication: AWS Cognito + OAuth 2.0
- Deployment: ArgoCD GitOps with canary releases

## Migration Approach

### Phase 1: Foundation (Weeks 1-4)
- Set up target infrastructure (IaC with Terraform)
- Implement CI/CD pipeline for new platform
- Deploy monitoring stack (Prometheus + Grafana)

### Phase 2: Strangler Fig (Weeks 5-12)
- Migrate read-only endpoints first
- Implement API gateway routing (old vs new)
- Gradual traffic shift with feature flags

### Phase 3: Core Migration (Weeks 13-20)
- Migrate transaction processing logic
- Database migration with zero-downtime cutover
- IBM MQ to Kafka bridge then full cutover

### Phase 4: Decommission (Weeks 21-24)
- Remove legacy routing
- Decommission old infrastructure
- Final security audit and PCI-DSS recertification

## Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Data loss during DB migration | Critical | Low | Dual-write pattern + reconciliation |
| PCI compliance gap during transition | High | Medium | Maintain both environments certified |
| Performance regression | Medium | Medium | Load testing at each phase gate |
| Team skill gap (.NET to cloud-native) | Medium | High | Training budget + pair programming |

## Resource Requirements

- 2x Senior Cloud Engineers (full-time, 24 weeks)
- 1x Database Migration Specialist (part-time, 12 weeks)
- 1x Security/Compliance Engineer (part-time, 24 weeks)
- 1x Technical Lead (.NET + cloud-native experience)
