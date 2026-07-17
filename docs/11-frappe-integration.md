# 11 — Frappe / ERPNext Integration

Frappe and ERPNext integration is handled by **`cofferdam-app`**
(`datahenge/cofferdam-app`), a companion Frappe app. The `cofferdam` core
library has no Frappe dependency at any layer (ADR-0012).

## What `cofferdam-app` provides

- Site policy discovery (`sites/{site}/environment_policy.toml`) using
  `frappe.local.site`
- Per-process policy caching and explicit reload
- `frappe.sendmail` interception via hooks and monkey-patching, routed through
  the policy and decoration engine
- Webhook delivery interception
- Frappe-aware logging

See the `cofferdam-app` repository for installation and configuration.

## Using `cofferdam` in a Frappe context without `cofferdam-app`

Call `load_policy` directly with an explicit path:

```python
from cofferdam import load_policy

policy = load_policy("sites/staging.example.com/environment_policy.toml")
```

Site discovery is the caller's responsibility. `cofferdam-app` automates this
for the common bench case.
