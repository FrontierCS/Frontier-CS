import random
import re

class Solution:
    def __init__(self):
        # Heuristic keywords/patterns that often require higher intelligence models
        # These are derived from general knowledge of LLM capabilities on benchmarks like GSM8K, MATH, MBPP, etc.
        self.expensive_keywords = [
            # Math/Reasoning indicators
            "solve", "calculate", "equation", "proof", "prove", "integral", "derivative",
            "matrix", "probability", "theorem", "lemma", "algorithm", "complexity",
            "logic", "reasoning", "step-by-step", "explain why", "evaluate", "analyze",
            
            # Coding indicators
            "python", "java", "c++", "code", "function", "class", "script", "algorithm",
            "debug", "error", "exception", "api", "framework", "library", "sql", "database",
            "regex", "html", "css", "javascript", "react", "node", "docker", "kubernetes",
            
            # Complex task indicators
            "summary", "summarize", "extract", "classification", "classify", "translation",
            "translate", "rewrite", "paraphrase", "creative", "poem", "story", "essay",
            "critique", "review", "comparison", "compare", "contrast", "nuance", "subtle",
            "inference", "implication", "cause", "effect", "relationship", "connection",
            "context", "background", "history", "philosophy", "psychology", "sociology",
            "economics", "politics", "law", "medicine", "biology", "chemistry", "physics",
            "astronomy", "geology", "engineering", "architecture", "design", "art",
            "literature", "music", "film", "culture", "religion", "ethics", "moral",
            
            # Specific tough benchmarks often in training data
            "gsm8k", "math", "mbpp", "humaneval", "apps", "code_contests", "olympiad",
            "theoremqa", "sciq", "pubmedqa", "medqa", "professional_law", "lsat"
        ]
        
        self.cheap_keywords = [
            # Simple factual/lookup queries
            "capital of", "who is", "when was", "what is", "define", "meaning of",
            "synonym", "antonym", "spelling", "grammar", "simple", "easy", "basic",
            "list of", "name of", "count", "how many", "true or false", "yes or no"
        ]

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
        
        # Ensure candidate_models is valid
        if not candidate_models:
            return "cheap" # Default fallback
            
        # Cost estimates (normalized relative to 'cheap') - conceptual values
        # cheap: 1x, mid: 10x, expensive: 50x
        # Lambda is 150. This means if 'expensive' is 0.5% more accurate than 'mid', 
        # but costs $0.03 more, and lambda*cost = 150 * 0.03 = 4.5 penalty.
        # Accuracy is 0-1. 
        # Let's look at the actual costs in the reference dataset.
        # Example costs:
        # cheap (mistral-7b): ~5e-5 to 1e-4
        # mid (mixtral-8x7b): ~4e-4
        # expensive (gpt-4): ~3e-3 to 1e-2
        
        # Lambda = 150.
        # Cost of expensive ~ 0.005. Penalty ~ 150 * 0.005 = 0.75.
        # Cost of mid ~ 0.0005. Penalty ~ 150 * 0.0005 = 0.075.
        # Cost of cheap ~ 0.0001. Penalty ~ 150 * 0.0001 = 0.015.
        
        # Diff mid vs cheap: cost diff ~0.06. Accuracy gain needed > 0.06.
        # Diff expensive vs mid: cost diff ~0.675. Accuracy gain needed > 0.675.
        
        # This implies 'expensive' is VERY heavily penalized. It should only be used 
        # when we are almost certain 'mid' will fail and 'expensive' will succeed.
        # In many benchmarks, top open source models (mid) are close to GPT-4 (expensive).
        # Given the massive penalty, 'expensive' is rarely the optimal choice unless 
        # the prompt is extremely hard.
        
        # Strategy:
        # 1. Default to 'cheap'.
        # 2. Use 'mid' for moderately complex tasks (coding, reasoning).
        # 3. Use 'expensive' ONLY for extremely difficult tasks where 'mid' has low success rate.
        
        # Analyze eval_name
        eval_lower = eval_name.lower()
        
        # Tasks where 'mid' (e.g., Mixtral) often struggles compared to 'expensive' (GPT-4)
        # Usually complex reasoning, heavy coding, creative writing with constraints.
        expensive_tasks = [
            "math", "code", "reasoning", "hard", "advanced", "professional", 
            "olympiad", "theorem", "proof", "physics", "chemistry", "biology",
            "medicine", "law"
        ]
        
        # Tasks where 'cheap' might suffice or 'mid' is definitely enough
        cheap_tasks = [
            "trivia", "common_sense", "grammar", "spelling", "synonym", "classification",
            "extraction", "summary", "simple", "arc-easy", "piqa", "boolq"
        ]
        
        # Check eval_name hints
        is_hard_task = any(t in eval_lower for t in expensive_tasks)
        is_easy_task = any(t in eval_lower for t in cheap_tasks)
        
        # Text analysis
        query_lower = query.lower()
        query_len = len(query)
        
        # Heuristics based on query features
        has_math = bool(re.search(r'[\d\+\-\*/\^=]{3,}', query)) or "solve" in query_lower
        has_code = "def " in query or "class " in query or "import " in query or "
