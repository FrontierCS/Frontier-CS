#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

int ask(const std::vector<int>& left, const std::vector<int>& right) {
    std::cout << "? " << left.size() << " " << right.size() << std::endl;
    for (size_t i = 0; i < left.size(); ++i) {
        std::cout << left[i] << (i == left.size() - 1 ? "" : " ");
    }
    std::cout << std::endl;
    for (size_t i = 0; i < right.size(); ++i) {
        std::cout << right[i] << (i == right.size() - 1 ? "" : " ");
    }
    std::cout << std::endl;
    std::cout.flush();
    int force;
    std::cin >> force;
    return force;
}

void answer(const std::vector<int>& demagnetized) {
    std::cout << "! " << demagnetized.size();
    for (int mag : demagnetized) {
        std::cout << " " << mag;
    }
    std::cout << std::endl;
    std::cout.flush();
}

void solve() {
    int n;
    std::cin >> n;

    std::vector<int> G;
    G.push_back(1);
    int polar_found = -1;

    for (int i = 2; i <= n; ++i) {
        int force = ask(G, {i});
        if (force != 0) {
            polar_found = i;
            break;
        }
        G.push_back(i);
    }

    std::vector<int> demagnetized;
    int other_polar = -1;

    int low = 0, high = G.size() - 1;
    while (low < high) {
        int mid = low + (high - low) / 2;
        std::vector<int> left_half;
        for (int k = low; k <= mid; ++k) {
            left_half.push_back(G[k]);
        }
        int force = ask(left_half, {polar_found});
        if (force != 0) {
            high = mid;
        } else {
            low = mid + 1;
        }
    }
    other_polar = G[low];

    for (int magnet : G) {
        if (magnet != other_polar) {
            demagnetized.push_back(magnet);
        }
    }

    for (int i = polar_found + 1; i <= n; ++i) {
        int force = ask({polar_found}, {i});
        if (force == 0) {
            demagnetized.push_back(i);
        }
    }
    
    std::sort(demagnetized.begin(), demagnetized.end());
    answer(demagnetized);
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