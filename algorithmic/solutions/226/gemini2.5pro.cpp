#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <map>

const int THRESHOLD = 24;

long long solve(long long m, long long cur_x, long long cur_y) {
    if (m <= 0) {
        return 0;
    }
    if (cur_x < cur_y) {
        std::swap(cur_x, cur_y);
    }

    if (cur_x > m) {
        return m;
    }

    if (cur_x > THRESHOLD) {
        if (cur_y > m) { // Only x matters
            long long q = m / cur_x;
            long long r = m % cur_x;
            return r * ((q + 1 + 1) / 2) + (cur_x - r) * ((q + 1) / 2);
        }
        // Approximation for large x, y
        long long L = cur_x + cur_y;
        long long q = m / L;
        long long r = m % L;
        long long ans_L = L / 2;
        return q * ans_L + r / 2;
    }

    std::vector<bool> is_valid_mask_arr(1 << cur_x, false);
    for (int mask = 0; mask < (1 << cur_x); ++mask) {
        bool ok = true;
        for (int i = 0; i < cur_x; ++i) {
            if (!((mask >> i) & 1)) continue;
            if (i + cur_y < cur_x && ((mask >> (i + cur_y)) & 1)) {
                ok = false;
                break;
            }
        }
        if (ok) {
            is_valid_mask_arr[mask] = true;
        }
    }
    
    long long L = cur_x + cur_y;
    long long limit = m;
    if (m > 2 * L) {
        limit = 2 * L;
    }

    std::map<int, long long> dp;
    dp[0] = 0;
    std::vector<long long> ans(limit + 1, 0);

    for (int i = 0; i < limit; ++i) {
        std::map<int, long long> next_dp;
        long long max_val = 0;
        for (auto const& [mask, val] : dp) {
            // dp mask has bit k for vertex i-1-k
            
            // Case 1: Don't take vertex i.
            // New mask is for i, i-1, ..., i-x+1.
            // bit k is for i-k.
            // Old bit k (for i-1-k) becomes new bit k+1 (for i-(k+1)).
            int next_mask_0 = mask >> 1;
            if (next_dp.find(next_mask_0) == next_dp.end() || val > next_dp[next_mask_0]) {
                next_dp[next_mask_0] = val;
            }

            // Case 2: Take vertex i.
            // It conflicts with i-x and i-y.
            // In the old mask, i-x is at bit x-1, i-y is at bit y-1.
            bool can_take = true;
            if (((mask >> (cur_x - 1)) & 1)) can_take = false;
            if (cur_y > 0 && ((mask >> (cur_y - 1)) & 1)) can_take = false;
            
            if (can_take) {
                // New bit for i is 1. i is at position 0 in new mask.
                int next_mask_1 = next_mask_0 | (1 << (cur_x - 1));
                if (is_valid_mask_arr[next_mask_1]) {
                     if (next_dp.find(next_mask_1) == next_dp.end() || val + 1 > next_dp[next_mask_1]) {
                        next_dp[next_mask_1] = val + 1;
                    }
                }
            }
        }
        dp = next_dp;
        for (auto const& [mask, val] : dp) {
            if (val > max_val) {
                max_val = val;
            }
        }
        ans[i + 1] = max_val;
    }

    if (m <= 2 * L) {
        return ans[m];
    }

    long long C_L = ans[2 * L] - ans[L];
    long long q = (m - L) / L;
    long long r = (m - L) % L;
    
    return ans[L] + q * C_L + (ans[L + r] - ans[L]);
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    long long n, x, y;
    std::cin >> n >> x >> y;

    long long g = std::gcd(x, y);
    long long xp = x / g;
    long long yp = y / g;

    long long m_long = n / g + 1;
    long long m_short = n / g;
    long long count_long = n % g;
    long long count_short = g - count_long;

    long long total_ans = 0;
    if (count_long > 0) {
        total_ans += count_long * solve(m_long, xp, yp);
    }
    if (count_short > 0) {
        total_ans += count_short * solve(m_short, xp, yp);
    }

    std::cout << total_ans << std::endl;

    return 0;
}