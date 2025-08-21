"""Demo script to test the Content Workflow Agent with sample content."""

import asyncio
import json
from pathlib import Path

from .graph import build_graph
from .models import State


async def main():
    """Run demo with sample blog content."""
    try:
        # Load sample blog content
        sample_path = Path("examples/sample_blog.md")
        if not sample_path.exists():
            print(f"Sample blog not found at {sample_path}")
            return

        with open(sample_path, "r", encoding="utf-8") as f:
            blog_text = f.read()

        print("Content Workflow Agent Demo")
        print("=" * 40)
        print(f"Processing sample blog ({len(blog_text)} characters)...")

        # Initialize state
        initial_state: State = {
            "text": blog_text,
            "topic_hint": "artificial intelligence and marketing",
            "key_points": [],
            "drafts": {},
            "claims": {},
            "reviews": {},
            "timings": [],
            "errors": [],
        }

        # Build and run workflow
        graph = build_graph()
        final_state = graph.invoke(initial_state)

        # Print results summary
        print("\nWorkflow Results:")
        print("-" * 20)
        print(f"Key points extracted: {len(final_state['key_points'])}")
        print(f"Platform posts generated: {len(final_state['drafts'])}")
        print(f"Claims extracted: {sum(len(claims) for claims in final_state['claims'].values())}")
        print(f"Reviews completed: {len(final_state['reviews'])}")
        print(f"Posting times suggested: {len(final_state['timings'])}")

        if final_state["errors"]:
            print(f"Errors encountered: {len(final_state['errors'])}")
            for error in final_state["errors"]:
                print(f"  - {error}")

        # Show sample outputs
        print("\nSample Key Points:")
        for i, kp in enumerate(final_state["key_points"][:3], 1):
            print(f"  {i}. {kp.text} (importance: {kp.importance:.2f})")

        print("\nPlatform Post Lengths:")
        for platform, post in final_state["drafts"].items():
            print(f"  {platform}: {len(post.primary_text)} characters")

        print("\nReview Status:")
        for platform, review in final_state["reviews"].items():
            status_emoji = {"pass": "✅", "flag": "⚠️", "block": "❌"}.get(review.status, "❓")
            print(f"  {platform}: {status_emoji} {review.status}")

        print("\nDemo completed successfully!")

    except Exception as e:
        print(f"Demo failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
