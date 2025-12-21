import pandas as pd
import io
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

class Solution:
    def __init__(self):
        # Reference dataset provided in the problem description
        csv_data = """sample_id,prompt,eval_name,WizardLM/WizardLM-13B-V1.2,claude-instant-v1,claude-v1,claude-v2,gpt-3.5-turbo-1106,gpt-4-1106-preview,meta/code-llama-instruct-34b-chat,meta/llama-2-70b-chat,mistralai/mistral-7b-chat,mistralai/mixtral-8x7b-chat,zero-one-ai/Yi-34B-Chat,gpt-3.5-turbo-1106|model_response,claude-instant-v1|model_response,claude-v1|model_response,claude-v2|model_response,gpt-4-1106-preview|model_response,meta/llama-2-70b-chat|model_response,mistralai/mixtral-8x7b-chat|model_response,zero-one-ai/Yi-34B-Chat|model_response,WizardLM/WizardLM-13B-V1.2|model_response,meta/code-llama-instruct-34b-chat|model_response,mistralai/mistral-7b-chat|model_response,gpt-3.5-turbo-1106|total_cost,claude-instant-v1|total_cost,claude-v1|total_cost,claude-v2|total_cost,gpt-4-1106-preview|total_cost,meta/llama-2-70b-chat|total_cost,mistralai/mixtral-8x7b-chat|total_cost,zero-one-ai/Yi-34B-Chat|total_cost,WizardLM/WizardLM-13B-V1.2|total_cost,meta/code-llama-instruct-34b-chat|total_cost,mistralai/mistral-7b-chat|total_cost,oracle_model_to_route_to
mmlu-professional-psychology.val.221,"['Please answer with the letter of the correct answer.\\n\\nWhich of the following values is least characteristic of Asians and Asian Americans?\\nA) self-control\\nB) shame\\nC) egalitarianism\\nD) fatalism\\nPrint only a single choice  from ""A"" or ""B"" or ""C"" or ""D"" without explanation. Answer:']",mmlu-professional-psychology,0.0,1.0,1.0,1.0,1.0,1.0,0.0,0.0,0.0,0.0,1.0,['C)'],['C'],['C'],['C'],['C'],['\\nAnswer'],['D)'],['C'],['\\nB'],['\\nAnswer'],['\\nA'],7.500000000000001e-05,5.92e-05,0.0005920000000000001,0.0005920000000000001,0.00074,6.57e-05,4.38e-05,5.7600000000000004e-05,2.19e-05,5.6648000000000004e-05,1.46e-05,zero-one-ai/Yi-34B-Chat
mbpp.dev.325,['Write a function to compute the n-th power of each number in a list.'],mbpp,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,0.0,1.0,1.0,"[""Here's a Python function to compute the n-th power of each number in a list:\\n\\n
