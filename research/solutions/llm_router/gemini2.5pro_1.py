import ast

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
        
        # 1. Default routing based on eval_name (the strongest signal)
        
        # Hard tasks -> default to 'expensive'
        # These typically involve complex reasoning, code generation, or specialized knowledge.
        if eval_name.startswith('grade-school-math') or \
           'chinese' in eval_name or 'Chinese' in eval_name or \
           eval_name in ['bias_detection', 'consensus_summary']:
            model = 'expensive'
        
        # Easy tasks -> default to 'cheap'
        # These are often straightforward classification or simple generation tasks.
        elif eval_name.startswith('winogrande') or \
             eval_name.startswith('abstract2title') or \
             eval_name.startswith('arc-challenge'):
            model = 'cheap'

        # MMLU tasks have varying difficulty, so we handle them with more nuance.
        elif eval_name.startswith('mmlu'):
            # Default for MMLU is 'cheap' as many are simple multiple-choice questions.
            model = 'cheap'
            # Escalate for subjects that sound more technical or advanced.
            hard_mmlu_keywords = [
                'professional', 'college', 'jurisprudence', 'law', 
                'physics', 'computer_science', 'econometrics', 
                'abstract_algebra', 'moral_disputes'
            ]
            if any(k in eval_name for k in hard_mmlu_keywords):
                model = 'mid'

        # Other tasks with a clear default based on observed performance.
        elif eval_name.startswith('hellaswag'):
            model = 'mid'
        elif eval_name.startswith('mbpp'):
            # Coding tasks often require more than the cheapest model. 'mid' is a good balance.
            model = 'mid'
        
        # Fallback for any other unknown task. 'mid' is a safe general-purpose default.
        else:
            model = 'mid'

        # 2. Fine-tuning overrides based on query content and length
        
        query_len = len(query)
        lower_query = query.lower()

        # Escalation from 'cheap' to 'mid'
        if model == 'cheap':
            # Long queries are often more complex.
            if query_len > 1200:
                model = 'mid'
            else:
                # Queries with code-like content are harder.
                code_keywords = ['program', 'code', 'function', 'python', 
                                 'list', 'algorithm', 'sum ←', 'for each']
                if any(k in lower_query for k in code_keywords):
                    model = 'mid'

        # Escalation from 'mid' to 'expensive'
        if model == 'mid':
            # Extremely long Hellaswag prompts might involve more complex scenarios.
            if eval_name.startswith('hellaswag') and query_len > 1500:
                model = 'expensive'
            # Long MBPP descriptions might imply more complex requirements.
            if eval_name.startswith('mbpp') and query_len > 250:
                model = 'expensive'

        # De-escalation from 'expensive' to 'mid'
        if model == 'expensive':
            # Simple math problems with short questions can often be handled by 'mid'.
            if eval_name.startswith('grade-school-math'):
                try:
                    # The query string is a list of strings; parse it to get the actual question.
                    q_list = ast.literal_eval(query)
                    if isinstance(q_list, list) and len(q_list) > 1:
                        actual_question = q_list[1]
                        if len(actual_question) < 120:
                            model = 'mid'
                except (ValueError, SyntaxError):
                    # If parsing fails, use a simple length heuristic on the whole string.
                    if query_len < 800:
                        model = 'mid'
            
            # Simple, short coding problems.
            elif eval_name.startswith('mbpp'):
                 if query_len < 120:
                     model = 'mid'

        # Final check to ensure the returned model is valid.
        if model not in candidate_models:
            # This should not happen with the default list, but as a safeguard.
            if 'mid' in candidate_models:
                return 'mid'
            elif 'cheap' in candidate_models:
                return 'cheap'
            else:
                return candidate_models[0]

        return model
