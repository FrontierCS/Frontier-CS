#include <iostream>
#include <vector>
#include <algorithm>
#include <tuple>

void solve() {
    int n;
    long long x;
    std::cin >> n >> x;
    std::vector<int> t(n);
    for (int i = 0; i < n; ++i) {
        std::cin >> t[i];
    }

    // Define block boundaries
    std::vector<int> s(12);
    for (int i = 0; i <= 11; ++i) {
        s[i] = static_cast<int>((long long)i * n / 11);
    }

    // Define operations
    std::vector<std::tuple<int, int, long long>> ops;
    long long C = x / 4;

    // Operation 1
    ops.emplace_back(s[1] + 1, n, -4 * C);
    
    // Operations 2 to 10
    for (int k = 2; k <= 10; ++k) {
        ops.emplace_back(s[k] + 1, n, C);
    }
    
    // Calculate effective change for each block
    std::vector<long long> delta(11);
    delta[0] = 0; // Block 0 is unaffected by these suffix operations
    for(int k = 1; k <= 10; ++k) {
        delta[k] = (long long)(k - 5) * C;
    }

    // Create the modified sequence
    std::vector<long long> t_prime(n);
    int block_idx = 0;
    for (int i = 0; i < n; ++i) {
        while (block_idx < 10 && i >= s[block_idx + 1]) {
            block_idx++;
        }
        t_prime[i] = t[i] + delta[block_idx];
    }

    // Compute LIS of the modified sequence using a standard O(n log n) algorithm
    std::vector<long long> M;
    for (long long val : t_prime) {
        auto it = std::lower_bound(M.begin(), M.end(), val);
        if (it == M.end()) {
            M.push_back(val);
        } else {
            *it = val;
        }
    }

    // Output the results
    std::cout << M.size() << std::endl;
    for (const auto& op : ops) {
        std::cout << std::get<0>(op) << " " << std::get<1>(op) << " " << std::get<2>(op) << std::endl;
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    solve();
    return 0;
}