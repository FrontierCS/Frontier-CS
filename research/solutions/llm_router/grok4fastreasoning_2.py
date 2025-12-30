class Solution:
    def solve(self, query: str, eval_name: str, candidate_models: list[str]) -> str:
        # Simple heuristic: choose the first model for now (placeholder implementation)
        # In a real scenario, this would use more sophisticated logic like keyword matching
        # or a pre-trained classifier to select the best model for the query.
        if candidate_models:
            return candidate_models[0]
        return ""