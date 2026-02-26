# Nokia NSP - Network Service Provisioner

A Django-based web application for managing Nokia SR OS 7750 routers via NETCONF/YANG. Provision VPLS services, monitor FDB/MAC tables, and manage device inventory through a clean web interface.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Django](https://img.shields.io/badge/Django-5.x-green)
![NETCONF](https://img.shields.io/badge/NETCONF-RFC6241-orange)
![Nokia SR OS](https://img.shields.io/badge/Nokia-SR--7750-004990)

## Features

### Device Management
- Device inventory with NETCONF connection details
- Encrypted credential storage (Fernet)
- One-click NETCONF connectivity testing
- Status tracking (online/offline/unknown)

### VPLS Service Provisioning
- Create VPLS services with SAPs (Service Access Points)
- Deploy/delete configurations across multiple devices via NETCONF
- Full deployment logging with config sent and device response
- Service lifecycle tracking (planned/deployed/failed/deleted)

### Monitoring
- **Dashboard** - Device count, service stats, recent deployments
- **FDB/MAC Table** - Live MAC address table per device with AJAX refresh and CSV export
- **Interfaces** - Port status, admin/oper state, speed, descriptions

### Access Control
- Role-based access: **Admin**, **Operator**, **Viewer**
- Admin: full access + user management
- Operator: device and service provisioning
- Viewer: read-only dashboards and tables

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Django 5.x |
| NETCONF | ncclient (Nokia SR OS / ALU) |
| Config Templates | Jinja2 (NETCONF XML) |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Frontend | Bootstrap 5.3, DataTables, jQuery |
| Encryption | Fernet (cryptography) |

## Project Structure

```
nokia-nsp/
├── nokia_nsp/              # Django project settings
├── apps/
│   ├── accounts/           # Authentication & user roles
│   ├── devices/            # Device inventory CRUD
│   ├── services/           # VPLS service provisioning
│   └── monitoring/         # Dashboard, FDB, interfaces
├── netconf_lib/            # NETCONF operations library
│   ├── connection.py       # NETCONF session manager
│   ├── nokia_vpls.py       # VPLS create/delete/SAP ops
│   ├── nokia_fdb.py        # FDB/MAC table retrieval
│   └── nokia_interfaces.py # Interface status retrieval
├── netconf_templates/      # Jinja2 NETCONF XML templates
│   ├── vpls_create.xml
│   ├── vpls_delete.xml
│   └── vpls_sap.xml
├── templates/              # Django HTML templates
└── static/                 # CSS, JS, images
```

## Quick Start

### Option A: Docker (Recommended)

```bash
docker run -d -p 8000:8000 \
  -e SECRET_KEY=your-secret-key \
  -e FERNET_KEY=your-fernet-key \
  -e DEBUG=True \
  -e DATABASE_DIR=/app/data \
  -v nokia-nsp-data:/app/data \
  lililower/nokia-nsp:latest
```

Or with docker-compose:

```bash
curl -O https://raw.githubusercontent.com/lililower/nokia-nsp/master/docker-compose.yml
docker compose up -d
```

Open `http://localhost:8000` - default login: **admin / admin123**

### Option B: Local Development

#### 1. Clone and install

```bash
git clone https://github.com/lililower/nokia-nsp.git
cd nokia-nsp
python -m pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set:
```env
SECRET_KEY=your-django-secret-key
DEBUG=True
FERNET_KEY=your-fernet-key
```

Generate a Fernet key:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 3. Initialize database

```bash
python manage.py makemigrations accounts devices services monitoring
python manage.py migrate
python manage.py createsuperuser
```

### 4. Run

```bash
python manage.py runserver
```

Open `http://localhost:8000` and log in.

## NETCONF Configuration

Devices connect via NETCONF (RFC 6241) with Nokia SR OS device parameters (`device_params: alu`). Default port is **830**. The app uses:

- `edit-config` with candidate datastore + commit for service provisioning
- `get` with subtree filters for state retrieval (FDB, interfaces)
- Nokia YANG namespace: `urn:nokia.com:sros:ns:yang:sr:conf` / `sr:state`

## Screenshots

> _Coming soon_

---

## Roadmap

### Phase 1 - Core Hardening
- [ ] Add EPIPE (L2 point-to-point) service type
- [ ] Add VPRN (L3 VPN) service type
- [ ] Service edit/modify with SAP add/remove on deployed services
- [ ] Bulk device import (CSV upload)
- [ ] Device group/site tagging

### Phase 2 - Monitoring & Visibility
- [ ] Real-time interface utilization (rx/tx counters, errors)
- [ ] Service health dashboard (per-service FDB count, SAP status)
- [ ] Auto-refresh polling for dashboard and FDB tables
- [ ] Interface traffic graphs (Chart.js)
- [ ] Alarm/event log viewer from Nokia devices
- [ ] LLDP/CDP neighbor discovery display

### Phase 3 - Configuration Management
- [ ] Config backup/restore per device
- [ ] Config diff viewer (running vs candidate vs saved)
- [ ] Configuration templates library (user-defined Jinja2 templates)
- [ ] Rollback support with saved config snapshots
- [ ] Batch config push to device groups

### Phase 4 - Operations & Automation
- [ ] Scheduled tasks (config backup, status polling) via Celery
- [ ] Webhook/email notifications on deployment success/failure
- [ ] REST API for external integrations
- [ ] Audit trail with detailed user activity logging
- [ ] Multi-tenancy (customer-scoped views)

### Phase 5 - Advanced Features
- [ ] Network topology map (D3.js / vis.js)
- [ ] YANG model browser
- [ ] gNMI/gRPC telemetry streaming support
- [ ] Integration with Nokia NSP / NFM-P northbound APIs
- [ ] Docker/docker-compose deployment
- [ ] PostgreSQL + Redis for production
- [ ] LDAP/RADIUS authentication

## Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes
4. Push and open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) for details.
