# Monitor Pod

Monitoring stack bundle with:
- `node-exporter`
- `gpu-exporter` (NVIDIA DCGM)
- `cadvisor`
- `prometheus`
- `grafana`
- `nginx` reverse proxy

## Usage

```bash
bundle pods build monitor
bundle pods run monitor
bundle pods logs monitor
bundle pods status monitor
```

Endpoints:
- Grafana via NGINX: `http://localhost/grafana/`
- Prometheus via NGINX: `http://localhost/prometheus/`
- Direct Grafana: `http://localhost:3000`
- Node Exporter: `http://localhost:9100/metrics`

## Notes

- Update `.env.grafana` before first run (`GF_SECURITY_ADMIN_PASSWORD`).
- `gpu-exporter` requires NVIDIA runtime/driver support.
