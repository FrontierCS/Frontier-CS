#include <iostream>
#include <string>
#include <vector>
#include <cmath>
#include <algorithm>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    std::string s;
    std::cin >> s;
    int n = s.length();

    int m0 = 0;
    for (char c : s) {
        if (c == '0') {
            m0++;
        }
    }
    int m1 = n - m0;

    if (m1 == 0) {
        std::cout << 0 << std::endl;
        return 0;
    }

    std::vector<int> p1(n + 1, 0);
    for (int i = 0; i < n; ++i) {
        p1[i + 1] = p1[i] + (s[i] - '0');
    }

    long long ans = 0;
    int k_max;

    if (m0 > 0) {
        k_max = static_cast<int>(sqrt(m0));
    } else {
        k_max = 0;
    }
    
    if (m1 < k_max) {
        k_max = m1;
    }

    for (int k = 1; k <= k_max; ++k) {
        long long len = (long long)k * k + k;
        if (len > n) {
            break;
        }
        for (int i = 0; i <= n - len; ++i) {
            if (p1[i + len] - p1[i] == k) {
                ans++;
            }
        }
    }
    
    std::cout << ans << std::endl;

    return 0;
}