#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <string>
#include <cstdlib>

// Use type aliases for clarity and easier modification.
using ll = long long;
using ull = unsigned long long;
using state = std::pair<ll, ull>;

// Generates a pruned set of subset sums for the given elements.
// The beam width W controls the size of the set of sums.
std::vector<state> generate_sums(const std::vector<std::pair<ll, int>>& elements, const int W) {
    std::vector<state> sums = {{0, 0}};

    for (const auto& elem : elements) {
        ll val = elem.first;
        int idx = elem.second;
        ull bit = 1ULL << idx;

        std::vector<state> new_sums_part;
        new_sums_part.reserve(sums.size());
        for (const auto& s : sums) {
            new_sums_part.push_back({s.first + val, s.second | bit});
        }

        std::vector<state> merged_sums;
        merged_sums.resize(sums.size() + new_sums_part.size());
        std::merge(sums.begin(), sums.end(), new_sums_part.begin(), new_sums_part.end(), merged_sums.begin());

        // Remove duplicates by sum. If two subsets have the same sum, we only need one.
        merged_sums.erase(std::unique(merged_sums.begin(), merged_sums.end(), 
            [](const state& a, const state& b){ return a.first == b.first; }), 
            merged_sums.end());

        // Prune the set of sums if it's too large.
        if (merged_sums.size() > W) {
            std::vector<state> pruned_sums;
            pruned_sums.reserve(W);
            double step = static_cast<double>(merged_sums.size() - 1) / (W > 1 ? W - 1 : 1);
            for (int i = 0; i < W; ++i) {
                pruned_sums.push_back(merged_sums[static_cast<size_t>(round(i * step))]);
            }
            sums = std::move(pruned_sums);
        } else {
            sums = std::move(merged_sums);
        }
    }
    return sums;
}

int main() {
    // Fast I/O
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    ll T;
    std::cin >> n >> T;

    std::vector<ll> a(n);
    for (int i = 0; i < n; ++i) {
        std::cin >> a[i];
    }
    
    // Split the input array into two halves.
    int n1 = n / 2;
    std::vector<std::pair<ll, int>> first_half, second_half;
    for (int i = 0; i < n1; ++i) {
        first_half.push_back({a[i], i});
    }
    for (int i = n1; i < n; ++i) {
        // Index in the second half's mask is relative.
        second_half.push_back({a[i], i - n1});
    }

    // Beam width for the search. A larger W gives better results but is slower.
    const int W = 200000;
    
    // Generate subset sums for both halves.
    std::vector<state> s1 = generate_sums(first_half, W);
    std::vector<state> s2 = generate_sums(second_half, W);

    ll best_error = -1;
    ull best_mask1 = 0, best_mask2 = 0;
    
    // Combine sums from the two halves to find the best total sum.
    for (const auto& p1 : s1) {
        ll sum1 = p1.first;
        ull mask1 = p1.second;
        ll target = T - sum1;

        // Binary search for the sum in s2 that is closest to the target.
        auto it = std::lower_bound(s2.begin(), s2.end(), std::make_pair(target, 0ULL));

        // Check the found element and the one before it.
        if (it != s2.end()) {
            ll sum2 = it->first;
            ull mask2 = it->second;
            ll current_sum = sum1 + sum2;
            ll current_error = std::abs(current_sum - T);

            if (best_error == -1 || current_error < best_error) {
                best_error = current_error;
                best_mask1 = mask1;
                best_mask2 = mask2;
            }
        }
        if (it != s2.begin()) {
            it--;
            ll sum2 = it->first;
            ull mask2 = it->second;
            ll current_sum = sum1 + sum2;
            ll current_error = std::abs(current_sum - T);

            if (best_error == -1 || current_error < best_error) {
                best_error = current_error;
                best_mask1 = mask1;
                best_mask2 = mask2;
            }
        }
    }

    // Reconstruct the final binary string from the best masks.
    std::string result(n, '0');
    for (int i = 0; i < n1; ++i) {
        if ((best_mask1 >> i) & 1) {
            result[i] = '1';
        }
    }
    for (int i = 0; i < n - n1; ++i) {
        if ((best_mask2 >> i) & 1) {
            result[n1 + i] = '1';
        }
    }
    
    std::cout << result << std::endl;

    return 0;
}