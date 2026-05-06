# Local Demo Control Plan

1. Add a livedemo control script with `start`, `watch`, `status`, `kill`, and
   `restart` commands.
2. Store PID and log files under an ignored `.run/` directory.
3. Start the backend via `uv run --no-project` with only web dependencies so
   PyTorch is not installed for the skeleton demo.
4. Start the frontend via `npm install` when needed, then `npm run dev`.
