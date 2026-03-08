# Website Pod

This pod starts the Bundle website with:

```bash
bundle website site start bundle --host 0.0.0.0 --port 8000
```

It uses a multi-stage `python:3.12-slim` image to keep the runtime small while still installing the package and its `website` dependencies from local source.

## Usage

```bash
bundle pods build website
bundle pods run website
bundle pods logs website
bundle pods status website
```

Open `http://localhost:8000`.

## Notes

- The image intentionally omits extra system packages to stay small.
- Frontend build tooling is not required at runtime; the pod serves the checked-in website assets.
