import pandas as pd
import numpy as np

class Solution:
    def solve(
        self,
        df: pd.DataFrame,
        early_stop: int = 100000,
        row_stop: int = 4,
        col_stop: int = 2,
        col_merge: list = None,
        one_way_dep: list = None,
        distinct_value_threshold: float = 0.7,
        parallel: bool = True,
    ) -> pd.DataFrame:
        
        # Working copy to prevent side effects and handle merges
        df_work = df.copy()
        
        # 1. Apply Column Merges
        if col_merge:
            for group in col_merge:
                # Filter for columns that actually exist in the dataframe
                valid_cols = [c for c in group if c in df_work.columns]
                
                if len(valid_cols) > 1:
                    # Construct new column name (just for DataFrame integrity)
                    new_col_name = "+".join([str(c) for c in valid_cols])
                    
                    # Concatenate column values as strings
                    merged_series = df_work[valid_cols[0]].astype(str)
                    for c in valid_cols[1:]:
                        merged_series = merged_series + df_work[c].astype(str)
                    
                    # Insert merged column and remove original columns
                    df_work[new_col_name] = merged_series
                    df_work.drop(columns=valid_cols, inplace=True)
        
        # 2. Data Preparation
        # If dataset is very large, sample it to estimate the optimal order within time limits.
        # N=20000 is sufficient for a robust estimate.
        N = len(df_work)
        if N > 20000:
            df_sample = df_work.sample(n=20000, random_state=42)
        else:
            df_sample = df_work

        cols = list(df_sample.columns)
        num_cols = len(cols)
        
        # Precompute string values and their lengths for the sample
        col_data = {}
        col_lens = {}
        col_total_len = {}
        
        for c in cols:
            s = df_sample[c].astype(str)
            col_data[c] = s.values
            l = s.str.len().values
            col_lens[c] = l
            col_total_len[c] = l.sum()

        # 3. Beam Search for Optimal Column Order
        # We want to maximize the prefix hit rate, which roughly corresponds to maximizing
        # the sum of lengths of prefixes shared with previous rows.
        # This is equivalent to minimizing the entropy/unique bytes introduced at each step.
        
        beam_width = 4
        
        # Initial state: no columns selected, all rows in same root group (0)
        # We use int32 for group IDs for memory efficiency
        initial_groups = np.zeros(len(df_sample), dtype=np.int32)
        
        # State: {'score': float, 'groups': np.array, 'used': set, 'order': list}
        current_states = [{
            'score': 0,
            'groups': initial_groups,
            'used': set(),
            'order': []
        }]
        
        for step in range(num_cols):
            next_states = []
            
            for state in current_states:
                available_cols = [c for c in cols if c not in state['used']]
                
                for c in available_cols:
                    vals = col_data[c]
                    lens = col_lens[c]
                    groups = state['groups']
                    
                    # Construct a temporary DataFrame to group by (current_group, new_col_value)
                    # We need to calculate the "cost" of adding this column:
                    # Cost = sum of lengths of unique values introduced in each group.
                    # Gain = Total Length - Cost.
                    temp_df = pd.DataFrame({'g': groups, 'v': vals, 'l': lens})
                    
                    # Drop duplicates to find unique branches in the prefix tree
                    unique_pairs = temp_df.drop_duplicates(subset=['g', 'v'])
                    
                    # The cost is the length of these unique branches (they are "new" information)
                    cost = unique_pairs['l'].sum()
                    gain = col_total_len[c] - cost
                    new_score = state['score'] + gain
                    
                    # Calculate new group IDs for the next step
                    # ngroup() assigns a unique integer to each (group, value) pair
                    new_groups = temp_df.groupby(['g', 'v'], sort=False).ngroup().values.astype(np.int32)
                    
                    # Secondary metric: number of resulting groups (fragmentation)
                    num_groups = len(unique_pairs)
                    
                    next_states.append({
                        'score': new_score,
                        'groups': new_groups,
                        'used': state['used'] | {c},
                        'order': state['order'] + [c],
                        'num_groups': num_groups
                    })
            
            # Select best states
            # Sort by score descending. Tie-break with number of groups (fewer is better/less fragmentation)
            next_states.sort(key=lambda x: (x['score'], -x['num_groups']), reverse=True)
            current_states = next_states[:beam_width]

        # 4. Return Result
        best_state = current_states[0]
        final_order = best_state['order']
        
        return df_work[final_order]