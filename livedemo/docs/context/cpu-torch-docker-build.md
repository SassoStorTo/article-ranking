# CPU Torch Docker Build Context

The backend Docker build runs `uv sync --no-dev` inside
`livedemo/docker/backend.Dockerfile`. The livedemo package depends on the local
`news-ranker` package, and `news-ranker` depends on `sentence-transformers`.
On Linux, the default PyPI `torch` resolution pulls CUDA-oriented packages such
as `nvidia-*` and `triton`, which exhausted disk space while extracting
`triton`.

The livedemo container does not need GPU acceleration for local development.
`uv sync` can be given PyTorch's CPU wheel index and asked to re-resolve only
`torch` during the image build. A dry run with those flags resolved
`torch==2.11.0+cpu` and omitted the CUDA packages and `triton`.
