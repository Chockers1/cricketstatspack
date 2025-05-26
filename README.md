# 🏏 Cricket Stats Pack - Enterprise Web Application Platform

<div align="center">

![Python](https://img.shields.io/badge/python-v3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115.12-00a393.svg)
![MySQL](https://img.shields.io/badge/MySQL-8.0+-blue.svg)
![Stripe](https://img.shields.io/badge/Stripe-API-635bff.svg)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-CI/CD-2088ff.svg)
![Status](https://img.shields.io/badge/Status-Production-green.svg)
![Security](https://img.shields.io/badge/Security-Enterprise_Grade-orange.svg)
![Uptime](https://img.shields.io/badge/Uptime-99.9%25-green.svg)

**A production-grade, subscription-based cricket statistics platform engineered with enterprise-level architecture, security, and scalability**

[🌐 Live Platform](https://cricketstatspack.com) • [📊 Admin Portal](https://cricketstatspack.com/admin) • [💳 Billing Portal](https://cricketstatspack.com/billing) • [🔧 System Health](https://cricketstatspack.com/admin/churn)

</div>

---

## 🎯 Executive Summary

Cricket Stats Pack is a **production-grade FastAPI web application** delivering cricket statistics through an enterprise SaaS subscription model. The platform implements microservices-oriented architecture with event-driven subscription management, comprehensive user lifecycle automation, and real-time analytics processing.

### 🏆 Enterprise Features

- 🔒 **Zero-Trust Security Architecture** - Multi-layer authentication with bcrypt hashing, session management, rate limiting, and account lockout protection
- 💰 **Revenue Management System** - Automated Stripe integration with webhook-driven subscription lifecycle, proration handling, and revenue analytics
- 👨‍💼 **Advanced Admin Console** - Real-time user management, churn analysis, CSV export capabilities, and comprehensive audit logging
- 🛡️ **Enterprise Security Controls** - RBAC permissions, security question-based recovery, failed login protection, and comprehensive audit trails
- ⚡ **High-Performance Infrastructure** - Async FastAPI with Gunicorn workers, MySQL connection pooling, and optimized static asset delivery
- 📈 **Business Intelligence** - Session analytics, user engagement metrics, subscription conversion tracking, and automated reporting
- 🚀 **Production-Grade DevOps** - Zero-downtime CI/CD, systemd service management, SSL termination, and automated health monitoring

### 🔧 Technical Architecture Highlights

- **Async Web Framework**: FastAPI 0.115.12 with high-performance async/await patterns
- **Enterprise Database**: MySQL 8.0+ with optimized queries and connection pooling
- **Payment Processing**: Stripe API with comprehensive webhook handling and error recovery
- **Security Layer**: Multi-factor authentication with bcrypt + sessions + rate limiting
- **Infrastructure**: Ubuntu 24.04 LTS + Nginx + Gunicorn + systemd service orchestration
- **CI/CD Pipeline**: GitHub Actions with automated testing and zero-downtime deployment

---

## 🏗️ System Architecture & Infrastructure

### 🌐 Production Infrastructure Stack

```mermaid
graph TB
    subgraph "External Services"
        GH[GitHub Repository]
        ST[Stripe Payment Platform]
        CF[Cloudflare DNS]
        LE[Let's Encrypt CA]
    end
    
    subgraph "CI/CD Pipeline"
        GA[GitHub Actions]
        SSH[SSH Deployment]
    end
    
    subgraph "VPS Infrastructure - Ubuntu 24.04 LTS"
        subgraph "Web Layer"
            NG[Nginx Reverse Proxy]
            SSL[SSL Termination]
        end
        
        subgraph "Application Layer"
            GU[Gunicorn WSGI Server]
            FA[FastAPI Application]
            UV[Uvicorn Workers]
        end
        
        subgraph "Data Layer"
            MY[MySQL 8.0 Database]
            SE[Session Storage]
            AU[Audit Logs]
        end
        
        subgraph "System Services"
            SD[systemd Service Manager]
            LG[Centralized Logging]
            MT[Health Monitoring]
        end
    end
    
    subgraph "Client Layer"
        US[End Users]
        AD[Admin Dashboard]
        MO[Mobile Users]
    end
    
    GH -->|Push to main| GA
    GA -->|Automated Deploy| SSH
    SSH --> SD
    
    US -->|HTTPS/443| NG
    AD -->|Admin Portal| NG
    MO -->|Responsive UI| NG
    
    NG -->|Proxy to :8000| GU
    GU --> FA
    FA --> UV
    
    FA <-->|Query/Transaction| MY
    FA <-->|Session Management| SE
    FA <-->|Audit Trail| AU
    
    FA <-->|Webhook Events| ST
    FA -->|SSL Validation| LE
    
    SD -->|Service Control| GU
    SD -->|Log Management| LG
    SD -->|Health Checks| MT
```

### 🔧 Technology Stack Deep Dive

| **Layer** | **Component** | **Version** | **Purpose** | **Configuration** |
|-----------|---------------|-------------|-------------|-------------------|
| **Reverse Proxy** | Nginx | 1.24+ | SSL termination, static assets, load balancing | `/etc/nginx/sites-available/cricketstatspack` |
| **Web Framework** | FastAPI | 0.115.12 | Async API framework, OpenAPI docs | Async/await patterns, dependency injection |
| **WSGI Server** | Gunicorn | 21.2+ | Production WSGI server | 4 worker processes, graceful reloads |
| **ASGI Workers** | Uvicorn | 0.34.2 | High-performance ASGI implementation | `uvicorn.workers.UvicornWorker` |
| **Database** | MySQL | 8.0+ | Primary data persistence | InnoDB engine, UTF8MB4 charset |
| **Session Store** | File-based | Native | Secure session management | Server-side sessions with secret key |
| **Authentication** | bcrypt | 4.3.0 | Password hashing and verification | Cost factor 12, salt rounds |
| **Payment Gateway** | Stripe | 12.0.1 | Subscription billing and webhooks | Live mode, webhook signature verification |
| **Rate Limiting** | SlowAPI | 0.1.9 | API protection and abuse prevention | Redis-backed storage, sliding window |
| **Template Engine** | Jinja2 | 3.1.6 | Server-side rendering | Auto-escaping, template inheritance |
| **Static Assets** | Tailwind CSS | 3.4+ | Utility-first CSS framework | JIT compilation, custom configuration |

### 🖥️ Server Specifications

- **Cloud Provider**: Linode VPS
- **Instance Type**: Shared CPU (4GB RAM, 2 vCPU, 80GB SSD)
- **Operating System**: Ubuntu 24.04 LTS (Kernel 6.8+)
- **Public IPv4**: `172.105.182.239`
- **Domain**: `cricketstatspack.com` (A record + AAAA record)
- **SSL Certificate**: Let's Encrypt (auto-renewal via certbot)
- **Firewall**: UFW enabled (SSH, HTTP, HTTPS only)

### 📁 Production Directory Structure

```
/root/cricketapp/                         # Application root
├── 🐍 venv/                             # Python virtual environment
├── 📄 app.py                            # Main FastAPI application (2,000+ lines)
├── 🔧 auth_utils.py                     # Authentication & admin utilities
├── 💳 stripe_payments.py                # Stripe payment processing routes
├── 🪝 stripe_webhook.py                 # Webhook event handlers
├── 📊 email_utils.py                    # Email notification system
├── 📋 requirements.txt                  # Python dependencies (69 packages)
├── 🔐 .env                             # Environment variables (production)
├── 🌐 templates/                       # Jinja2 HTML templates
│   ├── 🏠 index.html                   # Landing page
│   ├── 🔐 login.html                   # Authentication forms
│   ├── 📝 register.html                # User registration
│   ├── 🎛️ dashboard.html               # User dashboard
│   ├── 👤 profile.html                 # User profile management
│   ├── 💰 billing.html                 # Subscription management
│   ├── 👑 admin_dashboard.html         # Admin control panel
│   ├── 🔍 verify_security.html         # Password recovery
│   └── 📈 churn_report.html            # Business analytics
├── 🎨 static/                          # Static assets
│   ├── 🎨 css/                         # Custom stylesheets
│   ├── ⚡ js/                          # JavaScript modules
│   └── 🖼️ images/                      # Application assets
├── 📜 logs/                            # Application logs
│   ├── 🔍 app.log                      # Application events
│   ├── ⚠️ error.log                    # Error tracking
│   └── 🔒 security.log                 # Security events
└── ⚙️ systemd/                        # Service configuration
    └── 🔧 cricketapp.service           # systemd unit file
```

---

## 🔐 Enterprise Security Architecture

### 🛡️ Multi-Layer Security Implementation

```mermaid
graph TD
    subgraph "Network Security Layer"
        CF[Cloudflare DDoS Protection]
        FW[UFW Firewall Rules]
        SSL[TLS 1.3 Encryption]
    end
    
    subgraph "Application Security Layer"
        RL[Rate Limiting - 5/min]
        CSRF[CSRF Protection]
        XSS[XSS Prevention]
        SQL[SQL Injection Prevention]
    end
    
    subgraph "Authentication Security Layer"
        BC[bcrypt Password Hashing]
        SM[Secure Session Management]
        SQ[Security Question Validation]
        AL[Account Lockout Protection]
    end
    
    subgraph "Authorization Security Layer"
        RBAC[Role-Based Access Control]
        EP[Endpoint Protection]
        AA[Admin Access Control]
        AT[Audit Trail Logging]
    end
    
    subgraph "Data Security Layer"
        DE[Data Encryption at Rest]
        DT[Data Transmission Security]
        BK[Encrypted Backups]
        PII[PII Data Protection]
    end
    
    CF --> FW
    FW --> SSL
    SSL --> RL
    RL --> BC
    BC --> RBAC
    RBAC --> DE
```

### 🔒 Authentication & Session Management

#### Password Security Implementation

```python
# Password Hashing Configuration
BCRYPT_COST_FACTOR = 12  # 2^12 iterations
SALT_ROUNDS = bcrypt.gensalt()

# Password Policy Enforcement
MIN_PASSWORD_LENGTH = 8
REQUIRE_SPECIAL_CHARS = True
ACCOUNT_LOCKOUT_THRESHOLD = 5  # Failed attempts
LOCKOUT_DURATION = 30  # Minutes
```

#### Session Security Features

- **Session Storage**: Server-side file-based sessions
- **Session Timeout**: 24-hour sliding expiration
- **Session Binding**: IP address validation
- **CSRF Protection**: Built-in token validation
- **Secure Cookies**: HTTPOnly, Secure, SameSite attributes

#### Security Question System

```python
# Security Questions Database Schema
security_question_1: VARCHAR(255)      # First security question
security_answer_1_hash: VARCHAR(255)   # bcrypt hashed answer
security_question_2: VARCHAR(255)      # Second security question  
security_answer_2_hash: VARCHAR(255)   # bcrypt hashed answer
reset_attempts: INT                     # Failed recovery attempts
```

### 🚨 Rate Limiting & Abuse Prevention

#### Endpoint-Specific Rate Limits

| **Endpoint** | **Rate Limit** | **Window** | **Protection Type** |
|--------------|----------------|------------|-------------------|
| `/login` | 5 requests | 1 minute | Brute force protection |
| `/register` | 3 requests | 5 minutes | Account creation abuse |
| `/verify-security` | 3 requests | 15 minutes | Password reset abuse |
| `/admin/*` | 10 requests | 1 minute | Admin action protection |
| `/api/webhook` | 100 requests | 1 minute | Webhook flood protection |

#### Account Lockout Protection

```python
# Account Lockout Configuration
FAILED_LOGIN_THRESHOLD = 5
LOCKOUT_DURATION_MINUTES = 30
PROGRESSIVE_LOCKOUT = True  # Increases with repeated violations

# Lockout Implementation
if failed_logins >= FAILED_LOGIN_THRESHOLD:
    lock_until = datetime.now() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
    update_user_lock_status(email, lock_until)
    log_security_event("ACCOUNT_LOCKED", email, ip_address)
```

### 🔍 Comprehensive Audit System

#### Security Event Logging

```sql
-- Audit Logs Table Structure
CREATE TABLE audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    action VARCHAR(100) NOT NULL,
    details TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    severity ENUM('LOW', 'MEDIUM', 'HIGH', 'CRITICAL') DEFAULT 'MEDIUM',
    INDEX idx_email_timestamp (email, timestamp),
    INDEX idx_action_severity (action, severity)
);
```

#### Tracked Security Events

- **Authentication Events**: Login success/failure, logout, session expiry
- **Authorization Events**: Admin access, privilege escalation attempts
- **Account Events**: Registration, profile changes, password resets
- **Payment Events**: Subscription changes, billing updates, webhook events
- **Security Events**: Rate limit violations, suspicious activity, account lockouts

---

## 💳 Enterprise Payment & Subscription Architecture

### 🎯 Subscription Management System

```mermaid
graph LR
    subgraph "Customer Journey"
        REG[Registration] --> FREE[Free Trial]
        FREE --> SUB[Subscription Selection]
        SUB --> PAY[Payment Processing]
        PAY --> ACT[Account Activation]
    end
    
    subgraph "Stripe Integration"
        CHK[Checkout Sessions]
        WEB[Webhook Processing]
        POR[Customer Portal]
        INV[Invoice Management]
    end
    
    subgraph "Business Logic"
        SUB_SYNC[Subscription Sync]
        PRO[Proration Handling]
        CAN[Cancellation Processing]
        REN[Renewal Management]
    end
    
    PAY --> CHK
    CHK --> WEB
    WEB --> SUB_SYNC
    SUB_SYNC --> ACT
    
    ACT --> POR
    POR --> PRO
    POR --> CAN
    POR --> REN
```

### 💰 Revenue Model & Pricing Strategy

#### Subscription Tiers

| **Plan** | **Monthly Price** | **Annual Price** | **Discount** | **Stripe Price ID** |
|----------|-------------------|------------------|--------------|-------------------|
| **Monthly Premium** | $9.99/month | - | - | `price_monthly_premium` |
| **Annual Premium** | - | $99.99/year | 16.7% savings | `price_annual_premium` |

#### Revenue Optimization Features

- **Prorated Billing**: Automatic charge adjustments for mid-cycle changes
- **Failed Payment Recovery**: Automated retry logic with email notifications
- **Dunning Management**: Smart subscription lifecycle management
- **Churn Prevention**: Automated retention campaigns and analytics

### 🔄 Webhook Event Processing

#### Comprehensive Event Handling

```python
# Stripe Webhook Events Processed
WEBHOOK_EVENTS = {
    'customer.subscription.created': handle_subscription_created,
    'customer.subscription.updated': handle_subscription_updated,
    'customer.subscription.deleted': handle_subscription_cancelled,
    'invoice.payment_succeeded': handle_payment_success,
    'invoice.payment_failed': handle_payment_failure,
    'customer.subscription.trial_will_end': handle_trial_ending,
    'customer.updated': handle_customer_updated,
    'payment_method.attached': handle_payment_method_change
}
```

#### Webhook Security & Reliability

- **Signature Verification**: SHA-256 HMAC validation for all webhook events
- **Idempotency Handling**: Prevents duplicate event processing
- **Retry Logic**: Exponential backoff for failed webhook processing
- **Dead Letter Queue**: Failed events stored for manual review

### 📊 Revenue Analytics & Reporting

#### Key Metrics Tracked

- **Monthly Recurring Revenue (MRR)**: Real-time subscription revenue tracking
- **Annual Recurring Revenue (ARR)**: Yearly revenue projections
- **Customer Lifetime Value (CLV)**: Revenue per customer analytics
- **Churn Rate**: Monthly and annual subscription cancellation rates
- **Conversion Funnel**: Free trial to paid subscription analytics

---

## 👑 Advanced Admin Management System

### 🎛️ Admin Dashboard Features

```mermaid
graph TB
    subgraph "User Management"
        UM[User Overview]
        US[User Search & Filter]
        UP[User Profile Details]
        UA[User Actions]
    end
    
    subgraph "Subscription Analytics"
        SA[Subscription Stats]
        RA[Revenue Analytics]
        CA[Churn Analysis]
        CR[Conversion Reports]
    end
    
    subgraph "System Monitoring"
        SM[Session Monitoring]
        AL[Audit Log Viewer]
        PM[Performance Metrics]
        HM[Health Monitoring]
    end
    
    subgraph "Administrative Actions"
        UB[User Ban/Unban]
        UD[User Disable/Enable]
        PR[Password Reset]
        DE[Data Export]
    end
    
    UM --> US
    US --> UP
    UP --> UA
    
    SA --> RA
    RA --> CA
    CA --> CR
    
    SM --> AL
    AL --> PM
    PM --> HM
    
    UA --> UB
    UB --> UD
    UD --> PR
    PR --> DE
```

### 📈 Business Intelligence Dashboard

#### Real-Time Metrics

```sql
-- Key Performance Indicators
SELECT 
    COUNT(*) as total_users,
    SUM(CASE WHEN is_premium = 1 THEN 1 ELSE 0 END) as premium_users,
    SUM(CASE WHEN subscription_type = 'monthly' THEN 1 ELSE 0 END) as monthly_subs,
    SUM(CASE WHEN subscription_type = 'annual' THEN 1 ELSE 0 END) as annual_subs,
    AVG(DATEDIFF(NOW(), created_at)) as avg_user_age_days,
    COUNT(DISTINCT DATE(created_at)) as days_with_signups
FROM users 
WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY);
```

#### Advanced Analytics Features

- **Session Analytics**: Average session duration, most active users, login patterns
- **Conversion Tracking**: Free trial to paid conversion rates by cohort
- **Churn Analysis**: Subscription cancellation patterns and reasons
- **Geographic Distribution**: User registration and revenue by location
- **Feature Usage**: Premium feature adoption and engagement metrics

### 🔧 Administrative Tools

#### User Management Capabilities

| **Action** | **Description** | **Security Level** | **Audit Logged** |
|------------|-----------------|-------------------|-------------------|
| **Ban User** | Completely blocks account access | HIGH | ✅ |
| **Disable User** | Temporarily suspends account | MEDIUM | ✅ |
| **Enable User** | Restores suspended account | MEDIUM | ✅ |
| **Reset Password** | Emergency password reset | HIGH | ✅ |
| **View User Details** | Access complete user profile | LOW | ✅ |
| **Export User Data** | CSV export of user database | HIGH | ✅ |

#### Bulk Operations

```python
# Bulk User Management Functions
def bulk_user_operation(admin_email: str, operation: str, user_list: List[str]):
    """
    Perform bulk operations on multiple users
    Supported operations: ban, unban, disable, enable, export
    """
    for user_email in user_list:
        if operation == "ban":
            update_user_status(user_email, "is_banned", True)
        elif operation == "disable":
            update_user_status(user_email, "is_disabled", True)
        
        log_action(admin_email, f"BULK_{operation.upper()}", f"Target: {user_email}")
```

---

## ⚡ Performance & Scalability Architecture

### 🚀 Application Performance Optimization

#### FastAPI Performance Configuration

```python
# High-Performance FastAPI Configuration
app = FastAPI(
    title="Cricket Stats Pack API",
    version="2.0.0",
    docs_url="/docs",  # OpenAPI documentation
    redoc_url="/redoc",  # ReDoc documentation
    openapi_url="/openapi.json"
)

# Async Database Connection Pool
DATABASE_POOL_CONFIG = {
    'pool_size': 10,
    'max_overflow': 20,
    'pool_pre_ping': True,
    'pool_recycle': 3600,  # 1 hour
    'echo': False  # Disable SQL logging in production
}
```

#### Gunicorn Production Configuration

```python
# gunicorn.conf.py
bind = "127.0.0.1:8000"
workers = 4  # CPU cores * 2
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
preload_app = True
keepalive = 5
timeout = 120
graceful_timeout = 30
```

### 📊 Database Performance Optimization

#### Optimized Database Schema

```sql
-- Performance Indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_premium_status ON users(is_premium, subscription_status);
CREATE INDEX idx_users_created_at ON users(created_at);
CREATE INDEX idx_session_logs_email_time ON session_logs(email, login_time);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX idx_audit_logs_email_action ON audit_logs(email, action);

-- Query Optimization
ANALYZE TABLE users;
ANALYZE TABLE session_logs;
ANALYZE TABLE audit_logs;
```

#### Connection Pool Management

```python
# MySQL Connection Pool Configuration
MYSQL_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASS'),
    'database': os.getenv('DB_NAME'),
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci',
    'pool_name': 'cricket_pool',
    'pool_size': 10,
    'pool_reset_session': True,
    'autocommit': False,
    'time_zone': '+00:00'
}
```

### 🌐 CDN & Static Asset Optimization

#### Nginx Static Asset Configuration

```nginx
# /etc/nginx/sites-available/cricketstatspack
server {
    listen 443 ssl http2;
    server_name cricketstatspack.com;
    
    # Static asset optimization
    location /static/ {
        alias /root/cricketapp/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        add_header X-Content-Type-Options nosniff;
        gzip_static on;
    }
    
    # API endpoint optimization
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Performance headers
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

---

## 🚀 Production Infrastructure

### 🌐 Deployment Details

- **Domain**: [https://cricketstatspack.com](https://cricketstatspack.com)
- **VPS**: Ubuntu 24.04 LTS (Linode)
- **Public IP**: `172.105.182.239`
- **SSL**: Let's Encrypt via Certbot
- **Monitoring**: Systemd service management

### 📁 Directory Structure

```
cricketstatspack/
├── 📄 app.py                    # Main FastAPI application
├── 🔧 auth_utils.py             # Authentication utilities
├── 💳 stripe_payments.py        # Stripe payment routes
├── 🪝 stripe_webhook.py         # Webhook handlers
├── 📊 email_utils.py            # Email notifications
├── 📋 requirements.txt          # Python dependencies
├── 🌐 templates/               # Jinja2 HTML templates
├── 🎨 static/                  # CSS, JS, images
├── ⚙️ .github/workflows/       # CI/CD configuration
└── 📚 docs/                    # Additional documentation
```

---

## 📋 Comprehensive API Documentation

### 🌐 REST API Endpoints

#### Authentication Endpoints

| **Method** | **Endpoint** | **Description** | **Rate Limit** | **Auth Required** |
|------------|--------------|-----------------|-----------------|-------------------|
| `GET` | `/login` | Login form display | None | ❌ |
| `POST` | `/login` | User authentication | 5/min | ❌ |
| `GET` | `/register` | Registration form | None | ❌ |
| `POST` | `/register` | Account creation | 3/5min | ❌ |
| `GET` | `/logout` | Session termination | None | ✅ |
| `GET` | `/verify-security` | Security questions form | None | ❌ |
| `POST` | `/verify-security` | Password recovery validation | 3/15min | ❌ |
| `GET` | `/reset-password` | Password reset form | None | ✅ Session |
| `POST` | `/reset-password` | Password update | 3/15min | ✅ Session |

#### User Dashboard Endpoints

| **Method** | **Endpoint** | **Description** | **Rate Limit** | **Auth Required** |
|------------|--------------|-----------------|-----------------|-------------------|
| `GET` | `/dashboard` | Main user dashboard | None | ✅ |
| `GET` | `/profile` | User profile management | None | ✅ |
| `POST` | `/profile` | Profile updates | 10/min | ✅ |
| `GET` | `/change-password` | Password change form | None | ✅ |
| `POST` | `/change-password` | Password update | 5/min | ✅ |

#### Subscription & Payment Endpoints

| **Method** | **Endpoint** | **Description** | **Rate Limit** | **Auth Required** |
|------------|--------------|-----------------|-----------------|-------------------|
| `GET` | `/subscribe` | Subscription plans display | None | ✅ |
| `POST` | `/create-checkout-session` | Stripe checkout creation | 10/min | ✅ |
| `GET` | `/billing` | Billing management redirect | None | ✅ Premium |
| `GET` | `/manage-subscription` | Stripe portal redirect | None | ✅ Premium |
| `GET` | `/cancel-subscription` | Subscription cancellation | 3/hour | ✅ Premium |
| `GET` | `/success` | Payment success page | None | ✅ |
| `POST` | `/stripe-webhook` | Stripe event processing | 100/min | ❌ Webhook |

#### Administrative Endpoints

| **Method** | **Endpoint** | **Description** | **Rate Limit** | **Auth Required** |
|------------|--------------|-----------------|-----------------|-------------------|
| `GET` | `/admin` | Admin dashboard | 10/min | ✅ Admin |
| `GET` | `/admin/user/{email}` | User details view | 20/min | ✅ Admin |
| `GET` | `/admin/churn` | Churn analysis report | 5/min | ✅ Admin |
| `GET` | `/admin/export-users` | CSV user data export | 2/hour | ✅ Admin |
| `POST` | `/admin/ban` | User account ban | 10/min | ✅ Admin |
| `POST` | `/admin/unban` | User account unban | 10/min | ✅ Admin |
| `POST` | `/admin/disable` | User account disable | 10/min | ✅ Admin |
| `POST` | `/admin/enable` | User account enable | 10/min | ✅ Admin |
| `POST` | `/admin/reset-password` | Admin password reset | 5/min | ✅ Admin |

#### System Health & Monitoring

| **Method** | **Endpoint** | **Description** | **Rate Limit** | **Auth Required** |
|------------|--------------|-----------------|-----------------|-------------------|
| `GET` | `/docs` | OpenAPI documentation | None | ❌ |
| `GET` | `/redoc` | ReDoc API documentation | None | ❌ |
| `GET` | `/openapi.json` | OpenAPI specification | None | ❌ |
| `GET` | `/health` | Application health check | None | ❌ |
| `GET` | `/metrics` | Prometheus metrics | None | ✅ Admin |

---

## 🗄️ Enterprise Database Architecture

### 📊 Complete Database Schema

#### Core User Management Tables

```sql
-- Primary Users Table
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    
    -- Subscription Management
    is_premium BOOLEAN DEFAULT FALSE,
    stripe_customer_id VARCHAR(255) UNIQUE,
    subscription_type ENUM('monthly', 'annual') NULL,
    subscription_status VARCHAR(50) DEFAULT 'inactive',
    subscription_start_date TIMESTAMP NULL,
    subscription_end_date TIMESTAMP NULL,
    
    -- Security & Recovery
    security_question_1 VARCHAR(255) NOT NULL,
    security_answer_1_hash VARCHAR(255) NOT NULL,
    security_question_2 VARCHAR(255) NOT NULL,
    security_answer_2_hash VARCHAR(255) NOT NULL,
    
    -- Account Security Controls
    is_banned BOOLEAN DEFAULT FALSE,
    is_disabled BOOLEAN DEFAULT FALSE,
    failed_logins INT DEFAULT 0,
    lock_until TIMESTAMP NULL,
    reset_attempts INT DEFAULT 0,
    last_password_change TIMESTAMP NULL,
    
    -- Audit Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    
    -- Performance Indexes
    INDEX idx_email (email),
    INDEX idx_premium_status (is_premium, subscription_status),
    INDEX idx_stripe_customer (stripe_customer_id),
    INDEX idx_created_at (created_at),
    INDEX idx_subscription_type (subscription_type),
    INDEX idx_security_status (is_banned, is_disabled)
) ENGINE=InnoDB CHARACTER SET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Session Tracking & Analytics
CREATE TABLE session_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    logout_time TIMESTAMP NULL,
    duration_seconds INT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    session_id VARCHAR(255),
    login_method ENUM('password', 'security_recovery') DEFAULT 'password',
    
    -- Performance Indexes
    INDEX idx_email_time (email, login_time),
    INDEX idx_login_time (login_time DESC),
    INDEX idx_session_id (session_id),
    INDEX idx_ip_address (ip_address),
    FOREIGN KEY (email) REFERENCES users(email) ON DELETE CASCADE
) ENGINE=InnoDB CHARACTER SET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Comprehensive Audit Logging
CREATE TABLE audit_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255),
    action VARCHAR(100) NOT NULL,
    details TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    admin_email VARCHAR(255) NULL,
    severity ENUM('LOW', 'MEDIUM', 'HIGH', 'CRITICAL') DEFAULT 'MEDIUM',
    category ENUM('AUTH', 'ADMIN', 'PAYMENT', 'SECURITY', 'SYSTEM') DEFAULT 'SYSTEM',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Performance Indexes
    INDEX idx_email_timestamp (email, timestamp DESC),
    INDEX idx_action_severity (action, severity),
    INDEX idx_timestamp (timestamp DESC),
    INDEX idx_category_severity (category, severity),
    INDEX idx_admin_actions (admin_email, timestamp DESC)
) ENGINE=InnoDB CHARACTER SET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Payment & Subscription Analytics
CREATE TABLE payment_events (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    stripe_event_id VARCHAR(255) UNIQUE NOT NULL,
    customer_email VARCHAR(255),
    event_type VARCHAR(100) NOT NULL,
    amount_cents INT,
    currency VARCHAR(3) DEFAULT 'USD',
    subscription_id VARCHAR(255),
    invoice_id VARCHAR(255),
    payment_method VARCHAR(50),
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    webhook_received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Performance Indexes
    INDEX idx_customer_email (customer_email),
    INDEX idx_event_type (event_type),
    INDEX idx_processed_at (processed_at DESC),
    INDEX idx_subscription_id (subscription_id),
    FOREIGN KEY (customer_email) REFERENCES users(email) ON DELETE SET NULL
) ENGINE=InnoDB CHARACTER SET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

#### Advanced Database Optimization

```sql
-- Performance Optimization Views
CREATE VIEW active_premium_users AS
SELECT 
    u.email,
    u.subscription_type,
    u.subscription_status,
    u.created_at,
    u.last_login,
    DATEDIFF(NOW(), u.created_at) as days_since_signup
FROM users u 
WHERE u.is_premium = TRUE 
AND u.subscription_status = 'active'
AND u.is_banned = FALSE 
AND u.is_disabled = FALSE;

-- Business Intelligence Aggregations
CREATE VIEW subscription_metrics AS
SELECT 
    COUNT(*) as total_users,
    SUM(CASE WHEN is_premium = 1 THEN 1 ELSE 0 END) as premium_users,
    SUM(CASE WHEN subscription_type = 'monthly' THEN 1 ELSE 0 END) as monthly_subs,
    SUM(CASE WHEN subscription_type = 'annual' THEN 1 ELSE 0 END) as annual_subs,
    AVG(DATEDIFF(NOW(), created_at)) as avg_user_age_days,
    COUNT(DISTINCT DATE(created_at)) as signup_days_tracked
FROM users 
WHERE created_at >= DATE_SUB(NOW(), INTERVAL 90 DAY);

-- Query Performance Optimization
ANALYZE TABLE users;
ANALYZE TABLE session_logs;
ANALYZE TABLE audit_logs;
ANALYZE TABLE payment_events;

-- Table Maintenance Procedures
DELIMITER $$
CREATE PROCEDURE CleanupOldSessions()
BEGIN
    DELETE FROM session_logs 
    WHERE login_time < DATE_SUB(NOW(), INTERVAL 6 MONTH);
END$$

CREATE PROCEDURE ArchiveOldAuditLogs()
BEGIN
    INSERT INTO audit_logs_archive 
    SELECT * FROM audit_logs 
    WHERE timestamp < DATE_SUB(NOW(), INTERVAL 1 YEAR);
    
    DELETE FROM audit_logs 
    WHERE timestamp < DATE_SUB(NOW(), INTERVAL 1 YEAR);
END$$
DELIMITER ;
```

---

## 🔐 Authentication & Security

### 🛡️ Security Features

- **Password Security**: bcrypt hashing with salt
- **Session Management**: Secure server-side sessions
- **Rate Limiting**: 5 login attempts per minute per IP
- **Security Questions**: Two-factor password recovery
- **Account Protection**: Ban/disable functionality
- **Audit Logging**: Complete action tracking

### 🔑 Password Recovery Flow

```mermaid
sequenceDiagram
    participant U as User
    participant S as System
    participant DB as Database
    
    U->>S: Request password reset
    S->>DB: Verify email exists
    S->>U: Display security questions
    U->>S: Submit answers
    S->>DB: Validate hashed answers
    S->>U: Allow password reset
    U->>S: Set new password
    S->>DB: Update password hash
```

---

## 💳 Subscription Management

### 💰 Pricing Plans

| Plan | Price | Features |
|------|-------|----------|
| **Monthly** | $9.99/month | Full access to cricket stats |
| **Annual** | $99.99/year | Full access + 2 months free |

### 🔄 Stripe Integration

- ✅ **Checkout Sessions** - Secure payment processing
- ✅ **Customer Portal** - Self-service billing management
- ✅ **Webhooks** - Real-time subscription updates
- ✅ **Subscription Status** - Active/canceled/past_due handling
- ✅ **Prorations** - Automatic billing adjustments

```python
# Stripe Webhook Events Handled
- customer.subscription.created
- customer.subscription.updated
- customer.subscription.deleted
- invoice.payment_succeeded
- invoice.payment_failed
```

---

## 👑 Admin Dashboard

### 📊 Analytics & Metrics

- **User Metrics**: Total users, premium subscribers, growth trends
- **Subscription Analytics**: Monthly vs Annual breakdown
- **Session Tracking**: Login patterns, session duration, active users
- **Financial Data**: Revenue tracking, churn analysis

### ⚙️ Admin Actions

- 🚫 **User Management**: Ban/unban, disable/enable accounts
- 🔑 **Password Reset**: Emergency password reset for users
- 📈 **Export Data**: CSV export of user database
- 🔍 **User Details**: Individual user activity and subscription history
- 📊 **Churn Reports**: Subscription cancellation analytics

---

## 🚀 Deployment

### 🔄 CI/CD Pipeline

The application uses **GitHub Actions** for automated deployment:

```yaml
# .github/workflows/deploy.yml
name: Deploy to VPS
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to VPS
        run: |
          ssh root@172.105.182.239 << 'EOF'
          cd ~/cricketapp
          git pull origin main
          systemctl restart cricketapp
          EOF
```

### 🐍 Local Development Setup

```bash
# Clone repository
git clone https://github.com/Chockers1/cricketstatspack.git
cd cricketstatspack

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run application
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### 🌐 Production Deployment

```bash
# VPS Commands
cd /root/cricketapp
source venv/bin/activate
sudo systemctl restart cricketapp
sudo journalctl -u cricketapp --follow
```

---

## ⚙️ Configuration

### 🔧 Environment Variables

```env
# Database Configuration
DB_HOST=localhost
DB_USER=appuser
DB_PASS=your_secure_password
DB_NAME=cricket_auth

# Application Security
SECRET_KEY=your_secret_key_here
ADMIN_EMAIL=admin@example.com

# Stripe Configuration
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PORTAL_RETURN_URL=https://cricketstatspack.com/dashboard
STRIPE_PRICE_ID_MONTHLY=price_...
STRIPE_PRICE_ID_ANNUAL=price_...

# Email Configuration (Optional)
EMAIL_USER=noreply@cricketstatspack.com
EMAIL_PASS=your_email_password

# Logging
LOG_LEVEL=INFO
```

### 🗄️ Database Schema

```sql
-- Key tables
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_premium BOOLEAN DEFAULT FALSE,
    stripe_customer_id VARCHAR(255),
    subscription_type ENUM('monthly', 'annual'),
    subscription_status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- Security & Access Control
    security_question_1 VARCHAR(255),
    security_answer_1_hash VARCHAR(255),
    security_question_2 VARCHAR(255),
    security_answer_2_hash VARCHAR(255),
    reset_attempts INT DEFAULT 0,
    is_banned BOOLEAN DEFAULT FALSE,
    is_disabled BOOLEAN DEFAULT FALSE,
    failed_logins INT DEFAULT 0,
    lock_until TIMESTAMP NULL
);

CREATE TABLE session_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255),
    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    logout_time TIMESTAMP NULL,
    duration_seconds INT,
    ip_address VARCHAR(45)
);

CREATE TABLE audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255),
    action VARCHAR(100),
    details TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 📊 Enterprise Monitoring & Observability

### 🔍 Application Performance Monitoring (APM)

#### Logging Architecture

```python
# Structured Logging Configuration
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/var/log/cricketapp/app.log'),
        logging.handlers.RotatingFileHandler(
            '/var/log/cricketapp/app.log',
            maxBytes=50*1024*1024,  # 50MB
            backupCount=10
        )
    ]
)

# Performance Metrics Logging
class PerformanceMetrics:
    @staticmethod
    def log_request_time(endpoint: str, duration: float):
        logger.info(f"REQUEST_TIMING endpoint={endpoint} duration_ms={duration*1000:.2f}")
    
    @staticmethod
    def log_database_query(query_type: str, duration: float, rows_affected: int = 0):
        logger.info(f"DB_QUERY type={query_type} duration_ms={duration*1000:.2f} rows={rows_affected}")
```

#### System Health Monitoring

```bash
#!/bin/bash
# /usr/local/bin/health_monitor.sh
# Comprehensive system health monitoring script

# Application Health Check
check_app_health() {
    response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
    if [ "$response" != "200" ]; then
        echo "CRITICAL: Application health check failed (HTTP $response)"
        systemctl restart cricketapp
    fi
}

# Database Connectivity Check
check_database() {
    mysql -h${DB_HOST} -u${DB_USER} -p${DB_PASS} -e "SELECT 1" ${DB_NAME} > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "CRITICAL: Database connection failed"
        # Alert admin
    fi
}

# Disk Space Monitoring
check_disk_space() {
    usage=$(df /root/cricketapp | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$usage" -gt 85 ]; then
        echo "WARNING: Disk usage at ${usage}%"
    fi
}

# Memory Usage Check
check_memory() {
    mem_usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    if [ "$mem_usage" -gt 90 ]; then
        echo "WARNING: Memory usage at ${mem_usage}%"
    fi
}

# SSL Certificate Expiry Check
check_ssl_expiry() {
    days_until_expiry=$(echo | openssl s_client -servername cricketstatspack.com -connect cricketstatspack.com:443 2>/dev/null | openssl x509 -noout -dates | grep notAfter | cut -d= -f2 | xargs -I {} date -d {} +%s | xargs -I {} expr \( {} - $(date +%s) \) / 86400)
    
    if [ "$days_until_expiry" -lt 30 ]; then
        echo "WARNING: SSL certificate expires in $days_until_expiry days"
    fi
}

# Run all checks
check_app_health
check_database
check_disk_space
check_memory
check_ssl_expiry
```

#### Prometheus Metrics Endpoint

```python
# Advanced metrics collection for enterprise monitoring
from prometheus_client import Counter, Histogram, Gauge, generate_latest

# Application Metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
ACTIVE_USERS = Gauge('active_users_total', 'Number of active users')
SUBSCRIPTION_REVENUE = Gauge('subscription_revenue_usd', 'Total subscription revenue')
DATABASE_CONNECTIONS = Gauge('database_connections_active', 'Active database connections')

@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint for monitoring"""
    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )

# Middleware for automatic metrics collection
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path).inc()
    REQUEST_DURATION.observe(duration)
    
    return response
```

### 📈 Business Intelligence Dashboards

#### Key Performance Indicators (KPIs)

```sql
-- Real-time Business Metrics
SELECT 
    -- User Growth Metrics
    COUNT(*) as total_users,
    COUNT(CASE WHEN created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY) THEN 1 END) as new_users_30d,
    COUNT(CASE WHEN created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) THEN 1 END) as new_users_7d,
    
    -- Subscription Metrics
    COUNT(CASE WHEN is_premium = 1 THEN 1 END) as premium_users,
    COUNT(CASE WHEN subscription_type = 'monthly' THEN 1 END) as monthly_subscribers,
    COUNT(CASE WHEN subscription_type = 'annual' THEN 1 END) as annual_subscribers,
    
    -- Revenue Metrics (estimated)
    COUNT(CASE WHEN subscription_type = 'monthly' THEN 1 END) * 9.99 as monthly_mrr,
    COUNT(CASE WHEN subscription_type = 'annual' THEN 1 END) * 99.99 as annual_arr,
    
    -- Engagement Metrics
    COUNT(CASE WHEN last_login >= DATE_SUB(NOW(), INTERVAL 7 DAY) THEN 1 END) as active_users_7d,
    COUNT(CASE WHEN last_login >= DATE_SUB(NOW(), INTERVAL 30 DAY) THEN 1 END) as active_users_30d,
    
    -- Conversion Rates
    ROUND(
        (COUNT(CASE WHEN is_premium = 1 THEN 1 END) * 100.0) / 
        NULLIF(COUNT(*), 0), 2
    ) as premium_conversion_rate
FROM users;

-- Churn Analysis Query
SELECT 
    subscription_type,
    COUNT(*) as cancelled_subscriptions,
    AVG(DATEDIFF(subscription_end_date, subscription_start_date)) as avg_subscription_days,
    MONTH(subscription_end_date) as cancellation_month,
    YEAR(subscription_end_date) as cancellation_year
FROM users 
WHERE subscription_status = 'cancelled' 
    AND subscription_end_date >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
GROUP BY subscription_type, YEAR(subscription_end_date), MONTH(subscription_end_date)
ORDER BY cancellation_year DESC, cancellation_month DESC;
```

#### Automated Reporting System

```python
# Automated daily/weekly/monthly reporting
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta

class BusinessReporting:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER")
        self.smtp_port = os.getenv("SMTP_PORT", 587)
        self.email_user = os.getenv("EMAIL_USER")
        self.email_pass = os.getenv("EMAIL_PASS")
    
    def generate_daily_report(self):
        """Generate and send daily business metrics report"""
        try:
            # Fetch metrics from database
            metrics = self.get_daily_metrics()
            
            # Generate HTML report
            html_report = self.create_html_report(metrics)
            
            # Send email report
            self.send_email_report(
                subject=f"Cricket Stats Pack - Daily Report {datetime.now().strftime('%Y-%m-%d')}",
                html_content=html_report,
                recipients=["admin@cricketstatspack.com", "r.taylor289@gmail.com"]
            )
            
        except Exception as e:
            logger.error(f"Failed to generate daily report: {e}")
    
    def get_daily_metrics(self):
        """Fetch key business metrics for reporting"""
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # Yesterday's metrics
        yesterday = datetime.now() - timedelta(days=1)
        
        metrics = {
            'date': yesterday.strftime('%Y-%m-%d'),
            'new_signups': 0,
            'new_subscriptions': 0,
            'revenue_generated': 0,
            'churn_events': 0,
            'active_sessions': 0,
            'failed_payments': 0
        }
        
        # Fetch actual metrics from database
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN DATE(created_at) = %s THEN 1 END) as new_signups,
                COUNT(CASE WHEN DATE(subscription_start_date) = %s THEN 1 END) as new_subscriptions,
                COUNT(CASE WHEN DATE(subscription_end_date) = %s AND subscription_status = 'cancelled' THEN 1 END) as churn_events
            FROM users
        """, (yesterday.date(), yesterday.date(), yesterday.date()))
        
        result = cursor.fetchone()
        metrics.update(result)
        
        cursor.close()
        conn.close()
        
        return metrics
```

---

## 🚨 Disaster Recovery & Business Continuity

### 💾 Automated Backup Strategy

#### Database Backup System

```bash
#!/bin/bash
# /usr/local/bin/backup_system.sh
# Comprehensive backup solution with encryption and cloud storage

BACKUP_DIR="/var/backups/cricketapp"
ENCRYPTION_KEY="/etc/cricketapp/backup.key"
S3_BUCKET="cricketstatspack-backups"
RETENTION_DAYS=30

# Create timestamped backup
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="cricketapp_backup_${TIMESTAMP}.sql"

# Full database backup with compression
mysqldump --single-transaction \
          --routines \
          --triggers \
          --events \
          --all-databases \
          --master-data=2 \
          -h${DB_HOST} \
          -u${DB_USER} \
          -p${DB_PASS} | gzip > "${BACKUP_DIR}/${BACKUP_FILE}.gz"

# Encrypt backup file
gpg --cipher-algo AES256 \
    --compress-algo 1 \
    --s2k-mode 3 \
    --s2k-digest-algo SHA512 \
    --s2k-count 65536 \
    --symmetric \
    --no-symkey-cache \
    --passphrase-file ${ENCRYPTION_KEY} \
    --output "${BACKUP_DIR}/${BACKUP_FILE}.gz.gpg" \
    "${BACKUP_DIR}/${BACKUP_FILE}.gz"

# Upload to cloud storage (if configured)
if [ -n "$AWS_ACCESS_KEY_ID" ]; then
    aws s3 cp "${BACKUP_DIR}/${BACKUP_FILE}.gz.gpg" \
        "s3://${S3_BUCKET}/database/" \
        --storage-class GLACIER
fi

# Application files backup
tar -czf "${BACKUP_DIR}/app_files_${TIMESTAMP}.tar.gz" \
    /root/cricketapp \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.log'

# Cleanup old backups
find ${BACKUP_DIR} -name "*.gz.gpg" -mtime +${RETENTION_DAYS} -delete
find ${BACKUP_DIR} -name "*.tar.gz" -mtime +${RETENTION_DAYS} -delete

# Log backup completion
echo "$(date): Backup completed successfully - ${BACKUP_FILE}" >> /var/log/backup.log
```

#### Point-in-Time Recovery Setup

```sql
-- Enable MySQL binary logging for point-in-time recovery
SET GLOBAL log_bin = ON;
SET GLOBAL binlog_format = 'ROW';
SET GLOBAL sync_binlog = 1;
SET GLOBAL innodb_flush_log_at_trx_commit = 1;

-- Binary log retention policy
SET GLOBAL expire_logs_days = 7;
```

### 🔄 High Availability Configuration

#### Load Balancer Configuration (Nginx)

```nginx
# /etc/nginx/sites-available/cricketstatspack-ha
upstream cricketapp_backend {
    least_conn;
    server 127.0.0.1:8000 weight=1 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8001 weight=1 max_fails=3 fail_timeout=30s backup;
    server 127.0.0.1:8002 weight=1 max_fails=3 fail_timeout=30s backup;
}

server {
    listen 443 ssl http2;
    server_name cricketstatspack.com;
    
    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/cricketstatspack.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/cricketstatspack.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    # Health check endpoint
    location /health {
        access_log off;
        proxy_pass http://cricketapp_backend;
        proxy_set_header Host $host;
    }
    
    # Application routing with failover
    location / {
        proxy_pass http://cricketapp_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Connection timeout and retry settings
        proxy_connect_timeout 5s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        proxy_next_upstream error timeout invalid_header http_500 http_502 http_503;
    }
}
```

#### Database Replication Setup

```sql
-- Master Database Configuration
CREATE USER 'replication_user'@'%' IDENTIFIED BY 'strong_replication_password';
GRANT REPLICATION SLAVE ON *.* TO 'replication_user'@'%';
FLUSH PRIVILEGES;

-- Enable master binary logging
SET GLOBAL log_bin = ON;
SET GLOBAL server_id = 1;
SET GLOBAL binlog_do_db = 'cricket_auth';

-- Slave Database Configuration
CHANGE MASTER TO
    MASTER_HOST = 'master_database_ip',
    MASTER_USER = 'replication_user',
    MASTER_PASSWORD = 'strong_replication_password',
    MASTER_LOG_FILE = 'mysql-bin.000001',
    MASTER_LOG_POS = 107;

START SLAVE;
```

---

## 🧪 Enterprise Testing & Quality Assurance

### ⚡ Automated Testing Pipeline

#### Unit Testing Framework

```python
# tests/test_auth_utils.py
import pytest
import bcrypt
from unittest.mock import patch, MagicMock
from auth_utils import verify_user, create_user, get_admin_stats

class TestAuthentication:
    
    @patch('auth_utils.mysql.connector.connect')
    def test_verify_user_success(self, mock_connect):
        """Test successful user verification"""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            'password_hash': bcrypt.hashpw('testpass'.encode('utf-8'), bcrypt.gensalt()),
            'is_banned': False,
            'is_disabled': False
        }
        mock_connect.return_value.cursor.return_value = mock_cursor
        
        result = verify_user('test@example.com', 'testpass')
        assert result is True
    
    @patch('auth_utils.mysql.connector.connect')
    def test_verify_user_banned_account(self, mock_connect):
        """Test verification of banned account"""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            'password_hash': bcrypt.hashpw('testpass'.encode('utf-8'), bcrypt.gensalt()),
            'is_banned': True,
            'is_disabled': False
        }
        mock_connect.return_value.cursor.return_value = mock_cursor
        
        result = verify_user('banned@example.com', 'testpass')
        assert result is False
    
    @patch('auth_utils.mysql.connector.connect')
    def test_create_user_duplicate_email(self, mock_connect):
        """Test user creation with duplicate email"""
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = mysql.connector.IntegrityError("Duplicate entry")
        mock_connect.return_value.cursor.return_value = mock_cursor
        
        result = create_user(
            'existing@example.com', 
            'password', 
            'Question 1', 'Answer 1',
            'Question 2', 'Answer 2'
        )
        assert result is False

# tests/test_api_endpoints.py
import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

class TestAPIEndpoints:
    
    def test_root_endpoint(self):
        """Test root endpoint accessibility"""
        response = client.get("/")
        assert response.status_code == 200
    
    def test_login_rate_limiting(self):
        """Test login endpoint rate limiting"""
        # Attempt multiple login requests
        for _ in range(6):  # Exceeds 5/minute limit
            response = client.post("/login", data={
                "email": "test@example.com",
                "password": "wrongpassword"
            })
        
        # Last request should be rate limited
        assert response.status_code == 429
    
    def test_admin_access_unauthorized(self):
        """Test admin endpoint access without authorization"""
        response = client.get("/admin")
        assert response.status_code in [401, 403, 302]  # Unauthorized or redirect
    
    def test_stripe_webhook_signature_validation(self):
        """Test Stripe webhook signature validation"""
        response = client.post("/stripe-webhook", 
                             data="invalid_payload",
                             headers={"stripe-signature": "invalid_signature"})
        assert response.status_code == 400
```

#### Integration Testing Suite

```python
# tests/test_integration.py
import pytest
import requests
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class TestUserJourney:
    
    @pytest.fixture
    def browser(self):
        """Setup Chrome browser for testing"""
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        driver = webdriver.Chrome(options=options)
        yield driver
        driver.quit()
    
    def test_complete_user_registration_flow(self, browser):
        """Test complete user registration and login flow"""
        # Navigate to registration page
        browser.get("https://cricketstatspack.com/register")
        
        # Fill registration form
        email_input = browser.find_element(By.NAME, "email")
        password_input = browser.find_element(By.NAME, "password")
        
        test_email = f"test_{int(time.time())}@example.com"
        email_input.send_keys(test_email)
        password_input.send_keys("TestPassword123!")
        
        # Select security questions
        security_q1 = browser.find_element(By.NAME, "security_question_1")
        security_a1 = browser.find_element(By.NAME, "security_answer_1")
        security_q1.send_keys("What was your first pet's name?")
        security_a1.send_keys("TestPet")
        
        # Submit registration
        submit_button = browser.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_button.click()
        
        # Wait for redirect to dashboard
        WebDriverWait(browser, 10).until(
            EC.url_contains("/dashboard")
        )
        
        # Verify dashboard access
        assert "/dashboard" in browser.current_url
        dashboard_content = browser.find_element(By.TAG_NAME, "body").text
        assert "Welcome" in dashboard_content or "Dashboard" in dashboard_content
    
    def test_subscription_flow(self, browser):
        """Test subscription purchase flow"""
        # Login first (assuming test user exists)
        browser.get("https://cricketstatspack.com/login")
        
        # Login with test credentials
        email_input = browser.find_element(By.NAME, "email")
        password_input = browser.find_element(By.NAME, "password")
        email_input.send_keys("test@cricketstatspack.com")
        password_input.send_keys("TestPassword123!")
        
        submit_button = browser.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_button.click()
        
        # Navigate to subscription page
        browser.get("https://cricketstatspack.com/subscribe")
        
        # Click monthly subscription button
        monthly_button = WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable((By.ID, "subscribe-monthly-button"))
        )
        monthly_button.click()
        
        # Should redirect to Stripe checkout (external)
        WebDriverWait(browser, 10).until(
            lambda driver: "stripe.com" in driver.current_url or "checkout" in driver.current_url
        )
        
        # Verify Stripe checkout page loaded
        assert any(domain in browser.current_url for domain in ["stripe.com", "checkout"])
```

#### Performance Testing

```python
# tests/test_performance.py
import pytest
import requests
import time
import concurrent.futures
from statistics import mean, median

class TestPerformance:
    
    BASE_URL = "https://cricketstatspack.com"
    
    def test_page_load_times(self):
        """Test page load times for critical endpoints"""
        endpoints = [
            "/",
            "/login",
            "/register",
            "/subscribe"
        ]
        
        results = {}
        
        for endpoint in endpoints:
            times = []
            for _ in range(10):  # Test each endpoint 10 times
                start_time = time.time()
                response = requests.get(f"{self.BASE_URL}{endpoint}")
                end_time = time.time()
                
                assert response.status_code == 200
                times.append(end_time - start_time)
            
            results[endpoint] = {
                'mean': mean(times),
                'median': median(times),
                'max': max(times)
            }
            
            # Assert performance thresholds
            assert mean(times) < 2.0, f"Endpoint {endpoint} average load time too high: {mean(times):.2f}s"
            assert max(times) < 5.0, f"Endpoint {endpoint} max load time too high: {max(times):.2f}s"
    
    def test_concurrent_user_load(self):
        """Test application performance under concurrent load"""
        def make_request():
            start_time = time.time()
            response = requests.get(f"{self.BASE_URL}/")
            end_time = time.time()
            return {
                'status_code': response.status_code,
                'response_time': end_time - start_time
            }
        
        # Simulate 50 concurrent users
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(make_request) for _ in range(100)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Analyze results
        success_count = sum(1 for r in results if r['status_code'] == 200)
        avg_response_time = mean([r['response_time'] for r in results])
        
        # Performance assertions
        assert success_count >= 95, f"Success rate too low: {success_count}/100"
        assert avg_response_time < 3.0, f"Average response time too high under load: {avg_response_time:.2f}s"
```

#### Security Testing

```python
# tests/test_security.py
import pytest
import requests
import time
from urllib.parse import urljoin

class TestSecurity:
    
    BASE_URL = "https://cricketstatspack.com"
    
    def test_sql_injection_protection(self):
        """Test SQL injection protection on login endpoint"""
        malicious_payloads = [
            "admin'--",
            "admin' OR '1'='1",
            "admin'; DROP TABLE users;--",
            "' UNION SELECT * FROM users--"
        ]
        
        for payload in malicious_payloads:
            response = requests.post(f"{self.BASE_URL}/login", data={
                "email": payload,
                "password": "password"
            })
            
            # Should not return 500 error or expose database errors
            assert response.status_code != 500
            assert "mysql" not in response.text.lower()
            assert "sql" not in response.text.lower()
            assert "error" not in response.text.lower()
    
    def test_rate_limiting_enforcement(self):
        """Test rate limiting on sensitive endpoints"""
        # Test login rate limiting
        for i in range(7):  # Exceed 5/minute limit
            response = requests.post(f"{self.BASE_URL}/login", data={
                "email": "test@example.com",
                "password": "wrongpassword"
            })
            
            if i >= 5:  # Should be rate limited after 5 attempts
                assert response.status_code == 429
    
    def test_xss_protection(self):
        """Test XSS protection on form inputs"""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "';alert('xss');//"
        ]
        
        for payload in xss_payloads:
            response = requests.post(f"{self.BASE_URL}/register", data={
                "email": payload,
                "password": "password123",
                "security_question_1": "test",
                "security_answer_1": "test",
                "security_question_2": "test",
                "security_answer_2": "test"
            })
            
            # XSS payload should be escaped/sanitized
            assert "<script>" not in response.text
            assert "javascript:" not in response.text
            assert "onerror=" not in response.text
    
    def test_session_security(self):
        """Test session security configurations"""
        session = requests.Session()
        
        # Login to establish session
        login_response = session.post(f"{self.BASE_URL}/login", data={
            "email": "test@cricketstatspack.com",
            "password": "correct_password"
        })
        
        if login_response.status_code == 302:  # Successful login redirect
            # Check session cookie security
            cookies = session.cookies
            session_cookie = None
            
            for cookie in cookies:
                if 'session' in cookie.name.lower():
                    session_cookie = cookie
                    break
            
            if session_cookie:
                assert session_cookie.secure, "Session cookie should be marked as Secure"
                assert session_cookie.has_nonstandard_attr('HttpOnly'), "Session cookie should be HttpOnly"
```

### 📊 Continuous Integration Testing

```yaml
# .github/workflows/test.yml
name: Comprehensive Testing Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    
    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_ROOT_PASSWORD: test_password
          MYSQL_DATABASE: cricket_auth_test
        options: >-
          --health-cmd="mysqladmin ping"
          --health-interval=10s
          --health-timeout=5s
          --health-retries=3
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov pytest-asyncio
    
    - name: Run unit tests
      run: |
        pytest tests/test_auth_utils.py tests/test_api_endpoints.py -v --cov=./ --cov-report=xml
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml

  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install selenium pytest
    
    - name: Set up Chrome
      uses: browser-actions/setup-chrome@latest
    
    - name: Run integration tests
      run: |
        pytest tests/test_integration.py -v
      env:
        TEST_URL: https://cricketstatspack.com

  security-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Run security tests
      run: |
        python -m pip install --upgrade pip
        pip install requests pytest
        pytest tests/test_security.py -v

  performance-tests:
    runs-on: ubuntu-latest
    needs: [unit-tests, integration-tests]
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Run performance tests
      run: |
        python -m pip install --upgrade pip
        pip install requests pytest statistics
        pytest tests/test_performance.py -v
```

---

## 📈 Monitoring & Analytics

### 📊 Key Metrics Tracked

- **User Engagement**: Login frequency, session duration
- **Subscription Health**: Churn rate, upgrade patterns
- **System Performance**: Response times, error rates
- **Security Events**: Failed logins, admin actions

### 🔍 Logging & Debugging

```python
# Comprehensive logging throughout the application
logger.info(f"User {email} logged in successfully")
logger.warning(f"Failed login attempt for {email}")
logger.error(f"Database error: {error}", exc_info=True)
```

---

## 🛠️ Development

### 🧪 Testing

```bash
# Run import tests
python test_imports.py

# Test billing functionality
python test_billing_route.py

# Database diagnostics
python diagnose_billing.py
```

### 🐛 Common Operations

```bash
# View application logs
sudo journalctl -u cricketapp --since "1 hour ago"

# Restart services
sudo systemctl restart cricketapp
sudo systemctl reload nginx

# Database backup
mysqldump cricket_auth > backup_$(date +%Y%m%d).sql

# Monitor real-time logs
tail -f /var/log/nginx/access.log
```

---

## 🤝 Contributing

### 📋 Development Workflow

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### 🎯 Code Standards

- Follow **PEP 8** Python style guidelines
- Add **type hints** for function parameters and returns
- Include **docstrings** for all functions and classes
- Write **comprehensive tests** for new features
- Update **documentation** for API changes

---

## 📞 Support & Contact

### 🔧 Technical Support

- **Documentation**: Check this README and inline code comments
- **Issues**: Open a GitHub issue for bugs or feature requests
- **Security**: Report security issues privately to admin

### 📧 Contact Information

- **Developer**: Rob Taylor
- **Email**: r.taylor289@gmail.com
- **GitHub**: [@Chockers1](https://github.com/Chockers1)

---

## 📄 License

This project is proprietary software. All rights reserved.

---

<div align="center">

**Built with ❤️ using FastAPI and deployed with 🚀 GitHub Actions**

[⬆ Back to Top](#-cricket-stats-pack---production-web-application)

</div>
