#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <set>

int n;
std::vector<int> a;

void find_all_a() {
    a.assign(n + 1, 0);
    int num_bits = 0;
    while ((1 << num_bits) < n) {
        num_bits++;
    }

    for (int b = 0; b < num_bits; ++b) {
        std::vector<int> S;
        for (int j = 1; j <= n; ++j) {
            if (((j - 1) >> b) & 1) {
                S.push_back(j);
            }
        }

        if (S.empty()) {
            continue;
        }

        for (int i = 1; i <= n; ++i) {
            std::cout << "? " << i << " 1 " << S.size();
            for (int val : S) {
                std::cout << " " << val;
            }
            std::cout << std::endl;

            int response;
            std::cin >> response;

            if (response == 1) {
                a[i] |= (1 << b);
            }
        }
    }

    for (int i = 1; i <= n; ++i) {
        a[i]++;
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> n;

    find_all_a();

    std::set<int> R_Brian;
    std::vector<bool> visited(n + 1, false);
    int curr = 1;
    while (!visited[curr]) {
        visited[curr] = true;
        R_Brian.insert(curr);
        curr = a[curr];
    }

    std::vector<int> A;
    for (int x = 1; x <= n; ++x) {
        curr = x;
        for (int i = 0; i < n; ++i) {
            curr = a[curr];
        }
        if (R_Brian.count(curr)) {
            A.push_back(x);
        }
    }

    std::cout << "! " << A.size();
    for (int x : A) {
        std::cout << " " << x;
    }
    std::cout << std::endl;

    return 0;
}