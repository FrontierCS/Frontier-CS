#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <map>
#include <iomanip>
#include <numeric>

using namespace std;

// Custom power function for long double to maintain precision
long double power(long double base, int exp) {
    long double res = 1.0;
    while (exp > 0) {
        if (exp % 2 == 1) res *= base;
        base *= base;
        exp /= 2;
    }
    return res;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n, m;
    cin >> n >> m;

    vector<string> s(m);
    for (int i = 0; i < m; ++i) {
        cin >> s[i];
    }

    // Step 1: Group columns by their character patterns
    map<vector<char>, int> counts;
    for (int j = 0; j < n; ++j) {
        vector<char> v(m);
        for (int i = 0; i < m; ++i) {
            v[i] = s[i][j];
        }
        counts[v]++;
    }

    // Step 2: Group unique column patterns by their conflict masks
    // A tuple of masks {Z, A, C, G, T} defines a pattern type.
    // Z is the mask of strings with non-'?' chars. A, C, G, T are for respective chars.
    map<vector<int>, int> counts_prime;
    for (auto const& [v, num] : counts) {
        vector<int> masks(5, 0); // Z, A, C, G, T
        for (int i = 0; i < m; ++i) {
            if (v[i] == 'A') {
                masks[0] |= (1 << i);
                masks[1] |= (1 << i);
            } else if (v[i] == 'C') {
                masks[0] |= (1 << i);
                masks[2] |= (1 << i);
            } else if (v[i] == 'G') {
                masks[0] |= (1 << i);
                masks[3] |= (1 << i);
            } else if (v[i] == 'T') {
                masks[0] |= (1 << i);
                masks[4] |= (1 << i);
            }
        }
        counts_prime[masks] += num;
    }

    int full_mask = (1 << m) - 1;
    
    // Step 3: Dynamic Programming
    // dp[mask] will store the PIE sum for all non-empty submasks of 'mask'.
    vector<long double> dp(1 << m, 0.0);
    // Base case (i=0): The product term is 1. The PIE sum is 1 for any non-empty set.
    for (int mask = 1; mask < (1 << m); ++mask) {
        dp[mask] = 1.0;
    }

    for (auto const& [masks, num] : counts_prime) {
        vector<long double> next_dp(1 << m, 0.0);
        
        // Probabilities for a column to match a random char, raised to the power of `num`
        long double p4 = 1.0; // (4/4)^num
        long double p1 = power(0.25, num); // (1/4)^num
        // p0 is 0, so we don't need a variable for it.

        int z_mask = masks[0];
        int a_mask = masks[1];
        int c_mask = masks[2];
        int g_mask = masks[3];
        int t_mask = masks[4];
        
        // Pre-calculate complement masks for efficiency in the DP loop
        int nz_mask = full_mask ^ z_mask;
        int ncgt_mask = full_mask ^ (c_mask | g_mask | t_mask);
        int nagt_mask = full_mask ^ (a_mask | g_mask | t_mask);
        int nact_mask = full_mask ^ (a_mask | c_mask | t_mask);
        int nacg_mask = full_mask ^ (a_mask | c_mask | g_mask);

        // DP transition
        for (int mask = 1; mask < (1 << m); ++mask) {
            long double current_val = 0;
            
            // Contribution from subsets compatible with any of A,C,G,T (all '?'s)
            current_val += p4 * dp[mask & nz_mask];
            
            // Contribution from subsets compatible with 'A' but not 'C','G','T'
            current_val += p1 * (dp[mask & ncgt_mask] - dp[mask & nz_mask]);
            
            // Contribution from subsets compatible with 'C' but not 'A','G','T'
            current_val += p1 * (dp[mask & nagt_mask] - dp[mask & nz_mask]);
            
            // Contribution from subsets compatible with 'G' but not 'A','C','T'
            current_val += p1 * (dp[mask & nact_mask] - dp[mask & nz_mask]);
            
            // Contribution from subsets compatible with 'T' but not 'A','C','G'
            current_val += p1 * (dp[mask & nacg_mask] - dp[mask & nz_mask]);
            
            next_dp[mask] = current_val;
        }
        dp = next_dp;
    }

    // Step 4: The final answer is the PIE sum for all m strings.
    cout << fixed << setprecision(12) << dp[full_mask] << endl;

    return 0;
}