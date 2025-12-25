import re
import math

class Solution:
    """
    An LLM Router that selects the best model for a given query based on a
    heuristic scoring system. The goal is to maximize accuracy while minimizing cost.
    
    The strategy is as follows:
    1.  **Task-based Baseline**: Assign a baseline score to each model tier ("cheap", "mid", "expensive")
        based on the `eval_name`. This reflects the general difficulty and nature of the task.
        For example, coding tasks (`mbpp`) get higher baseline scores for more expensive models,
        while simpler MCQ tasks might favor cheaper models.
    2.  **Query-based Feature Adjustments**: Modify the baseline scores using features extracted
        from the query text. These features act as proxies for the specific query's complexity.
        -   **Length**: Longer queries are assumed to be more complex.
        -   **Structure**: The number of lines can indicate more complex formatting or context.
        -   **Content Keywords/Patterns**:
            -   Presence of code blocks ('
