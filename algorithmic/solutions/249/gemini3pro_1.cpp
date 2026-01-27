#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>

using namespace std;

// Function to perform query
int query(int i, int j) {
    cout << "? " << i << " " << j << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
}

int main() {
    // Optimization for faster I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    // We will maintain a list of candidates for the index containing 0.
    // Initially, all indices 1..n are candidates.
    vector<int> candidates(n);
    iota(candidates.begin(), candidates.end(), 1);

    mt19937 rng(1337);

    // Step 1: Select a "good" pivot.
    // A pivot with a low number of set bits (popcount) helps reduce the candidate set drastically.
    // We try a few random candidates and estimate their "size" by querying against random witnesses.
    int pivot = -1;
    if (n > 20) {
        int num_cands = 8;
        int num_witness = 4;
        
        // Randomly select indices for testing
        vector<int> p(n);
        iota(p.begin(), p.end(), 1);
        shuffle(p.begin(), p.end(), rng);
        
        vector<int> potential_pivots;
        for(int i=0; i<num_cands; ++i) potential_pivots.push_back(p[i]);
        
        vector<int> witnesses;
        for(int i=num_cands; i<num_cands+num_witness; ++i) witnesses.push_back(p[i]);

        long long best_score = -1;
        
        for (int cand : potential_pivots) {
            long long score = 0;
            for (int w : witnesses) {
                // By construction, cand != w
                score += query(cand, w);
            }
            if (best_score == -1 || score < best_score) {
                best_score = score;
                pivot = cand;
            }
        }
    } else {
        // For small N, just pick a random candidate
        uniform_int_distribution<int> dist(0, n - 1);
        pivot = candidates[dist(rng)];
    }

    // Step 2: First pass filtering.
    // Query all candidates against the chosen pivot.
    // The zero element z satisfies (z | pivot) == pivot.
    // All other elements x satisfy (x | pivot) >= pivot.
    // Thus, the minimum returned value corresponds to the case where one operand is 0 (or submask).
    // Note: If pivot itself is 0, responses are p_i, minimum is 1. We handle both cases by collecting minimizers.
    
    int min_val = -1;
    vector<pair<int, int>> responses;
    responses.reserve(n);

    for (int i : candidates) {
        if (i == pivot) continue;
        int val = query(i, pivot);
        if (min_val == -1 || val < min_val) {
            min_val = val;
        }
        responses.push_back({i, val});
    }

    // New candidates are those that yielded the minimum value, plus the pivot itself.
    vector<int> next_candidates;
    next_candidates.push_back(pivot);
    for (auto& p : responses) {
        if (p.second == min_val) {
            next_candidates.push_back(p.first);
        }
    }
    candidates = next_candidates;

    // Step 3: Refine candidates until only one remains.
    // We pick a random pivot OUTSIDE the current candidate set.
    // This allows us to distinguish candidates. The one that is zero (or submask of pivot) will minimize the OR result.
    while (candidates.size() > 1) {
        int p = -1;
        // Find a pivot not in candidates
        while (true) {
            uniform_int_distribution<int> dist(1, n);
            p = dist(rng);
            bool collision = false;
            for (int x : candidates) {
                if (x == p) {
                    collision = true;
                    break;
                }
            }
            if (!collision) break;
        }

        min_val = -1;
        responses.clear();
        for (int i : candidates) {
            int val = query(i, p);
            if (min_val == -1 || val < min_val) {
                min_val = val;
            }
            responses.push_back({i, val});
        }

        next_candidates.clear();
        for (auto& pair : responses) {
            if (pair.second == min_val) {
                next_candidates.push_back(pair.first);
            }
        }
        candidates = next_candidates;
    }

    // Step 4: We found the index of 0. Now restore the rest of the array.
    int zero_idx = candidates[0];
    vector<int> ans(n + 1);
    ans[zero_idx] = 0;

    for (int i = 1; i <= n; ++i) {
        if (i == zero_idx) continue;
        // p_i | 0 = p_i
        ans[i] = query(i, zero_idx);
    }

    // Output result
    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << ans[i];
    }
    cout << endl;

    return 0;
}