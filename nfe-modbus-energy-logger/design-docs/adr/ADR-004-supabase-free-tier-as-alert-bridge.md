# ADR-004: Supabase Free Tier as Pi-to-Dashboard Alert Bridge

## Status
Accepted (for MVP)

## Context
The Streamlit dashboard runs on Streamlit Community Cloud (a separate cloud environment with no direct network path to the Pi). The Pi must push alert data somewhere that the dashboard can read. Several bridge options were evaluated:

| Option | Cost | Complexity | Offline behaviour |
|---|---|---|---|
| Direct Pi HTTP (ngrok/Cloudflare Tunnel) | Free | Medium | Dashboard unreachable if Pi offline |
| MQTT broker (HiveMQ free, CloudMQTT) | Free | High | Requires always-on broker |
| Firebase Realtime DB | Free tier | Medium | Good offline support |
| **Supabase (PostgreSQL, free tier)** | **Free (500MB)** | **Low** | **Pi pushes when online, dashboard reads independently** |
| AWS DynamoDB / S3 | Free tier limited | High | Complex IAM setup |

Supabase provides a REST API out of the box (PostgREST) with an auto-generated API key — no backend code to write. The `supabase-py` library is available for both the Pi (push) and Streamlit (pull).

## Decision
Use Supabase free tier as the alert bridge:

**Schema (minimal):**
```sql
CREATE TABLE alerts (
    id          BIGSERIAL PRIMARY KEY,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    meter_id    INT NOT NULL,
    meter_name  TEXT NOT NULL,
    prediction  INT NOT NULL,          -- 0=normal, 1=theft
    probability FLOAT NOT NULL,        -- model confidence
    scenario    TEXT,                  -- e.g. 'bypass_red' if classifying scenarios
    i_l1        FLOAT, i_l2 FLOAT, i_l3 FLOAT,
    v_l1        FLOAT, v_l2 FLOAT, v_l3 FLOAT,
    p_total     FLOAT,
    pf_total    FLOAT
);

CREATE TABLE readings (
    id          BIGSERIAL PRIMARY KEY,
    logged_at   TIMESTAMPTZ NOT NULL,
    meter_id    INT NOT NULL,
    meter_name  TEXT NOT NULL,
    v_l1        FLOAT, v_l2 FLOAT, v_l3 FLOAT,
    i_l1        FLOAT, i_l2 FLOAT, i_l3 FLOAT,
    p_total     FLOAT, pf_total FLOAT, frequency FLOAT
);
```

**Pi side (detect.py):** `supabase.table("alerts").insert({...}).execute()` on every theft detection event.

**Dashboard side (app.py):** `supabase.table("alerts").select("*").order("detected_at", desc=True).limit(100).execute()` on each Streamlit refresh.

## Consequences

**Better:**
- Zero cost for MVP (500 MB free tier; alert rows are tiny — 1 year of daily alerts ≈ <1 MB)
- Dashboard and Pi are fully decoupled — dashboard works even when Pi is offline (shows historical alerts)
- PostgREST auto-generates REST endpoints from the schema — no API code to write
- Supabase dashboard lets engineers inspect the raw alert table directly
- `supabase-py` is the same library on both ends — consistent interface

**Worse:**
- Supabase free tier has a 1-week inactivity pause — if no alerts occur for 7 days, the project pauses (must be manually resumed)
- 2 projects maximum on free tier — consumes one of Rincol Tech's two free Supabase project slots
- Pi must have internet access to push alerts — if offline for extended periods, alerts are lost (not queued)
- API key management: Supabase anon key is embedded in both detect.py and app.py — must not be committed to public Git (use .env)

**Migration path (scale):** Replace Supabase with Timescale Cloud (free tier, better for time-series), or self-hosted TimescaleDB on a DigitalOcean $4/month droplet, when alert volume or query complexity grows.

**Environment variables required (not committed to Git):**
```
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_ANON_KEY=<key>
```
Both are set in `.env` on the Pi and as Streamlit Community Cloud secrets on the dashboard.
