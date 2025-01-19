from typing import Dict
from tools.context_interceptor import ContextInterceptor


class MetadataInterceptor(ContextInterceptor):
    name = "metadata_interceptor"
    description = "Adds metadata to context based on content analysis"

    def pre_completion(self, context: Dict) -> Dict:
        # Analyze context and add relevant metadata
        if "conversation_history" in context:
            word_count = sum(
                len(msg.get("content", "").split())
                for msg in context["conversation_history"]
            )

            # Add metadata flags
            context["metadata"] = {
                "word_count": word_count,
                "requires_citation": word_count > 100,
                "complexity_level": (
                    "high"
                    if word_count > 200
                    else "medium" if word_count > 50 else "low"
                ),
            }
        return context


class ActionInterceptor(ContextInterceptor):
    name = "action_interceptor"
    description = "Takes actions based on metadata flags"

    def pre_completion(self, context: Dict) -> Dict:
        metadata = context.get("metadata", {})

        if metadata.get("requires_citation"):
            # Add citation requirement to system message
            context["system_message"] = (
                context.get("system_message", "")
                + "\nPlease include citations for any factual claims."
            )

        if metadata.get("complexity_level") == "high":
            # Add request for simpler language
            context["system_message"] = (
                context.get("system_message", "")
                + "\nPlease use clear, simple language."
            )

        return context


def test_metadata_flow():
    # Create sample context
    context = {
        "conversation_history": [
            {
                "role": "user",
                "content": "Tell me about quantum physics and its applications in modern technology. "
                * 10,
            }
        ]
    }

    # Create interceptor chain
    metadata_interceptor = MetadataInterceptor()
    action_interceptor = ActionInterceptor()

    # Process through chain
    print("Initial context:", context)

    # First interceptor adds metadata
    context = metadata_interceptor.pre_completion(context)
    print("\nAfter metadata interceptor:")
    print("Metadata added:", context.get("metadata"))

    # Second interceptor acts on metadata
    context = action_interceptor.pre_completion(context)
    print("\nAfter action interceptor:")
    print("System message modifications:", context.get("system_message"))


if __name__ == "__main__":
    test_metadata_flow()
