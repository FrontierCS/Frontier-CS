#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <cmath>
#include <algorithm>

void solve() {
    int n1 = 100000;
    std::cout << "? " << n1;
    for (int i = 0; i < n1; ++i) {
        std::cout << " " << 1;
    }
    std::cout << std::endl;
    
    long long L1;
    std::cin >> L1;

    if (L1 == 1) {
        std::cout << "! " << 100000 << std::endl;
        return;
    }

    long long W_low = (100000LL + L1 - 1) / L1;
    long long W_high;
    if (L1 > 1) {
        W_high = (100000LL - 1) / (L1 - 1);
    } else {
        W_high = 100000;
    }
    
    if (W_low >= W_high) {
        std::cout << "! " << W_low << std::endl;
        return;
    }

    long long P = W_high - W_low;
    int n2 = 2 * P;
    
    std::cout << "? " << n2;
    for (long long j = 0; j < P; ++j) {
        long long sum = W_low + j + 1;
        long long w1 = sum / 2;
        long long w2 = sum - w1;
        std::cout << " " << w1 << " " << w2;
    }
    std::cout << std::endl;
    
    long long L2;
    std::cin >> L2;
    
    long long k = 2 * P - L2;
    long long W = W_low + k;
    std::cout << "! " << W << std::endl;
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