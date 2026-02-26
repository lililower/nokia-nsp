import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nokia_nsp.settings")

application = get_wsgi_application()
