#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <utility>

int n;

int ask(const std::vector<int>& vec) {
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

int ask_slice(const std::vector<int>& base_vec, int start_idx, int end_idx) {
    if (start_idx >= end_idx) {
        return 0;
    }
    std::cout << "? " << (end_idx - start_idx);
    for (int i = start_idx; i < end_idx; ++i) {
        std::cout << " " << base_vec[i];
    }
    std::cout << std::endl;
    int result;
    std::cin >> result;
    return result;
}

int ask_slice_with_extra(const std::vector<int>& base_vec, int start_idx, int end_idx, int extra_node) {
    if (start_idx >= end_idx) {
        std::vector<int> temp_vec = {extra_node};
        return ask(temp_vec);
    }
    std::cout << "? " << (end_idx - start_idx + 1);
    for (int i = start_idx; i < end_idx; ++i) {
        std::cout << " " << base_vec[i];
    }
    std::cout << " " << extra_node;
    std::cout << std::endl;
    int result;
    std::cin >> result;
    return result;
}

bool has_ancestor(int u, const std::vector<int>& v_nodes, int start_idx, int end_idx) {
    if (start_idx >= end_idx) {
        return false;
    }
    int val1 = ask_slice(v_nodes, start_idx, end_idx);
    int val2 = ask_slice_with_extra(v_nodes, start_idx, end_idx, u);
    return val1 == val2;
}

void solve() {
    int ty;
    std::cin >> n >> ty;

    std::vector<std::pair<int, int>> sorted_nodes(n);
    std::vector<int> all_nodes(n);
    std::iota(all_nodes.begin(), all_nodes.end(), 1);

    for (int i = 1; i <= n; ++i) {
        std::vector<int> q_vec;
        q_vec.push_back(i);
        for (int j = 1; j <= n; ++j) {
            if (i == j) continue;
            q_vec.push_back(j);
        }
        sorted_nodes[i - 1] = {ask(q_vec), i};
    }

    std::sort(sorted_nodes.begin(), sorted_nodes.end());

    std::vector<int> v(n);
    for (int i = 0; i < n; ++i) {
        v[i] = sorted_nodes[i].second;
    }

    std::vector<int> par(n + 1, 0);

    if (n > 1) {
        par[v[0]] = 0;
    }
    
    for (int i = 1; i < n; ++i) {
        int u = v[i];
        int low = 0, high = i - 1;

        while (low < high) {
            int mid = low + (high - low) / 2;
            if (has_ancestor(u, v, mid + 1, high + 1)) {
                low = mid + 1;
            } else {
                high = mid;
            }
        }
        par[u] = v[low];
    }
    
    std::cout << "!";
    for (int i = 1; i <= n; ++i) {
        std::cout << " " << par[i];
    }
    std::cout << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    solve();
    return 0;
}