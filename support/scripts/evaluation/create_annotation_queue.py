"""
Create and configure LangSmith annotation queue for UAT.

This script creates an annotation queue for human review of traces during UAT,
with automatic rules to populate it with uncertain or problematic traces.
"""

import os

from langsmith import Client


def create_annotation_queue():
    """Create UAT review queue in LangSmith."""
    api_key = os.getenv("LANGCHAIN_API_KEY")
    if not api_key:
        raise ValueError("LANGCHAIN_API_KEY environment variable not set")

    client = Client(api_key=api_key)

    # Create UAT review queue
    try:
        queue_info = client.create_annotation_queue(
            name="uat-review-queue",
            description="UAT testing - review traces with low confidence, errors, or edge cases",
            default_dataset="code-chef-gold-standard-v1",  # Auto-add to this dataset
        )

        print(f"✅ Created annotation queue: {queue_info.id}")
        print(f"📊 URL: https://smith.langchain.com/annotation-queues/{queue_info.id}")

        # Print manual setup instructions
        print("\n" + "=" * 60)
        print("⚠️  Manual setup required in LangSmith UI:")
        print("=" * 60)
        print("1. Go to Annotation Queues → uat-review-queue → Rules")
        print("2. Add filters:")
        print("   - metadata.intent_confidence < 0.75")
        print("   - errors IS NOT NULL")
        print("   - latency_ms > 5000")
        print("3. Set sampling rate: 20%")
        print("4. Enable auto-population")
        print("=" * 60)

        return queue_info

    except Exception as e:
        print(f"❌ Error creating annotation queue: {e}")
        print("Note: Queue may already exist. Check LangSmith UI.")
        raise


if __name__ == "__main__":
    create_annotation_queue()
