"""Quick script to update Linear roadmap for Week 2 completion."""

import os
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

# Set up client
transport = RequestsHTTPTransport(
    url="https://api.linear.app/graphql",
    headers={"Authorization": os.environ["LINEAR_API_KEY"]},
)
client = Client(transport=transport, fetch_schema_from_transport=True)

# Get project issues
query = gql(
    """
query {
  issues(filter: {project: {id: {eq: "b21cbaa1-9f09-40f4-b62a-73e0f86dd501"}}}) {
    nodes {
      id
      identifier
      title
      state {
        name
      }
    }
  }
}
"""
)

result = client.execute(query)

print("\n=== code/chef - Linear Roadmap ===\n")
for node in result["issues"]["nodes"]:
    status_icon = (
        "✅"
        if node["state"]["name"] == "Done"
        else "🔄" if node["state"]["name"] == "In Progress" else "📋"
    )
    print(
        f"{status_icon} {node['identifier']}: {node['title']} [{node['state']['name']}]"
    )
    print(f"   UUID: {node['id']}")
    print()
