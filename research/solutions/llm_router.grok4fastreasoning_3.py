import math

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
        # Simple heuristic: for coding tasks (eval_name == "mbpp"), choose 'expensive'
        # Otherwise, choose 'cheap' for simple queries
        if eval_name == "mbpp":
            return "expensive"
        else:
            return "cheap"