class VibesMeetError(RuntimeError):
    """Base integration exception."""


class VibesMeetValidationError(VibesMeetError):
    """The local payload is incomplete or invalid."""


class VibesMeetAuthError(VibesMeetError):
    """Authentication or authorization failed."""


class VibesMeetConflictError(VibesMeetError):
    """Remote and local state cannot be safely merged automatically."""


class VibesMeetRemoteError(VibesMeetError):
    """The remote service returned an unexpected failure."""

    def __init__(self, message: str, *, status_code: int | None = None, body: object = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body
