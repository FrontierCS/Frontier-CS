import pandas as pd
from joblib import Parallel, delayed

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
        """
        Reorder columns in the DataFrame to maximize prefix hit rate.
        
        Args:
            df: Input DataFrame to optimize
            early_stop: Early stopping parameter (default: 100000)
            row_stop: Row stopping parameter (default: 4)
            col_stop: Column stopping parameter (default: 2)
            col_merge: List of column groups to merge (columns in each group are merged into one)
            one_way_dep: List of one-way dependencies (not used in this variant)
            distinct_value_threshold: Threshold for distinct values (default: 0.7)
            parallel: Whether to use parallel processing (default: True)
        
        Returns:
            DataFrame with reordered columns (same rows, different column order)
        """
        if df.empty:
            return df

        # 1. Handle col_merge
        if col_merge:
            merged_df_cols = {}
            merged_cols_set = set()
            for group in col_merge:
                if not group: continue
                merged_cols_set.update(group)
                new_col_name = '_'.join(map(str, group))
                merged_df_cols[new_col_name] = df[group].astype(str).agg(''.join, axis=1)
            
            df_processed = pd.DataFrame(merged_df_cols, index=df.index)

            # Add non-merged columns
            for col in df.columns:
                if col not in merged_cols_set:
                    df_processed[col] = df[col]
        else:
            df_processed = df.copy()

        # 2. Convert all to string for internal processing
        df_str = df_processed.astype(str)

        all_cols = df_str.columns.tolist()
        if len(all_cols) <= 1:
            return df_processed

        # 3. Separate high-cardinality columns
        num_rows = len(df_str)
        threshold = distinct_value_threshold * num_rows
        
        n_distincts = df_str.nunique().to_dict()

        high_card_cols = []
        low_card_cols = []

        for c in all_cols:
            if n_distincts.get(c, num_rows) > threshold and n_distincts.get(c, num_rows) > 1:
                high_card_cols.append(c)
            else:
                low_card_cols.append(c)
        
        high_card_cols.sort(key=lambda c: n_distincts.get(c, num_rows))
        
        # 4. Greedy search on low-cardinality columns
        P = []
        U = low_card_cols
        
        if not U: # All columns are high cardinality
            P.extend(high_card_cols)
            return df_processed[P]

        # 4.1. Choose p_1 based on fewest distinct values
        low_card_n_distincts = {c: n_distincts.get(c, num_rows) for c in U}
        p_1 = min(U, key=lambda c: low_card_n_distincts[c])
        P.append(p_1)
        U.remove(p_1)

        # 4.2. Greedy search for p_2 ... p_col_stop
        M_low = len(low_card_cols)
        
        def calculate_score(c, current_P, df_to_use):
            return c, df_to_use[current_P + [c]].drop_duplicates().shape[0]

        search_depth = min(col_stop, M_low)

        for k in range(2, search_depth + 1):
            if not U:
                break
            
            if parallel and len(U) > 1:
                n_jobs = -1 
                results = Parallel(n_jobs=n_jobs, prefer="threads")(
                    delayed(calculate_score)(c, P, df_str) for c in U
                )
                scores = dict(results)
            else:
                scores = {c: calculate_score(c, P, df_str)[1] for c in U}

            p_k = min(scores, key=scores.get)
            P.append(p_k)
            U.remove(p_k)

        # 4.3. Sort the rest of low-cardinality columns by their global nunique
        if U:
            U.sort(key=lambda c: low_card_n_distincts[c])
            P.extend(U)
            
        # 5. Append high-cardinality columns at the end
        P.extend(high_card_cols)
        
        return df_processed[P]