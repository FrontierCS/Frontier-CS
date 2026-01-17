#include <iostream>
#include <string>
#include <vector>
#include <cmath>

void solve() {
    std::string s;
    std::cin >> s;
    int n = s.length();

    std::vector<int> ones_prefix_sum(n + 1, 0);
    for (int i = 0; i < n; ++i) {
        ones_prefix_sum[i + 1] = ones_prefix_sum[i] + (s[i] - '0');
    }

    long long total_count = 0;
    
    // Using j as the right endpoint of the substring (0-indexed)
    for (int j = 0; j < n; ++j) {
        // k is the number of ones
        // The length of the substring is k*k + k.
        // For a substring ending at j, its length must be <= j+1.
        // So, k*k + k <= j+1, which implies k*k < j+1, so k < sqrt(j+1).
        int k_max = static_cast<int>(sqrt(j + 1.0));
        for (int k = 1; k <= k_max; ++k) {
            long long len = (long long)k * k + k;
            
            // The starting index i must be non-negative.
            // i = j - len + 1 >= 0  => j+1 >= len
            if (j + 1 < len) {
                // This check is implicitly handled by k_max, but kept for clarity.
                continue;
            }

            int i = (int)(j + 1 - len);
            
            // Check if the number of ones in s[i..j] is exactly k.
            if (ones_prefix_sum[j + 1] - ones_prefix_sum[i] == k) {
                total_count++;
            }
        }
    }

    std::cout << total_count << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    solve();
    return 0;
}