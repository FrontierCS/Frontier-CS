#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <cmath>

using namespace std;

// Fenwick Tree for efficient inversion counting
struct Fenwick {
    int size;
    vector<int> tree;
    Fenwick(int n) : size(n), tree(n + 1, 0) {}
    void add(int i, int val) {
        for (; i <= size; i += i & -i) tree[i] += val;
    }
    int query(int i) {
        int sum = 0;
        for (; i > 0; i -= i & -i) sum += tree[i];
        return sum;
    }
    void clear() {
        fill(tree.begin(), tree.end(), 0);
    }
};

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    if (n == 0) return 0;

    // sorted_indices stores indices of p[1...r-1] sorted descending by value
    // sorted_indices[0] is the index of the largest element found so far
    vector<int> sorted_indices;
    sorted_indices.reserve(n);
    sorted_indices.push_back(1);

    // Cache for inversion parities of prefixes: parity_inv[l] stores I(l, r-1) % 2
    vector<int> parity_inv(n + 1);
    
    // Fenwick tree for O(r log r) precomputation of inversion parities
    Fenwick bit(n);
    
    // Random number generator for query selection
    mt19937 rng(1337);

    // Temporary array for relative values to use in BIT
    vector<int> val(n + 1);

    for (int r = 2; r <= n; ++r) {
        // 1. Calculate Q(l, r-1) for all 1 <= l < r locally using the known prefix permutation.
        // We assume p[idx] has relative value based on its rank in sorted_indices.
        // sorted_indices[k] is the (k+1)-th largest, so we assign it a relative value of r-2-k.
        // Values will be in range [0, r-2].
        int sz = r - 1;
        for (int k = 0; k < sz; ++k) {
            val[sorted_indices[k]] = sz - 1 - k; 
        }
        
        int current_inv_parity = 0;
        bit.clear();
        // Iterate backwards from r-1 to 1 to compute suffix inversion counts
        for (int l = r - 1; l >= 1; --l) {
            int v = val[l];
            // Count how many elements to the right (already in BIT) are smaller than current element v.
            // bit stores frequencies of values. query(v) sums frequencies for values 0 to v-1.
            int smaller = bit.query(v); 
            current_inv_parity = (current_inv_parity + smaller) & 1;
            parity_inv[l] = current_inv_parity;
            bit.add(v + 1, 1); // Add current value v (mapped to v+1 in 1-based BIT)
        }

        // 2. Determine rank M of p_r (i.e., number of elements in p[1...r-1] greater than p_r).
        // M corresponds to the position where p_r should be inserted in sorted_indices.
        vector<int> candidates(r);
        iota(candidates.begin(), candidates.end(), 0);

        while (candidates.size() > 1) {
            // Find a query index 'l' that splits the candidates set roughly in half
            int chosen_l = -1;
            int best_diff = 1e9;
            
            // Try a few random 'l' to find a good split
            int num_trials = 15;
            for(int t = 0; t < num_trials; ++t) {
                int l = (rng() % (r - 1)) + 1;
                
                int c0 = 0, c1 = 0;
                int min_cand = candidates.front();
                int max_cand = candidates.back();
                
                // Calculate prediction for each candidate efficiently
                // pred(M) = (count of j < M such that sorted_indices[j] >= l) % 2
                int curr_p = 0;
                // Pre-calculate parity up to min_cand
                for(int i=0; i<min_cand; ++i) {
                     if (sorted_indices[i] >= l) curr_p ^= 1;
                }
                
                int cand_idx = 0;
                for (int m = min_cand; m <= max_cand; ++m) {
                    if (m > 0 && sorted_indices[m-1] >= l) curr_p ^= 1;
                    
                    if (cand_idx < candidates.size() && candidates[cand_idx] == m) {
                        if (curr_p == 0) c0++; else c1++;
                        cand_idx++;
                    }
                }
                
                int diff = abs(c0 - c1);
                if (diff < best_diff) {
                    best_diff = diff;
                    chosen_l = l;
                }
                // If we found a near-perfect split, stop trying
                if (diff == 0 || (candidates.size() % 2 == 1 && diff == 1)) break;
            }
            
            // Perform the query
            cout << "? " << chosen_l << " " << r << endl;
            int q_res;
            cin >> q_res;
            
            // The query returns parity of inversions in p[l...r].
            // We know I(l, r) = I(l, r-1) + count(i in [l, r-1] s.t. p[i] > p[r]).
            // So count(...) % 2 = (Q(l, r) - I(l, r-1)) % 2.
            int required_parity = (q_res - parity_inv[chosen_l]);
            if (required_parity < 0) required_parity += 2;
            else required_parity &= 1;
            
            // Filter candidates based on the result
            vector<int> next_candidates;
            next_candidates.reserve(candidates.size());
            
            int min_cand = candidates.front();
            int max_cand = candidates.back();
            int curr_p = 0;
            for(int i=0; i<min_cand; ++i) {
                 if (sorted_indices[i] >= chosen_l) curr_p ^= 1;
            }
            
            int cand_idx = 0;
            for (int m = min_cand; m <= max_cand; ++m) {
                if (m > 0 && sorted_indices[m-1] >= chosen_l) curr_p ^= 1;
                
                if (cand_idx < candidates.size() && candidates[cand_idx] == m) {
                    if (curr_p == required_parity) {
                        next_candidates.push_back(m);
                    }
                    cand_idx++;
                }
            }
            candidates = next_candidates;
        }

        // Insert p_r at the determined rank
        sorted_indices.insert(sorted_indices.begin() + candidates[0], r);
    }

    // Reconstruct permutation
    // sorted_indices contains indices from largest value to smallest value
    vector<int> p(n + 1);
    for (int i = 0; i < n; ++i) {
        p[sorted_indices[i]] = n - i;
    }

    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << p[i];
    }
    cout << endl;

    return 0;
}