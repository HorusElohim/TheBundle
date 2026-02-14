from bundle.website import components


def test_component_registry_exposes_websocket_base():
    base = components.get_component("ws-websocket-base")
    assert base is not None
    assert base.abstract is True
    assert base.ws_path == "/ws/ecc"


def test_component_registry_composes_websocket_defaults():
    heartbeat = components.get_component("ws-heartbeat")
    assert heartbeat is not None
    assert heartbeat.extends == "ws-websocket-base"
    assert heartbeat.ws_path == "/ws/ecc"
    assert any(asset.path.endswith("heartbeat/frontend/ws.js") for asset in heartbeat.assets)
    assert all(asset.route_name == "components_static" for asset in heartbeat.assets)


def test_component_registry_hides_abstract_components_from_default_collection():
    slugs = {component.slug for component in components.components()}
    assert "ws-websocket-base" not in slugs
    assert {"ws-ecc", "ws-heartbeat", "ws-toast"}.issubset(slugs)
