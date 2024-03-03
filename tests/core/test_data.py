# Copyright 2023 HorusElohim

# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership. The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at

#   http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import pytest
import bundle

bundle.testing.TEST_LOGGER.debug("testing pydantic data")

DATA_CLASSES_TO_TEST = [
    bundle.core.Data,
    bundle.testing.classes.TestComplexData,
    bundle.testing.classes.TestComplexAtom,
    bundle.testing.classes.TestComplexAtomMultipleInheritance,
]


@pytest.mark.parametrize("dataclass", DATA_CLASSES_TO_TEST)
def test_dataclass(dataclass, cprofile_folder, reference_folder, tmp_path: bundle.Path):
    @bundle.testing.decorators.data(ref_dir=reference_folder, tmp_dir=tmp_path, cprofile_dump_dir=cprofile_folder)
    @bundle.testing.decorators.cprofile(cprofile_dump_dir=cprofile_folder)
    def data_default_init():
        return dataclass()

    data_default_init()
