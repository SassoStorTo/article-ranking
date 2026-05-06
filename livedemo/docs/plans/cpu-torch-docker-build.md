# CPU Torch Docker Build Plan

1. Update `livedemo/docker/backend.Dockerfile` so the image build re-resolves
   `torch` against PyTorch's CPU wheel index during `uv sync --no-dev`.
2. Verify with a Linux-targeted `uv sync --dry-run` that the resolver selects
   `torch==2.11.0+cpu` and no `nvidia-*` or `triton` packages.
3. Copy the corrected repo to the remote server without macOS AppleDouble files.
4. Run the remote Compose build command to confirm the backend image builds.
