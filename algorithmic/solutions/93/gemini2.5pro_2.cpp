#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <utility>

int ask(const std::vector<int>& nodes) {
    std::cout << "? " << nodes.size();
    for (int node : nodes) {
        std::cout << " " << node;
    }
    std::cout << std::endl;
    int result;
    std::cin >> result;
    return result;
}

bool are_related(int u, int v) {
    return ask({u, v}) == 1;
}

void solve() {
    int n, ty;
    std::cin >> n >> ty;

    if (n == 1) {
        std::cout << "! 0" << std::endl;
        return;
    }

    std::vector<std::pair<int, int>> sz_nodes(n);
    
    for (int i = 1; i <= n; ++i) {
        std::vector<int> query_nodes;
        query_nodes.reserve(n);
        query_nodes.push_back(i);
        for (int j = 1; j <= n; ++j) {
            if (i == j) continue;
            query_nodes.push_back(j);
        }
        sz_nodes[i - 1] = {ask(query_nodes) - 1, i};
    }

    std::sort(sz_nodes.begin(), sz_nodes.end());

    std::vector<int> p(n + 1);
    for (int i = 0; i < n; ++i) {
        p[i + 1] = sz_nodes[i].second;
    }

    std::vector<int> par(n + 1, 0);
    par[p[1]] = 0;

    for (int i = 2; i <= n; ++i) {
        int u = p[i];
        int low = 1, high = i - 1, ans_idx = -1;
        
        while (low <= high) {
            int mid = low + (high - low) / 2;
            int v = p[mid];
            
            if (are_related(u, v)) {
                ans_idx = mid;
                low = mid + 1;
            } else {
                high = mid - 1;
            }
        }
        par[u] = p[ans_idx];
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