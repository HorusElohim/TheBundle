# Website Components

This package contains reusable UI components that can be attached to one or more pages.

## Structure

Each component is a complete folder that can include:

- `component.py`: Python `Data` class describing the component.
- `template.html`: HTML template rendered by page macros.
- `component.css`: component stylesheet (optional).
- `component.ts`: component TypeScript source (optional).
- `component.js`: built runtime script (optional).
- `assets/`: additional static assets (optional).

Example:

```text
components/websocket/toast/
  component.py
  template.html
  component.css
  component.ts
  component.js
```

Graphics foundations now live in `components/graphic/`:

- `components/graphic/base`: shared graphics component behavior.
- `components/graphic/twoD`: base for canvas/SVG style components.
- `components/graphic/threeD`: base for Three.js/WebGL style components.

## Registration model

Components are not globally activated by default. A page activates them explicitly.

```python
COMPONENTS = (
    ecc.WebSocketECCComponent(params=WebSocketComponentParams(endpoint="/ws/ecc-1")),
    heartbeat.WebSocketHeartbeatComponent(),
    toast.WebSocketToastComponent(),
)

components.attach_routes(router, *COMPONENTS)
```

This keeps routing page-scoped and avoids accidental global websocket endpoints.

## WebSocket base design

`components.websocket.base` provides shared building blocks:

- Frontend inheritance:
  - `WebSocketBaseComponent.shared_assets` declares shared assets using component-root paths.
  - `components/websocket/base/component.css` is loaded for all websocket components.
  - Templates use shared `ws-panel` structure classes and keep component classes for local theming.
  - Local websocket `component.css` files should focus on variables and necessary overrides only.
- `create_router(endpoint, handler)`:
  creates one websocket route and delegates to a handler.
- `run_websocket(websocket, *task_factories)`:
  shared lifecycle with task gather/cancellation.
- `every(seconds, tick)`:
  periodic loop helper.
- `drain_text(websocket)`:
  receive-and-discard helper for client messages.
- `receive_json(handler)`:
  JSON receive loop helper.
- `MessageRouter`:
  typed message dispatch by `Data` model `type`.

This yields small composable blocks instead of custom monolithic loops.

## Graphics + websocket composition

`components.websocket.base.GPXWebSocketBaseComponent` composes websocket and
graphics concerns:

- websocket route/lifecycle comes from `WebSocketBaseComponent`
- 3D graphics defaults come from `graphic.threeD.GraphicThreeDComponent`

Three.js heartbeat components (`heartbeat_earth`, `heartbeat_earth_moon`) use
this composed base.

## Typed websocket messages

`components.websocket.base.messages` contains typed `Data` models:

- `KeepAliveMessage`
- `AckMessage`
- `ErrorMessage`

All websocket payloads use `Data` serialization/deserialization helpers:

- parse with `await Message.from_dict(payload)`
- send with `await message.send(websocket)` (internally `as_dict`)

## Default and custom behavior

- `WebSocketBaseComponent` defines the default websocket behavior (`keepalive_loop`).
- Components that need custom runtime (for example toast server-push messages)
  override only `handle_websocket`, while keeping route wiring inherited.
