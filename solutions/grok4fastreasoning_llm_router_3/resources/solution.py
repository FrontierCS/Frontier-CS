class Solution:
    def solve(self, query: str, eval_name: str, candidate_models: list[str]) -> str:
        """
        Select exactly one routing option for the given query.
        Args:
            query: The user query.
            eval_name: The dataset or task name (e.g., "mbpp").
            candidate_models: A list of available routing options 
                              (["cheap", "mid", "expensive"] by default).
        Returns:
            A single string from candidate_models indicating
            the chosen model.
        """
        # Assume cost tiers: cheap=1, mid=2, expensive=3
        # Simple heuristic: longer queries need more expensive models
        # for accuracy, shorter ones can use cheaper for cost minimization
        query_length = len(query)
        
        if query_length > 100:
            # Long query: high accuracy needed, choose expensive
            for model in candidate_models:
                if "expensive" in model.lower():
                    return model
        elif query_length > 50:
            # Medium query: choose mid
            for model in candidate_models:
                if "mid" in model.lower():
                    return model
        else:
            # Short query: choose cheap to minimize cost
            for model in candidate_models:
                if "cheap" in model.lower():
                    return model
        
        # Fallback to first model if no match
        return candidate_models[0]
