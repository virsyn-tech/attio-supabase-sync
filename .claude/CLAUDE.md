# Attio Supabase Sync

## Project Overview
Automated daily sync from **Attio CRM** (Merchants object) to **Supabase** (`RCTI_Merchant` table) using GitHub Actions.

---

## Architecture

```
Attio CRM (Merchants)  →  GitHub Action (daily)  →  Supabase (RCTI_Merchant)
         ↓                         ↓
   Record References          Python Script
   - Agent                    - Fetch merchants
   - Master Agent             - Resolve references
   - People                   - Map columns
                              - Upsert to Supabase
```

---

## Connected Systems

### Supabase - APS Project
- **Project ID**: `thxvfnachnpgmeottlem`
- **Region**: us-east-2
- **Table**: `RCTI_Merchant` (981 rows, MID primary key)
- **URL**: `https://thxvfnachnpgmeottlem.supabase.co`

### Attio CRM
- **Object**: `merchants`
- **Related Objects**: `agents`, `people`
- **API**: REST API v2

---

## Column Mapping (Attio → Supabase)

| Supabase Column | Attio Source | Notes |
|-----------------|--------------|-------|
| `MID` | `mid` | Primary key |
| `Trading Name` | `trading_name` | |
| `Qantas Plan` | `qantas_plan` | Select: Black/Gold/Green/Tailored |
| `eftpos_structure` | `debit_eftpos_structure` | Select: Fixed/Variable |
| `Number of Terminals` | `number_of_terminals` | |
| `Merchant Terminal Rental` | `merchant_terminal_rental` | Currency AUD |
| `APS Terminal Rental` | `aps_terminal_rental` | Currency AUD |
| `Merchant Staus` | `merchant_status` | Select: New/Existing |
| `Agent Name` | `agent` → `agent_name` | Record reference lookup |
| `Agent Rate` | `agent` → `agent_commission_rate` | Record reference lookup |
| `Master Agent Name` | `master_agent` → `agent_name` | Record reference lookup |
| `Master Agent Rate` | `master_agent` → `master_agent_rate` | Record reference lookup |
| `Status` | `account_status` | Select: Active/Cancelled/Suspended/Churned |
| `Owner/ Manager Name` | `people[0]` → `name.full_name` | First linked person |
| `Email` | `people[0]` → `email_addresses[0]` | First linked person |
| `Phone Number` | `people[0]` → `phone_numbers[0]` | First linked person |

---

## Sync Behavior
- **Schedule**: Daily at 6 AM UTC via GitHub Actions
- **Mode**: Upsert (update existing by MID, insert new)
- **Deletions**: Never delete from Supabase
- **Contact Info**: Use first person linked to merchant

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ATTIO_API_KEY` | Attio API access token |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key |

---

## Files

| File | Purpose |
|------|---------|
| `sync_attio_to_supabase.py` | Main sync script |
| `requirements.txt` | Python dependencies |
| `.github/workflows/sync-attio-supabase.yml` | Daily cron workflow |
| `.env` | Local credentials (gitignored) |
| `.env.example` | Template for env vars |

---

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run sync locally
python sync_attio_to_supabase.py

# Test with dry run (no writes)
DRY_RUN=true python sync_attio_to_supabase.py
```

---

## Changelog

- **2026-03-07**: Initial implementation - Attio to Supabase sync with GitHub Actions
