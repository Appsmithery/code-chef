import os
import requests
import json

LINEAR_API_KEY = os.getenv("LINEAR_API_KEY")

query = """
query {
  webhooks {
    nodes {
      id
      label
      url
      enabled
      resourceTypes
      creator {
        name
      }
    }
  }
}
"""

headers = {
    "Authorization": f"Bearer {LINEAR_API_KEY}",
    "Content-Type": "application/json",
}

response = requests.post(
    "https://api.linear.app/graphql", headers=headers, json={"query": query}
)
print(json.dumps(response.json(), indent=2))
