# Contributing to EmoVest

Thanks for considering a contribution. EmoVest is a local-first trading journal, so changes should protect privacy, make reflection easier, and never present financial advice as a product feature.

## Before you start

1. Search the [open issues](https://github.com/ELROKA02/EmoVest/issues) to avoid duplicate work.
2. For a sizeable feature or behavior change, open an issue first and describe the user problem it solves.
3. Read the [roadmap](ROADMAP.md) and keep contributions focused on one concern.

## Branches

| Branch | Purpose |
| --- | --- |
| `main` | Stable, releasable code |
| `develop` | Integration branch |
| `feature/*` | A focused new capability |
| `fix/*` | A focused bug fix |

Branch from `develop` unless the maintainer asks otherwise. Open pull requests back to `develop` and explain the user-facing effect, testing performed, and any privacy implications.

## Local development

The Windows desktop application combines React, Tauri, FastAPI, and local SQLite.

```powershell
cd backend
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt

cd ..
.\scripts\build-windows-sidecar.ps1

cd frontend
pnpm install
pnpm desktop:dev
```

Run the smallest relevant checks before opening a pull request. For interface changes, run `pnpm lint` and `pnpm build` from `frontend/`. If you change background AI work, also validate persistence, retries, and recovery after a restart.

## Contribution principles

- Keep changes small, documented, and easy to review.
- Do not add network calls, telemetry, or remote AI behavior without making the data flow explicit and optional.
- Keep emotional analysis indicative; do not add trading signals, financial advice, or promises of profitability.
- Add or update tests when behavior changes.
- Use clear, inclusive language in code, documentation, and issues.

## Reporting a security issue

Please do not disclose a suspected vulnerability in a public issue. Follow [SECURITY.md](SECURITY.md) instead.
