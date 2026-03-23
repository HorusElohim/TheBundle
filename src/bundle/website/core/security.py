# Copyright 2026 HorusElohim
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

"""Security policies and middleware for website HTTP responses."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware

DEFAULT_CSP = "; ".join(
    [
        "default-src 'self'",
        "base-uri 'self'",
        "object-src 'none'",
        "frame-ancestors 'self'",
        "frame-src 'self'",
        "img-src 'self' data: blob: https://*.ytimg.com https://ytimg.com",
        "font-src 'self' data:",
        "style-src 'self'",
        "script-src 'self' https://unpkg.com https://esm.sh 'report-sample'",
        "worker-src 'self'",
        "connect-src 'self' ws: wss: https://esm.sh",
        "report-uri /csp-report",
    ]
)

EXCALIDRAW_CSP = "; ".join(
    [
        "default-src 'self' https://excalidraw.nyc3.cdn.digitaloceanspaces.com",
        "base-uri 'self'",
        "object-src 'none'",
        "frame-ancestors 'self'",
        "frame-src 'self'",
        "img-src 'self' data: blob: https:",
        "font-src 'self' data: https:",
        "style-src 'self' 'unsafe-inline' https:",
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://scripts.simpleanalyticscdn.com https://excalidraw.nyc3.cdn.digitaloceanspaces.com https://esm.sh 'report-sample'",
        "worker-src 'self' blob:",
        "connect-src 'self' ws: wss: https: https://esm.sh",
        "report-uri /csp-report",
    ]
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Apply per-route CSP to keep pages isolated and avoid script leakage."""

    async def dispatch(self, request, call_next):
        """Attach CSP and baseline security headers to each response."""
        response = await call_next(request)
        path = request.url.path
        is_excalidraw = path.startswith("/excalidraw")
        selected_csp = EXCALIDRAW_CSP if is_excalidraw else DEFAULT_CSP
        response.headers["Content-Security-Policy"] = selected_csp
        response.headers["Content-Security-Policy-Report-Only"] = selected_csp
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
