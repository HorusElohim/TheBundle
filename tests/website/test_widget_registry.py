from bundle.website import widgets


def test_widget_registry_exposes_websocket_base():
    base = widgets.get("ws-websocket-base")
    assert base is not None
    assert base.abstract is True
    assert base.ws_path == "/ws/ecc"


def test_widget_registry_composes_websocket_defaults():
    heartbeat = widgets.get("ws-heartbeat")
    assert heartbeat is not None
    assert heartbeat.extends == "ws-websocket-base"
    assert heartbeat.ws_path == "/ws/ecc"
    assert any(asset.path.endswith("heartbeat/frontend/ws.js") for asset in heartbeat.assets)
    assert all(asset.route_name == "widgets_static" for asset in heartbeat.assets)


def test_widget_registry_hides_abstract_widgets_from_default_collection():
    slugs = {widget.slug for widget in widgets.widgets()}
    assert "ws-websocket-base" not in slugs
    assert {"ws-ecc", "ws-heartbeat", "ws-toast"}.issubset(slugs)
