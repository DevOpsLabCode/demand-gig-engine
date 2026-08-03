# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Serves the dependency-free load-balancer liveness probe before host-sensitive middleware.

"""Middleware used for infrastructure-only liveness checks."""

from django.http import JsonResponse


class LivenessMiddleware:
    """Return the API liveness response before tracing or host validation runs."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # ALB health checks use the target's private IP in the Host header.
        # Bypass host-sensitive middleware only for this exact public probe;
        # every application route still uses Django's configured ALLOWED_HOSTS.
        if request.method == "GET" and request.path_info == "/api/health/":
            return JsonResponse(
                {"status": "ok", "service": "demand-gig-backend"}
            )

        return self.get_response(request)
