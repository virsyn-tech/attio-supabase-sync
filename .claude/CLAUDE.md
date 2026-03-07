# Attio Supabase Sync

## Project Overview
Automated daily sync from **Attio CRM** (Merchants object) to **two Supabase projects** using GitHub Actions.

- **APS Project**: `RCTI_Merchant` table (Title Case columns)
- **Agent Reports Project**: `rcti_merchant` table (snake_case columns)

---

## Architecture

```
                              ┌─────────────────────────────────┐
                              │  GitHub Actions (12 PM IST)     │
                              │  virsyn-tech/attio-supabase-sync│
                              └───────────────┬─────────────────┘
                                              │
              ┌───────────────────────────────┼───────────────────────────────┐
              │                               │                               │
              ▼                               ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────┐     ┌─────────────────────────┐
│  Attio CRM              │     │  sync_attio_to_         │     │  sync_attio_to_         │
│  - Merchants            │────▶│  supabase.py            │     │  agent_reports.py       │
│  - Agents               │     │  (APS Project)          │     │  (Agent Reports)        │
│  - People               │     └───────────┬─────────────┘     └───────────┬─────────────┘
└─────────────────────────┘                 │                               │
                                            ▼                               ▼
                              ┌─────────────────────────┐     ┌─────────────────────────┐
                              │  Supabase APS           │     │  Supabase Agent Reports │
                              │  RCTI_Merchant          │     │  rcti_merchant          │
                              │  (Title Case columns)   │     │  (snake_case columns)   │
                              └─────────────────────────┘     └─────────────────────────┘
```

---

## Supabase Projects

### 1. APS Project
- **Project ID**: `thxvfnachnpgmeottlem`
- **Region**: us-east-2
- **Table**: `RCTI_Merchant`
- **URL**: `https://thxvfnachnpgmeottlem.supabase.co`
- **Column Style**: Title Case (`Agent Rate`, `Trading Name`)
- **Merchants**: 990

### 2. Agent Reports Project
- **Project ID**: `ryhjuyrszbavujewlutt`
- **Region**: ap-south-1
- **Table**: `rcti_merchant`
- **URL**: `https://ryhjuyrszbavujewlutt.supabase.co`
- **Column Style**: snake_case (`agent_rate`, `trading_name`)
- **Extra Columns**: `created_at`, `updated_at`
- **Merchants**: 990

---

## GitHub Repository

- **Repo**: [virsyn-tech/attio-supabase-sync](https://github.com/virsyn-tech/attio-supabase-sync)
- **Branch**: `master`

### Secrets Configured
| Secret | Description |
|--------|-------------|
| `ATTIO_API_KEY` | Attio API access token |
| `SUPABASE_URL` | APS Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | APS service role key |
| `AGENT_REPORTS_SUPABASE_URL` | Agent Reports Supabase URL |
| `AGENT_REPORTS_SUPABASE_KEY` | Agent Reports service role key |

---

## Workflows

### 1. Sync Attio to Supabase (APS)
- **File**: `.github/workflows/sync-attio-supabase.yml`
- **Script**: `sync_attio_to_supabase.py`
- **Schedule**: Daily at 12 PM IST (6:30 AM UTC)
- **Target**: APS `RCTI_Merchant` table

### 2. Sync Attio to Agent Reports
- **File**: `.github/workflows/sync-agent-reports.yml`
- **Script**: `sync_attio_to_agent_reports.py`
- **Schedule**: Daily at 12 PM IST (6:30 AM UTC)
- **Target**: Agent Reports `rcti_merchant` table

### Failure Notifications
Both workflows create a GitHub issue on failure with:
- Link to the failed run
- Timestamp
- `sync-failure` label

---

## Column Mapping

### APS Project (Title Case)

| Supabase Column | Attio Source | Notes |
|-----------------|--------------|-------|
| `MID` | `mid` | Primary key |
| `Trading Name` | `trading_name` | |
| `Qantas Plan` | `qantas_plan` | Select |
| `eftpos_structure` | `debit_eftpos_structure` | Select |
| `Number of Terminals` | `number_of_terminals` | |
| `Merchant Terminal Rental` | `merchant_terminal_rental` | Currency AUD |
| `APS Terminal Rental` | `aps_terminal_rental` | Currency AUD |
| `Merchant Staus` | `merchant_status` | Select |
| `Agent Name` | `agent` → `agent_name` | Record ref |
| `Agent Rate` | `agent` → `agent_commission_rate` | Record ref |
| `Master Agent Name` | `master_agent` → `agent_name` | Record ref |
| `Master Agent Rate` | `master_agent` → `master_agent_rate` | Record ref |
| `Status` | `account_status` | Select |
| `Owner/ Manager Name` | `people[0]` → `name` | First person |
| `Email` | `people[0]` → `email_addresses[0]` | First person |
| `Phone Number` | `people[0]` → `phone_numbers[0]` | First person |

### Agent Reports Project (snake_case)

| Supabase Column | Attio Source | Notes |
|-----------------|--------------|-------|
| `mid` | `mid` | Primary key |
| `trading_name` | `trading_name` | |
| `qantas_plan` | `qantas_plan` | Select |
| `eftpos_structure` | `debit_eftpos_structure` | Select |
| `number_of_terminals` | `number_of_terminals` | |
| `merchant_terminal_rental` | `merchant_terminal_rental` | Currency AUD |
| `aps_terminal_rental` | `aps_terminal_rental` | Currency AUD |
| `merchant_status` | `merchant_status` | Select |
| `agent_name` | `agent` → `agent_name` | Record ref |
| `agent_rate` | `agent` → `agent_commission_rate` | Numeric |
| `master_agent_name` | `master_agent` → `agent_name` | Record ref |
| `master_agent_rate` | `master_agent` → `master_agent_rate` | Text → Numeric |
| `status` | `account_status` | Select |
| `owner_manager_name` | `people[0]` → `name` | First person |
| `email` | `people[0]` → `email_addresses[0]` | First person |
| `phone_number` | `people[0]` → `phone_numbers[0]` | First person |
| `updated_at` | Auto-generated | UTC timestamp |
| `created_at` | Supabase default | First insert only |

---

## Sync Behavior

- **Schedule**: Daily at 12 PM IST (6:30 AM UTC)
- **Mode**: Upsert (update existing by MID, insert new)
- **Deletions**: Never deletes from Supabase
- **Contact Info**: Uses first person linked to merchant
- **Batch Size**: 100 records per upsert
- **Rate Limiting**: Automatic retry with exponential backoff

---

## Files

| File | Purpose |
|------|---------|
| `sync_attio_to_supabase.py` | APS sync script (Title Case) |
| `sync_attio_to_agent_reports.py` | Agent Reports sync script (snake_case) |
| `requirements.txt` | Python dependencies |
| `.github/workflows/sync-attio-supabase.yml` | APS daily workflow |
| `.github/workflows/sync-agent-reports.yml` | Agent Reports daily workflow |
| `.env` | Local credentials (gitignored) |
| `.env.example` | Template for env vars |

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ATTIO_API_KEY` | Attio API access token |
| `SUPABASE_URL` | APS Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | APS service role key |
| `AGENT_REPORTS_SUPABASE_URL` | Agent Reports Supabase URL |
| `AGENT_REPORTS_SUPABASE_KEY` | Agent Reports service role key |
| `DRY_RUN` | Set to `true` to skip database writes |
| `TEST_MODE` | Set to `true` to sync only 1 merchant |

---

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run APS sync locally
python sync_attio_to_supabase.py

# Run Agent Reports sync locally
python sync_attio_to_agent_reports.py

# Dry run (no writes)
DRY_RUN=true python sync_attio_to_supabase.py

# Test mode (1 merchant only)
TEST_MODE=true python sync_attio_to_agent_reports.py

# Trigger workflow manually
gh workflow run "Sync Attio to Supabase"
gh workflow run "Sync Attio to Agent Reports"

# Check workflow status
gh run list --limit 5
```

---

## Data Fixes Applied

### Master Agent Rate Correction (2026-03-07)
Fixed incorrect `master_agent_rate` values in Attio for Master Agent type records.

**Problem**: Master Agents had their own commission rate in `master_agent_rate` instead of `0`.

**Records Fixed** (11 total):
- Neil Bhatt, Jarrad Parke, Tim Sefton, Allan & Kevin
- Wayne Connell, Allan Asplin, Woosh, Peter Willis
- Andrew Reeves, Kevin Gibbs, Scott Griffiths

All were updated to `master_agent_rate: "0"` since Master Agents don't pay anyone above them.

---

## Changelog

| Date | Change |
|------|--------|
| 2026-03-07 | Initial implementation - APS sync with GitHub Actions |
| 2026-03-07 | Fixed Master Agent Rate data in Attio (11 records) |
| 2026-03-07 | Changed schedule from 6 AM UTC to 12 PM IST (6:30 AM UTC) |
| 2026-03-07 | Added failure notifications (creates GitHub issue) |
| 2026-03-07 | Added Agent Reports sync (second Supabase project) |
| 2026-03-07 | Pushed to GitHub: virsyn-tech/attio-supabase-sync |
| 2026-03-07 | Configured 5 repository secrets |
| 2026-03-07 | Tested both workflows with test merchant |
| 2026-03-07 | Project complete - 990 merchants synced to both projects |
