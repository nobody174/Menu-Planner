# Local-Only Feature Flags

Developer-only switches for features that are still being built and are
**not ready for public users yet**. Every flag defaults to OFF. The public
build (Render production) never has any of these set, so nothing here
changes what a real user sees unless you explicitly turn one on in your own
local `.env` file.

---

## Current flags

| Flag (env var) | Default | Gates |
|---|---|---|
| `FEATURE_DESSERTS_DRINKS` | off | F2: Dessert + drink browsing |
| `FEATURE_SIDE_STASH` | off | F8: Side stash feature |
| `FEATURE_DESSERT_PLANNER` | off | F9: Dessert system integrated into the dinner planner |

These map 1:1 to `FEATURE_FLAGS` in `deployment/flask_app.py`.

---

## Enabling a flag locally

Add the relevant line(s) to your own `.env` file (never commit this):

```
FEATURE_DESSERTS_DRINKS=true
```

Accepted "on" values (case-insensitive): `1`, `true`, `yes`, `on`. Anything
else — including leaving the variable unset entirely — is treated as off.
Restart the Flask process after changing `.env` for the change to take effect.

---

## Using a flag in code

Backend (routes): call `feature_enabled('desserts_drinks')` rather than
reading `FEATURE_FLAGS` directly — this keeps one place to change the lookup
logic later (e.g. a per-household override) without touching every call site.

```python
from deployment.flask_app import feature_enabled

if not feature_enabled('side_stash'):
    abort(404)
```

Templates: `feature_flags` is injected into every template's context via
`inject_config()`, so you can gate UI directly:

```jinja
{% if feature_flags.dessert_planner %}
  <!-- hidden planner UI -->
{% endif %}
```

---

## Safety notes

- If a flag somehow ends up set to a truthy value while `FLASK_ENV=production`,
  `flask_app.py` logs a loud warning at startup (`FEATURE_FLAGS` block, right
  after `IS_PRODUCTION` is defined) — this should never happen in practice,
  since Render's environment doesn't define these vars, but the warning is a
  cheap safety net in case someone copies `.env` values into production by mistake.
- Adding a new hidden feature: pick a new `FEATURE_<NAME>` env var, add it to
  the `FEATURE_FLAGS` dict in `flask_app.py`, and add a row to the table above.
- Don't gate anything security-sensitive behind a flag alone (e.g. don't rely
  on a flag to hide data a user shouldn't be able to fetch some other way) —
  flags are for hiding unfinished UI/routes, not for access control.
