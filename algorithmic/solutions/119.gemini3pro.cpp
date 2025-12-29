#include <iostream>
#include <vector>
#include <cmath>
#include <map>
#include <algorithm>

using namespace std;

long long M = 1e9 + 7;

long long power(long long base, long long exp) {
    long long res = 1;
    base %= M;
    while (exp > 0) {
        if (exp % 2 == 1) res = (res * base) % M;
        base = (base * base) % M;
        exp /= 2;
    }
    return res;
}

long long modInverse(long long n) {
    return power(n, M - 2);
}

class DiscreteLog {
    long long g;
    long long m; 
    std::map<long long, int> table;
public:
    DiscreteLog(long long gen) {
        g = gen;
        m = (long long)sqrt(M - 1) + 1;
        long long cur = 1;
        for (int j = 0; j < m; ++j) {
            table[cur] = j;
            cur = (cur * g) % M;
        }
    }

    long long solve_optimized(long long a) {
        long long inv_a = modInverse(a);
        long long gm = power(g, m);
        long long cur = inv_a; 
        for (int i = 0; i <= m; ++i) {
            if (table.count(cur)) {
                // inv(a) * g^{mi} = g^j  => a = g^{mi - j}
                long long res = ((long long)i * m - table[cur]) % (M - 1);
                if (res < 0) res += (M - 1);
                return res;
            }
            cur = (cur * gm) % M;
        }
        return -1;
    }
};

long long evaluate(int n, const vector<int>& ops, const vector<long long>& a) {
    long long val = a[0];
    for (int i = 1; i <= n; ++i) {
        if (i - 1 < ops.size()) {
            if (ops[i-1] == 0) { // +
                val = (val + a[i]) % M;
            } else { // *
                val = (val * a[i]) % M;
            }
        } else {
            // Assume future ops are + for simulation
            val = (val + a[i]) % M;
        }
    }
    return val;
}

int main() {
    int n;
    if (!(cin >> n)) return 0;

    int BLOCK_SIZE = 30;
    int num_blocks = (n + BLOCK_SIZE - 1) / BLOCK_SIZE;

    DiscreteLog dlog(5); // primitive root 5 for 10^9+7
    
    vector<int> final_ops; 
    vector<long long> a(n + 1);
    
    for (int b = 0; b < num_blocks; ++b) {
        int start = b * BLOCK_SIZE + 1;
        int end = min((b + 1) * BLOCK_SIZE, n);
        int current_len = end - start + 1;

        // Construct input array a
        for (int i = 1; i < start; ++i) {
            a[i] = (i * 123456789LL + 987654321LL) % (M - 2) + 2; 
        }
        for (int i = start; i <= end; ++i) {
            int bit = i - start;
            long long exp = (1LL << bit);
            a[i] = power(5, exp);
        }
        for (int i = end + 1; i <= n; ++i) {
            a[i] = 1;
        }

        // Query 1
        a[0] = 1;
        cout << "?";
        for (int i = 0; i <= n; ++i) cout << " " << a[i];
        cout << endl;
        long long v1; cin >> v1;

        // Query 2
        a[0] = 2;
        cout << "?";
        for (int i = 0; i <= n; ++i) cout << " " << a[i];
        cout << endl;
        long long v2; cin >> v2;

        long long P_obs = (v2 - v1 + M) % M;
        long long Q_obs = (2 * v1 - v2 + 2 * M) % M;

        long long pref = 1;
        for (int i = 1; i < start; ++i) {
            if (final_ops[i-1] == 1) { // *
                pref = (pref * a[i]) % M;
            }
        }
        
        long long target = (P_obs * modInverse(pref)) % M;
        long long S = dlog.solve_optimized(target);
        
        vector<long long> candidates;
        candidates.push_back(S);
        // S + M - 1 might be a valid sum of powers of 2 (if S is small)
        // Max possible sum is 2^30 - 1.
        if (S + M - 1 < (1LL << 30)) { 
             candidates.push_back(S + M - 1);
        }
        
        vector<int> best_block_ops;
        bool found_any = false;

        for (long long cand_S : candidates) {
            vector<int> block_ops;
            bool ok = true;
            // Decode bits
            for (int k = 0; k < current_len; ++k) {
                if ((cand_S >> k) & 1) block_ops.push_back(1);
                else block_ops.push_back(0);
            }
            if (cand_S >= (1LL << current_len)) ok = false; 

            if (!ok) continue;

            vector<int> temp_ops = final_ops;
            temp_ops.insert(temp_ops.end(), block_ops.begin(), block_ops.end());
            
            vector<long long> a_zero = a;
            a_zero[0] = 0;
            long long val = evaluate(n, temp_ops, a_zero);
            
            long long diff = (val - Q_obs + M) % M;
            int remaining_ops = n - (int)temp_ops.size();
            
            if (diff <= remaining_ops) {
                best_block_ops = block_ops;
                found_any = true;
                // If multiple candidates valid, we just take the last one or break.
                // With high probability only one is valid.
            }
        }
        
        if (!found_any) {
            // Should not happen
            return 0;
        }
        final_ops.insert(final_ops.end(), best_block_ops.begin(), best_block_ops.end());
    }
    
    cout << "!";
    for (int x : final_ops) cout << " " << x;
    cout << endl;

    return 0;
}