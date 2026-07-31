# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Exposes the WSGI application used by Gunicorn and other production-compatible Python web servers.
# Documentation: Inline comments explain intent; executable behavior is unchanged.

"""
Exposes the WSGI application used by Gunicorn and other production-compatible Python web servers.

Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = get_wsgi_application()
