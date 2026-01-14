#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int n;
    std::cin >> n;

    if (n == 1) {
        std::cout << "1 1" << std::endl;
        return 0;
    }

    std::vector<std::vector<int>> inv(n + 2, std::vector<int>(n + 2, 0));

    for (int l = 1; l <= n; ++l) {
        for (int r = l + 1; r <= n; ++r) {
            std::cout << "0 " << l << " " << r << std::endl;
            std::cin >> inv[l][r];
        }
    }

    std::vector<std::vector<int>> b(n + 1, std::vector<int>(n + 1, 0));
    for (int i = 1; i <= n; ++i) {
        for (int j = i + 1; j <= n; ++j) {
            long long val = (long long)inv[i][j] - inv[i + 1][j] - inv[i][j - 1] + inv[i + 1][j - 1];
            b[i][j] = (val % 2 + 2) % 2;
        }
    }

    std::vector<int> p(n + 1);
    std::vector<int> p_k_minus_1_parity(n + 1);

    for (int k = 1; k <= n; ++k) {
        long long sum_rel_order = 0;
        sum_rel_order += (k - 1);
        for (int j = 1; j < k; ++j) {
            sum_rel_order -= b[j][k];
        }
        for (int j = k + 1; j <= n; ++j) {
            sum_rel_order += b[k][j];
        }
        p_k_minus_1_parity[k] = (sum_rel_order % 2 + 2) % 2;
    }

    std::vector<int> odd_indices, even_indices;
    std::vector<int> odd_values, even_values;

    for (int k = 1; k <= n; ++k) {
        if (p_k_minus_1_parity[k] == 0) { // p_k - 1 is even -> p_k is odd
            odd_indices.push_back(k);
        } else { // p_k - 1 is odd -> p_k is even
            even_indices.push_back(k);
        }
    }

    for (int v = 1; v <= n; ++v) {
        if (v % 2 == 1) {
            odd_values.push_back(v);
        } else {
            even_values.push_back(v);
        }
    }

    auto comparator = [&](int i, int j) {
        // returns true if p[i] < p[j]
        int u = std::min(i, j), v = std::max(i, j);
        bool u_gt_v = (b[u][v] == 1);
        if (i < j) { // p_i < p_j means b[i][j] is 0
            return !u_gt_v;
        } else { // p_j < p_i means b[j][i] is 1
            return u_gt_v;
        }
    };

    std::sort(odd_indices.begin(), odd_indices.end(), comparator);
    std::sort(even_indices.begin(), even_indices.end(), comparator);

    for (size_t i = 0; i < odd_indices.size(); ++i) {
        p[odd_indices[i]] = odd_values[i];
    }
    for (size_t i = 0; i < even_indices.size(); ++i) {
        p[even_indices[i]] = even_values[i];
    }

    std::cout << "1";
    for (int i = 1; i <= n; ++i) {
        std::cout << " " << p[i];
    }
    std::cout << std::endl;

    return 0;
}