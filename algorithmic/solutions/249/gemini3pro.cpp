#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <map>
#include <set>
#include <cstdlib>

using namespace std;

// Global map to memoize queries
map<pair<int, int>, int> memo;

// Function to perform query
int query(int i, int j) {
    if (i == j) return 0;
    if (i > j) swap(i, j);
    if (memo.count({i, j})) return memo[{i, j}];
    
    cout << "? " << i << " " << j << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0); // Invalid query or limit exceeded
    return memo[{i, j}] = res;
}

int main() {
    // Disable synchronization for speed
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    // Start with all indices as candidates
    vector<int> candidates(n);
    iota(candidates.begin(), candidates.end(), 1);

    mt19937 rng(1337);

    // Heuristic to pick a good initial pivot (one with small value/few bits)
    // This avoids the worst-case scenario where a random pivot is large (e.g., 2047)
    // consuming N queries without filtering much.
    int pivot = -1;
    if (n > 10) {
        int best_score = -1;
        int best_p = -1;
        // Sample a few candidates
        for (int k = 0; k < 12; ++k) {
            int idx = (rng() % n) + 1; 
            int other = (rng() % n) + 1;
            while (other == idx) other = (rng() % n) + 1;
            
            int val = query(idx, other);
            if (best_p == -1 || val < best_score) {
                best_score = val;
                best_p = idx;
            }
        }
        pivot = best_p;
    } else {
        pivot = candidates[rng() % n];
    }

    // Iteratively filter candidates
    // The set of candidates always contains 0 (unless pivot was 0, but we add pivot back)
    // Pivot filtering logic:
    // If pivot != 0, min(pivot | x) is pivot (when x is subset of pivot, including 0).
    //   So 0 is kept. Pivot is added back.
    // If pivot == 0, min(pivot | x) = min(x) approx 1. 
    //   Indices achieving min usually don't include 0. But we add pivot(0) back.
    // So 0 is always preserved.
    while (candidates.size() > 2) {
        int min_val = -1;
        vector<pair<int, int>> results;
        results.reserve(candidates.size());

        for (int x : candidates) {
            if (x == pivot) continue;
            int val = query(pivot, x);
            if (min_val == -1 || val < min_val) {
                min_val = val;
            }
            results.push_back({x, val});
        }

        vector<int> next_candidates;
        for (auto p : results) {
            if (p.second == min_val) {
                next_candidates.push_back(p.first);
            }
        }
        // Always keep the pivot as it could be 0
        next_candidates.push_back(pivot);
        candidates = next_candidates;
        
        // Pick a new pivot randomly from the remaining candidates
        pivot = candidates[rng() % candidates.size()];
    }

    // Resolve the final 1 or 2 candidates
    int zero_idx = -1;
    if (candidates.size() == 1) {
        zero_idx = candidates[0];
    } else {
        int a = candidates[0];
        int b = candidates[1];
        while (true) {
            int k = (rng() % n) + 1;
            if (k == a || k == b) continue;
            int va = query(a, k);
            int vb = query(b, k);
            if (va < vb) {
                zero_idx = a;
                break;
            } else if (vb < va) {
                zero_idx = b;
                break;
            }
            // If equal, try another k
        }
    }

    // Recover the permutation
    vector<int> p(n + 1);
    p[zero_idx] = 0;
    for (int i = 1; i <= n; ++i) {
        if (i == zero_idx) continue;
        p[i] = query(zero_idx, i);
    }

    // Output answer
    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << p[i];
    }
    cout << endl;

    return 0;
}