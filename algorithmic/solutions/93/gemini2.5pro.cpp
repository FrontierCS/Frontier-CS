#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <functional>

int n;

int do_query(const std::vector<int>& vec) {
    if (vec.empty()) {
        return 0;
    }
    std::cout << "? " << vec.size();
    for (int x : vec) {
        std::cout << " " << x;
    }
    std::cout << std::endl;
    int result;
    std::cin >> result;
    return result;
}

// Check if u has an ancestor in R(C), where C is a set of nodes with higher D-value,
// sorted by D-value. R(C) are the roots of the forest induced by C.
// The check is true if `query(C)` == `query(C + {u})`.
bool has_ancestor_in_roots(int u, const std::vector<int>& C) {
    if (C.empty()) {
        return false;
    }
    int q1 = do_query(C);
    std::vector<int> C_u = C;
    C_u.push_back(u);
    int q2 = do_query(C_u);
    return q1 == q2;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int ty;
    std::cin >> n >> ty;

    std::vector<std::pair<int, int>> d_values;
    std::vector<int> query_vec;
    query_vec.reserve(n);
    for (int i = 1; i <= n; ++i) {
        query_vec.clear();
        query_vec.push_back(i);
        for (int j = 1; j <= n; ++j) {
            if (i != j) {
                query_vec.push_back(j);
            }
        }
        int res = do_query(query_vec);
        d_values.push_back({n - res, i});
    }

    std::sort(d_values.rbegin(), d_values.rend());

    std::vector<int> sorted_nodes;
    sorted_nodes.reserve(n);
    for (const auto& p : d_values) {
        sorted_nodes.push_back(p.second);
    }

    std::vector<int> par(n + 1);
    par[sorted_nodes[0]] = 0;

    std::vector<int> C;
    for (int i = 1; i < n; ++i) {
        int u = sorted_nodes[i];
        
        int low = 0, high = i - 1;
        int parent_idx = 0;

        while (low <= high) {
            int mid = low + (high - low) / 2;
            C.clear();
            for (int j = mid; j < i; ++j) {
                C.push_back(sorted_nodes[j]);
            }
            if (has_ancestor_in_roots(u, C)) {
                parent_idx = mid;
                low = mid + 1;
            } else {
                high = mid - 1;
            }
        }
        
        par[u] = sorted_nodes[parent_idx];
    }

    std::cout << "!";
    for (int i = 1; i <= n; ++i) {
        std::cout << " " << par[i];
    }
    std::cout << std::endl;

    return 0;
}