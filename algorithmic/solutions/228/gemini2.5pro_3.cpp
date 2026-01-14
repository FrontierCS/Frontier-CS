#include <iostream>
#include <string>
#include <vector>
#include <cmath>

void solve() {
    std::string s;
    std::cin >> s;
    int n = s.length();

    std::vector<int> o(n + 1, 0);
    int total_zeros = 0;
    for (int i = 0; i < n; ++i) {
        o[i + 1] = o[i] + (s[i] == '1');
        if (s[i] == '0') {
            total_zeros++;
        }
    }

    long long ans = 0;
    if (total_zeros == 0) {
        std::cout << 0 << std::endl;
        return;
    }

    int max_k = static_cast<int>(sqrt(total_zeros));

    for (int k = 1; k <= max_k; ++k) {
        long long l = (long long)k * k + k;
        if (l > n) {
            break;
        }
        
        // Sliding window of length l
        int current_ones = o[l] - o[0];
        if (current_ones == k) {
            ans++;
        }

        for (int j = l + 1; j <= n; ++j) {
            current_ones += (s[j - 1] - '0') - (s[j - l - 1] - '0');
            if (current_ones == k) {
                ans++;
            }
        }
    }

    std::cout << ans << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    solve();
    return 0;
}