import sys
import os
import boto3
import httpx
from botocore.exceptions import ClientError

# --- Path Setup ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.logging import get_logger
from app.core.config import get_settings

logger = get_logger("rekognition-audit")

# --- Configuration ---
DEFAULT_COLLECTION_ID = 'new-face-collection-11'
rekognition = boto3.client("rekognition", region_name="us-east-2")

try:
    settings = get_settings()
    central_base_url = settings.CENTRAL_BASE
    users_url = f"{central_base_url.rstrip('/')}/users/"
    verify_ssl = getattr(settings, "AVIGILON_API_VERIFY_SSL", True)
    logger.info(f"Configured to audit against Central API at: {central_base_url}")
except Exception as e:
    logger.error(f"Failed to get settings for Central API: {e}. Audit cannot proceed.", exc_info=True)
    central_base_url = None
    users_url = None
    verify_ssl = True


def get_all_rekognition_users(collection_id: str):
    """
    Lists all users from a Rekognition collection, handling pagination automatically.
    Returns a list of user dictionaries or an empty list on error.
    """
    if not rekognition:
        logger.error("Rekognition client is not initialized.")
        return []

    all_users = []
    try:
        paginator = rekognition.get_paginator('list_users')
        logger.info(f"Fetching all users from Rekognition collection '{collection_id}'...")
        pages = paginator.paginate(CollectionId=collection_id)
        for page in pages:
            all_users.extend(page.get('Users', []))
        logger.info(f"Found a total of {len(all_users)} users in Rekognition.")
        return all_users
    except ClientError as e:
        logger.error(f"Failed to list users from Rekognition: {e.response['Error']['Message']}", exc_info=True)
        return []


def get_all_central_users_sync():
    """
    Fetches all users from Central DB and returns a dict indexed by _id.
    """
    if not users_url:
        logger.error("Central users URL not configured.")
        return {}

    try:
        with httpx.Client(verify=verify_ssl, timeout=10, follow_redirects=True) as client:
            response = client.get(users_url.rstrip('/'))
            response.raise_for_status()
            users = response.json()

            if not isinstance(users, list):
                logger.error("Unexpected Central API response format.")
                return {}

            return {user["_id"]: user for user in users if "_id" in user}

    except Exception as e:
        logger.error(f"Failed to fetch users from Central: {e}", exc_info=True)
        return {}


def audit_users(collection_id: str):
    """
    Main function to perform the audit. It fetches all users from Rekognition
    and compares them with users in the Central DB.
    """
    if not central_base_url:
        logger.error("Central API URL is not configured. Aborting audit.")
        return

    logger.info(f"--- Starting Audit for Rekognition Collection: {collection_id} ---")

    rek_users = get_all_rekognition_users(collection_id)
    if not rek_users:
        logger.info("No users found in Rekognition collection or an error occurred. Audit complete.")
        return

    central_users_by_id = get_all_central_users_sync()
    if not central_users_by_id:
        logger.error("Failed to fetch users from Central DB. Aborting audit.")
        return

    orphaned_users = []

    for i, user in enumerate(rek_users):
        user_id = user.get("UserId")
        if not user_id:
            continue

        logger.info(f"Verifying user {i + 1}/{len(rek_users)}: {user_id}")

        if user_id not in central_users_by_id:
            logger.warning(f"DISCREPANCY FOUND: User '{user_id}' exists in Rekognition but NOT in Central DB.")
            orphaned_users.append(user_id)

    # --- Reporting ---
    print("\n" + "=" * 50)
    print("--- Rekognition User Audit Report ---")
    print(f"Collection ID: {collection_id}")
    print(f"Total users found in Rekognition: {len(rek_users)}")
    print("=" * 50 + "\n")

    if orphaned_users:
        print(f"🔴 Found {len(orphaned_users)} orphaned users (exist in Rekognition but not Central DB):")
        for user_id in orphaned_users:
            print(f"  - {user_id}")
    else:
        print("✅ No orphaned users found. All Rekognition users exist in Central DB.")

    print("\n--- Audit Complete ---")


if __name__ == "__main__":
    audit_users(collection_id=DEFAULT_COLLECTION_ID)
