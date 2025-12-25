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
        # Simple heuristic: use "cheap" for short queries, "expensive" for long or complex ones
        # This is a basic implementation; in practice, this could be trained on the reference dataset
        word_count = len(query.split())
        
        if word_count <= 5:
            return "cheap"
        elif word_count <= 15:
            return "mid"
        else:
            return "expensive"
