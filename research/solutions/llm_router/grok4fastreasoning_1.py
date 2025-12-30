class Solution:
    def solve(self, query: str, candidate_models: list[str]) -> str:
        # Simple keyword-based routing for demonstration
        query_lower = query.lower()
        if any(word in query_lower for word in ['code', 'program', 'function', 'algorithm']):
            # Choose a coding model if available
            for model in candidate_models:
                if 'code' in model.lower() or 'program' in model.lower():
                    return model
        elif any(word in query_lower for word in ['math', 'calculate', 'equation']):
            # Choose a math model if available
            for model in candidate_models:
                if 'math' in model.lower() or 'calc' in model.lower():
                    return model
        elif any(word in query_lower for word in ['history', 'event', 'year']):
            # Choose a history model if available
            for model in candidate_models:
                if 'hist' in model.lower() or 'history' in model.lower():
                    return model
        else:
            # Default to the first candidate
            return candidate_models[0]