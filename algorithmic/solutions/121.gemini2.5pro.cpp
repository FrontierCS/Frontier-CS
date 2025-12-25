#include <iostream>
#include <vector>
#include <string>
#include <iomanip>
#include <cmath>

#if defined(__GNUC__) || defined(__clang__)
#define popcount __builtin_popcount
#else
int popcount(int n) {
    int count = 0;
    while (n > 0) {
        n &= (n - 1);
        count++;
    }
    return count;
}
#endif

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int n, m;
    std::cin >> n >> m;
    std::vector<std::string> s(m);
    for (int i = 0; i < m; ++i) {
        std::cin >> s[i];
    }

    int num_masks = 1 << m;

    std::vector<bool> is_incompatible(num_masks, false);
    for (int j = 0; j < n; ++j) {
        for (int i1 = 0; i1 < m; ++i1) {
            if (s[i1][j] == '?') continue;
            for (int i2 = i1 + 1; i2 < m; ++i2) {
                if (s[i2][j] != '?' && s[i1][j] != s[i2][j]) {
                    is_incompatible[(1 << i1) | (1 << i2)] = true;
                }
            }
        }
    }

    for (int i = 0; i < m; ++i) {
        for (int mask = 0; mask < num_masks; ++mask) {
            if (mask & (1 << i)) {
                is_incompatible[mask] = is_incompatible[mask] || is_incompatible[mask ^ (1 << i)];
            }
        }
    }

    std::vector<int> unconstrained_counts(num_masks, 0);
    for (int j = 0; j < n; ++j) {
        int union_mask = 0;
        for (int i = 0; i < m; ++i) {
            if (s[i][j] != '?') {
                union_mask |= (1 << i);
            }
        }
        int unconstrained_mask = (num_masks - 1) ^ union_mask;
        unconstrained_counts[unconstrained_mask]++;
    }

    for (int i = 0; i < m; ++i) {
        for (int mask = 0; mask < num_masks; ++mask) {
            if (mask & (1 << i)) {
                unconstrained_counts[mask ^ (1 << i)] += unconstrained_counts[mask];
            }
        }
    }

    std::vector<double> pow_025(n + 1);
    pow_025[0] = 1.0;
    for (int i = 1; i <= n; ++i) {
        pow_025[i] = pow_025[i - 1] * 0.25;
    }
    
    double total_prob = 0.0;
    for (int mask = 1; mask < num_masks; ++mask) {
        if (!is_incompatible[mask]) {
            int sign = (popcount(mask) % 2 == 1) ? 1 : -1;
            int constrained_count = n - unconstrained_counts[mask];
            total_prob += sign * pow_025[constrained_count];
        }
    }

    std::cout << std::fixed << std::setprecision(12) << total_prob << std::endl;

    return 0;
}