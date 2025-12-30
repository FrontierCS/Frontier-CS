#include <iostream>
#include <vector>
#include <cmath>
#include <map>
#include <algorithm>

using namespace std;

long long N;
const int MOD = 1e9 + 7;
const int MOD_EXP = 1e9 + 6;

// Computes (base^exp) % MOD
long long power(long long base, long long exp) {
    long long res = 1;
    base %= MOD;
    while (exp > 0) {
        if (exp % 2 == 1) res = (res * base) % MOD;
        base = (base * base) % MOD;
        exp /= 2;
    }
    return res;
}

// Baby-step Giant-step algorithm to find x such that 2^x = target (mod MOD)
// Returns the smallest non-negative x.
long long discrete_log(long long target) {
    long long m = 32000; // sqrt(10^9) approx
    
    map<long long, int> table;
    long long curr = 1;
    for (int j = 0; j < m; ++j) {
        if (table.find(curr) == table.end()) table[curr] = j;
        curr = (curr * 2) % MOD;
    }
    
    long long factor = power(2, MOD - 1 - m); // 2^{-m}
    long long cur_target = target;
    
    // We need to cover range up to MOD-1. (m+1)*m > MOD-1
    for (int i = 0; i < m + 5; ++i) { 
        if (table.count(cur_target)) {
            return (long long)i * m + table[cur_target];
        }
        cur_target = (cur_target * factor) % MOD;
    }
    return -1;
}

struct BlockResult {
    long long val_a0_1;
    long long M0;
    vector<long long> candidates;
};

vector<BlockResult> results;
vector<int> final_ops; 
bool solved = false;

// Evaluate the expression for verification
long long evaluate(const vector<int>& ops, const vector<long long>& a) {
    long long val = a[0];
    for (int i = 1; i <= N; ++i) {
        if (ops[i-1] == 0) { // +
            val = (val + a[i]) % MOD;
        } else { // x
            val = (val * a[i]) % MOD;
        }
    }
    return val;
}

// Backtracking to find consistent operators
void solve_backtrack(int block_idx, vector<long long>& current_masks) {
    if (solved) return;
    if (block_idx == results.size()) {
        // Construct full operators from masks
        vector<int> test_ops;
        for (int b = 0; b < results.size(); ++b) {
            long long mask = current_masks[b];
            int limit = (b == results.size() - 1) ? (N % 30 == 0 ? 30 : N % 30) : 30;
            for (int k = 0; k < limit; ++k) {
                if ((mask >> k) & 1) test_ops.push_back(1);
                else test_ops.push_back(0);
            }
        }
        
        // Verify consistency with all block observations
        bool ok = true;
        for (int b = 0; b < results.size(); ++b) {
            vector<long long> a(N + 1, 1);
            a[0] = 1;
            int start_idx = b * 30;
            int limit = (b == results.size() - 1) ? (N % 30 == 0 ? 30 : N % 30) : 30;
            for (int k = 0; k < limit; ++k) {
                long long exponent = (1LL << k); 
                a[start_idx + k + 1] = power(2, exponent);
            }
            
            long long res = evaluate(test_ops, a);
            if (res != results[b].val_a0_1) {
                ok = false;
                break;
            }
        }
        
        if (ok) {
            final_ops = test_ops;
            solved = true;
        }
        return;
    }

    for (long long mask : results[block_idx].candidates) {
        current_masks[block_idx] = mask;
        solve_backtrack(block_idx + 1, current_masks);
        if (solved) return;
    }
}

int main() {
    cin >> N;
    
    int num_blocks = (N + 29) / 30;
    
    for (int b = 0; b < num_blocks; ++b) {
        int start = b * 30 + 1;
        int end = min((long long)(b + 1) * 30, N);
        int len = end - start + 1;
        
        // Prepare query input a
        vector<long long> q_a(N + 1, 1);
        q_a[0] = 1;
        for (int i = 0; i < len; ++i) {
            int idx = start + i;
            long long exponent = (1LL << i); 
            q_a[idx] = power(2, exponent);
        }
        
        // Query 1: a0 = 1
        cout << "?";
        for (long long val : q_a) cout << " " << val;
        cout << endl;
        long long val1;
        cin >> val1;
        
        // Query 2: a0 = 2
        q_a[0] = 2;
        cout << "?";
        for (long long val : q_a) cout << " " << val;
        cout << endl;
        long long val2;
        cin >> val2;
        
        long long M0 = (val2 - val1 + MOD) % MOD;
        
        BlockResult res;
        res.val_a0_1 = val1;
        res.M0 = M0;
        
        long long V = discrete_log(M0);
        
        // Possible mask values are V or V + (MOD-1), checking against 2^len - 1
        long long max_mask = (1LL << len) - 1;
        
        if (V <= max_mask) res.candidates.push_back(V);
        if (V + MOD_EXP <= max_mask) res.candidates.push_back(V + MOD_EXP);
        
        results.push_back(res);
    }
    
    vector<long long> masks(num_blocks);
    solve_backtrack(0, masks);
    
    cout << "!";
    for (int op : final_ops) {
        cout << " " << op;
    }
    cout << endl;
    
    return 0;
}