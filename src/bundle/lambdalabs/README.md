# bundle.lambdalabs

Lambda Labs cloud GPU integration for TheBundle.

Provides a Python API and CLI for launching GPU instances, running remote jobs,
and managing SSH keys — purpose-built for the `bundle recon3d` training pipeline.

---

## Quickstart (zero to running GPU in minutes)

```bash
bundle lambdalabs quickstart
```

This interactive wizard walks you through:

1. Creating a [Lambda Labs account](https://cloud.lambdalabs.com/sign-up)
2. Generating an API key at https://cloud.lambdalabs.com/api-keys
3. Saving credentials locally (`~/.bundle/lambdalabs.json`)
4. Adding your SSH public key to Lambda
5. Choosing an instance type and launching

---

## Manual setup

### 1. Save your API key

```bash
bundle lambdalabs setup --api-key YOUR_KEY --ssh-key my-ssh-key-name
```

Or export the env var:

```bash
export LAMBDA_API_KEY=your_key_here
```

Config is stored at `~/.bundle/lambdalabs.json`.

### 2. Add your SSH public key

```bash
# Add ~/.ssh/id_rsa.pub (default)
bundle lambdalabs keys add --name my-key

# Or specify a different key
bundle lambdalabs keys add --name my-key --pub-key ~/.ssh/id_ed25519.pub
```

### 3. Browse available GPU types

```bash
bundle lambdalabs types
```

Output:
```
┌─────────────────────┬────────────────────────────────┬───────┬───────────┬───────────────┬──────┐
│ Name                │ Description                    │ vCPUs │ RAM (GiB) │ Storage (GiB) │ $/hr │
├─────────────────────┼────────────────────────────────┼───────┼───────────┼───────────────┼──────┤
│ gpu_1x_a10          │ 1x A10 (24 GB)                 │    30 │       200 │          1500 │$0.75 │
│ gpu_1x_a100_sxm4    │ 1x A100 SXM4 (40 GB)           │    30 │       200 │          1500 │$1.29 │
│ gpu_8x_a100_80gb_sxm4│ 8x A100 SXM4 (80 GB)          │   240 │      1800 │         20480 │$14.32│
└─────────────────────┴────────────────────────────────┴───────┴───────────┴───────────────┴──────┘
```

### 4. Launch an instance

```bash
# Launch and wait for active
bundle lambdalabs instances launch --type gpu_1x_a10 --key my-key --name recon3d-job

# Launch without waiting
bundle lambdalabs instances launch --type gpu_1x_a10 --key my-key --no-wait
```

### 5. List active instances

```bash
bundle lambdalabs instances list
```

### 6. Terminate an instance

```bash
bundle lambdalabs instances terminate INSTANCE_ID
```

---

## Running recon3d on Lambda

### Full pipeline (SfM → Train on Lambda → Visualize locally)

```bash
# Uses config from ~/.bundle/lambdalabs.json
bundle recon3d run --workspace ./ws --lambda

# Attach to an already-running instance
bundle recon3d run --workspace ./ws --lambda --instance-id abc123

# Auto-terminate instance when done
bundle recon3d run --workspace ./ws --lambda --auto-terminate
```

### Training only on Lambda

```bash
bundle recon3d gaussians --workspace ./ws --lambda --instance-id abc123
```

### Local preview after Lambda training (Metal / CPU / CUDA)

```bash
bundle recon3d visualize --workspace ./ws --experiment default
```

---

## Python API

```python
import asyncio
from bundle.lambdalabs import LambdaClient, LambdaLabsConfig, RemoteJob
from pathlib import Path

async def main():
    # --- Low-level client ---
    async with LambdaClient(api_key="your_key") as client:
        # List instance types
        types = await client.instance_types()
        for name, it in types.items():
            print(f"{name}: ${it.price_per_hour:.2f}/hr")

        # Launch
        ids = await client.launch(
            instance_type_name="gpu_1x_a10",
            ssh_key_names=["my-key"],
            name="my-job",
        )

        # Wait for active
        instance = await client.wait_active(ids[0])
        print(f"Ready: {instance.ip}")

        # Terminate
        await client.terminate([instance.id])

    # --- High-level RemoteJob ---
    job = RemoteJob(auto_terminate=True)          # reads ~/.bundle/lambdalabs.json
    await job.launch(instance_type="gpu_1x_a10", ssh_key_name="my-key")
    await job.wait()
    await job.setup()                              # installs bundle on remote
    await job.upload(Path("./workspace"), Path("/home/ubuntu/job1"))
    await job.run("bundle recon3d gaussians --workspace /home/ubuntu/job1 --renderer 3dgut")
    await job.download(Path("/home/ubuntu/job1/runs"), Path("./workspace/runs"))
    await job.terminate()                          # auto_terminate=True handles this too

asyncio.run(main())
```

---

## Configuration reference

`~/.bundle/lambdalabs.json`:

```json
{
  "api_key": "your_lambda_api_key",
  "default_ssh_key": "my-key",
  "default_region": "us-east-1",
  "default_instance_type": "gpu_1x_a10"
}
```

All fields can also be set via environment variables:

| Env var              | Purpose                          |
|----------------------|----------------------------------|
| `LAMBDA_API_KEY`     | Lambda Labs API key              |
| `LAMBDA_INSTANCE_ID` | Attach to existing instance ID   |

---

## Module structure

```
bundle/lambdalabs/
├── __init__.py     # Public API exports
├── client.py       # Async httpx REST client (Lambda Labs API v1)
├── config.py       # LambdaLabsConfig — persisted at ~/.bundle/lambdalabs.json
├── models.py       # Pydantic models: Instance, InstanceType, SshKey, etc.
├── runner.py       # RemoteJob — full job lifecycle management
└── cli.py          # bundle lambdalabs CLI
```
