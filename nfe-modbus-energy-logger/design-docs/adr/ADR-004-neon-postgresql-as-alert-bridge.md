# ADR-004: Neon PostgreSQL (Free Tier) as Pi-to-Dashboard Alert Bridge

## Status
Accepted (replaces earlier draft that proposed Supabase)

## Context
The Streamlit dashboard runs on Streamlit Community Cloud. The Raspberry Pi runs inference locally. A shared data store is needed so the Pi can write alerts and the dashboard can read them independently.

### Why Supabase was initially considered — and rejected

Supabase was the first candidate because it provides a built-in REST API (PostgREST) and a Python client (`supabase-py`). However, Supabase has a **critical operational flaw for a monitoring system**:

> Supabase free tier **pauses the entire project after 7 days of inactivity**.

For a theft detection system, *no theft detected* is the normal (good) state. If no new alerts are inserted for 7 consecutive days, Supabase pauses the database and the dashboard goes dark — requiring a manual visit to the Supabase dashboard to resume. This is unacceptable for an unattended monitoring system.

### Options evaluated

| Option | Inactivity behaviour | Cost | Complexity |
|---|---|---|---|
| **Neon PostgreSQL** | Compute scales to zero (5 min idle), DB always reachable, wakes in ~1s | Free | Low |
| Supabase free tier | Entire project paused after 7 days idle — must manually resume | Free | Low |
| Firebase Realtime DB | No pause | Free tier limited | Medium |
| Self-hosted PostgreSQL (Render) | No pause | Free tier (512MB RAM) | Medium |
| TimescaleDB Cloud | No pause | Free starter | Medium |

### Consistency with existing stack

Neon is already used in this workspace:
- **DSN project** (`dsn-production` on Neon, AWS US East 1) uses Neon as the production database on Render
- Same account, same provider, same mental model — no new tool to learn

## Decision

Use **Neon PostgreSQL free tier** as the alert bridge between the Pi and the Streamlit dashboard.

**Schema:**
```sql
CREATE TABLE alerts (
    id          BIGSERIAL PRIMARY KEY,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    meter_id    INT NOT NULL,
    meter_name  TEXT NOT NULL,
    prediction  INT NOT NULL,        -- 0=normal, 1=theft
    probability FLOAT NOT NULL,      -- model confidence (0.0–1.0)
    i_l1        FLOAT,
    i_l2        FLOAT,
    i_l3        FLOAT,
    v_l1        FLOAT,
    v_l2        FLOAT,
    v_l3        FLOAT,
    p_total     FLOAT,
    pf_total    FLOAT,
    frequency   FLOAT
);

CREATE TABLE readings (
    id          BIGSERIAL PRIMARY KEY,
    logged_at   TIMESTAMPTZ NOT NULL,
    meter_id    INT NOT NULL,
    meter_name  TEXT NOT NULL,
    v_l1        FLOAT, v_l2 FLOAT, v_l3 FLOAT,
    i_l1        FLOAT, i_l2 FLOAT, i_l3 FLOAT,
    p_total     FLOAT,
    pf_total    FLOAT,
    frequency   FLOAT
);
```

**Pi side (detect.py):**
```python
import psycopg2, os
conn = psycopg2.connect(os.environ["NEON_DATABASE_URL"])
cur = conn.cursor()
cur.execute("INSERT INTO alerts (...) VALUES (...)", (...))
conn.commit()
```

**Streamlit side (app.py):**
```python
import streamlit as st
conn = st.connection("neon", type="sql", url=st.secrets["NEON_DATABASE_URL"])
df = conn.query("SELECT * FROM alerts ORDER BY detected_at DESC LIMIT 200")
st.dataframe(df)
```

**Environment variable (not committed to Git):**
```
NEON_DATABASE_URL=postgresql://neondb_owner:<password>@<endpoint>.neon.tech/neondb?sslmode=require
```
- Set as `.env` on Pi (loaded by detect.py via `python-dotenv`)
- Set as a Streamlit Community Cloud secret (`st.secrets`)

## Consequences

**Better:**
- No inactivity pause — database is always reachable regardless of alert frequency
- `st.connection` with a PostgreSQL URL is 1 line in Streamlit — simpler than supabase-py
- `psycopg2` on Pi is a standard, lightweight library — no extra dependencies beyond what the Pi already has
- One database provider across the entire workspace (DSN + Lubega both on Neon)
- Neon's branching feature allows creating a `dev` branch of the DB for testing alert insertion without affecting the live dashboard

**Worse:**
- No built-in REST API — Pi must use psycopg2 direct connection rather than HTTP POST
- Neon free tier: 0.5 GB storage, 1 compute unit, 1 project per account (check: DSN already uses one project — Lubega will need a second Neon account OR a second database within the same project)
- Direct database connection from Pi means the Neon connection string (with password) must be securely stored in `.env` on the Pi and never committed to Git

**Note on Neon project limit:**
Neon free tier allows up to **10 projects** per account (as of 2026). DSN uses 1. Lubega can use a second project on the same Neon account. No second account needed.
