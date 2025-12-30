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
        # Simple heuristic: based on query length and keywords
        # Assume candidate_models is ["cheap", "mid", "expensive"]
        length = len(query)
        lower_query = query.lower()
        
        if length < 50 or any(word in lower_query for word in ["simple", "easy", "basic"]):
            return "cheap"
        elif length < 100 or any(word in lower_query for word in ["medium", "normal", "standard"]):
            return "mid"
        else:
            return "expensive"