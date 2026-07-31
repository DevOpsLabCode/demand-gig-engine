#!/usr/bin/env python
# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Provides Django command-line entry points for development, migrations, administration, and operational commands.
# Documentation: Inline comments explain intent; executable behavior is unchanged.

"""
Provides Django command-line entry points for development, migrations, administration, and operational commands.

Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
"""

import os
import sys

# Execute the command-line entry point only when this module is run directly.
if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
