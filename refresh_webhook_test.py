#!/usr/bin/env python3
"""Remove and re-add emoji reaction to trigger fresh webhook"""

import asyncio
import httpx
import os


async def remove_and_readd_reaction():
    api_key = os.getenv(
        "LINEAR_API_KEY",
        "lin_oauth_8f8990917b7e520efcd51f8ebe84055a251f53f8738bb526c8f2fac8ff0a1571",
    )
    comment_id = "8d73720e-2e95-41b7-a388-3deb041810e0"

    # First, get existing reactions
    query_reactions = """
    query GetReactions($commentId: String!) {
      comment(id: $commentId) {
        reactionData {
          reaction
          users {
            nodes {
              id
              name
            }
          }
        }
      }
    }
    """

    print(f"Fetching existing reactions on comment {comment_id}...")

    async with httpx.AsyncClient() as client:
        # Get reactions
        response = await client.post(
            "https://api.linear.app/graphql",
            headers={"Authorization": api_key, "Content-Type": "application/json"},
            json={"query": query_reactions, "variables": {"commentId": comment_id}},
        )

        data = response.json()
        print(f"Response: {data}")

        if "errors" in data:
            print(f"❌ Error fetching reactions: {data['errors']}")
            return

        reactions = data["data"]["comment"]["reactions"]["nodes"]

        print(f"Found {len(reactions)} existing reactions")

        # Remove my reactions (👍)
        for reaction in reactions:
            if reaction["emoji"] in ["+1", "👍"]:
                reaction_id = reaction["id"]
                print(f"Removing reaction {reaction_id} ({reaction['emoji']})")

                delete_mutation = """
                mutation ReactionDelete($id: String!) {
                  reactionDelete(id: $id) {
                    success
                  }
                }
                """

                del_response = await client.post(
                    "https://api.linear.app/graphql",
                    headers={
                        "Authorization": api_key,
                        "Content-Type": "application/json",
                    },
                    json={"query": delete_mutation, "variables": {"id": reaction_id}},
                )

                del_data = del_response.json()
                if del_data["data"]["reactionDelete"]["success"]:
                    print(f"   ✅ Removed reaction {reaction_id}")
                else:
                    print(f"   ❌ Failed to remove reaction {reaction_id}")

        # Wait a moment
        await asyncio.sleep(1)

        # Now add new reaction
        print(f"\nAdding fresh 👍 reaction...")

        add_mutation = """
        mutation ReactionCreate($input: ReactionCreateInput!) {
          reactionCreate(input: $input) {
            success
            reaction {
              id
              emoji
              createdAt
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
            print(f"❌ Error adding reaction: {add_data['errors']}")
        else:
            result = add_data["data"]["reactionCreate"]
            if result["success"]:
                print(f"✅ Fresh reaction added!")
                print(f"   Reaction ID: {result['reaction']['id']}")
                print(f"   Emoji: {result['reaction']['emoji']}")
                print(f"   Created: {result['reaction']['createdAt']}")
                print()
                print("🎯 Webhook should now be triggered!")
                print(
                    "   Monitor: ssh root@45.55.173.72 'docker logs deploy-orchestrator-1 -f'"
                )


if __name__ == "__main__":
    asyncio.run(remove_and_readd_reaction())
