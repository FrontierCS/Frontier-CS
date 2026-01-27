#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

// Perform a query "? i j" and return result
int query(int i, int j) {
    cout << "? " << i << " " << j << endl;
    int resp;
    cin >> resp;
    if (resp == -1) {
        exit(0);
    }
    return resp;
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    // Initially, all indices 1..n are candidates for being 0
    vector<int> candidates;
    candidates.reserve(n);
    for (int i = 1; i <= n; ++i) {
        candidates.push_back(i);
    }

    // Random number generator
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    // Filter candidates until at most 2 remain
    while (candidates.size() > 2) {
        // Pick a random pivot from current candidates
        uniform_int_distribution<int> dist(0, candidates.size() - 1);
        int pivot_idx = dist(rng);
        int pivot = candidates[pivot_idx];

        vector<pair<int, int>> results;
        int min_val = -1;

        // Query pivot against all other candidates
        for (int x : candidates) {
            if (x == pivot) continue;
            
            int val = query(pivot, x);
            results.push_back({val, x});
            
            if (min_val == -1 || val < min_val) {
                min_val = val;
            }
        }

        // Filter: keep pivot and those who gave the minimum result
        vector<int> next_candidates;
        next_candidates.push_back(pivot);
        for (auto& p : results) {
            if (p.first == min_val) {
                next_candidates.push_back(p.second);
            }
        }

        // Update candidates
        candidates = next_candidates;
    }

    int zero_idx = -1;
    if (candidates.size() == 1) {
        zero_idx = candidates[0];
    } else {
        // Two candidates left, determine which is 0
        int a = candidates[0];
        int b = candidates[1];
        
        // Try auxillary indices w until we can distinguish
        int w = 1;
        while (true) {
            // Find a valid w != a and w != b
            while (w == a || w == b) w++;
            if (w > n) w = 1; // Should technically not be reachable given logic

            int val_a = query(a, w);
            int val_b = query(b, w);

            if (val_a < val_b) {
                // p_a is likely 0
                zero_idx = a;
                break;
            } else if (val_b < val_a) {
                // p_b is likely 0
                zero_idx = b;
                break;
            }
            // If equal, try next w
            w++;
        }
    }

    // Now we have the index of 0. Restore permutation.
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