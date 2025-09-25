#!/bin/bash

# Monitoring Setup Script for Provider Validation System
# This script sets up the complete monitoring stack with Prometheus, Grafana, and Alertmanager

set -e

echo "🔧 Setting up Provider Validation Monitoring Stack"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
print_status "Checking prerequisites..."

if ! command -v docker >/dev/null 2>&1; then
    print_error "Docker is required but not installed"
    exit 1
fi

if ! command -v docker-compose >/dev/null 2>&1; then
    print_error "Docker Compose is required but not installed"
    exit 1
fi

print_success "Prerequisites check passed"

# Create monitoring directory structure
print_status "Creating monitoring directory structure..."

mkdir -p monitoring/{prometheus,rules,grafana/{dashboards,provisioning},alertmanager,nginx,blackbox}
mkdir -p monitoring/grafana/dashboards/dashboard-screenshots

print_success "Directory structure created"

# Create environment file for monitoring
print_status "Creating environment configuration..."

cat > monitoring/.env << EOF
# Monitoring Environment Configuration

# Slack Configuration
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
SLACK_CHANNEL=#alerts

# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=alerts@yourdomain.com
SMTP_PASSWORD=your-app-password
ALERT_EMAIL_FROM=alerts@yourdomain.com
ALERT_EMAIL_TO=admin@yourdomain.com,oncall@yourdomain.com

# Webhook Configuration
WEBHOOK_URL=https://your-webhook-endpoint.com/alerts
WEBHOOK_USERNAME=webhook-user
WEBHOOK_PASSWORD=webhook-password

# Database Configuration (for exporters)
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_DB=provider_validation

# Redis Configuration
REDIS_PASSWORD=redis-password

# Application Configuration
APP_HOST=app
APP_PORT=8000
EOF

print_success "Environment configuration created"

# Create Grafana provisioning configuration
print_status "Creating Grafana provisioning configuration..."

# Datasource configuration
cat > monitoring/grafana/provisioning/datasources/prometheus.yml << EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
EOF

# Dashboard provisioning
cat > monitoring/grafana/provisioning/dashboards/dashboards.yml << EOF
apiVersion: 1

providers:
  - name: 'default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
EOF

print_success "Grafana provisioning configuration created"

# Create Nginx configuration
print_status "Creating Nginx reverse proxy configuration..."

cat > monitoring/nginx/nginx.conf << EOF
events {
    worker_connections 1024;
}

http {
    upstream prometheus {
        server prometheus:9090;
    }

    upstream grafana {
        server grafana:3000;
    }

    upstream alertmanager {
        server alertmanager:9093;
    }

    server {
        listen 80;
        server_name localhost;

        location /prometheus/ {
            proxy_pass http://prometheus/;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }

        location /grafana/ {
            proxy_pass http://grafana/;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }

        location /alertmanager/ {
            proxy_pass http://alertmanager/;
            proxy_set_header Host \$host;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto \$scheme;
        }

        location / {
            return 200 'Provider Validation Monitoring Stack\\n\\nAvailable services:\\n- Grafana: http://localhost:8080/grafana/\\n- Prometheus: http://localhost:8080/prometheus/\\n- Alertmanager: http://localhost:8080/alertmanager/\\n';
            add_header Content-Type text/plain;
        }
    }
}
EOF

print_success "Nginx configuration created"

# Create Blackbox exporter configuration
print_status "Creating Blackbox exporter configuration..."

cat > monitoring/blackbox/blackbox.yml << EOF
modules:
  http_2xx:
    prober: http
    timeout: 5s
    http:
      valid_http_versions: ["HTTP/1.1", "HTTP/2.0"]
      valid_status_codes: []
      method: GET
      headers:
        User-Agent: "Blackbox Exporter"
      no_follow_redirects: false
      fail_if_ssl: false
      fail_if_not_ssl: false
      tls_config:
        insecure_skip_verify: false

  http_post_2xx:
    prober: http
    timeout: 5s
    http:
      valid_http_versions: ["HTTP/1.1", "HTTP/2.0"]
      valid_status_codes: []
      method: POST
      headers:
        Content-Type: application/json
      body: '{}'

  tcp_connect:
    prober: tcp
    timeout: 5s

  icmp:
    prober: icmp
    timeout: 5s
    icmp:
      preferred_ip_protocol: "ip4"

  dns_tcp:
    prober: dns
    timeout: 5s
    dns:
      transport_protocol: "tcp"
      preferred_ip_protocol: "ip4"
      query_name: "example.com"

  dns_udp:
    prober: dns
    timeout: 5s
    dns:
      transport_protocol: "udp"
      preferred_ip_protocol: "ip4"
      query_name: "example.com"
EOF

print_success "Blackbox exporter configuration created"

# Create startup script
print_status "Creating monitoring startup script..."

cat > monitoring/start-monitoring.sh << 'EOF'
#!/bin/bash

# Start Monitoring Stack
echo "🚀 Starting Provider Validation Monitoring Stack..."

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Start monitoring services
docker-compose -f docker-compose.monitoring.yml up -d

echo "✅ Monitoring stack started successfully!"
echo ""
echo "📊 Access URLs:"
echo "  Grafana:      http://localhost:3001 (admin/admin123)"
echo "  Prometheus:   http://localhost:9090"
echo "  Alertmanager: http://localhost:9093"
echo "  Nginx Proxy:  http://localhost:8080"
echo ""
echo "🔧 Useful Commands:"
echo "  View logs:    docker-compose -f docker-compose.monitoring.yml logs -f"
echo "  Stop stack:   docker-compose -f docker-compose.monitoring.yml down"
echo "  Restart:      docker-compose -f docker-compose.monitoring.yml restart"
EOF

chmod +x monitoring/start-monitoring.sh

# Create stop script
cat > monitoring/stop-monitoring.sh << 'EOF'
#!/bin/bash

# Stop Monitoring Stack
echo "🛑 Stopping Provider Validation Monitoring Stack..."

docker-compose -f docker-compose.monitoring.yml down

echo "✅ Monitoring stack stopped successfully!"
EOF

chmod +x monitoring/stop-monitoring.sh

# Create test script
cat > monitoring/test-monitoring.sh << 'EOF'
#!/bin/bash

# Test Monitoring Stack
echo "🧪 Testing Provider Validation Monitoring Stack..."

# Test Prometheus
echo "Testing Prometheus..."
if curl -s http://localhost:9090/-/healthy >/dev/null; then
    echo "✅ Prometheus is healthy"
else
    echo "❌ Prometheus is not responding"
fi

# Test Grafana
echo "Testing Grafana..."
if curl -s http://localhost:3001/api/health >/dev/null; then
    echo "✅ Grafana is healthy"
else
    echo "❌ Grafana is not responding"
fi

# Test Alertmanager
echo "Testing Alertmanager..."
if curl -s http://localhost:9093/-/healthy >/dev/null; then
    echo "✅ Alertmanager is healthy"
else
    echo "❌ Alertmanager is not responding"
fi

echo "🧪 Monitoring stack test completed!"
EOF

chmod +x monitoring/test-monitoring.sh

print_success "Monitoring scripts created"

# Create README for monitoring
print_status "Creating monitoring documentation..."

cat > monitoring/README.md << 'EOF'
# Provider Validation Monitoring Stack

This directory contains the complete monitoring stack for the Provider Data Validation & Directory Management system.

## Components

- **Prometheus**: Metrics collection and alerting
- **Grafana**: Visualization and dashboards
- **Alertmanager**: Alert routing and notifications
- **Node Exporter**: System metrics
- **cAdvisor**: Container metrics
- **Redis Exporter**: Redis metrics
- **PostgreSQL Exporter**: Database metrics
- **Blackbox Exporter**: HTTP/HTTPS monitoring

## Quick Start

1. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Start Monitoring Stack**:
   ```bash
   ./start-monitoring.sh
   ```

3. **Access Services**:
   - Grafana: http://localhost:3001 (admin/admin123)
   - Prometheus: http://localhost:9090
   - Alertmanager: http://localhost:9093
   - Nginx Proxy: http://localhost:8080

4. **Test Setup**:
   ```bash
   ./test-monitoring.sh
   ```

## Configuration

### Environment Variables

Edit the `.env` file to configure:
- Slack webhook URLs
- Email SMTP settings
- Database credentials
- Webhook endpoints

### Grafana Dashboards

The system includes pre-configured dashboards:
- Provider Validation System Dashboard
- System Health Overview
- Alert Status Dashboard

### Alert Rules

Alert rules are configured in `prometheus/rules/`:
- High manual review queue
- Low validation rate
- Job failures
- Security events
- System health issues

## Monitoring Endpoints

The application exposes these monitoring endpoints:
- `/api/metrics/prometheus` - Prometheus metrics
- `/api/metrics/json` - JSON metrics
- `/api/metrics/health` - Health check metrics
- `/api/metrics/dashboard` - Dashboard metrics
- `/api/metrics/alerts` - Active alerts

## Troubleshooting

### Common Issues

1. **Services not starting**:
   - Check Docker is running
   - Verify port availability
   - Check logs: `docker-compose logs -f`

2. **No metrics showing**:
   - Verify application is running
   - Check Prometheus targets
   - Verify metrics endpoint accessibility

3. **Alerts not firing**:
   - Check alert rules configuration
   - Verify Alertmanager configuration
   - Test alert conditions manually

### Useful Commands

```bash
# View all logs
docker-compose logs -f

# Restart specific service
docker-compose restart prometheus

# Check service status
docker-compose ps

# Access service shell
docker-compose exec prometheus sh

# Update configuration
docker-compose restart
```

## Customization

### Adding New Metrics

1. Add metrics to `backend/monitoring/metrics.py`
2. Update dashboard configuration
3. Add alert rules if needed

### Creating New Dashboards

1. Create dashboard JSON in `grafana/dashboards/`
2. Update provisioning configuration
3. Restart Grafana

### Adding New Alert Rules

1. Add rules to `prometheus/rules/`
2. Update Alertmanager configuration
3. Restart Prometheus and Alertmanager

## Security Considerations

- Change default passwords
- Use HTTPS in production
- Restrict network access
- Enable authentication
- Regular security updates

## Performance Tuning

- Adjust scrape intervals
- Optimize query performance
- Use recording rules
- Monitor resource usage
- Scale horizontally if needed
EOF

print_success "Monitoring documentation created"

# Create sample environment file
print_status "Creating sample environment configuration..."

cat > monitoring/.env.example << EOF
# Monitoring Environment Configuration Example
# Copy this file to .env and update with your actual values

# Slack Configuration
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
SLACK_CHANNEL=#alerts

# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=alerts@yourdomain.com
SMTP_PASSWORD=your-app-password
ALERT_EMAIL_FROM=alerts@yourdomain.com
ALERT_EMAIL_TO=admin@yourdomain.com

# Webhook Configuration
WEBHOOK_URL=https://your-webhook-endpoint.com/alerts
WEBHOOK_USERNAME=webhook-user
WEBHOOK_PASSWORD=webhook-password

# Database Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_DB=provider_validation

# Redis Configuration
REDIS_PASSWORD=redis-password
EOF

print_success "Sample environment configuration created"

# Final setup instructions
print_status "Setup completed successfully!"
echo ""
echo "🎉 Provider Validation Monitoring Stack Setup Complete!"
echo ""
echo "📋 Next Steps:"
echo "  1. Edit monitoring/.env with your configuration"
echo "  2. Start the monitoring stack: cd monitoring && ./start-monitoring.sh"
echo "  3. Access Grafana at http://localhost:3001 (admin/admin123)"
echo "  4. Import the dashboard from grafana/dashboards/"
echo "  5. Configure Slack/email alerts in .env"
echo ""
echo "📚 Documentation:"
echo "  - Monitoring README: monitoring/README.md"
echo "  - Dashboard screenshots: monitoring/grafana/dashboard-screenshots/"
echo "  - Configuration files: monitoring/*/"
echo ""
echo "🔧 Management Commands:"
echo "  - Start: cd monitoring && ./start-monitoring.sh"
echo "  - Stop: cd monitoring && ./stop-monitoring.sh"
echo "  - Test: cd monitoring && ./test-monitoring.sh"
echo ""
print_success "Monitoring setup completed! 🚀"
