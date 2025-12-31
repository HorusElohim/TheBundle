import pytest
from pydantic import ValidationError

from bundle.usd.model import LoadScene, SceneInfo
from bundle.usd import backend as usd_backend


def test_scene_info_validation():
    info = SceneInfo(prim_count=12, layer_count=3, meters_per_unit=0.01, up_axis="Y")
    assert info.prim_count == 12
    assert info.layer_count == 3
    assert info.meters_per_unit == 0.01
    assert info.up_axis == "Y"


def test_load_scene_requires_path():
    with pytest.raises(ValidationError):
        LoadScene(path="")


def test_backend_missing_pxr(monkeypatch):
    backend = usd_backend.USDBackend()

    def raise_missing():
        raise usd_backend.MissingUSDBackend("pxr missing")

    monkeypatch.setattr(usd_backend, "_require_pxr", raise_missing)

    with pytest.raises(usd_backend.MissingUSDBackend):
        backend.open("scene.usd")
