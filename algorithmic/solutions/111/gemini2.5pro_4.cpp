#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int n;
    std::cin >> n;

    std::vector<int> s = {0};

    for (int i = 0; ; ++i) {
        long long m1 = 1LL << (2 * i);
        long long m2 = 2LL << (2 * i);

        if (m1 > n) {
            break;
        }

        int current_size = s.size();
        for (int j = 0; j < current_size; ++j) {
            if (s[j] + m1 <= n) {
                s.push_back(s[j] + m1);
            }
        }
        for (int j = 0; j < current_size; ++j) {
            if (s[j] + m2 <= n) {
                s.push_back(s[j] + m2);
            }
        }

        if (s.size() == current_size) {
            break;
        }
    }

    std::vector<int> result;
    for (int val : s) {
        if (val > 0) {
            result.push_back(val);
        }
    }

    if (result.empty() && n > 0) {
        result.push_back(1);
    }

    std::cout << result.size() << "\n";
    bool first = true;
    for (int val : result) {
        if (!first) {
            std::cout << " ";
        }
        std::cout << val;
        first = false;
    }
    std::cout << "\n";

    return 0;
}