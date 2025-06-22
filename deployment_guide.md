# 🚀 Complete Deployment Guide - News Agent System

## 🎯 **Overview**

This guide covers deploying the News Agent system across different environments, from local development to enterprise production deployments with monitoring, scaling, and security.

---

## 📋 **Deployment Options**

### **1. 🏠 Local Development**
- **Use Case**: Testing, development, personal use
- **Resources**: Minimal (1 CPU, 512MB RAM)
- **Setup Time**: 5 minutes

### **2. 🖥️ Single Server**
- **Use Case**: Small team, proof of concept
- **Resources**: 2 CPU, 2GB RAM, 20GB storage
- **Setup Time**: 15 minutes

### **3. ☁️ Cloud Container**
- **Use Case**: Scalable production deployment
- **Resources**: Auto-scaling, load balancing
- **Setup Time**: 30 minutes

### **4. 🏢 Enterprise Deployment**
- **Use Case**: Large organization, high availability
- **Resources**: Multi-region, monitoring, security
- **Setup Time**: 1-2 hours

---

## 🏠 **Local Development Deployment**

### **Quick Start**
```bash
# 1. Clone/download project files
# 2. Install dependencies
pip install -r requirements.txt

# 3. Run installer
python install_news_agent.py

# 4. Start services
python run_news_agent.py          # CLI interface
python web_dashboard.py           # Web interface
python api_server.py              # API server
```

### **Configuration**
```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

### **Verification**
```bash
# Test the system
python test_news_agent.py

# Check web interface
curl http://localhost:5000

# Check API
curl http://localhost:8000/health
```

---

## 🖥️ **Single Server Deployment**

### **Server Requirements**
- **OS**: Ubuntu 20.04+ / CentOS 8+ / RHEL 8+
- **CPU**: 2 cores minimum
- **RAM**: 2GB minimum, 4GB recommended
- **Storage**: 20GB SSD
- **Network**: Internet access for news scraping

### **Installation Steps**

#### **1. System Preparation**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11
sudo apt install software-properties-common -y
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-pip -y

# Install system dependencies
sudo apt install nginx redis-server postgresql-client git curl -y
```

#### **2. User Setup**
```bash
# Create dedicated user
sudo useradd -m -s /bin/bash newsagent
sudo usermod -aG sudo newsagent

# Switch to user
sudo su - newsagent

# Create application directory
mkdir -p ~/newsagent
cd ~/newsagent
```

#### **3. Application Setup**
```bash
# Download application files
# (Copy all Python files to ~/newsagent/)

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Download NLTK data
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"

# Run installer
python install_news_agent.py
```

#### **4. Configuration**
```bash
# Create production configuration
cp .env.example .env

# Edit configuration
nano .env
```

Example production `.env`:
```bash
# API Keys
OPENAI_API_KEY=sk-your-key-here
HUGGINGFACE_API_KEY=hf_your-key-here

# Database
DATABASE_PATH=/home/newsagent/newsagent/data/news_agent.db

# Web Settings
WEB_HOST=0.0.0.0
WEB_PORT=5000
API_HOST=0.0.0.0
API_PORT=8000

# Logging
LOG_LEVEL=INFO
ENABLE_LOGGING=true

# Performance
MAX_ARTICLES_PER_SOURCE=30
SCRAPING_DELAY=1.0

# Notifications
EMAIL_NOTIFICATIONS_ENABLED=true
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
EMAIL_TO=alerts@yourcompany.com
```

#### **5. Service Setup**
```bash
# Create systemd service files
sudo nano /etc/systemd/system/newsagent-api.service
```

```ini
[Unit]
Description=News Agent API Server
After=network.target

[Service]
Type=simple
User=newsagent
WorkingDirectory=/home/newsagent/newsagent
Environment=PATH=/home/newsagent/newsagent/venv/bin
ExecStart=/home/newsagent/newsagent/venv/bin/python api_server.py
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Create web dashboard service
sudo nano /etc/systemd/system/newsagent-web.service
```

```ini
[Unit]
Description=News Agent Web Dashboard
After=network.target newsagent-api.service

[Service]
Type=simple
User=newsagent
WorkingDirectory=/home/newsagent/newsagent
Environment=PATH=/home/newsagent/newsagent/venv/bin
ExecStart=/home/newsagent/newsagent/venv/bin/python web_dashboard.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Create scheduler service
sudo nano /etc/systemd/system/newsagent-scheduler.service
```

```ini
[Unit]
Description=News Agent Scheduler
After=network.target

[Service]
Type=simple
User=newsagent
WorkingDirectory=/home/newsagent/newsagent
Environment=PATH=/home/newsagent/newsagent/venv/bin
ExecStart=/home/newsagent/newsagent/venv/bin/python -c "
from integrated_news_agent import IntegratedNewsAgent, EnhancedNewsScheduler, NewsConfig;
import os;
config = NewsConfig();
agent = IntegratedNewsAgent(
  openai_api_key=os.getenv('OPENAI_API_KEY'),
  huggingface_api_key=os.getenv('HUGGINGFACE_API_KEY'),
  config=config
);
scheduler = EnhancedNewsScheduler(agent);
scheduler.start_scheduler(interval_hours=2)
"
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
```

#### **6. Start Services**
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable and start services
sudo systemctl enable newsagent-api newsagent-web newsagent-scheduler
sudo systemctl start newsagent-api newsagent-web newsagent-scheduler

# Check status
sudo systemctl status newsagent-api
sudo systemctl status newsagent-web
sudo systemctl status newsagent-scheduler
```

#### **7. Nginx Setup**
```bash
# Create nginx configuration
sudo nano /etc/nginx/sites-available/newsagent
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # API Server
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Web Dashboard
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/newsagent /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### **8. SSL Setup (Let's Encrypt)**
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx -y

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

---

## ☁️ **Cloud Container Deployment**

### **Docker Deployment**

#### **1. Build and Run**
```bash
# Build image
docker build -t news-agent:latest .

# Run with docker-compose
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs -f
```

#### **2. Environment Variables**
```bash
# Create production environment file
cat > .env.prod << EOF
OPENAI_API_KEY=sk-your-key-here
HUGGINGFACE_API_KEY=hf_your-key-here
DATABASE_PATH=/app/data/news_agent.db
LOG_LEVEL=INFO
MAX_ARTICLES_PER_SOURCE=30
EOF
```

#### **3. Production Compose**
```bash
# Use production compose
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### **AWS ECS Deployment**

#### **1. Create ECR Repository**
```bash
# Create repository
aws ecr create-repository --repository-name news-agent

# Build and push image
$(aws ecr get-login --no-include-email)
docker build -t news-agent .
docker tag news-agent:latest YOUR_ACCOUNT.dkr.ecr.REGION.amazonaws.com/news-agent:latest
docker push YOUR_ACCOUNT.dkr.ecr.REGION.amazonaws.com/news-agent:latest
```

#### **2. Create Task Definition**
```json
{
  "family": "news-agent",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "news-agent-api",
      "image": "YOUR_ACCOUNT.dkr.ecr.REGION.amazonaws.com/news-agent:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DATABASE_PATH",
          "value": "/app/data/news_agent.db"
        }
      ],
      "secrets": [
        {
          "name": "OPENAI_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:REGION:ACCOUNT:secret:openai-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/news-agent",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

#### **3. Create ECS Service**
```bash
# Create cluster
aws ecs create-cluster --cluster-name news-agent-cluster

# Create service
aws ecs create-service \
    --cluster news-agent-cluster \
    --service-name news-agent-service \
    --task-definition news-agent \
    --desired-count 2 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"
```

### **Kubernetes Deployment**

#### **1. Create Namespace**
```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: news-agent
```

#### **2. Create Secrets**
```yaml
# secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: news-agent-secrets
  namespace: news-agent
type: Opaque
data:
  openai-api-key: <base64-encoded-key>
  huggingface-api-key: <base64-encoded-key>
```

#### **3. Create Deployment**
```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: news-agent-api
  namespace: news-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: news-agent-api
  template:
    metadata:
      labels:
        app: news-agent-api
    spec:
      containers:
      - name: news-agent-api
        image: news-agent:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_PATH
          value: "/app/data/news_agent.db"
        - name: OPENAI_API_KEY
          valueFrom:
            secretKeyRef:
              name: news-agent-secrets
              key: openai-api-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        volumeMounts:
        - name: data-volume
          mountPath: /app/data
      volumes:
      - name: data-volume
        persistentVolumeClaim:
          claimName: news-agent-pvc
```

#### **4. Create Service**
```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: news-agent-service
  namespace: news-agent
spec:
  selector:
    app: news-agent-api
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

#### **5. Deploy**
```bash
kubectl apply -f namespace.yaml
kubectl apply -f secrets.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

---

## 🏢 **Enterprise Deployment**

### **High Availability Setup**

#### **1. Load Balancer Configuration**
```nginx
# /etc/nginx/nginx.conf
upstream news_agent_api {
    least_conn;
    server api1.internal:8000 max_fails=3 fail_timeout=30s;
    server api2.internal:8000 max_fails=3 fail_timeout=30s;
    server api3.internal:8000 max_fails=3 fail_timeout=30s;
}

upstream news_agent_web {
    least_conn;
    server web1.internal:5000 max_fails=3 fail_timeout=30s;
    server web2.internal:5000 max_fails=3 fail_timeout=30s;
}

server {
    listen 443 ssl http2;
    server_name news-agent.company.com;

    ssl_certificate /etc/ssl/certs/news-agent.crt;
    ssl_certificate_key /etc/ssl/private/news-agent.key;

    location /api/ {
        proxy_pass http://news_agent_api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://news_agent_web;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

#### **2. Database Clustering**
```bash
# PostgreSQL setup for production
sudo apt install postgresql-12 postgresql-client-12

# Configure master-slave replication
# Master server configuration
echo "wal_level = replica" >> /etc/postgresql/12/main/postgresql.conf
echo "max_wal_senders = 3" >> /etc/postgresql/12/main/postgresql.conf
echo "wal_keep_segments = 64" >> /etc/postgresql/12/main/postgresql.conf

# Slave server configuration
echo "hot_standby = on" >> /etc/postgresql/12/main/postgresql.conf
```

#### **3. Redis Clustering**
```bash
# Redis cluster setup
redis-cli --cluster create \
  redis1.internal:7000 \
  redis2.internal:7000 \
  redis3.internal:7000 \
  redis4.internal:7000 \
  redis5.internal:7000 \
  redis6.internal:7000 \
  --cluster-replicas 1
```

### **Monitoring Setup**

#### **1. Prometheus Configuration**
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'news-agent-api'
    static_configs:
      - targets: ['api1.internal:8000', 'api2.internal:8000', 'api3.internal:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'news-agent-web'
    static_configs:
      - targets: ['web1.internal:5000', 'web2.internal:5000']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node1.internal:9100', 'node2.internal:9100', 'node3.internal:9100']
```

#### **2. Grafana Dashboards**
```json
{
  "dashboard": {
    "title": "News Agent System Overview",
    "panels": [
      {
        "title": "API Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])"
          }
        ]
      },
      {
        "title": "Articles Processed",
        "type": "stat",
        "targets": [
          {
            "expr": "increase(articles_processed_total[1h])"
          }
        ]
      }
    ]
  }
}
```

#### **3. Alerting Rules**
```yaml
# alerts.yml
groups:
  - name: news-agent
    rules:
      - alert: HighAPILatency
        expr: rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m]) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High API latency detected"
          
      - alert: ScrapingFailed
        expr: increase(scraping_failures_total[1h]) > 5
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Multiple scraping failures detected"
```

---

## 🔒 **Security Configuration**

### **1. API Security**
```python
# Add to api_server.py
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

# JWT configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### **2. Rate Limiting**
```python
# Add rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)

@app.get("/api/articles")
@limiter.limit("100/minute")
async def get_articles(request: Request):
    # Rate limited endpoint
    pass
```

### **3. Input Validation**
```python
# Enhanced input validation
from pydantic import validator, EmailStr

class SecureAgentConfig(BaseModel):
    max_articles_per_source: int = Field(..., ge=1, le=100)
    
    @validator('max_articles_per_source')
    def validate_max_articles(cls, v):
        if v > 50 and not is_premium_user():
            raise ValueError('Free tier limited to 50 articles per source')
        return v
```

### **4. Network Security**
```bash
# Firewall configuration
sudo ufw enable
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow specific ports
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS

# Internal network access only
sudo ufw allow from 10.0.0.0/8 to any port 8000  # API
sudo ufw allow from 10.0.0.0/8 to any port 5000  # Web
```

---

## 📊 **Performance Optimization**

### **1. Database Optimization**
```sql
-- Create indexes for better performance
CREATE INDEX CONCURRENTLY idx_articles_scraped_at ON articles(scraped_at);
CREATE INDEX CONCURRENTLY idx_articles_source_category ON articles(source, category);
CREATE INDEX CONCURRENTLY idx_articles_content_hash ON articles(content_hash);

-- Partition large tables
CREATE TABLE articles_2024 PARTITION OF articles 
FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
```

### **2. Caching Strategy**
```python
# Redis caching implementation
import redis
from functools import wraps

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def cache_result(expiration=3600):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            redis_client.setex(cache_key, expiration, json.dumps(result))
            return result
        return wrapper
    return decorator

@cache_result(expiration=1800)  # 30 minutes
def get_trending_topics(hours=24):
    # Expensive operation
    pass
```

### **3. Connection Pooling**
```python
# Database connection pooling
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    'postgresql://user:pass@localhost/newsagent',
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

---

## 🔧 **Maintenance Procedures**

### **1. Backup Strategy**
```bash
#!/bin/bash
# backup.sh - Daily backup script

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/newsagent"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
sqlite3 /app/data/news_agent.db ".backup $BACKUP_DIR/news_agent_$DATE.db"

# Backup configuration
tar -czf $BACKUP_DIR/config_$DATE.tar.gz /app/config /app/.env

# Backup logs (last 7 days)
find /app/logs -name "*.log" -mtime -7 -exec cp {} $BACKUP_DIR/ \;

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -name "*.db" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

# Upload to S3 (optional)
aws s3 sync $BACKUP_DIR s3://newsagent-backups/$(date +%Y/%m/%d)/
```

### **2. Log Rotation**
```bash
# /etc/logrotate.d/newsagent
/app/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 newsagent newsagent
    postrotate
        systemctl reload newsagent-api
        systemctl reload newsagent-web
    endscript
}
```

### **3. Health Checks**
```bash
#!/bin/bash
# health_check.sh

# Check API health
API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
if [ $API_STATUS -ne 200 ]; then
    echo "API unhealthy: $API_STATUS"
    systemctl restart newsagent-api
fi

# Check web dashboard
WEB_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000)
if [ $WEB_STATUS -ne 200 ]; then
    echo "Web dashboard unhealthy: $WEB_STATUS"
    systemctl restart newsagent-web
fi

# Check disk space
DISK_USAGE=$(df /app | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "High disk usage: $DISK_USAGE%"
    # Cleanup old exports and logs
    find /app/exports -name "*.json" -mtime +7 -delete
    find /app/logs -name "*.log" -mtime +14 -delete
fi

# Check database size
DB_SIZE=$(du -m /app/data/news_agent.db | awk '{print $1}')
if [ $DB_SIZE -gt 1000 ]; then
    echo "Large database: ${DB_SIZE}MB"
    # Run cleanup
    python -c "
from integrated_news_agent import IntegratedNewsAgent;
agent = IntegratedNewsAgent();
deleted = agent.cleanup_old_articles(days=30);
print(f'Cleaned up {deleted} old articles');
agent.close()
"
fi
```

### **4. Update Procedure**
```bash
#!/bin/bash
# update.sh

# Stop services
sudo systemctl stop newsagent-scheduler
sudo systemctl stop newsagent-web
sudo systemctl stop newsagent-api

# Backup current version
cp -r /app/newsagent /app/newsagent.backup.$(date +%Y%m%d)

# Update code
cd /app/newsagent
git pull origin main

# Update dependencies
source venv/bin/activate
pip install --upgrade -r requirements.txt

# Run tests
python test_news_agent.py

# Start services
sudo systemctl start newsagent-api
sudo systemctl start newsagent-web
sudo systemctl start newsagent-scheduler

# Verify deployment
sleep 30
curl -f http://localhost:8000/health || exit 1
curl -f http://localhost:5000 || exit 1

echo "Update completed successfully"
```

---

## 📈 **Scaling Guidelines**

### **Horizontal Scaling Indicators**
- API response time > 2 seconds
- CPU usage > 80% for 10+ minutes
- Memory usage > 85%
- Queue depth > 100 pending requests

### **Vertical Scaling Guidelines**
- Increase CPU: When scraping takes > 30 minutes
- Increase Memory: When getting OOM errors
- Increase Storage: When database > 5GB

### **Auto-scaling Configuration**
```yaml
# kubernetes-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: news-agent-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: news-agent-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

---

## 🎯 **Conclusion**

This deployment guide provides comprehensive instructions for deploying the News Agent system across different environments. Choose the deployment option that best fits your needs:

- **Local Development**: Quick testing and development
- **Single Server**: Small team or proof of concept
- **Cloud Container**: Scalable production deployment
- **Enterprise**: High availability, multi-region deployment

Remember to:
- 🔒 **Secure** your deployment with proper authentication and encryption
- 📊 **Monitor** system performance and health
- 💾 **Backup** your data regularly
- 🔄 **Update** the system with new features and security patches
- 📈 **Scale** based on usage patterns and performance metrics

**Your News Agent system is now ready for production deployment! 🚀**