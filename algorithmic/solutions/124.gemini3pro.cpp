#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>
#include <random>
#include <set>

using namespace std;

int n;
int query(const vector<int>& idxs) {
    cout << "? " << idxs.size();
    for (int x : idxs) cout << " " << x;
    cout << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
}

// Global cache for queries
map<vector<int>, int> cache_queries;

int perform_query(vector<int> idxs) {
    sort(idxs.begin(), idxs.end());
    if (cache_queries.count(idxs)) return cache_queries[idxs];
    return cache_queries[idxs] = query(idxs);
}

int gcd(int a, int b) {
    return b == 0 ? a : gcd(b, a % b);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    if (!(cin >> n)) return 0;

    vector<int> q(n + 1, 0); // Relative values, q[1] = 0
    int L = 1; // Current LCM modulus

    // Order of moduli designed to minimize queries
    vector<int> moduli = {2, 4, 8, 3, 5, 7};

    for (int m : moduli) {
        if (L >= n) break;
        
        int g = gcd(L, m);
        int f = m / g;
        if (f == 1) continue;

        int old_L = L;
        L = L * f;

        // Ensure we can perform queries of size m
        if (n < m) continue;

        // Determine size of base to brute force
        int K = min(n, 12);
        if (K < m) K = n; // Should be covered by min(n,12) since m <= 8

        // --- Solve base indices 1..K ---
        // Generate candidates for each base element based on previous modulus
        vector<vector<int>> base_cands(K + 1);
        for (int i = 1; i <= K; ++i) {
            for (int s = 0; s < f; ++s) {
                base_cands[i].push_back(q[i] + s * old_L);
            }
        }
        // q[1] is fixed to 0
        base_cands[1] = {0};

        // Recursive generation of all valid combinations for base
        vector<vector<int>> combos;
        combos.push_back({});
        for (int i = 1; i <= K; ++i) {
            vector<vector<int>> next_combos;
            for (const auto& comb : combos) {
                for (int val : base_cands[i]) {
                    vector<int> nc = comb;
                    nc.push_back(val);
                    next_combos.push_back(nc);
                }
            }
            combos = next_combos;
        }

        // Filter combinations using random queries within base
        mt19937 rng(1337);
        while (combos.size() > 1) {
            // Pick a random subset of size m from 1..K
            vector<int> subset;
            vector<int> p(K);
            iota(p.begin(), p.end(), 1);
            shuffle(p.begin(), p.end(), rng);
            for(int i=0; i<m; ++i) subset.push_back(p[i]);
            
            // Perform query
            int res = perform_query(subset);

            // Filter
            vector<vector<int>> next_combos;
            next_combos.reserve(combos.size());
            for (const auto& c : combos) {
                long long sum = 0;
                for (int idx : subset) sum += c[idx - 1]; // c is 0-indexed relative to 1..K
                int rem = sum % m;
                bool good = (res == 1) ? (rem == 0) : (rem != 0);
                if (good) next_combos.push_back(c);
            }
            combos = next_combos;
        }

        // Update q for base
        for (int i = 1; i <= K; ++i) {
            q[i] = combos[0][i - 1];
        }

        // --- Solve for remaining i > K ---
        // Precompute subsets of base with specific sum modulo m
        vector<vector<int>> subset_for_residue(m);
        // Find subsets of size m-1
        int needed = m;
        int attempts = 0;
        while (needed > 0 && attempts < 3000) {
            vector<int> sub;
            vector<int> p(K);
            iota(p.begin(), p.end(), 1);
            shuffle(p.begin(), p.end(), rng);
            long long current_sum = 0;
            for(int i=0; i<m-1; ++i) {
                sub.push_back(p[i]);
                current_sum += q[p[i]];
            }
            int r = current_sum % m;
            // q[i] + sum == 0 (mod m) => q[i] == -sum (mod m)
            int target_res = (-r % m + m) % m;
            
            if (subset_for_residue[target_res].empty()) {
                subset_for_residue[target_res] = sub;
                needed--;
            }
            attempts++;
        }

        for (int i = K + 1; i <= n; ++i) {
            vector<int> cands;
            for (int s = 0; s < f; ++s) cands.push_back(q[i] + s * old_L);
            
            int found_idx = -1;
            // Iterate candidates, last one is implicit
            for (int k = 0; k < (int)cands.size() - 1; ++k) {
                int cand = cands[k];
                int r = cand % m;
                if (!subset_for_residue[r].empty()) {
                    vector<int> sub = subset_for_residue[r];
                    sub.push_back(i);
                    int res = perform_query(sub);
                    if (res == 1) {
                        found_idx = k;
                        break;
                    }
                } 
            }
            
            if (found_idx != -1) {
                q[i] = cands[found_idx];
            } else {
                q[i] = cands.back();
            }
        }
    }

    // Reconstruct permutation
    for (int start = 1; start <= n; ++start) {
        if (start > n / 2 && start > (n+1)/2) continue; // slight relaxation
        if (start > n / 2) continue;

        vector<int> p(n + 1);
        vector<bool> used(n + 1, false);
        bool ok = true;
        for (int i = 1; i <= n; ++i) {
            // q[i] is (p[i] - p[1]) mod L
            // p[i] = (start + q[i]) congruent mod L
            // 1 <= p[i] <= n
            long long val_long = (long long)start + q[i];
            int val = (val_long % L);
            if (val <= 0) val += L; 
            
            if (val > n) {
                ok = false; break;
            }
            if (used[val]) {
                ok = false; break;
            }
            used[val] = true;
            p[i] = val;
        }
        
        if (ok && p[1] == start) {
             cout << "!";
             for (int i = 1; i <= n; ++i) cout << " " << p[i];
             cout << endl;
             return 0;
        }
    }
    
    return 0;
}