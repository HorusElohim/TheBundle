# Website Pod

This pod starts the Bundle website with:

```bash
bundle website site start bundle --host 0.0.0.0 --port 8000
```

It uses `thebundle/bases/cpu` as its base image.

## Usage

```bash
bundle pods build services/website
bundle pods run services/website
bundle pods logs services/website
bundle pods status services/website
```

Open `http://localhost:8000`.

### Dev mode

Mounts local source for fast iteration — no rebuild needed:

```bash
docker compose --profile dev up website-dev
```

## Notes

- The image intentionally omits extra system packages to stay small.
- Frontend build tooling is not required at runtime; the pod serves the checked-in website assets.
