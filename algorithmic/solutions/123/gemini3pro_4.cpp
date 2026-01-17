#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <cmath>
#include <algorithm>

using namespace std;

// Fibonacci numbers array
long long F[60];

// Initialize Fibonacci numbers
void init_fib() {
    F[0] = 1;
    F[1] = 1;
    for (int i = 2; i < 60; ++i) {
        F[i] = F[i - 1] + F[i - 2];
    }
}

int main() {
    // Optimize I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    init_fib();
    
    int n;
    if (!(cin >> n)) return 0;
    
    // g0: candidates where the previous query was consistent (or initial state)
    // g1: candidates where the previous query was inconsistent (must be a lie)
    vector<int> g0(n);
    iota(g0.begin(), g0.end(), 1);
    vector<int> g1;
    
    int rem = 53; // Maximum queries allowed
    
    // We stop if we can handle the remaining candidates with guesses (<= 2 total candidates)
    // or if we run out of queries.
    while (g0.size() + g1.size() > 2 && rem > 0) {
        long long n0 = g0.size();
        long long n1 = g1.size();
        
        // Calculate the target weight for the YES branch to balance the search tree.
        // Weight of a candidate in g0 with `rem` queries is F[rem+1].
        // Weight of a candidate in g1 with `rem` queries is F[rem].
        // Total weight W = n0 * F[rem+1] + n1 * F[rem].
        // We aim for half of this in each branch.
        long long total_weight = n0 * F[rem + 1] + n1 * F[rem];
        long long target = total_weight / 2;
        
        // We select k0 from g0 and k1 from g1 to be in the query set S.
        // Weight in YES branch:
        // Candidates from g0 in S become g0 in next step (rem-1): k0 * F[rem]
        // Candidates from g0 not in S become g1 in next step (rem-1): (n0 - k0) * F[rem-1]
        // Candidates from g1 in S become g0 in next step (rem-1): k1 * F[rem]
        // Candidates from g1 not in S are eliminated: 0
        //
        // W_YES = k0*F[rem] + (n0-k0)*F[rem-1] + k1*F[rem]
        //       = n0*F[rem-1] + k0*(F[rem]-F[rem-1]) + k1*F[rem]
        //       = n0*F[rem-1] + k0*F[rem-2] + k1*F[rem]
        
        long long current_base = n0 * F[rem - 1];
        long long best_diff = -1;
        int best_k0 = 0, best_k1 = 0;
        
        long long term = 0;
        if (rem >= 2) term = F[rem - 2];
        
        // Iterate over k1 (g1 is typically smaller, or we just balance k1 first)
        // Since the functions are linear, we can compute optimal k0 for each k1.
        for (int k1 = 0; k1 <= n1; ++k1) {
            long long weight_from_k1 = k1 * F[rem];
            long long needed_from_k0 = target - (current_base + weight_from_k1);
            
            int k0 = 0;
            if (term > 0) {
                // Approximate division
                k0 = needed_from_k0 / term;
            } else {
                // If term is 0 (rem=1), k0 doesn't affect weight in this metric
                k0 = 0; 
            }
            
            // Check k0 and k0+1 to handle integer division rounding
            for (int cand_k0 : {k0, k0 + 1}) {
                if (cand_k0 < 0) cand_k0 = 0;
                if (cand_k0 > n0) cand_k0 = n0;
                
                long long val;
                if (rem >= 2) {
                    val = current_base + (long long)cand_k0 * term + weight_from_k1;
                } else {
                    // Special case for rem=1 where formula degenerates
                    // W_YES size-wise proxy: n0 + k1
                    val = n0 + k1;
                }
                
                long long diff = abs(val - target);
                if (best_diff == -1 || diff < best_diff) {
                    best_diff = diff;
                    best_k0 = cand_k0;
                    best_k1 = k1;
                }
            }
        }
        
        // Construct the query set S
        vector<int> S;
        S.reserve(best_k0 + best_k1);
        for (int i = 0; i < best_k0; ++i) S.push_back(g0[i]);
        for (int i = 0; i < best_k1; ++i) S.push_back(g1[i]);
        
        // Ensure S is not empty (unless n0+n1=0 which loop prevents)
        if (S.empty()) {
            if (!g0.empty()) { S.push_back(g0[0]); best_k0 = 1; }
            else if (!g1.empty()) { S.push_back(g1[0]); best_k1 = 1; }
        }
        
        cout << "? " << S.size();
        for (int x : S) cout << " " << x;
        cout << endl;
        
        string resp;
        cin >> resp;
        
        vector<int> next_g0, next_g1;
        // Pre-allocate approximately
        next_g0.reserve(n0 + n1);
        next_g1.reserve(n0);
        
        if (resp == "YES") {
            // g0 in S -> Consistent -> g0
            for (int i = 0; i < best_k0; ++i) next_g0.push_back(g0[i]);
            // g0 not in S -> Inconsistent -> g1 (assuming lie)
            for (int i = best_k0; i < n0; ++i) next_g1.push_back(g0[i]);
            // g1 in S -> Consistent -> g0 (was lie, now truth)
            for (int i = 0; i < best_k1; ++i) next_g0.push_back(g1[i]);
            // g1 not in S -> Inconsistent -> Eliminated (lie->lie impossible)
        } else {
            // g0 in S -> Inconsistent -> g1
            for (int i = 0; i < best_k0; ++i) next_g1.push_back(g0[i]);
            // g0 not in S -> Consistent -> g0
            for (int i = best_k0; i < n0; ++i) next_g0.push_back(g0[i]);
            // g1 in S -> Inconsistent -> Eliminated
            // g1 not in S -> Consistent -> g0
            for (int i = best_k1; i < n1; ++i) next_g0.push_back(g1[i]);
        }
        
        g0 = next_g0;
        g1 = next_g1;
        rem--;
    }
    
    // Combine remaining candidates
    vector<int> cands;
    cands.insert(cands.end(), g0.begin(), g0.end());
    cands.insert(cands.end(), g1.begin(), g1.end());
    
    // Make guesses
    for (int x : cands) {
        cout << "! " << x << endl;
        string resp;
        cin >> resp;
        if (resp == ":)") return 0;
        // if ":(", we continue to the next guess
    }
    
    return 0;
}