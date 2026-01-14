#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <functional>

long long gcd(long long a, long long b) {
    while (b) {
        a %= b;
        std::swap(a, b);
    }
    return a;
}

long long mis_on_path(const std::vector<long long>& weights) {
    int m = weights.size();
    if (m == 0) return 0;
    if (m == 1) return weights[0];
    
    std::vector<long long> dp(m);
    dp[0] = weights[0];
    dp[1] = std::max(weights[0], weights[1]);
    
    for (int i = 2; i < m; ++i) {
        dp[i] = std::max(dp[i - 1], dp[i - 2] + weights[i]);
    }
    return dp[m - 1];
}

long long mis_on_cycle(const std::vector<long long>& weights) {
    int m = weights.size();
    if (m == 0) return 0;
    if (m == 1) return weights[0];

    // Case 1: Don't include the first element.
    std::vector<long long> path1(weights.begin() + 1, weights.end());
    long long res1 = mis_on_path(path1);

    // Case 2: Include the first element.
    // This disallows its neighbors (the second and the last element).
    long long res2 = weights[0];
    if (m > 2) {
        std::vector<long long> path2(weights.begin() + 2, weights.end() - 1);
        res2 += mis_on_path(path2);
    }
    
    return std::max(res1, res2);
}

long long solve_coprime(long long N, long long X, long long Y) {
    if (N <= 0) return 0;
    long long L = X + Y;
    
    std::vector<long long> weights(L + 1);
    for (int k = 1; k <= L; ++k) {
        if (N >= k) {
            weights[k] = (N - k) / L + 1;
        } else {
            weights[k] = 0;
        }
    }
    
    std::vector<long long> cycle_weights;
    cycle_weights.reserve(L);
    
    long long current_res = 1;
    for (int i = 0; i < L; ++i) {
        cycle_weights.push_back(weights[current_res]);
        current_res = (current_res - 1 + X) % L + 1;
    }
    
    return mis_on_cycle(cycle_weights);
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    
    long long n, x, y;
    std::cin >> n >> x >> y;
    
    long long common_divisor = gcd(x, y);
    long long X = x / common_divisor;
    long long Y = y / common_divisor;
    
    long long ans = 0;
    
    long long n_per_group = n / common_divisor;
    long long rem_groups = n % common_divisor;
    
    long long res1 = 0;
    if (rem_groups > 0) {
        res1 = solve_coprime(n_per_group + 1, X, Y);
        ans += rem_groups * res1;
    }
    
    if (common_divisor - rem_groups > 0) {
        long long res2 = solve_coprime(n_per_group, X, Y);
        ans += (common_divisor - rem_groups) * res2;
    }
    
    std::cout << ans << std::endl;
    
    return 0;
}