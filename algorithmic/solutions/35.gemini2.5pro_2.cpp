#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <functional>

bool query(int x, const std::vector<int>& S) {
    if (S.empty()) {
        return false;
    }
    std::cout << "? " << x << " " << S.size();
    for (int val : S) {
        std::cout << " " << val;
    }
    std::cout << std::endl;
    int response;
    std::cin >> response;
    if (response == -1) {
        exit(0);
    }
    return response == 1;
}

void solve_test_case() {
    int n;
    std::cin >> n;
    if (n == -1) exit(0);

    std::vector<int> indices(2 * n - 1);
    std::iota(indices.begin(), indices.end(), 1);

    std::vector<int> candidates(n);
    std::iota(candidates.begin(), candidates.end(), 1);

    while (candidates.size() > 1) {
        std::vector<int> s1, s2;
        size_t mid = indices.size() / 2;
        for (size_t i = 0; i < indices.size(); ++i) {
            if (i < mid) {
                s1.push_back(indices[i]);
            } else {
                s2.push_back(indices[i]);
            }
        }

        std::vector<int> u1;
        std::vector<bool> in_u1_flags(n + 1, false);

        for (int x : candidates) {
            if (query(x, s1)) {
                u1.push_back(x);
                in_u1_flags[x] = true;
            }
        }

        std::vector<int> c1, c3;
        for (int x : u1) {
             if (query(x, s2)) {
                c3.push_back(x);
            } else {
                c1.push_back(x);
            }
        }
        
        if ((s1.size() % 2) != (c3.size() % 2)) {
            indices = s1;
            candidates = c1;
        } else {
            std::vector<int> c2;
            for (int x : candidates) {
                if (!in_u1_flags[x]) {
                     if (query(x, s2)) {
                         c2.push_back(x);
                     }
                }
            }
            indices = s2;
            candidates = c2;
        }
    }
    
    std::cout << "! " << candidates[0] << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int t;
    std::cin >> t;
    while (t--) {
        solve_test_case();
    }
    return 0;
}