#include <iostream>
#include <vector>
#include <algorithm>
#include <random>

using namespace std;

// Function to query the interactive judge
long long query(const vector<int>& a) {
    cout << "?";
    for (int x : a) cout << " " << x;
    cout << endl;
    long long res;
    cin >> res;
    return res;
}

const int MOD = 1e9 + 7;

// Helper to simulate a block of operators and inputs
// Returns {accumulated_sum_increment, final_term_value}
pair<long long, long long> process_block(const vector<int>& block_ops, const vector<int>& block_a, long long curr_val) {
    long long sum_inc = 0;
    long long val = curr_val;
    for (size_t i = 0; i < block_ops.size(); ++i) {
        if (block_ops[i] == 0) { // +
            sum_inc = (sum_inc + val) % MOD;
            val = block_a[i];
        } else { // *
            val = (val * block_a[i]) % MOD;
        }
    }
    return {sum_inc, val};
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    // 1. Determine total number of '+' operators.
    // Set a_0 = 2, all other a_i = 1.
    // If op_i is +, it adds a term. If *, it continues a term.
    // With a inputs as 1 (except a0=2), the sequence is a sum of terms.
    // The first term has value 2 (from a0), subsequent terms have value 1.
    // Value = 2 + (number of terms starting after 0) = 2 + (number of +).
    vector<int> a_base(n + 1, 1);
    a_base[0] = 2;
    long long r_base = query(a_base);
    int total_plus = (r_base - 2 + MOD) % MOD; 

    vector<int> final_ops(n);
    int seen_plus = 0;
    
    // Tracks the state of the computation (value of current term, accumulated sum)
    // assuming inputs are a_0=2, a_{1...}=1 for the prefix processed so far.
    long long current_val = 2; 
    long long current_sum = 0;

    // Block size determined to fit within 40 queries (N=600 -> ~34 blocks with size 18)
    int block_size = 18;
    mt19937 rng(1337);

    for (int i = 0; i < n; i += block_size) {
        int end = min(n, i + block_size);
        int len = end - i;
        
        // Prepare query with random values for the current block
        // a_0 = 2, a_{1..i} = 1, a_{i+1..end} = random, a_{end+1..n} = 1
        vector<int> q_a(n + 1, 1);
        q_a[0] = 2;
        vector<int> block_inputs;
        for (int k = 0; k < len; ++k) {
            int val = 2 + (rng() % 10000); // Random values >= 2 to avoid ambiguity
            q_a[i + 1 + k] = val;
            block_inputs.push_back(val);
        }
        
        long long res = query(q_a);
        
        // Calculate the target value we need to match from the simulation
        // The result from the judge includes the effect of the suffix (all 1s).
        // Suffix effect adds 1 for every '+' in the suffix.
        // Suffix '+' count = total_plus - seen_plus - (plus in current block).
        // V_total = (Simulated_Sum + Simulated_Val) + Suffix_Plus_Count
        // => Sim_Sum + Sim_Val - Plus_In_Block = V_total - (Total_Plus - Seen_Plus)
        
        long long target_part = (res - (total_plus - seen_plus)) % MOD;
        if (target_part < 0) target_part += MOD;

        int best_mask = -1;
        int limit = 1 << len;
        
        // Brute force all operator patterns for this block
        for (int mask = 0; mask < limit; ++mask) {
            vector<int> temp_ops(len);
            int plus_count = 0;
            for (int k = 0; k < len; ++k) {
                if ((mask >> k) & 1) {
                    temp_ops[k] = 1; // *
                } else {
                    temp_ops[k] = 0; // +
                    plus_count++;
                }
            }
            
            pair<long long, long long> p = process_block(temp_ops, block_inputs, current_val);
            long long sim_res = (current_sum + p.first + p.second) % MOD;
            
            long long check_val = (sim_res - plus_count) % MOD;
            if (check_val < 0) check_val += MOD;
            
            if (check_val == target_part) {
                best_mask = mask;
                break; // Found matching pattern
            }
        }
        
        // Record found operators and update global state
        vector<int> best_block_ops(len);
        for (int k = 0; k < len; ++k) {
            if ((best_mask >> k) & 1) best_block_ops[k] = 1;
            else best_block_ops[k] = 0;
            final_ops[i + k] = best_block_ops[k];
            if (best_block_ops[k] == 0) seen_plus++;
        }
        
        // Update current_sum and current_val as if this block had inputs equal to 1
        // This sets up the correct prefix state for the next block
        vector<int> ones(len, 1);
        pair<long long, long long> p = process_block(best_block_ops, ones, current_val);
        current_sum = (current_sum + p.first) % MOD;
        current_val = p.second;
    }
    
    cout << "! ";
    for (int i = 0; i < n; ++i) {
        cout << final_ops[i] << (i == n - 1 ? "" : " ");
    }
    cout << endl;

    return 0;
}