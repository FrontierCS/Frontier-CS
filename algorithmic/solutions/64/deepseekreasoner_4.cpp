#include <iostream>
#include <vector>
#include <algorithm>
#include <unordered_map>
#include <bitset>
#include <cmath>
#include <cstdlib>

using namespace std;

int main() {
    int n;
    long long T;
    cin >> n >> T;
    vector<long long> a(n);
    for (int i = 0; i < n; ++i) {
        cin >> a[i];
    }

    // Separate non-zero elements with their original indices
    vector<pair<long long, int>> non_zero;
    for (int i = 0; i < n; ++i) {
        if (a[i] != 0) {
            non_zero.push_back({a[i], i});
        }
    }

    int m = non_zero.size();
    if (m == 0) {
        // All numbers are zero, output all zeros
        cout << string(n, '0') << endl;
        return 0;
    }

    // Sort non-zero values in descending order
    sort(non_zero.begin(), non_zero.end(), [](const pair<long long, int>& x, const pair<long long, int>& y) {
        return x.first > y.first;
    });

    vector<long long> b_vals(m);
    vector<int> b_idx(m);
    for (int i = 0; i < m; ++i) {
        b_vals[i] = non_zero[i].first;
        b_idx[i] = non_zero[i].second;
    }

    // Suffix sums: suffix[i] = sum of b_vals[i..m-1]
    vector<long long> suffix(m + 1, 0);
    for (int i = m - 1; i >= 0; --i) {
        suffix[i] = suffix[i + 1] + b_vals[i];
    }

    // Greedy from below
    bitset<100> greedy_mask;
    long long sum_greedy = 0;
    for (int i = 0; i < m; ++i) {
        if (sum_greedy + b_vals[i] <= T) {
            sum_greedy += b_vals[i];
            greedy_mask.set(b_idx[i]);
        }
    }
    long long best_err = llabs(T - sum_greedy);
    bitset<100> best_mask = greedy_mask;

    // Greedy from above (start with all non-zero, remove if possible)
    bitset<100> rev_mask;
    for (int i = 0; i < m; ++i) rev_mask.set(b_idx[i]);
    long long sum_rev = suffix[0];
    for (int i = 0; i < m; ++i) {
        if (sum_rev - b_vals[i] >= T) {
            sum_rev -= b_vals[i];
            rev_mask.reset(b_idx[i]);
        }
    }
    if (llabs(T - sum_rev) < best_err) {
        best_err = llabs(T - sum_rev);
        best_mask = rev_mask;
    }

    // Dynamic programming with pruning
    unordered_map<long long, bitset<100>> dp;
    dp[0] = bitset<100>();

    for (int i = 0; i < m; ++i) {
        unordered_map<long long, bitset<100>> new_dp;
        for (const auto& entry : dp) {
            long long s = entry.first;
            const bitset<100>& mask = entry.second;

            // Option 1: do not take b_vals[i]
            if (new_dp.find(s) == new_dp.end()) {
                new_dp[s] = mask;
            }

            // Option 2: take b_vals[i]
            long long s2 = s + b_vals[i];
            if (s2 > T + best_err) continue;
            if (s2 + suffix[i + 1] < T - best_err) continue;

            if (new_dp.find(s2) == new_dp.end()) {
                bitset<100> new_mask = mask;
                new_mask.set(b_idx[i]);
                new_dp[s2] = new_mask;

                long long err = llabs(T - s2);
                if (err < best_err) {
                    best_err = err;
                    best_mask = new_mask;
                    if (best_err == 0) break; // exact match found
                }
            }
        }
        if (best_err == 0) break;

        // Prune sums that cannot lead to a solution within best_err
        for (auto it = new_dp.begin(); it != new_dp.end(); ) {
            long long s = it->first;
            if (s > T + best_err || s + suffix[i + 1] < T - best_err) {
                it = new_dp.erase(it);
            } else {
                ++it;
            }
        }
        dp = move(new_dp);
    }

    // Output the binary string
    for (int i = 0; i < n; ++i) {
        cout << (best_mask[i] ? '1' : '0');
    }
    cout << endl;

    return 0;
}