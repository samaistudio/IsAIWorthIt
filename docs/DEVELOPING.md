# Developing IsAIWorthIt

## Layout

| Path | What it is |
|---|---|
| `isaiworthit.py` | Command line: dashboard, `init`, `sync`, `sources`, `reports`, `mcp`, `site` |
| `core/` | Standard-library Python: connectors, measurement, demo data, per-reader views, MCP server |
| `ui/` | React + TypeScript + Tailwind 4 source of the dashboard |
| `web/index.html` | The built dashboard (one self-contained file, committed so users never need Node) |
| `odoo_module/isaiworthit` | The Odoo 18 app |
| `docs/tutorial` | The guided tour and an example report file |
| `tests/` | Standard-library tests for `core/` and the command line |

## Tests

```bash
python3 -m unittest discover -s tests -t .          # Python 3.10+, no packages
cd ui && npm ci && npx tsc --noEmit                 # type check of the dashboard
docker compose -f odoo/docker-compose.yml run --rm odoo \
  odoo -d iaw_test -i isaiworthit --test-enable --test-tags /isaiworthit --stop-after-init
```

GitHub Actions runs the first two on every push (`.github/workflows/ci.yml`).

## Dashboard

```bash
cd ui && npm install && npm run build   # writes ../web/index.html
npm run dev                             # dev server; run `python3 isaiworthit.py` too, it serves /data
```

The Inter font is self-hosted in `ui/src/assets/fonts` and inlined by the build, so the page makes no request to another server.

Link parameters:

| Parameter | Effect |
|---|---|
| `?b=hotel` | open one business (slug from the menu) |
| `?as=everyone`, `?as=team:Support` | open a view |
| `?page=odoo`, `?page=sources`, `?page=access` | open a tab |
| `?theme=dark`, `?theme=light` | force a theme (default: follow the system) |
| `?compact=1` | start the parts below the chart closed (for a short embed) |
| `#licences`, `#teams`, `#tasks`, `#pay`, `#calc`, `#next` | jump to that part |

## Demo website

```bash
python3 isaiworthit.py site _site   # dashboard, demo data and guided tour
```

The folder is emptied first, so the command only accepts a new or empty folder or an earlier site. `.github/workflows/pages.yml` runs it on every push to `main` and publishes the result with GitHub Pages.
