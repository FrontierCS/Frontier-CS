class Solution:
    def solve(self, query: str, eval_name: str, candidate_models: list[str]) -> str:
        """
        Select a model from candidate_models based on the eval_name.
        For coding tasks, choose a code-specialized model if available.
        For QA or other tasks, choose a general or QA model.
        This is a simple heuristic; in a real router, this could be more sophisticated
        using query analysis or ML.
        """
        # Simple mapping based on eval_name to model type preference
        model_preferences = {
            'mbpp': 'code',
            'hellaswag': 'general',
            'arc-challenge': 'qa',
            'winogrande': 'qa',
            'grade-school-math': 'math',
            'chinese_zodiac': 'qa',
            'mmlu-*': 'knowledge',  # For all MMLU variants
            'consensus_summary': 'summarizer',
            'abstract2title': 'summarizer',
            'bias_detection': 'bias_detector',
            'chinese_homonym': 'linguistics',
            'chinese_character_riddles': 'riddle_solver',
            'chinese_modern_poem_identification': 'literature',
            'mbpp': 'code',
            # Default to general for unknown
            'default': 'general'
        }
        
        # Get preferred type
        pref_type = model_preferences.get(eval_name, 'default')
        
        # Find best matching model from candidates
        best_model = None
        for model in candidate_models:
            if pref_type in model.lower():
                best_model = model
                break
        if best_model is None:
            best_model = candidate_models[0]  # Fallback to first model
        
        return best_model
