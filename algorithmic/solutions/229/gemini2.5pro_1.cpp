#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <chrono>
#include <numeric>
#include <set>

// O(L log L) LIS for a subsegment t[start..end] (0-indexed)
int calculate_lis(const std::vector<int>& t, int start, int end) {
    if (start > end) {
        return 0;
    }
    std::vector<int> tails;
    for (int i = start; i <= end; ++i) {
        auto it = std::lower_bound(tails.begin(), tails.end(), t[i]);
        if (it == tails.end()) {
            tails.push_back(t[i]);
        } else {
            *it = t[i];
        }
    }
    return tails.size();
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    long long x;
    std::cin >> n >> x;
    std::vector<int> t(n);
    for (int i = 0; i < n; ++i) {
        std::cin >> t[i];
    }

    // If x is 0, no changes can be made.
    if (x == 0) {
        std::cout << calculate_lis(t, 0, n - 1) << "\n";
        for (int i = 0; i < 10; ++i) {
            std::cout << "1 1 0\n";
        }
        return 0;
    }

    // For small n, we can make the whole sequence increasing.
    // This takes n-1 operations. If n-1 <= 10, we can achieve LIS of length n.
    if (n <= 11) {
        std::cout << n << "\n";
        int op_count = 0;
        for (int i = 2; i <= n; ++i) {
            std::cout << i << " " << n << " " << x << "\n";
            op_count++;
        }
        // Pad with dummy operations to reach 10.
        for (int i = 0; i < 10 - op_count; ++i) {
            std::cout << "1 1 0\n";
        }
        return 0;
    }

    // Heuristic approach: Partition the array into 11 segments.
    // Make elements in later segments much larger than in earlier ones.
    // The total LIS becomes the sum of LISs of individual segments.
    // The goal is to find 10 split points that maximize this sum.
    // We use a randomized search to find good split points.

    std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());

    std::vector<int> best_splits;
    int max_lis = 0;

    // Adjust number of trials based on n to stay within time limits.
    int num_trials = 60;
    if (n > 50000) num_trials = 40;
    if (n > 100000) num_trials = 25;
    if (n > 150000) num_trials = 15;

    for (int trial = 0; trial <= num_trials; ++trial) {
        std::set<int> split_set;
        
        if (trial == 0) { // First trial: try evenly spaced splits
            for (int i = 1; i <= 10; ++i) {
                split_set.insert((long long)i * n / 11);
            }
            if(split_set.count(0)) split_set.erase(0); // split point must be > 0
            while (split_set.size() < 10) {
                 split_set.insert(std::uniform_int_distribution<int>(1, n - 1)(rng));
            }
        } else { // Subsequent trials: random splits
            while (split_set.size() < 10) {
                split_set.insert(std::uniform_int_distribution<int>(1, n - 1)(rng));
            }
        }
        
        std::vector<int> current_splits(split_set.begin(), split_set.end());
        std::sort(current_splits.begin(), current_splits.end());

        // Define segment boundaries based on splits
        std::vector<int> p;
        p.push_back(0); // Start of first segment
        p.insert(p.end(), current_splits.begin(), current_splits.end());
        p.push_back(n); // End of last segment

        int current_lis_sum = 0;
        for (size_t i = 0; i < p.size() - 1; ++i) {
            current_lis_sum += calculate_lis(t, p[i], p[i + 1] - 1);
        }

        if (current_lis_sum > max_lis) {
            max_lis = current_lis_sum;
            best_splits = current_splits;
        }
    }
    
    std::cout << max_lis << "\n";
    // Output the 10 operations corresponding to the best splits found.
    // These operations effectively add s*x to segment s, making values separable.
    for (int split_point : best_splits) {
        std::cout << split_point + 1 << " " << n << " " << x << "\n";
    }

    return 0;
}