#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <algorithm>

void solve() {
    // First query: 100000 words of length 1
    std::cout << "? 100000";
    for (int i = 0; i < 100000; ++i) {
        std::cout << " 1";
    }
    std::cout << std::endl;

    long long l1;
    std::cin >> l1;

    if (l1 == -1) { // Error case
        return;
    }

    if (l1 == 1) {
        std::cout << "! 100000" << std::endl;
        return;
    }

    // Determine the range [w_min, w_max] from l1
    long long w_min = (100000LL + l1 - 1) / l1;
    long long w_max = (100000LL - 1) / (l1 - 1);

    if (w_min == w_max) {
        std::cout << "! " << w_min << std::endl;
        return;
    }

    // Second query: construct an article to find W precisely
    long long s = w_max - w_min + 1;
    long long n2 = 2 * (s - 1);
    
    std::cout << "? " << n2;
    for (long long i = 1; i < s; ++i) {
        std::cout << " " << w_min << " " << i;
    }
    std::cout << std::endl;

    long long l2;
    std::cin >> l2;
    
    if (l2 == -1) { // Error case
        return;
    }

    // Calculate W from l2
    long long w = 2 * w_max - w_min - l2;
    std::cout << "! " << w << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int t;
    std::cin >> t;
    while (t--) {
        solve();
    }

    return 0;
}