# Repo Blueprint Studio macOS App

This package is a native macOS desktop shell for the existing Repo Blueprint Studio web app.

## Architecture

- The React frontend in `../frontend` remains the single shared UI implementation.
- The FastAPI backend in `../backend` remains the single shared backend implementation.
- This `macos-app` package only wraps those shared layers in Electron.

That means future product changes should continue to be made in `frontend/` and `backend/`, and the macOS app will inherit them automatically.

## Development

1. Start the shared backend:
   `cd ../backend && ./.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8002`
2. Start the shared frontend:
   `cd ../frontend && npm run dev -- --host 127.0.0.1`
3. Start the macOS shell:
   `cd macos-app && npm run dev`

By default, the Electron app loads `http://127.0.0.1:3000/` in development mode.

## Packaging

1. Install desktop dependencies:
   `cd macos-app && npm install`
2. Build the shared frontend:
   `npm run build:web`
3. Build the macOS package:
   `npm run package`

The packaged app loads the built frontend from `../frontend/dist` and starts the shared backend locally on `127.0.0.1:8002`.
