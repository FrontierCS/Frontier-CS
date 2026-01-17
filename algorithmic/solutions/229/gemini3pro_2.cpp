#include <iostream>
#include <vector>
#include <algorithm>
#include <ctime>
#include <random>

using namespace std;

// Function to calculate LIS length using standard O(N log N) algorithm
int calculate_lis(const vector<long long>& a) {
    if (a.empty()) return 0;
    vector<long long> tails;
    tails.reserve(a.size());
    for (long long x : a) {
        // lower_bound for strictly increasing subsequence
        auto it = lower_bound(tails.begin(), tails.end(), x);
        if (it == tails.end()) {
            tails.push_back(x);
        } else {
            *it = x;
        }
    }
    return tails.size();
}

int main() {
    // Optimize I/O operations for speed
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    long long x;
    if (!(cin >> n >> x)) return 0;

    vector<long long> t(n);
    for (int i = 0; i < n; ++i) {
        cin >> t[i];
    }

    // Identify candidate positions for cuts.
    // A cut at index k (0-based) means we add x to the suffix t[k...n-1].
    // This effectively lifts t[k] relative to t[k-1].
    // Good candidates are where t[k-1] >= t[k] (descents).
    vector<int> candidates;
    candidates.reserve(n);
    for (int i = 1; i < n; ++i) {
        if (t[i-1] >= t[i]) {
            candidates.push_back(i);
        }
    }
    
    // Fill with some fallback candidates if too few descents found
    if (candidates.size() < 20) {
        for (int i = 1; i < n; i += max(1, n/20)) {
            candidates.push_back(i);
        }
    }

    // Initialize cuts
    // We use a vector of 10 integers representing start indices (0-based).
    vector<int> cuts(10);
    
    // Strategy: Initialize with equidistant points from candidates if possible
    if (candidates.size() >= 10) {
        for (int i = 0; i < 10; ++i) {
            cuts[i] = candidates[i * candidates.size() / 10];
        }
    } else {
        // Default equidistant distribution
        for (int i = 0; i < 10; ++i) {
            cuts[i] = (long long)(i + 1) * n / 11;
            // Clamp to valid range [1, n-1] (since adding to 0 shifts everything, effectively useless for LIS)
            if (cuts[i] < 1) cuts[i] = 1;
            if (cuts[i] >= n) cuts[i] = n - 1;
        }
    }

    mt19937 rng(1337);

    // Lambda to evaluate a configuration of cuts
    auto eval = [&](const vector<int>& c) {
        vector<int> sorted_c = c;
        sort(sorted_c.begin(), sorted_c.end());
        
        vector<long long> temp = t;
        int cut_ptr = 0;
        long long current_add = 0;
        
        // Apply differences
        for (int i = 0; i < n; ++i) {
            while(cut_ptr < 10 && sorted_c[cut_ptr] <= i) {
                current_add += x;
                cut_ptr++;
            }
            temp[i] += current_add;
        }
        return calculate_lis(temp);
    };

    int best_len = eval(cuts);
    vector<int> best_cuts = cuts;

    // Run optimization for a fixed time duration
    clock_t start_time = clock();
    double time_limit = 0.85; // Target slightly under 1.0s to stay well within limits

    while ((double)(clock() - start_time) / CLOCKS_PER_SEC < time_limit) {
        vector<int> next_cuts = best_cuts;
        
        // Mutate one cut
        int idx = rng() % 10;
        int type = rng() % 100;
        
        if (type < 40 && !candidates.empty()) {
            // Jump to a known descent point
            next_cuts[idx] = candidates[rng() % candidates.size()];
        } else if (type < 70) {
            // Small local perturbation
            int range = n / 50;
            if (range < 2) range = 2;
            int shift = (rng() % (2 * range + 1)) - range;
            next_cuts[idx] += shift;
        } else {
            // Global random jump
            next_cuts[idx] = 1 + rng() % max(1, n - 1);
        }

        // Enforce bounds
        if (next_cuts[idx] < 1) next_cuts[idx] = 1;
        if (next_cuts[idx] >= n) next_cuts[idx] = n - 1;

        int current_len = eval(next_cuts);
        
        // Hill climbing acceptance
        if (current_len > best_len) {
            best_len = current_len;
            best_cuts = next_cuts;
        } else if (current_len == best_len) {
            // Allow side moves to escape local optima
            if (rng() % 5 == 0) best_cuts = next_cuts;
        }
    }

    // Output results
    cout << best_len << "\n";
    for (int i = 0; i < 10; ++i) {
        // Output format: l r d
        // Our cuts represent starting index (0-based) for suffix add.
        // Interval is [cut[i]+1, n] in 1-based indexing.
        int l = best_cuts[i] + 1;
        int r = n;
        cout << l << " " << r << " " << x << "\n";
    }

    return 0;
}