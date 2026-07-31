# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Defines typed VibesMeet validation, authentication, conflict, and remote-response errors for predictable boundary handling.
# Documentation: Inline comments explain intent; executable behavior is unchanged.

"""
Defines typed VibesMeet validation, authentication, conflict, and remote-response errors for predictable boundary handling.

Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
"""

class VibesMeetError(RuntimeError):
    """Base exception for failures at the VibesMeet integration boundary."""


class VibesMeetValidationError(VibesMeetError):
    """Signal invalid local input before any VibesMeet request is sent."""


class VibesMeetAuthError(VibesMeetError):
    """Signal rejected or missing VibesMeet authentication."""


class VibesMeetConflictError(VibesMeetError):
    """Signal an idempotency or remote-state conflict returned by VibesMeet."""


class VibesMeetRemoteError(VibesMeetError):
    """Preserve an unexpected VibesMeet HTTP response for controlled handling and diagnostics."""

    def __init__(self, message: str, *, status_code: int | None = None, body: object = None):
        """
        Capture the remote status code and response body alongside the integration error message.
        
        Args:
            message: Queue, webhook, or validation message being processed.
            status_code: HTTP status returned by the remote service.
            body: Decoded response or error body returned by the remote service.
        """
        super().__init__(message)
        self.status_code = status_code
        self.body = body
