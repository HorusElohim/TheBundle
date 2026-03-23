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

import torch
from ppisp import PPISP

from bundle import core

log = core.logger.setup_root_logger(name="ppisp.smoke", level=core.logger.Level.INFO)


def main() -> None:
    assert torch.cuda.is_available(), "CUDA is not available in the ppisp container."
    h, w, d = 8, 8, "cuda"
    xy = torch.stack(
        torch.meshgrid(torch.arange(h, device=d), torch.arange(w, device=d), indexing="ij")[::-1],
        -1,
    ).float()
    rgb = torch.rand((h, w, 3), device=d)
    with torch.no_grad():
        out = PPISP(num_cameras=1, num_frames=2).to(d)(rgb, xy, (w, h), 0, 0)
    assert out.shape == rgb.shape and torch.isfinite(out).all(), "Invalid PPISP output."
    log.info(
        "torch=%s cuda=%s available=%s",
        torch.__version__,
        torch.version.cuda,
        torch.cuda.is_available(),
    )
    log.info(
        "ppisp forward ok shape=%s dtype=%s device=%s",
        tuple(out.shape),
        out.dtype,
        out.device,
    )


if __name__ == "__main__":
    main()
