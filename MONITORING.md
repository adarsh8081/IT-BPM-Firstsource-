# Monitoring & Observability Guide

This document provides comprehensive information about the monitoring and observability capabilities of the Provider Data Validation & Directory Management application.

## Overview

The monitoring system provides real-time visibility into:
- **Performance Metrics**: Validation throughput, latency, and efficiency
- **System Health**: Worker status, queue lengths, and resource utilization
- **Data Quality**: Confidence scores, error rates, and compliance metrics
- **Security**: Access patterns, violations, and threat detection
- **Business KPIs**: Provider processing rates and quality benchmarks

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Application   │───▶│   Prometheus    │───▶│    Grafana      │
│                 │    │   (Metrics)     │    │ (Visualization) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Alertmanager   │◀───│   Alert Rules   │    │   Dashboards    │
│ (Notifications) │    │   (Thresholds)  │    │  (KPIs & Charts)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Key Metrics Tracked

### 1. Validation Performance
- **Validations per Second**: Current validation throughput
- **Average Validation Latency**: 50th, 95th, and 99th percentiles
- **Validation Success Rate**: Percentage of successful validations
- **Worker Utilization**: Active workers and their efficiency

### 2. Data Quality Metrics
- **High Confidence Percentage**: Providers with confidence > 0.8
- **Overall Confidence Distribution**: Confidence score histograms
- **Data Quality Score**: Aggregate quality assessment (0-1)
- **Compliance Violations**: Regulatory compliance tracking

### 3. Queue Management
- **Manual Review Queue Length**: Providers awaiting review
- **Queue Processing Time**: Time to process queue items
- **Queue Backlog Trends**: Historical queue depth analysis
- **Review Assignment Efficiency**: Reviewer workload distribution

### 4. System Health
- **Active Workers**: Number of running validation workers
- **Failed Jobs**: Job failure rate and error types
- **Database Connections**: Connection pool status
- **Memory Usage**: Application memory consumption
- **CPU Utilization**: System resource usage

### 5. External Service Integration
- **API Call Rates**: External service request frequency
- **API Response Times**: External service performance
- **API Error Rates**: External service reliability
- **Rate Limiting**: API quota usage and limits

### 6. Security Metrics
- **Security Events**: Authentication and authorization events
- **PII Access**: Sensitive data access tracking
- **Failed Login Attempts**: Authentication failures
- **Permission Violations**: Authorization failures

## Monitoring Endpoints

### Prometheus Metrics
```
GET /api/metrics/prometheus
```
Returns metrics in Prometheus format for scraping.

### JSON Metrics
```
GET /api/metrics/json
```
Returns metrics in JSON format for custom integrations.

### Health Check
```
GET /api/metrics/health
```
Returns system health status and key metrics.

### Dashboard Metrics
```
GET /api/metrics/dashboard
```
Returns formatted metrics for dashboard display.

### Active Alerts
```
GET /api/metrics/alerts
```
Returns currently active alerts and their status.

## Alert Rules

### Critical Alerts
- **No Active Workers**: No validation workers running
- **Critical Queue Length**: Manual review queue > 100 providers
- **High Failure Rate**: Job failure rate > 10%
- **Security Events**: Any security violations detected
- **Database Issues**: No active database connections

### Warning Alerts
- **High Queue Length**: Manual review queue > 50 providers
- **Low Validation Rate**: < 0.1 validations per second
- **Low Confidence Rate**: High confidence < 70%
- **High Latency**: 95th percentile > 30 seconds
- **External API Errors**: Error rate > 5%

### Info Alerts
- **System Maintenance**: Scheduled maintenance windows
- **Capacity Warnings**: Approaching resource limits
- **Performance Degradation**: Gradual performance decline

## Notification Channels

### Slack Integration
- **Critical Alerts**: #critical-alerts channel
- **Warning Alerts**: #alerts channel
- **Security Alerts**: #security channel
- **Info Alerts**: #monitoring channel

### Email Notifications
- **Critical Alerts**: Immediate email to on-call team
- **Warning Alerts**: Email to operations team
- **Security Alerts**: Email to security team
- **Daily Reports**: Summary of system performance

### Webhook Integration
- **Custom Integrations**: PagerDuty, OpsGenie, etc.
- **Ticketing Systems**: Jira, ServiceNow integration
- **Chat Platforms**: Microsoft Teams, Discord support

## Grafana Dashboards

### 1. Provider Validation System Dashboard
**Primary dashboard with key operational metrics**

**Panels:**
- Validation Rate (validations/sec)
- Manual Review Queue Length
- Validation Latency (percentiles)
- High Confidence Percentage
- Active Validation Workers
- Job Failure Rate
- External API Performance
- Data Quality Score
- Security Events

### 2. System Health Dashboard
**Infrastructure and system monitoring**

**Panels:**
- CPU Usage
- Memory Usage
- Disk Space
- Network I/O
- Database Performance
- Cache Hit Rates
- Container Metrics

### 3. Business Intelligence Dashboard
**Business KPIs and trends**

**Panels:**
- Daily Validation Volume
- Provider Processing Trends
- Quality Score Trends
- Review Queue Efficiency
- Cost per Validation
- SLA Compliance

### 4. Security Dashboard
**Security monitoring and compliance**

**Panels:**
- Security Event Timeline
- PII Access Patterns
- Authentication Failures
- Permission Violations
- Compliance Status
- Audit Trail

## Setup and Configuration

### 1. Quick Start
```bash
# Clone the repository
git clone <repository-url>
cd provider-validation

# Setup monitoring stack
./scripts/setup_monitoring.sh

# Configure environment
cd monitoring
cp .env.example .env
# Edit .env with your configuration

# Start monitoring
./start-monitoring.sh
```

### 2. Access URLs
- **Grafana**: http://localhost:3001 (admin/admin123)
- **Prometheus**: http://localhost:9090
- **Alertmanager**: http://localhost:9093
- **Application**: http://localhost:8000

### 3. Configuration Files
- **Prometheus**: `monitoring/prometheus/prometheus.yml`
- **Alertmanager**: `monitoring/alertmanager/alertmanager.yml`
- **Grafana**: `monitoring/grafana/provisioning/`
- **Environment**: `monitoring/.env`

## Customization

### Adding New Metrics

1. **Define Metric in Code**:
```python
from backend.monitoring.metrics import get_metrics_collector

# Create custom metric
custom_metric = Counter(
    'custom_metric_total',
    'Description of custom metric',
    ['label1', 'label2']
)

# Record metric
custom_metric.labels(label1='value1', label2='value2').inc()
```

2. **Update Dashboard**:
```json
{
  "title": "Custom Metric Panel",
  "targets": [
    {
      "expr": "rate(custom_metric_total[5m])",
      "legendFormat": "{{label1}} - {{label2}}"
    }
  ]
}
```

3. **Add Alert Rule**:
```yaml
- alert: CustomMetricAlert
  expr: custom_metric_total > 100
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Custom metric threshold exceeded"
```

### Creating Custom Dashboards

1. **Create Dashboard JSON**:
```bash
# Export existing dashboard
curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:3001/api/dashboards/uid/provider-validation > dashboard.json

# Modify and import
curl -X POST -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d @dashboard.json \
  http://localhost:3001/api/dashboards/db
```

2. **Add to Provisioning**:
```yaml
# monitoring/grafana/provisioning/dashboards/dashboards.yml
providers:
  - name: 'custom'
    type: file
    path: /var/lib/grafana/dashboards/custom
```

### Custom Alert Rules

1. **Create Alert Rule File**:
```yaml
# monitoring/prometheus/rules/custom-alerts.yml
groups:
  - name: custom-alerts
    rules:
      - alert: CustomAlert
        expr: custom_metric > threshold
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Custom alert triggered"
```

2. **Update Prometheus Configuration**:
```yaml
# monitoring/prometheus/prometheus.yml
rule_files:
  - "rules/*.yml"
  - "rules/custom-alerts.yml"
```

## Performance Optimization

### Query Optimization
- Use recording rules for complex calculations
- Implement proper metric labeling
- Optimize scrape intervals
- Use appropriate aggregation functions

### Resource Management
- Monitor Prometheus storage usage
- Implement data retention policies
- Use efficient metric cardinality
- Optimize Grafana dashboard queries

### Scaling Considerations
- Horizontal scaling with Prometheus federation
- Load balancing for high availability
- Caching strategies for frequently accessed data
- Resource allocation for monitoring components

## Troubleshooting

### Common Issues

1. **No Metrics Showing**:
   - Check Prometheus targets status
   - Verify application metrics endpoint
   - Check network connectivity
   - Review Prometheus configuration

2. **Alerts Not Firing**:
   - Verify alert rule syntax
   - Check Alertmanager configuration
   - Test alert conditions manually
   - Review notification channels

3. **High Resource Usage**:
   - Optimize query performance
   - Reduce metric cardinality
   - Implement data retention
   - Scale monitoring infrastructure

4. **Dashboard Loading Issues**:
   - Check Grafana logs
   - Verify datasource connectivity
   - Optimize dashboard queries
   - Review browser performance

### Debug Commands

```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Test alert rule
curl -X POST http://localhost:9090/api/v1/admin/tsdb/snapshot

# Check Grafana health
curl http://localhost:3001/api/health

# View application metrics
curl http://localhost:8000/api/metrics/prometheus

# Test alert endpoint
curl -X POST http://localhost:8000/api/metrics/alerts/test
```

### Log Analysis

```bash
# View monitoring logs
docker-compose -f monitoring/docker-compose.monitoring.yml logs -f

# Filter specific service logs
docker-compose -f monitoring/docker-compose.monitoring.yml logs -f prometheus

# Check application logs
docker-compose logs -f app
```

## Security Considerations

### Access Control
- Implement authentication for all monitoring services
- Use HTTPS in production environments
- Restrict network access to monitoring ports
- Implement role-based access control

### Data Protection
- Encrypt metrics data in transit
- Implement secure credential management
- Regular security updates
- Audit monitoring access logs

### Compliance
- HIPAA compliance for healthcare data
- SOC 2 compliance for security controls
- Regular compliance audits
- Data retention policy enforcement

## Best Practices

### Monitoring Strategy
1. **Define Clear SLIs/SLOs**: Establish service level indicators and objectives
2. **Implement Proper Alerting**: Use alert fatigue prevention strategies
3. **Regular Dashboard Reviews**: Keep dashboards relevant and actionable
4. **Performance Testing**: Test monitoring under load conditions

### Operational Excellence
1. **Runbook Documentation**: Document alert response procedures
2. **Incident Response**: Establish clear escalation procedures
3. **Regular Reviews**: Conduct monitoring effectiveness reviews
4. **Continuous Improvement**: Iterate on monitoring based on learnings

### Team Collaboration
1. **Shared Ownership**: Involve all teams in monitoring setup
2. **Training Programs**: Train teams on monitoring tools and practices
3. **Regular Communication**: Share monitoring insights across teams
4. **Feedback Loops**: Collect and act on monitoring feedback

## Future Enhancements

### Planned Features
- Machine learning-based anomaly detection
- Predictive alerting based on trends
- Advanced correlation analysis
- Integration with external monitoring platforms
- Mobile monitoring dashboards
- Automated remediation capabilities

### Scalability Improvements
- Multi-region monitoring support
- Cloud-native monitoring integration
- Microservices monitoring patterns
- Advanced federation strategies
- Real-time streaming analytics

This monitoring system provides comprehensive observability for the Provider Data Validation application, ensuring reliable operation and enabling data-driven decision making for continuous improvement.
