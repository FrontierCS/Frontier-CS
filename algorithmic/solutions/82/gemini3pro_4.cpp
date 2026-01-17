#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <map>

using namespace std;

// Map to cache query results to avoid repeating queries
map<pair<int, int>, int> cache_res;

// Function to perform query
int query(int i, int j) {
    if (i == j) return 0; // Should not happen based on logic
    if (i > j) swap(i, j);
    if (cache_res.count({i, j})) return cache_res[{i, j}];
    cout << "? " << i << " " << j << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return cache_res[{i, j}] = res;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    vector<int> p(n);
    iota(p.begin(), p.end(), 1);

    // Random shuffle to avoid adversarial cases
    mt19937 rng(1337);
    shuffle(p.begin(), p.end(), rng);

    // Step 1: Find a "good" pivot
    // A good pivot is an element that has a small OR sum with some partner.
    // This implies the pivot likely has many 0 bits, reducing masking effects.
    int pivot = -1;
    int best_partner = -1;
    int min_start_val = 1e9;
    
    int attempts = 0;
    // Try up to 5 candidates to be the pivot
    for (int i = 0; i < n && attempts < 5; ++i) {
        int candidate = p[i];
        int local_min = 1e9;
        int local_partner = -1;
        int partners_tried = 0;
        
        // Test against 5 random partners
        for (int j = 0; j < n && partners_tried < 5; ++j) {
            int partner = p[(i + j + 1) % n]; 
            if (candidate == partner) continue;
            
            int val = query(candidate, partner);
            if (val < local_min) {
                local_min = val;
                local_partner = partner;
            }
            partners_tried++;
        }
        
        // Keep the candidate that yields the smallest OR value (popcount heuristic)
        if (pivot == -1 || __builtin_popcount(local_min) < __builtin_popcount(min_start_val)) {
            pivot = candidate;
            best_partner = local_partner;
            min_start_val = local_min;
        }
        
        // If we found a very good pivot (popcount <= 6), stop searching
        if (__builtin_popcount(min_start_val) <= 6) break;
        attempts++;
    }

    // Step 2: Scan all other elements to find candidates for 0
    // We maintain a list of candidates that produce the minimal OR value with the pivot.
    vector<int> potential_zeros;
    potential_zeros.push_back(best_partner);
    int current_min_val = min_start_val;

    for (int i = 0; i < n; ++i) {
        int c = p[i];
        if (c == pivot || c == best_partner) continue;
        
        int val = query(pivot, c);
        if (val < current_min_val) {
            current_min_val = val;
            potential_zeros.clear();
            potential_zeros.push_back(c);
        } else if (val == current_min_val) {
            potential_zeros.push_back(c);
        }
    }
    
    // The pivot itself could be 0
    potential_zeros.push_back(pivot);

    // Step 3: Eliminate candidates
    // We compare candidates by querying them against random witnesses.
    // The true 0 will always produce the result p_w (minimal possible).
    // Others will produce p_c | p_w >= p_w.
    while (potential_zeros.size() > 1) {
        int w = p[rng() % n];
        
        // Ensure witness is not one of the candidates (needed for valid query)
        bool distinct = true;
        for (int cand : potential_zeros) {
            if (cand == w) {
                distinct = false;
                break;
            }
        }
        if (!distinct) continue; // Pick another witness

        int min_q = 1e9;
        vector<pair<int, int>> results;
        
        for (int cand : potential_zeros) {
            int val = query(cand, w);
            results.push_back({val, cand});
            if (val < min_q) min_q = val;
        }
        
        // Filter candidates that achieved the minimum value
        vector<int> next_candidates;
        for (auto& pr : results) {
            if (pr.first == min_q) {
                next_candidates.push_back(pr.second);
            }
        }
        potential_zeros = next_candidates;
    }

    int zero_idx = potential_zeros[0];
    
    // Step 4: Recover the permutation
    vector<int> final_p(n + 1);
    final_p[zero_idx] = 0;
    
    for (int i = 1; i <= n; ++i) {
        if (i == zero_idx) continue;
        final_p[i] = query(zero_idx, i);
    }

    // Output result
    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << final_p[i];
    }
    cout << endl;

    return 0;
}