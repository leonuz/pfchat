# PfChat unification note — 2026-03-19

Technical summary of the PfChat config and active-skill unification completed on 2026-03-19.

## Why this change was needed

PfChat had drifted into two different execution surfaces:

1. **Repo CLI path** under `pfchat/pfchat/...`
2. **Active OpenClaw skill path** under `skills/pfchat/...`

That created two practical problems:

- **Split configuration loading**
  - the repo CLI preferred `pfchat/.env`
  - the active skill effectively fell back to the workspace `.env`
- **Split capability surface**
  - the repo CLI had ntopng support
  - the active skill did not include the ntopng command stack

Result: pfSense and ntopng setup was not truly homogeneous, and the active OpenClaw skill could lag behind the repo behavior.

## Goal

Make PfChat behave as a single product with:

- one project-local setup
- one consistent config-loading rule
- one aligned capability surface between repo CLI and active skill
- ntopng treated as part of PfChat, not as an extra side path

## Pre-change state

### Config paths

**Repo CLI**
- Script: `pfchat/pfchat/scripts/pfchat_query.py`
- Preferred config path: `/home/openclaw/.openclaw/workspace/pfchat/.env`

**Active skill**
- Script: `skills/pfchat/scripts/pfchat_query.py`
- Effective config path in practice: `/home/openclaw/.openclaw/workspace/.env`
- It did not have the same project-local `.env` behavior as the repo CLI.

### Capability split

**Repo CLI supported:**
- pfSense commands
- ntopng commands

**Active skill supported:**
- pfSense commands only
- no ntopng transport/backend/adapter stack present

## What changed

### 1. Single local setup path

PfChat now treats this file as the single project-local setup:

- `/home/openclaw/.openclaw/workspace/pfchat/.env`

That file is now the intended local source of truth for:

- `PFSENSE_HOST`
- `PFSENSE_API_KEY`
- `PFSENSE_VERIFY_SSL`
- `NTOPNG_BASE_URL`
- `NTOPNG_USERNAME`
- `NTOPNG_PASSWORD`
- `NTOPNG_AUTH_TOKEN`
- `NTOPNG_VERIFY_SSL`

### 2. Shared config resolution logic

`pfchat/pfchat/scripts/pfchat_query.py` was updated to use a shared config path resolver instead of split fallback behavior.

The active skill copy was then synced so `skills/pfchat/scripts/pfchat_query.py` follows the same rule.

Current behavior:
- both surfaces resolve PfChat config from the shared project-local `pfchat/.env`
- both surfaces use the same loading rule for pfSense and ntopng settings

## 3. ntopng migrated into the active skill

The active OpenClaw skill now includes the ntopng support files that previously existed only in the repo CLI surface:

- `skills/pfchat/scripts/ntopng_client.py`
- `skills/pfchat/scripts/ntopng_adapter.py`
- `skills/pfchat/scripts/ntopng_pyapi_backend.py`

Related references and skill docs were also synced into the active skill tree.

## 4. Active-skill command parity

The active skill now exposes the same ntopng command family as the repo CLI:

- `ntop-capabilities`
- `ntop-hosts`
- `ntop-host`
- `ntop-top-talkers`
- `ntop-alerts`
- `ntop-host-apps`
- `ntop-network-stats`

This removes the previous split where ntopng existed in the repo implementation but not in the active skill used by OpenClaw.

## Validation performed

### Shared `.env` validation

The shared config at:

- `/home/openclaw/.openclaw/workspace/pfchat/.env`

was validated live for both services.

### pfSense validation

Validated with:

```bash
python3 /home/openclaw/.openclaw/workspace/pfchat/pfchat/scripts/pfchat_query.py capabilities
```

Observed result:
- pfSense API auth succeeded
- OpenAPI schema access succeeded
- expected capabilities were returned

### ntopng validation

Validated with:

```bash
python3 /home/openclaw/.openclaw/workspace/pfchat/pfchat/scripts/pfchat_query.py ntop-capabilities
```

Observed result:
- ntopng API auth succeeded
- ntopng capabilities returned successfully
- live interface visibility confirmed

### Active skill validation

Validated the active skill copy directly with:

```bash
python3 /home/openclaw/.openclaw/workspace/skills/pfchat/scripts/pfchat_query.py capabilities
python3 /home/openclaw/.openclaw/workspace/skills/pfchat/scripts/pfchat_query.py ntop-capabilities
```

Observed result:
- active skill pfSense path works
- active skill ntopng path works
- parity confirmed for the tested command entry points

## Documentation updated

The unification was also reflected in the regular project docs:

- `README.md`
- `README.en.md`
- `README.es.md`
- `CHANGELOG.md`
- `CHANGELOG.en.md`
- `CHANGELOG.es.md`
- `TODO.md`
- `TODO.en.md`
- `TODO.es.md`
- `pfchat/pfchat/SKILL.md`
- `skills/pfchat/SKILL.md`

## Operational impact

### Before

- pfSense config could differ between repo CLI and active skill
- ntopng support existed in one surface but not the other
- troubleshooting depended on knowing which path had been invoked

### After

- one local setup path for PfChat
- one aligned config rule
- ntopng is part of PfChat in the active skill, not only in the repo copy
- repo CLI and active skill are much closer operationally

## Remaining caveat

This change establishes a single **project-local** source of truth for PfChat.

It does **not** automatically mean every unrelated workspace/global `.env` should be removed immediately without checking other consumers first. The important guarantee here is narrower and intentional:

- **PfChat itself** should use `/home/openclaw/.openclaw/workspace/pfchat/.env`

## Commit reference

Workspace commit for the unification work:

- `8f78dd1` — `Unify PfChat config and sync ntopng skill support`
