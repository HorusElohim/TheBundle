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

import os
from pathlib import Path

from bundle.core import platform_info


def get_app_data_path(app_name: str) -> Path:

    match platform_info.system:
        case "windows":
            app_data_dir = Path(os.environ["APPDATA"]) / app_name
        case "darwin":
            app_data_dir = Path.home() / "Library/Application Support" / app_name
        case "linux":
            app_data_dir = Path.home() / ".local/share" / app_name
        case _:
            raise ValueError(f"Unsupported platform: {platform_info.system}")

    app_data_dir.mkdir(parents=True, exist_ok=True)
    return app_data_dir


YOUTUBE_PATH = get_app_data_path("bundle.youtube")
POTO_TOKEN_PATH = YOUTUBE_PATH / "poto_token.json"
