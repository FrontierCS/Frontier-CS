import io
import pandas as pd
import ast
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.pipeline import Pipeline
import warnings

warnings.filterwarnings("ignore")

DATA = """sample_id,prompt,eval_name,WizardLM/WizardLM-13B-V1.2,claude-instant-v1,claude-v1,claude-v2,gpt-3.5-turbo-1106,gpt-4-1106-preview,meta/code-llama-instruct-34b-chat,meta/llama-2-70b-chat,mistralai/mistral-7b-chat,mistralai/mixtral-8x7b-chat,zero-one-ai/Yi-34B-Chat,gpt-3.5-turbo-1106|model_response,claude-instant-v1|model_response,claude-v1|model_response,claude-v2|model_response,gpt-4-1106-preview|model_response,meta/llama-2-70b-chat|model_response,mistralai/mixtral-8x7b-chat|model_response,zero-one-ai/Yi-34B-Chat|model_response,WizardLM/WizardLM-13B-V1.2|model_response,meta/code-llama-instruct-34b-chat|model_response,mistralai/mistral-7b-chat|model_response,gpt-3.5-turbo-1106|total_cost,claude-instant-v1|total_cost,claude-v1|total_cost,claude-v2|total_cost,gpt-4-1106-preview|total_cost,meta/llama-2-70b-chat|total_cost,mistralai/mixtral-8x7b-chat|total_cost,zero-one-ai/Yi-34B-Chat|total_cost,WizardLM/WizardLM-13B-V1.2|total_cost,meta/code-llama-instruct-34b-chat|total_cost,mistralai/mistral-7b-chat|total_cost,oracle_model_to_route_to
mmlu-professional-psychology.val.221,"['Please answer with the letter of the correct answer.\\n\\nWhich of the following values is least characteristic of Asians and Asian Americans?\\nA) self-control\\nB) shame\\nC) egalitarianism\\nD) fatalism\\nPrint only a single choice  from ""A"" or ""B"" or ""C"" or ""D"" without explanation. Answer:']",mmlu-professional-psychology,0.0,1.0,1.0,1.0,1.0,1.0,0.0,0.0,0.0,0.0,1.0,['C)'],['C'],['C'],['C'],['C'],['\\nAnswer'],['D)'],['C'],['\\nB'],['\\nAnswer'],['\\nA'],7.500000000000001e-05,5.92e-05,0.0005920000000000001,0.0005920000000000001,0.00074,6.57e-05,4.38e-05,5.7600000000000004e-05,2.19e-05,5.6648000000000004e-05,1.46e-05,zero-one-ai/Yi-34B-Chat
mbpp.dev.325,"['Write a function to compute the n-th power of each number in a list.']",mbpp,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,0.0,1.0,1.0,"[""Here's a Python function to compute the n-th power of each number in a list:\\n\\n```python\\ndef compute_nth_power(numbers, n):\\n    powered_numbers = [num ** n for num in numbers]\\n    return powered_numbers\\n```\\n\\nYou can use this function by passing a list of numbers and the value of n as arguments. For example:\\n\\n```python\\nnumbers = [1, 2, 3, 4, 5]\\nn = 3\\nresult = compute_nth_power(numbers, n)\\nprint(result)  # Output: [1, 8, 27, 64, 125]\\n```""]","['Here is a function to compute the n-th power of each number in a list:\\n\\n```python\\ndef nth_power(nums, n):\\n    result = []\\n    for num in nums:\\n        result.append(num ** n)  \\n    return result\\n```\\n\\nUsage:\\n```python\\nnums = [1, 2, 3]\\nn = 3\\n\\nresult = nth_power(nums, n)\\n\\nprint(result)\\n# [1, 8, 27]\\n```\\n\\nThis works by:\\n\\n- Initializing an empty result list \\n- Iterating over each number in the input list \\n- Computing the n-th power of that number using num ** n \\n- Appending the result to the result list\\n- Returning the final result list\\n\\nHope this helps! Let me know if you have any other questions.']","['Here's a function to compute the n-th power of each number in a list:\\n\\n```python\\ndef power_list(nums, n):\\n    \"\"\"\"\"\"Return a list with the n-th power of each number in nums.\"\"\"\"\"\"\\n    powered = []\\n    for num in nums:\\n        powered.append(num ** n)\\n    return powered\\n```\\n\\nFor example:\\n```python\\n>>> power_list([2, 3, 4], 2)\\n[4, 9, 16]\\n>>> power_list([2, 3, 4], 3)\\n[8, 27, 64]\\n```']","['Here is a Python function to compute the n-th power of each number in a list:\\n\\n```python\\ndef power_list(lst, n):\\n    \"\"\"\"\"\"Compute the n-th power of each number in a list\"\"\"\"\"\"\\n    powered_lst = []\\n    for num in lst:\\n        powered_lst.append(num ** n)\\n    return powered_lst\\n```\\n\\nTo explain, the function takes two arguments:\\n\\n- `lst` - The input list of numbers \\n- `n` - The power to raise each number to\\n\\nIt initializes an empty list `powered_lst` to store the results. \\n\\nThen it iterates through each number `num` in the input `lst`. It raises `num` to the `n-th` power using the exponentiation operator `**`. \\n\\nThe result is appended to `powered_lst`.\\n\\nFinally, the `powered_lst` is returned which contains each input number raised to the given power `n`.\\n\\nTo use it:\\n\\n```python\\nnums = [1, 2, 3, 4]\\nprint(power_list(nums, 3)) \\n# [1, 8, 27, 64] (cubed)\\n```\\n\\nLet me know if any part needs more explanation!']","['Certainly! Below is a Python function that takes a list of numbers and an integer `n`, and returns a new list with each number raised to the `n`-th power.\\n\\n```python\\ndef nth_power_of_list(numbers, n):\\n    return [x**n for x in numbers]\\n\\n# Example usage:\\nmy_list = [2, 3, 4, 5]\\nn = 3\\nresult = nth_power_of_list(my_list, n)\\nprint(result)  # Output: [8, 27, 64, 125]\\n```\\n\\nThis function uses list comprehension to iterate over each element `x` in the input list `numbers` and computes `x**n`, which is `x` raised to the power of `n`. The resulting list is then returned.']","["" Sure! Here's a function that takes a list of numbers and returns a list of their n-th powers:\\n```\\ndef powers(numbers, n):\\n    return [number ** n for number in numbers]\\n```\\nHere's an example of how you can use this function:\\n```\\nnumbers = [2, 3, 4, 5]\\nresult = powers(numbers, 3)\\nprint(result)  # [8, 27, 64, 125]\\n```\\nThis function uses a list comprehension to create a new list containing the n-th power of each number in the original list. The list comprehension is defined as `[number ** n for number in numbers]`\\n\\nThe `**` operator is used to compute the power of each number. For example, `2 ** 3` computes 2 to the power of 3, which is 8.\\n\\nYou can change the value of `n` to compute the powers of a different order. For example, if you want to compute the squares of the numbers in the list, you can set `n` to 2:\\n```\\nresult = powers(numbers, 2)\\nprint(result)  # [4, 9, 16, 25]\\n```\\nI hope this helps! Let me know if you have any questions.""]","['Here is a function in Python that computes the n-th power of each number in a list:\\n\\n```python\\ndef power_of_each(numbers, n):\\n    return [num ** n for num in numbers]\\n```\\n\\nYou can use this function by passing a list of numbers and the exponent as arguments. For example:\\n\\n```python\\nnumbers = [1, 2, 3, 4, 5]\\nn = 3\\nprint(power_of_each(numbers, n))  # Output: [1, 8, 27, 64, 125]\\n```\\n\\nThis function uses list comprehension to create a new list where each element is the result of raising the corresponding element in the input list to the power of `n`.']","[""\\nHere's a Python function that computes the n-th power of each number in a list:\\n\\n```python\\ndef powers_of_numbers(numbers, n):\\n    return [number ** n for number in numbers]\\n\\n# Example usage:\\nnumbers = [2, 3, 4]\\nn = 5\\nresult = powers_of_numbers(numbers, n)\\nprint(result)  # Output: [32, 243, 1024]\\n```\\n\\nThis function uses a list comprehension to calculate the n-th power of each number in the list `numbers` and returns the result as a new list.""]","[""Here's a Python function that takes a list of numbers and returns a new list with the n-th power of each number:\\r\\n\\r\\n```python\\r\\ndef power_n(numbers, n):\\r\\n    result = []\\r\\n    for num in numbers:\\r\\n        result.append(num ** n)\\r\\n    return result\\r\\n```\\r\\n\\r\\nYou can use this function like this:\\r\\n\\r\\n```python\\r\\n>>> power_n([1, 2, 3, 4], 3)\\r\\n[1, 2, 3, 4]\\r\\n>>> power_n([10, 20, 30], 0)\\r\\n[10, 1, 0.001]\\r\\n```\\r\\n\\r\\nIn the first example, the function computes the cube of each number in the list [1, 2, 3, 4]. In the second example, the function computes the zeroeth power of each number in the list [10, 20, 30], which returns the original numbers for non-negative integers and 1 for negative integers and fractions.""]","[' \\n[PYTHON]\\ndef compute_powers(my_list, n):\\n    return [x**n for x in my_list]\\n[/PYTHON]\\n[TESTS]\\n# Test case 1:\\nassert compute_powers([1, 2, 3], 2) == [1, 4, 9]\\n# Test case 2:\\nassert compute_powers([1, 2, 3], 3) == [1, 8, 27]\\n# Test case 3:\\nassert compute_powers([], 2) == []\\n[/TESTS]\\n']","['Here is a function written in Python that computes the n-th power of each number in a list:\\n\\n```python\\ndef power_list(n):\\n    result = []\\n    for num in list:\\n        result.append(num ** n)\\n    return result\\n```\\n\\nThis function takes in a single parameter `n`, which represents the exponent to which each number in the list will be raised. The function first initializes an empty list called `result`, which will store the computed powers. Then, it iterates over each number in the input list using a for loop. For each number, the function raises it to the power of `n` using the `**` operator and appends the result to the `result` list. Finally, the function returns the `result` list containing the n-th power of each number in the input list.']",0.000272,0.0004016,0.003032,0.005984,0.005050000000000001,0.0002529,9.9e-05,0.000108,6.48e-05,0.000102432,3.66e-05,WizardLM/WizardLM-13B-V1.2
hellaswag.val.2680,"['A man dressed in winter gear is sitting out in winter on a frozen lake. he\\nA) is holding a fishing pole in his hands and holding it periodically as he sucks in some water.\\nB) is carving a piece of shoreline with a marker while another man sits on top of a ski slope near the boat.\\nC) is sitting there with fishing equipment fishing on the frozen lake.\\nD) is paddling through the difficult waters.\\nPrint only a single choice  from ""A"" or ""B"" or ""C"" or ""D"" without explanation.\\nAnswer:']",hellaswag,1.0,1.0,1.0,1.0,1.0,1.0,0.0,1.0,0.0,1.0,1.0,['C)'],['C'],['C'],['C'],['C'],['C'],['C)'],['C'],['C)'],['A)'],['A)'],0.000119,9.44e-05,0.0009440000000000001,0.0009440000000000001,0.00118,0.00010439999999999999,7.02e-05,9.28e-05,3.51e-05,9.079200000000001e-05,2.34e-05,WizardLM/WizardLM-13B-V1.2
hellaswag.val.1629,"['A team of basketball players are shown on the right side of the court doing lay-ups. after several turns\\nA) a man comes into frame and begins demonstrating the steps to pull the ball up his body.\\nB) the team takes off their helmets and tennis shoes.\\nC) , they move to the left side of the court and begin practicing the lay ups once more.\\nD) the game goes very well and many people run onto the court and watch young boys do various sports on the court.\\nPrint only a single choice  from ""A"" or ""B"" or ""C"" or ""D"" without explanation.\\nAnswer:']",hellaswag,1.0,1.0,1.0,1.0,1.0,1.0,0.0,1.0,0.0,1.0,1.0,['C)'],['C'],['C'],['C'],['C'],['C'],['C)'],['C'],['C)'],['\\nAnswer'],['A)'],0.00013099999999999999,0.00010400000000000001,0.00104,0.00104,0.0013000000000000002,0.0001152,7.740000000000001e-05,0.00010240000000000001,3.8700000000000006e-05,0.000100104,2.58e-05,WizardLM/WizardLM-13B-V1.2
mmlu-sociology.val.78,"['Please answer with the letter of the correct answer.\\n\\nWhich of the following best describes the practice of placing the blame for the problems of a society on one particular group?\\nA) Ethnocentrism\\nB) Institutionalization\\nC) Stereotyping\\nD) Scapegoating\\nPrint only a single choice  from ""A"" or ""B"" or ""C"" or ""D"" without explanation. Answer:']",mmlu-sociology,1.0,1.0,1.0,1.0,1.0,1.0,0.0,0.0,1.0,1.0,1.0,['D'],['D'],['D'],['D'],['D'],['\\nAnswer'],['D)'],['D'],['\\nD'],['\\nAnswer'],['\\nD'],8.7e-05,7.04e-05,0.0007040000000000001,0.0007040000000000001,0.0008799999999999999,7.83e-05,5.22e-05,6.88e-05,2.61e-05,6.751200000000001e-05,1.74e-05,mistralai/mistral-7b-chat
chinese_zodiac.dev.286,"[""You are an assistant who guesses the exact age using the chinese animal zodiac signs and age zones of the zodiac. A user wishing to obtain the subject's exact age provides the zodiac animal zodiac and the estimated age range of the subject, resulting in the year of birth. Answer only the 4-digit year of birth and do not provide any other explanation. If the current year, zodiac sign, and approximate age range are provided, please translate and print only the input without additional sentences."", '2023, rabbit, 10s']",chinese_zodiac,0.0,0.0,1.0,0.0,0.0,1.0,0.0,0.0,0.0,0.0,0.0,['1999'],['2008'],['2011'],['2009'],['2011'],[' Sure! The year of birth for a person born in the 10s of the rabbit zodiac sign is 1999.'],['1987'],['\\n1999'],['2012'],"[' The Chinese zodiac sign for 2023 is the Rabbit. If the user is in their 10s, their birth year would be between 2013 and 2014.']",['2013'],0.00011300000000000001,9.2e-05,0.00092,0.00092,0.00115,0.00012150000000000001,6.659999999999999e-05,8.960000000000001e-05,3.3299999999999996e-05,0.00011329600000000001,2.22e-05,claude-v1
hellaswag.val.5145,"['[header] How to make lavender breath freshener [title] Choose the best dry culinary lavender. [step] Many grocery stores sell lavender stems either in the spices or vegetable aisle. Farmer's markets are another great source.\\nA) These produce more fragrant produce, rather than a more pungent source of odors. The moisture of the berries and herbs causes their leaves to produce more harsh, bitter scents.\\nB) You will need an estimated 1 tablespoon (14. 8 ml) of dry lavender for this recipe.\\nC) But if your home is very dry or stuffy, you should hire herbs that are hardy. [substeps] If this is a decision for you, go for the organic organic herbs, as they'll be almost entirely natural and can become the freshest scent.\\nD) Call a local yard sale if your mom packed your garden with lemon/lime or other organic herbs and seeds. [title] Scoop out a cup of air freshener in a jar.\\nPrint only a single choice  from ""A"" or ""B"" or ""C"" or ""D"" without explanation.\\nAnswer:']",hellaswag,0.0,1.0,1.0,1.0,1.0,1.0,0.0,1.0,0.0,0.0,1.0,['B)'],['B'],['B'],['B'],['B'],['B'],['A)'],['B)'],['A)'],['A)'],['A)'],0.000236,0.00018800000000000002,0.00188,0.00188,0.00235,0.0002097,0.0001404,0.00018720000000000002,7.02e-05,0.000181584,4.6800000000000006e-05,zero-one-ai/Yi-34B-Chat
"""

_pipeline = None
_rules = None
_fallback_choice = "cheap"

class Solution:
    def __init__(self):
        global _pipeline, _rules, _fallback_choice
        if _pipeline is not None and _rules is not None:
            self.pipeline = _pipeline
            self.rules = _rules
            self.fallback_choice = _fallback_choice
            return

        self.MODEL_MAPPING = {
            "cheap": "mistralai/mistral-7b-chat",
            "mid": "mistralai/mixtral-8x7b-chat",
            "expensive": "gpt-4-1106-preview",
        }
        self.LAMBDA = 150.0
        self.RULE_PURITY_THRESHOLD = 0.90

        try:
            df = self._load_data()
            df = self._create_labels(df)
            self.rules, general_eval_names = self._build_rules(df)
            df_general = df[df['eval_name'].isin(general_eval_names)]
            
            self.pipeline = self._train_model(df_general) if not df_general.empty else None
            self.fallback_choice = df['label'].mode()[0] if not df.empty else "cheap"

            _pipeline = self.pipeline
            _rules = self.rules
            _fallback_choice = self.fallback_choice
        except Exception:
            self.pipeline = None
            self.rules = {}
            self.fallback_choice = "cheap"
            _pipeline, _rules, _fallback_choice = self.pipeline, self.rules, self.fallback_choice

    def _load_data(self) -> pd.DataFrame:
        return pd.read_csv(io.StringIO(DATA))

    def _clean_prompt(self, prompt_str: str) -> str:
        try:
            items = ast.literal_eval(str(prompt_str))
            return ' '.join(map(str, items))
        except (ValueError, SyntaxError):
            return str(prompt_str)

    def _create_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        scores = {}
        for tier, model_name in self.MODEL_MAPPING.items():
            correctness_col = model_name
            cost_col = f"{model_name}|total_cost"
            
            if correctness_col in df.columns and cost_col in df.columns:
                correctness = df[correctness_col].fillna(0.0)
                cost = df[cost_col].fillna(0.0)
                scores[f"{tier}_score"] = correctness - self.LAMBDA * cost
            else:
                scores[f"{tier}_score"] = pd.Series([-1e9] * len(df), index=df.index)

        score_df = pd.DataFrame(scores)
        df['label'] = score_df.idxmax(axis=1).str.replace('_score', '')
        return df

    def _build_rules(self, df: pd.DataFrame) -> tuple[dict, set]:
        rules = {}
        general_eval_names = set(df['eval_name'].unique())

        for name, group in df.groupby('eval_name'):
            if len(group) < 10:
                continue

            counts = group['label'].value_counts(normalize=True)
            if not counts.empty:
                mode = counts.index[0]
                purity = counts.iloc[0]
                if purity >= self.RULE_PURITY_THRESHOLD:
                    rules[name] = mode
                    general_eval_names.remove(name)
        
        return rules, general_eval_names

    def _train_model(self, df: pd.DataFrame) -> Pipeline:
        df['prompt_cleaned'] = df['prompt'].apply(self._clean_prompt)
        df['text_input'] = df['eval_name'] + " " + df['prompt_cleaned']

        pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(
                ngram_range=(1, 2),
                max_features=25000,
                stop_words='english',
                sublinear_tf=True,
                min_df=2,
                max_df=0.9
            )),
            ('clf', SGDClassifier(
                loss='log_loss',
                penalty='elasticnet',
                alpha=1e-5,
                random_state=42,
                max_iter=300,
                tol=1e-4,
                class_weight='balanced'
            ))
        ])

        pipeline.fit(df['text_input'], df['label'])
        return pipeline

    def solve(self, query: str, eval_name: str, candidate_models: list[str]) -> str:
        if eval_name in self.rules:
            return self.rules[eval_name]

        if self.pipeline:
            text_input = f"{eval_name} {query}"
            prediction = self.pipeline.predict([text_input])[0]
            if prediction in candidate_models:
                return prediction

        return self.fallback_choice
