#!/usr/bin/env python3
"""
Attio to Supabase Sync Script

Syncs merchants from Attio CRM to Supabase RCTI_Merchant table.
Resolves record references for Agent, Master Agent, and People.

Usage:
    python sync_attio_to_supabase.py

Environment Variables:
    ATTIO_API_KEY - Attio API access token
    SUPABASE_URL - Supabase project URL
    SUPABASE_SERVICE_ROLE_KEY - Supabase service role key
    DRY_RUN - Set to 'true' to skip database writes (default: false)
"""

import os
import sys
import time
import logging
from typing import Any

import requests
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
ATTIO_API_KEY = os.getenv('ATTIO_API_KEY')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
DRY_RUN = os.getenv('DRY_RUN', 'false').lower() == 'true'
TEST_MODE = os.getenv('TEST_MODE', 'false').lower() == 'true'  # Limit to 1 merchant for testing

ATTIO_BASE_URL = 'https://api.attio.com/v2'
ATTIO_HEADERS = {
    'Authorization': f'Bearer {ATTIO_API_KEY}',
    'Content-Type': 'application/json'
}

# Cache for resolved records (agents, people)
agent_cache: dict[str, dict] = {}
people_cache: dict[str, dict] = {}


def validate_env():
    """Validate required environment variables."""
    missing = []
    if not ATTIO_API_KEY:
        missing.append('ATTIO_API_KEY')
    if not SUPABASE_URL:
        missing.append('SUPABASE_URL')
    if not SUPABASE_SERVICE_ROLE_KEY:
        missing.append('SUPABASE_SERVICE_ROLE_KEY')

    if missing:
        logger.error(f"Missing environment variables: {', '.join(missing)}")
        sys.exit(1)


def attio_request(method: str, endpoint: str, **kwargs) -> dict:
    """Make an Attio API request with retry logic."""
    url = f"{ATTIO_BASE_URL}{endpoint}"

    for attempt in range(3):
        try:
            response = requests.request(method, url, headers=ATTIO_HEADERS, **kwargs)

            if response.status_code == 429:
                # Rate limited - wait and retry
                retry_after = int(response.headers.get('Retry-After', 5))
                logger.warning(f"Rate limited. Waiting {retry_after}s...")
                time.sleep(retry_after)
                continue

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            if attempt == 2:
                raise
            logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
            time.sleep(2 ** attempt)

    return {}


def get_attribute_value(values: dict, slug: str, default: Any = None) -> Any:
    """Extract attribute value from Attio record values.

    Attio API returns values as:
    {
        "attribute_slug": [
            {"value": "text"} or {"currency_value": 123.45} or {"target_record_id": "uuid"} etc.
        ]
    }
    """
    attr_values = values.get(slug)
    if not attr_values or not isinstance(attr_values, list) or len(attr_values) == 0:
        return default

    first_value = attr_values[0]

    if not isinstance(first_value, dict):
        return default

    # Handle different attribute types
    if 'value' in first_value:
        return first_value['value']
    if 'option' in first_value:
        return first_value['option'].get('title') if isinstance(first_value['option'], dict) else first_value['option']
    if 'currency_value' in first_value:
        return first_value['currency_value']
    if 'target_record_id' in first_value:
        return first_value['target_record_id']
    if 'referenced_actor_id' in first_value:
        return first_value['referenced_actor_id']
    if 'email_address' in first_value:
        return first_value['email_address']
    if 'phone_number' in first_value:
        return first_value['phone_number']
    if 'full_name' in first_value:
        return first_value['full_name']
    if 'first_name' in first_value and 'last_name' in first_value:
        return f"{first_value.get('first_name', '')} {first_value.get('last_name', '')}".strip()

    return default


def get_record_reference_ids(values: dict, slug: str) -> list[str]:
    """Extract all record reference IDs from an attribute."""
    attr_values = values.get(slug)
    if not attr_values or not isinstance(attr_values, list):
        return []

    return [
        av['target_record_id']
        for av in attr_values
        if isinstance(av, dict) and 'target_record_id' in av
    ]


def fetch_agent(record_id: str) -> dict:
    """Fetch agent record from Attio with caching."""
    if record_id in agent_cache:
        return agent_cache[record_id]

    try:
        response = attio_request('GET', f'/objects/agents/records/{record_id}')
        agent_data = response.get('data', {})
        values = agent_data.get('values', {})

        agent = {
            'agent_name': get_attribute_value(values, 'agent_name'),
            'agent_commission_rate': get_attribute_value(values, 'agent_commission_rate'),
            'master_agent_rate': get_attribute_value(values, 'master_agent_rate'),
        }
        agent_cache[record_id] = agent
        return agent
    except Exception as e:
        logger.warning(f"Failed to fetch agent {record_id}: {e}")
        return {}


def fetch_person(record_id: str) -> dict:
    """Fetch person record from Attio with caching."""
    if record_id in people_cache:
        return people_cache[record_id]

    try:
        response = attio_request('GET', f'/objects/people/records/{record_id}')
        person_data = response.get('data', {})
        values = person_data.get('values', {})

        person = {
            'name': get_attribute_value(values, 'name'),
            'email': get_attribute_value(values, 'email_addresses'),
            'phone': get_attribute_value(values, 'phone_numbers'),
        }
        people_cache[record_id] = person
        return person
    except Exception as e:
        logger.warning(f"Failed to fetch person {record_id}: {e}")
        return {}


def fetch_all_merchants() -> list[dict]:
    """Fetch all merchant records from Attio with pagination."""
    merchants = []
    offset = 0
    limit = 1 if TEST_MODE else 500

    while True:
        logger.info(f"Fetching merchants (offset: {offset}, limit: {limit})...")

        response = attio_request(
            'POST',
            '/objects/merchants/records/query',
            json={
                'limit': limit,
                'offset': offset
            }
        )

        data = response.get('data', [])
        merchants.extend(data)

        # In test mode, only fetch 1 merchant
        if TEST_MODE or len(data) < limit:
            break

        offset += limit

    logger.info(f"Fetched {len(merchants)} merchants from Attio")
    return merchants


def transform_merchant(merchant: dict) -> dict:
    """Transform Attio merchant to Supabase RCTI_Merchant format."""
    values = merchant.get('values', {})

    # Get direct values
    mid = get_attribute_value(values, 'mid')
    if not mid:
        return None  # Skip merchants without MID

    # Resolve Agent reference
    agent_ids = get_record_reference_ids(values, 'agent')
    agent = fetch_agent(agent_ids[0]) if agent_ids else {}

    # Resolve Master Agent reference
    master_agent_ids = get_record_reference_ids(values, 'master_agent')
    master_agent = fetch_agent(master_agent_ids[0]) if master_agent_ids else {}

    # Peter Willis: if he is both agent and master agent, MA rate = 0
    master_agent_rate = master_agent.get('master_agent_rate')
    if agent_ids and master_agent_ids and agent_ids[0] == master_agent_ids[0]:
        if agent.get('agent_name') == 'Peter Willis':
            master_agent_rate = 0

    # Resolve People reference (first person only)
    people_ids = get_record_reference_ids(values, 'people')
    person = fetch_person(people_ids[0]) if people_ids else {}

    # Map to Supabase columns
    return {
        'MID': mid,
        'Trading Name': get_attribute_value(values, 'trading_name'),
        'Qantas Plan': get_attribute_value(values, 'qantas_plan'),
        'eftpos_structure': get_attribute_value(values, 'debit_eftpos_structure'),
        'Number of Terminals': get_attribute_value(values, 'number_of_terminals'),
        'Merchant Terminal Rental': get_attribute_value(values, 'merchant_terminal_rental'),
        'APS Terminal Rental': get_attribute_value(values, 'aps_terminal_rental'),
        'Merchant Staus': get_attribute_value(values, 'merchant_status'),
        'Agent Name': agent.get('agent_name'),
        'Agent Rate': agent.get('agent_commission_rate'),
        'Master Agent Name': master_agent.get('agent_name'),
        'Master Agent Rate': master_agent_rate,
        'Status': get_attribute_value(values, 'account_status'),
        'Owner/ Manager Name': person.get('name'),
        'Email': person.get('email'),
        'Phone Number': person.get('phone'),
    }


def upsert_to_supabase(supabase: Client, records: list[dict]) -> tuple[int, int]:
    """Upsert records to Supabase RCTI_Merchant table."""
    success_count = 0
    error_count = 0

    # Process in batches of 100
    batch_size = 100
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]

        try:
            if DRY_RUN:
                logger.info(f"[DRY RUN] Would upsert {len(batch)} records")
                success_count += len(batch)
            else:
                supabase.table('RCTI_Merchant').upsert(
                    batch,
                    on_conflict='MID'
                ).execute()
                success_count += len(batch)
                logger.info(f"Upserted batch {i // batch_size + 1} ({len(batch)} records)")
        except Exception as e:
            logger.error(f"Failed to upsert batch {i // batch_size + 1}: {e}")
            error_count += len(batch)

    return success_count, error_count


def main():
    """Main sync function."""
    logger.info("=" * 60)
    logger.info("Starting Attio to Supabase sync")
    logger.info("=" * 60)

    if TEST_MODE:
        logger.info("TEST MODE - Only syncing 1 merchant")
    if DRY_RUN:
        logger.info("DRY RUN MODE - No changes will be made to database")

    # Validate environment
    validate_env()

    # Initialize Supabase client
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

    # Fetch all merchants from Attio
    merchants = fetch_all_merchants()

    if not merchants:
        logger.warning("No merchants found in Attio")
        return

    # Transform merchants
    logger.info("Transforming merchant data...")
    transformed = []
    skipped = 0

    for i, merchant in enumerate(merchants):
        record = transform_merchant(merchant)
        if record:
            transformed.append(record)
        else:
            skipped += 1

        if (i + 1) % 100 == 0:
            logger.info(f"Transformed {i + 1}/{len(merchants)} merchants...")

    logger.info(f"Transformed {len(transformed)} merchants ({skipped} skipped)")

    # Upsert to Supabase
    logger.info("Upserting to Supabase...")
    success, errors = upsert_to_supabase(supabase, transformed)

    # Summary
    logger.info("=" * 60)
    logger.info("Sync complete!")
    logger.info(f"  Total merchants: {len(merchants)}")
    logger.info(f"  Successful: {success}")
    logger.info(f"  Errors: {errors}")
    logger.info(f"  Skipped (no MID): {skipped}")
    logger.info("=" * 60)

    # Exit with error if too many failures
    if errors > len(merchants) * 0.1:
        logger.error("Too many errors (>10%). Exiting with error code.")
        sys.exit(1)


if __name__ == '__main__':
    main()
