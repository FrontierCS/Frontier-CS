#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

void solve() {
    int n;
    std::cin >> n;

    int k = -1;
    for (int i = 2; i <= n; ++i) {
        std::cout << "? 1 " << i - 1 << std::endl;
        std::cout << i << std::endl;
        for (int j = 1; j < i; ++j) {
            std::cout << j << (j == i - 1 ? "" : " ");
        }
        std::cout << std::endl;
        std::cout.flush();

        int force;
        std::cin >> force;
        if (force != 0) {
            k = i;
            break;
        }
    }
    
    std::vector<int> demagnetized;
    int p;

    int low = 1, high = k - 1;
    while (low < high) {
        int mid = low + (high - low) / 2;
        int len = mid - low + 1;
        std::cout << "? 1 " << len << std::endl;
        std::cout << k << std::endl;
        for (int i = low; i <= mid; ++i) {
            std::cout << i << (i == mid ? "" : " ");
        }
        std::cout << std::endl;
        std::cout.flush();

        int force;
        std::cin >> force;
        if (force != 0) {
            high = mid;
        } else {
            low = mid + 1;
        }
    }
    p = low;

    for (int i = 1; i < k; ++i) {
        if (i != p) {
            demagnetized.push_back(i);
        }
    }

    for (int i = k + 1; i <= n; ++i) {
        std::cout << "? 1 1" << std::endl;
        std::cout << p << std::endl;
        std::cout << i << std::endl;
        std::cout.flush();
        int force;
        std::cin >> force;
        if (force == 0) {
            demagnetized.push_back(i);
        }
    }

    std::cout << "! " << demagnetized.size();
    for (int idx : demagnetized) {
        std::cout << " " << idx;
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