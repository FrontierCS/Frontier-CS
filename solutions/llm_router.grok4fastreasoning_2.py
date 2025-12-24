from typing import List

class Solution:
    def solve(self, query: str, eval_name: str, candidate_models: List[str]) -> str:
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
        # Simple heuristic: For coding-related tasks (e.g., "mbpp"), use "expensive"
        # For other tasks, use "mid" if query is short, "cheap" otherwise
        # This is a placeholder; in practice, use more sophisticated logic like LLM evaluation
        if "code" in eval_name.lower() or "python" in query.lower():
            return "expensive"
        elif len(query) < 50:
            return "cheap"
        else:
            return "mid"
