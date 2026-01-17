#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>
#include <cmath>

long long gcd(long long a, long long b) {
    while (b) {
        a %= b;
        std::swap(a, b);
    }
    return a;
}

long long solve(long long L, int X, int Y) {
    if (L <= 0) {
        return 0;
    }
    if (X > Y) {
        std::swap(X, Y);
    }

    std::vector<long long> dp(1 << Y, -1e18);
    dp[0] = 0;

    std::map<std::vector<long long>, std::pair<int, std::vector<long long>>> history;

    for (int i = 1; i <= L; ++i) {
        std::vector<long long> next_dp(1 << Y, -1e18);
        int MASK = (1 << Y) - 1;
        for (int mask = 0; mask < (1 << Y); ++mask) {
            if (dp[mask] < -1e17) continue;

            // Option 1: don't take element i-1
            int next_mask_0 = (mask << 1) & MASK;
            next_dp[next_mask_0] = std::max(next_dp[next_mask_0], dp[mask]);

            // Option 2: take element i-1
            // Check if i-1-X and i-1-Y are taken.
            // In the mask for i-1, these correspond to i-1-X and i-1-Y.
            // In the mask for i, which represents {i-Y, ..., i-1},
            // we decide on i. Its constraints are i-X, i-Y.
            // The bit for i-k in mask is at position Y-k.
            // So we check bits Y-X and 0.
            if ((mask & (1 << (Y - X))) == 0 && (mask & (1 << 0)) == 0) {
                 int next_mask_1 = ((mask << 1) & MASK) | 1;
                next_dp[next_mask_1] = std::max(next_dp[next_mask_1], dp[mask] + 1);
            }
        }
        dp = next_dp;
        
        std::vector<long long> diff_vec(1 << Y);
        long long base_val = dp[0];
        if (base_val < -1e17) {
            for(long long val : dp) if(val > -1e17) {base_val = val; break;}
            if(base_val < -1e17) base_val = 0;
        }

        for(int j=0; j<(1<<Y); ++j) diff_vec[j] = dp[j] > -1e17 ? dp[j] - base_val : -1;


        if (history.count(diff_vec)) {
            auto const& [prev_i, prev_dp] = history.at(diff_vec);
            
            long long cycle_len = i - prev_i;
            long long remaining_len = L - i;
            long long num_cycles = remaining_len / cycle_len;
            
            std::vector<long long> cycle_gain(1 << Y);
            for(int j=0; j<(1<<Y); ++j) {
                if(dp[j] > -1e17 && prev_dp[j] > -1e17)
                    cycle_gain[j] = dp[j] - prev_dp[j];
                else
                    cycle_gain[j] = 0;
            }

            std::vector<long long> final_dp = dp;
            for(int j=0; j<(1<<Y); ++j) {
                if(final_dp[j] > -1e17)
                    final_dp[j] += num_cycles * cycle_gain[j];
            }

            long long final_steps = remaining_len % cycle_len;
            for (int k = 0; k < final_steps; ++k) {
                std::vector<long long> temp_dp(1 << Y, -1e18);
                for (int mask = 0; mask < (1 << Y); ++mask) {
                    if (final_dp[mask] < -1e17) continue;

                    int next_mask_0 = (mask << 1) & MASK;
                    temp_dp[next_mask_0] = std::max(temp_dp[next_mask_0], final_dp[mask]);
                    
                    if ((mask & (1 << (Y - X))) == 0 && (mask & (1 << 0)) == 0) {
                        int next_mask_1 = ((mask << 1) & MASK) | 1;
                        temp_dp[next_mask_1] = std::max(temp_dp[next_mask_1], final_dp[mask] + 1);
                    }
                }
                final_dp = temp_dp;
            }
            
            long long max_val = 0;
            for (long long val : final_dp) {
                max_val = std::max(max_val, val);
            }
            return max_val;
        }
        
        history[diff_vec] = {i, dp};
        if (i > 400 && i > (1 << Y) ) { // Memory control heuristic
             break;
        }

    }

    long long max_val = 0;
    for (long long val : dp) {
        max_val = std::max(max_val, val);
    }
    return max_val;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    long long n;
    long long x, y;
    std::cin >> n >> x >> y;

    if (x > y) std::swap(x, y);

    long long common_divisor = gcd(x, y);
    long long X_ll = x / common_divisor;
    long long Y_ll = y / common_divisor;
    
    if (Y_ll > 12) {
        long long period = X_ll + Y_ll;
        long long per_period = period / 2;
        long long ans = (n / period) * per_period;
        long long rem = n % period;
        ans += rem / 2;
        std::cout << ans << std::endl;
        return 0;
    }
    int X = X_ll;
    int Y = Y_ll;

    long long len1 = n / common_divisor;
    long long len2 = n / common_divisor + 1;
    long long count2 = n % common_divisor;
    long long count1 = common_divisor - count2;

    long long ans1 = solve(len1, X, Y);
    long long ans2 = -1;

    if (count2 > 0) {
        if (len2 == len1) {
            ans2 = ans1;
        } else {
            ans2 = solve(len2, X, Y);
        }
    }
    
    long long total_ans = 0;
    if (count1 > 0) total_ans += count1 * ans1;
    if (count2 > 0) total_ans += count2 * ans2;

    std::cout << total_ans << std::endl;

    return 0;
}