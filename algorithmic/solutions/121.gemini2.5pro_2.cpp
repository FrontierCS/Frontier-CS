#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <iomanip>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n, m;
    std::cin >> n >> m;

    std::vector<std::string> s(m);
    for (int i = 0; i < m; ++i) {
        std::cin >> s[i];
    }

    std::vector<long long> non_q_mask_counts(1 << m, 0);
    for (int j = 0; j < n; ++j) {
        int non_q_mask = 0;
        for (int i = 0; i < m; ++i) {
            if (s[i][j] != '?') {
                non_q_mask |= (1 << i);
            }
        }
        non_q_mask_counts[non_q_mask]++;
    }

    std::vector<long long> sos_q_counts = non_q_mask_counts;
    for (int i = 0; i < m; ++i) {
        for (int mask = 0; mask < (1 << m); ++mask) {
            if (mask & (1 << i)) {
                sos_q_counts[mask] += sos_q_counts[mask ^ (1 << i)];
            }
        }
    }

    std::vector<long long> q_count(1 << m);
    int all_mask = (1 << m) - 1;
    for (int mask = 0; mask < (1 << m); ++mask) {
        q_count[mask] = sos_q_counts[all_mask ^ mask];
    }

    std::vector<bool> is_conflicted(1 << m, false);
    for (int j = 0; j < n; ++j) {
        for (int i1 = 0; i1 < m; ++i1) {
            for (int i2 = i1 + 1; i2 < m; ++i2) {
                if (s[i1][j] != '?' && s[i2][j] != '?' && s[i1][j] != s[i2][j]) {
                    is_conflicted[(1 << i1) | (1 << i2)] = true;
                }
            }
        }
    }

    for (int i = 0; i < m; ++i) {
        for (int mask = 0; mask < (1 << m); ++mask) {
            if (mask & (1 << i)) {
                is_conflicted[mask] = is_conflicted[mask] || is_conflicted[mask ^ (1 << i)];
            }
        }
    }

    long double total_prob = 0.0;
    for (int mask = 1; mask < (1 << m); ++mask) {
        if (is_conflicted[mask]) {
            continue;
        }

        long double term_prob = std::pow(4.0L, (long double)q_count[mask] - n);

        if (__builtin_popcount(mask) % 2 == 1) {
            total_prob += term_prob;
        } else {
            total_prob -= term_prob;
        }
    }

    std::cout << std::fixed << std::setprecision(12) << total_prob << std::endl;

    return 0;
}