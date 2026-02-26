#!/bin/sh
set -e

# Run migrations on startup
python manage.py migrate --noinput

# Create default admin if no users exist
python manage.py shell -c "
from apps.accounts.models import User
if not User.objects.exists():
    u = User.objects.create_superuser('admin', 'admin@nokia-nsp.local', 'admin123')
    u.role = 'admin'
    u.save()
    print('Default admin user created (admin/admin123)')
else:
    print('Users exist, skipping admin creation')
"

exec "$@"
