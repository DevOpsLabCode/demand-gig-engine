"""Contract-first VibesMeet integration bridge.

The public VibesMeet API contract is not assumed by this package. All endpoint
paths are configurable and the proposed contract is documented under docs/.
"""

from .client import VibesMeetClient, VibesMeetConfig
from .exceptions import (
    VibesMeetAuthError,
    VibesMeetConflictError,
    VibesMeetError,
    VibesMeetRemoteError,
    VibesMeetValidationError,
)

__all__ = [
    "VibesMeetClient",
    "VibesMeetConfig",
    "VibesMeetError",
    "VibesMeetAuthError",
    "VibesMeetConflictError",
    "VibesMeetRemoteError",
    "VibesMeetValidationError",
]
