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
        )

        print(f"✅ Created annotation queue: {queue_info.name}")
        print(
            f"📊 URL: https://smith.langchain.com/o/{client._get_optional_tenant_id()}/annotation-queues/{queue_info.id}"
        )

        # Print manual setup instructions
        print("\n" + "=" * 60)
        print("⚠️  Manual setup required in LangSmith UI:")
        print("=" * 60)
        print("1. Go to Annotation Queues → uat-review-queue → Settings")
        print("2. Configure auto-population rules (if available)")
        print("3. Alternatively, use the script to populate manually:")
        print(
            "   python support/scripts/evaluation/auto_annotate_traces.py --populate-queue"
        )
        print("4. Link to dataset 'code-chef-gold-standard-v1' for reviewed traces")
        print("=" * 60)
        print("\n💡 Next steps:")
        print(
            "   - Configure online evaluators in LangSmith UI (see LANGSMITH_UAT_QUICKSTART.md)"
        )
        print(
            "   - Run: python support/scripts/evaluation/auto_annotate_traces.py --populate-queue"
        )
        print(
            "   - Start daily reviews: python support/scripts/evaluation/daily_uat_review.py"
        )

        return queue_info

    except Exception as e:
        error_msg = str(e)
        if "already exists" in error_msg.lower() or "duplicate" in error_msg.lower():
            print(f"ℹ️  Annotation queue 'uat-review-queue' already exists")
            print(f"📊 URL: https://smith.langchain.com/annotation-queues")
            print("\n✅ You can proceed with the UAT workflow!")
            return None
        else:
            print(f"❌ Error creating annotation queue: {e}")
            print("\n💡 Troubleshooting:")
            print("   - Verify LANGCHAIN_API_KEY is valid")
            print("   - Check your LangSmith permissions")
            print("   - Queue may already exist - check LangSmith UI")
            raise


if __name__ == "__main__":
    create_annotation_queue()
