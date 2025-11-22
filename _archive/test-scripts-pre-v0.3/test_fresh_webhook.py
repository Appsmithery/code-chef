#!/usr/bin/env python3
"""Remove existing reaction and add fresh one to trigger webhook"""

import asyncio
import httpx
import os
import json


async def trigger_fresh_webhook():
    api_key = os.getenv(
        "LINEAR_API_KEY",
        "lin_oauth_8f8990917b7e520efcd51f8ebe84055a251f53f8738bb526c8f2fac8ff0a1571",
    )
    comment_id = "fc8c31dc-3834-4c20-972c-562d7ad5649a"  # Latest test approval

    print("🔍 Checking for existing reactions on comment...")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Get comment with reactions
        query = """
        query GetComment($id: String!) {
          comment(id: $id) {
            id
            body
            user {
              id
              name
            }
            reactionData
          }
        }
        """

        response = await client.post(
            "https://api.linear.app/graphql",
            headers={"Authorization": api_key, "Content-Type": "application/json"},
            json={"query": query, "variables": {"id": comment_id}},
        )

        data = response.json()
        print(f"📊 Response: {json.dumps(data, indent=2)}")

        if "errors" in data:
            print(f"❌ Error: {data['errors']}")
            return

        comment = data["data"]["comment"]
        reaction_data = comment.get("reactionData", [])

        print(f"\n📝 Comment by: {comment['user']['name']}")
        print(f"💬 Body preview: {comment['body'][:100]}...")
        print(f"\n🎭 Reaction data: {json.dumps(reaction_data, indent=2)}")

        # Now add a fresh reaction
        print(f"\n👍 Adding fresh reaction to trigger webhook...")

        add_mutation = """
        mutation ReactionCreate($input: ReactionCreateInput!) {
          reactionCreate(input: $input) {
            success
            reaction {
              id
              emoji
              createdAt
              user {
                id
                name
              }
            }
          }
        }
        """

        add_response = await client.post(
            "https://api.linear.app/graphql",
            headers={"Authorization": api_key, "Content-Type": "application/json"},
            json={
                "query": add_mutation,
                "variables": {"input": {"emoji": "👍", "commentId": comment_id}},
            },
        )

        add_data = add_response.json()

        if "errors" in add_data:
            print(f"⚠️  Error adding reaction: {add_data['errors']}")
            print(f"   (This might be expected if reaction already exists)")
        else:
            result = add_data["data"]["reactionCreate"]
            if result["success"]:
                print(f"✅ Reaction added successfully!")
                print(f"   Reaction ID: {result['reaction']['id']}")
                print(f"   User: {result['reaction']['user']['name']}")
                print(f"   Created: {result['reaction']['createdAt']}")
                print()
                print("🎯 Webhook should now be triggered by Linear!")
            else:
                print(f"❌ Failed to add reaction")


if __name__ == "__main__":
    asyncio.run(trigger_fresh_webhook())
