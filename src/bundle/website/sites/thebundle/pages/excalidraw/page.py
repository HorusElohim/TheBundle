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

"""Excalidraw page route wiring."""

from fastapi import Request
from fastapi.responses import HTMLResponse

from bundle.website.core.templating import PageModule, base_context

page = PageModule(
    __file__,
    name="Excalidraw",
    description="Draw and brainstorm with the Excalidraw canvas.",
)


@page.router.get("/excalidraw", response_class=HTMLResponse)
async def excalidraw_page(request: Request):
    """Render the Excalidraw host page."""
    context = base_context(request, {"title": "Excalidraw"})
    return page.templates.TemplateResponse(request, "index.html", context)
