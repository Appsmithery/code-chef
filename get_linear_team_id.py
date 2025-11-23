"""Get Linear team ID from API"""

import asyncio
import httpx
import os


async def get_teams():
    api_key = os.getenv(
        "LINEAR_API_KEY",
        "lin_oauth_8f8990917b7e520efcd51f8ebe84055a251f53f8738bb526c8f2fac8ff0a1571",
    )

    headers = {"Authorization": api_key, "Content-Type": "application/json"}

    query = """
    query {
        teams {
            nodes {
                id
                name
                key
            }
        }
    }
    """

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.linear.app/graphql",
            headers=headers,
            json={"query": query},
            timeout=30.0,
        )

        data = response.json()
        teams = data.get("data", {}).get("teams", {}).get("nodes", [])

        print("Linear Teams:")
        print("=" * 60)
        for team in teams:
            print(f"Name: {team['name']}")
            print(f"Key:  {team['key']}")
            print(f"ID:   {team['id']}")
            print("-" * 60)


asyncio.run(get_teams())
