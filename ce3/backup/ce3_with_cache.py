    def _display_usage_stats(self, token_usage: Optional[Dict] = None):
        # Get cache statistics
        cache_stats = self.prompt_cache.get_cache_stats()
        
        # Create horizontal cache stats display
        cache_display = (
            f"Cache: "
            f"Hits: {cache_stats['hits']} | "
            f"Misses: {cache_stats['misses']} | "
            f"Rate: {cache_stats['hit_rate']} | "
            f"Saved: {cache_stats['bytes_saved'] / 1024:.1f}KB"
        )
        self.console.print(cache_display)

        # Display token usage if available
        if token_usage:
            tokens_display = (
                f"Tokens: "
                f"In: {token_usage.input_tokens} | "
                f"Out: {token_usage.output_tokens} | "
                f"Total: {self.total_tokens_used} | "
                f"Remaining: {Config.MAX_CONVERSATION_TOKENS - self.total_tokens_used}"
            )
            self.console.print(tokens_display)