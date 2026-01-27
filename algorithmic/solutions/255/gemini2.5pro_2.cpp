#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

void solve() {
    int n;
    std::cin >> n;

    int k = -1;
    for (int i = 1; i < n; ++i) {
        std::cout << "? " << i << " " << 1 << std::endl;
        for (int j = 1; j <= i; ++j) {
            std::cout << j << (j == i ? "" : " ");
        }
        std::cout << std::endl;
        std::cout << i + 1 << std::endl;
        std::cout.flush();
        int force;
        std::cin >> force;
        if (force != 0) {
            k = i;
            break;
        }
    }

    int pivot = k + 1;
    
    int p1_idx = -1;
    for (int i = 1; i <= k; ++i) {
        std::cout << "? 1 1" << std::endl;
        std::cout << i << std::endl;
        std::cout << pivot << std::endl;
        std::cout.flush();
        int force;
        std::cin >> force;
        if (force != 0) {
            p1_idx = i;
            break;
        }
    }

    std::vector<int> demagnetized;
    for (int i = 1; i < p1_idx; ++i) {
        demagnetized.push_back(i);
    }
    for (int i = p1_idx + 1; i <= k; ++i) {
        demagnetized.push_back(i);
    }

    for (int i = k + 2; i <= n; ++i) {
        std::cout << "? 1 1" << std::endl;
        std::cout << i << std::endl;
        std::cout << pivot << std::endl;
        std::cout.flush();
        int force;
        std::cin >> force;
        if (force == 0) {
            demagnetized.push_back(i);
        }
    }

    std::cout << "! " << demagnetized.size();
    for (int mag : demagnetized) {
        std::cout << " " << mag;
    }
    std::cout << std::endl;
    std::cout.flush();
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