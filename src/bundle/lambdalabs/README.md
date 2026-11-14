# bundle.lambdalabs

Lambda Labs cloud GPU integration for TheBundle.

Provides a Python API and CLI for launching GPU instances, running remote jobs,
managing SSH keys, and using persistent filesystems — purpose-built for the
`bundle recon3d` training pipeline.

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
5. Creating a persistent filesystem (recommended — avoids re-uploading datasets)
6. Choosing an instance type and launching

---

## Manual setup

### 1. Save your API key

```bash
bundle lambdalabs setup \
  --api-key YOUR_KEY \
  --ssh-key my-ssh-key-name \
  --filesystem bundle-recon3d    # optional: default persistent filesystem
```

Or export env vars:

```bash
export LAMBDA_API_KEY=your_key_here
export LAMBDA_FILESYSTEM=bundle-recon3d   # optional
```

Config is stored at `~/.bundle/lambdalabs.json`.

### 2. Add your SSH public key

```bash
# Add ~/.ssh/id_rsa.pub (default)
bundle lambdalabs keys add --name my-key

# Or specify a different key
bundle lambdalabs keys add --name my-key --pub-key ~/.ssh/id_ed25519.pub
```

### 3. Create a persistent filesystem (recommended)

A filesystem is a persistent NFS volume that survives instance termination.
Images and SfM output are uploaded **once** and reused across jobs — no
re-uploading gigabytes of photos every run.

```bash
# Create and save as default
bundle lambdalabs filesystems create --name bundle-recon3d

# List filesystems in your account
bundle lambdalabs filesystems list
```

The filesystem is automatically mounted at `/home/ubuntu/<name>/` on every
instance that requests it. Cost: ~$0.20/GiB/month.

### 4. Browse available GPU types

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

### 5. Launch an instance

```bash
# Launch with a persistent filesystem mounted
bundle lambdalabs instances launch \
  --type gpu_1x_a10 \
  --key my-key \
  --name recon3d-job \
  --filesystem bundle-recon3d

# Launch without waiting
bundle lambdalabs instances launch --type gpu_1x_a10 --key my-key --no-wait
```

### 6. List active instances

```bash
bundle lambdalabs instances list
```

### 7. Terminate an instance

```bash
bundle lambdalabs instances terminate INSTANCE_ID
```

---

## Running recon3d on Lambda

Gaussian splatting training requires CUDA. Use Lambda to train in the cloud,
then visualize locally (Metal / CPU / CUDA — any platform).

### Full pipeline (SfM → Train on Lambda → Visualize locally)

```bash
# First run: uploads images + SfM output to persistent filesystem
bundle recon3d run \
  --workspace ./ws \
  --lambda \
  --filesystem bundle-recon3d \
  --auto-terminate

# Subsequent runs: skips re-uploading unchanged files (--ignore-existing)
bundle recon3d run \
  --workspace ./ws \
  --lambda \
  --filesystem bundle-recon3d \
  --auto-terminate

# Attach to an already-running instance
bundle recon3d run \
  --workspace ./ws \
  --lambda \
  --instance-id abc123 \
  --filesystem bundle-recon3d
```

### Training only on Lambda

```bash
bundle recon3d gaussians \
  --workspace ./ws \
  --lambda \
  --filesystem bundle-recon3d \
  --auto-terminate
```

### Local preview after Lambda training (Metal / CPU / CUDA)

```bash
bundle recon3d visualize --workspace ./ws --experiment default
```

---

## Persistent filesystem workflow

```
First job                        Subsequent jobs
─────────────────────────────    ────────────────────────────────
upload images → NFS              rsync --ignore-existing (fast)
upload SfM sparse → NFS          rsync --ignore-existing (fast)
run training on NFS data          run training on NFS data
download results → local          download results → local
terminate instance                terminate instance
NFS persists  ✓                  NFS persists  ✓
```

The `filesystem_name` is resolved from (in priority order):
1. `--filesystem` CLI flag / `LAMBDA_FILESYSTEM` env var
2. `default_filesystem` in `~/.bundle/lambdalabs.json`
3. No filesystem — workspace uploaded to ephemeral instance storage

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

        # List filesystems
        fss = await client.filesystems()
        for fs in fss:
            print(f"{fs.name} → {fs.path}")

        # Create filesystem
        fs = await client.create_filesystem("bundle-recon3d", region_name="us-east-1")

        # Launch with filesystem mounted
        ids = await client.launch(
            instance_type_name="gpu_1x_a10",
            ssh_key_names=["my-key"],
            name="my-job",
            file_system_names=["bundle-recon3d"],
        )

        # Wait for active
        instance = await client.wait_active(ids[0])
        print(f"Ready: {instance.ip}")

        # Terminate
        await client.terminate([instance.id])

    # --- High-level RemoteJob ---
    job = RemoteJob(
        auto_terminate=True,
        filesystem_name="bundle-recon3d",  # enables --ignore-existing on upload
    )
    await job.launch()                     # reads ~/.bundle/lambdalabs.json for defaults
    await job.wait()
    await job.setup()                      # installs bundle on remote
    await job.upload(Path("./workspace"), Path("/home/ubuntu/job1"))
    await job.run("bundle recon3d gaussians --workspace /home/ubuntu/job1 --renderer 3dgut")
    await job.download(Path("/home/ubuntu/job1/runs"), Path("./workspace/runs"))
    # terminate() called automatically when auto_terminate=True

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
  "default_instance_type": "gpu_1x_a10",
  "default_filesystem": "bundle-recon3d"
}
```

All fields can also be set via environment variables:

| Env var              | Purpose                                        |
|----------------------|------------------------------------------------|
| `LAMBDA_API_KEY`     | Lambda Labs API key                            |
| `LAMBDA_INSTANCE_ID` | Attach to an existing instance instead of launching |
| `LAMBDA_FILESYSTEM`  | Persistent filesystem name for workspace storage |

---

## Module structure

```
bundle/lambdalabs/
├── __init__.py     # Public API exports
├── client.py       # Async httpx REST client (Lambda Labs API v1)
├── config.py       # LambdaLabsConfig — persisted at ~/.bundle/lambdalabs.json
├── models.py       # Pydantic models: Instance, InstanceType, SshKey, Filesystem, etc.
├── runner.py       # RemoteJob — full job lifecycle management
├── cli.py          # bundle lambdalabs CLI
└── README.md       # This file
```
