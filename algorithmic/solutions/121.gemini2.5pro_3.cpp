#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <iomanip>

#ifdef _MSC_VER
#include <intrin.h>
#pragma intrinsic(__popcnt)

static inline int get_ctz(int n) {
    unsigned long index;
    if (_BitScanForward(&index, (unsigned long)n)) {
        return (int)index;
    }
    return 0; // Should not be reached for n > 0
}

#define __builtin_popcount __popcnt
#define __builtin_ctz get_ctz
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

    std::vector<int> q_count(1 << m, 0);
    std::vector<bool> is_conflict(1 << m, false);

    for (int k = 0; k < n; ++k) {
        std::vector<char> merged_char_for_pos(1 << m);
        merged_char_for_pos[0] = '?';

        for (int mask = 1; mask < (1 << m); ++mask) {
            int lsb_idx = __builtin_ctz(mask);
            int prev_mask = mask ^ (1 << lsb_idx);

            char prev_char = merged_char_for_pos[prev_mask];
            char new_char = s[lsb_idx][k];

            if (prev_char == '!') {
                merged_char_for_pos[mask] = '!';
            } else if (new_char == '?') {
                merged_char_for_pos[mask] = prev_char;
            } else if (prev_char == '?') {
                merged_char_for_pos[mask] = new_char;
            } else if (prev_char == new_char) {
                merged_char_for_pos[mask] = new_char;
            } else {
                merged_char_for_pos[mask] = '!';
            }

            if (is_conflict[mask]) {
                continue;
            }

            if (merged_char_for_pos[mask] == '!') {
                is_conflict[mask] = true;
            } else if (merged_char_for_pos[mask] == '?') {
                q_count[mask]++;
            }
        }
    }

    long double total_prob = 0.0L;

    for (int mask = 1; mask < (1 << m); ++mask) {
        if (is_conflict[mask]) {
            continue;
        }

        int subset_size = __builtin_popcount(mask);
        
        long double term_prob = powl(4.0L, (long double)q_count[mask] - n);

        if (subset_size % 2 != 0) { // Odd size subset
            total_prob += term_prob;
        } else { // Even size subset
            total_prob -= term_prob;
        }
    }

    std::cout << std::fixed << std::setprecision(12) << total_prob << std::endl;

    return 0;
}