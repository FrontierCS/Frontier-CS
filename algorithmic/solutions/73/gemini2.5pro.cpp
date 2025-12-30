#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

// Function to ask a query, with caching
int ask(int l, int r, std::vector<std::vector<int>>& cache) {
    if (l >= r) {
        return 0;
    }
    if (cache[l][r] != -1) {
        return cache[l][r];
    }
    std::cout << "0 " << l << " " << r << std::endl;
    int res;
    std::cin >> res;
    return cache[l][r] = res;
}

// Function to find the k-th smallest available number (1-indexed k)
int find_kth(int k, int n, const std::vector<bool>& used) {
    int count = 0;
    for (int val = 1; val <= n; ++val) {
        if (!used[val]) {
            count++;
            if (count == k) {
                return val;
            }
        }
    }
    return -1; // Should not be reached
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    std::vector<std::vector<int>> cache(n + 1, std::vector<int>(n + 1, -1));
    std::vector<int> p(n + 1);
    std::vector<bool> used(n + 1, false);

    std::vector<int> rems(n + 1);
    std::vector<int> K_vals(n + 1);

    for (int i = n; i >= 1; --i) {
        if (i == 1) {
            p[1] = find_kth(1, n, used);
            break;
        }

        for (int j = 1; j < i; ++j) {
            int q_ji = ask(j, i, cache);
            int q_ji_1 = ask(j, i - 1, cache);
            rems[j] = (q_ji - q_ji_1 + 2) % 2;
        }

        K_vals[i - 1] = rems[i - 1];
        for (int j = i - 2; j >= 1; --j) {
            int is_greater = (rems[j] - (K_vals[j + 1] % 2) + 2) % 2;
            K_vals[j] = K_vals[j + 1] + is_greater;
        }

        int C = K_vals[1];
        int k = i - C;
        
        p[i] = find_kth(k, n, used);
        used[p[i]] = true;
    }

    std::cout << "1";
    for (int i = 1; i <= n; ++i) {
        std::cout << " " << p[i];
    }
    std::cout << std::endl;

    return 0;
}