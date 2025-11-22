#!/usr/bin/env python3
"""Check Linear webhook configuration"""

import asyncio
import httpx
import os


async def check_webhooks():
    api_key = os.getenv(
        "LINEAR_API_KEY",
        "lin_oauth_8f8990917b7e520efcd51f8ebe84055a251f53f8738bb526c8f2fac8ff0a1571",
    )

    query = """
    query Webhooks {
      webhooks {
        nodes {
          id
          url
          enabled
          label
          resourceTypes
          createdAt
        }
      }
    }
    """

    print("Fetching Linear webhook configuration...")
    print()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.linear.app/graphql",
            headers={"Authorization": api_key, "Content-Type": "application/json"},
            json={"query": query},
        )

        data = response.json()

        if "errors" in data:
            print(f"❌ Error: {data['errors']}")
            return

        webhooks = data["data"]["webhooks"]["nodes"]

        print(f"Found {len(webhooks)} webhook(s) configured:")
        print("=" * 80)

        for webhook in webhooks:
            print(f"\n📌 Webhook: {webhook.get('label', 'Untitled')}")
            print(f"   ID: {webhook['id']}")
            print(f"   URL: {webhook['url']}")
            print(f"   Enabled: {'✅' if webhook['enabled'] else '❌'}")
            print(f"   Events: {', '.join(webhook['resourceTypes'])}")
            print(f"   Created: {webhook['createdAt']}")

        print()
        print("=" * 80)

        # Check if the correct URL is configured
        correct_url = "https://theshop.appsmithery.co/webhooks/linear"
        old_url = "https://theshop.appsmithery.co/webhook/linear"

        has_correct = any(w["url"] == correct_url for w in webhooks)
        has_old = any(w["url"] == old_url for w in webhooks)

        if has_correct:
            print(f"✅ Correct webhook URL configured: {correct_url}")
        elif has_old:
            print(f"⚠️  Old webhook URL found: {old_url}")
            print(f"   Please update to: {correct_url}")
        else:
            print(f"⚠️  Expected webhook URL not found")
            print(f"   Please add: {correct_url}")


if __name__ == "__main__":
    asyncio.run(check_webhooks())
