#include <iostream>
#include <string>
#include <vector>
#include <cmath>

void fast_io() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
}

int main() {
    fast_io();

    std::string s;
    std::cin >> s;
    int n = s.length();

    std::vector<int> ones_prefix_sum(n + 1, 0);
    for (int i = 0; i < n; ++i) {
        ones_prefix_sum[i + 1] = ones_prefix_sum[i] + (s[i] - '0');
    }

    long long count = 0;
    
    for (int j = 0; j < n; ++j) {
        for (int k = 1; ; ++k) {
            long long len = (long long)k * k + k;
            if (len > j + 1) {
                break;
            }
            int i_prefix_len = j + 1 - len;
            
            if (ones_prefix_sum[j + 1] - ones_prefix_sum[i_prefix_len] == k) {
                count++;
            }
        }
    }

    std::cout << count << std::endl;

    return 0;
}