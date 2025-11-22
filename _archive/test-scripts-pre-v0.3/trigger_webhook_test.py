#!/usr/bin/env python3
"""Trigger webhook test by adding emoji reaction to test approval"""

import asyncio
import httpx
import os


async def add_reaction():
    api_key = os.getenv(
        "LINEAR_API_KEY",
        "lin_oauth_8f8990917b7e520efcd51f8ebe84055a251f53f8738bb526c8f2fac8ff0a1571",
    )
    comment_id = "8d73720e-2e95-41b7-a388-3deb041810e0"

    mutation = """
    mutation ReactionCreate($input: ReactionCreateInput!) {
      reactionCreate(input: $input) {
        success
        reaction {
          id
          emoji
          createdAt
          comment {
            id
            body
          }
        }
      }
    }
    """

    variables = {"input": {"emoji": "👍", "commentId": comment_id}}

    print(f"Adding 👍 reaction to comment {comment_id}...")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.linear.app/graphql",
            headers={"Authorization": api_key, "Content-Type": "application/json"},
            json={"query": mutation, "variables": variables},
        )

        data = response.json()

        if "errors" in data:
            print(f"❌ Error: {data['errors']}")
        else:
            result = data["data"]["reactionCreate"]
            if result["success"]:
                print(f"✅ Reaction added successfully!")
                print(f"   Reaction ID: {result['reaction']['id']}")
                print(f"   Emoji: {result['reaction']['emoji']}")
                print(f"   Created: {result['reaction']['createdAt']}")
                print()
                print("🎯 Webhook should now be triggered!")
                print(
                    "   Monitor logs: ssh root@45.55.173.72 'docker logs deploy-orchestrator-1 -f'"
                )
            else:
                print(f"❌ Failed to add reaction")

        return data


if __name__ == "__main__":
    asyncio.run(add_reaction())
