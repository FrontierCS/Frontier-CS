#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <set>
#include <list>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n, m;
    std::cin >> n >> m;

    std::vector<std::set<int>> adj_set(n + 1);
    for (int i = 0; i < m; ++i) {
        int u, v;
        std::cin >> u >> v;
        adj_set[u].insert(v);
        adj_set[v].insert(u);
    }

    std::vector<std::vector<int>> adj(n + 1);
    std::vector<int> degree(n + 1);
    for (int i = 1; i <= n; ++i) {
        for (int neighbor : adj_set[i]) {
            adj[i].push_back(neighbor);
        }
        degree[i] = adj[i].size();
    }
    adj_set.clear();
    adj_set.shrink_to_fit();

    std::vector<std::list<int>> buckets(n);
    std::vector<std::list<int>::iterator> pos(n + 1);

    for (int i = 1; i <= n; ++i) {
        buckets[degree[i]].push_front(i);
        pos[i] = buckets[degree[i]].begin();
    }

    std::vector<int> result(n + 1, 0);
    std::vector<bool> removed(n + 1, false);
    int num_removed = 0;
    int min_deg_ptr = 0;

    std::vector<int> R;
    std::vector<bool> in_R(n + 1, false);
    std::vector<int> w_to_update;
    std::vector<int> delta_deg(n + 1, 0);

    while (num_removed < n) {
        while (min_deg_ptr < n && buckets[min_deg_ptr].empty()) {
            min_deg_ptr++;
        }
        if (min_deg_ptr == n) {
            break;
        }

        int v = buckets[min_deg_ptr].front();
        
        result[v] = 1;

        R.clear();
        
        if (!removed[v]) {
            R.push_back(v);
            in_R[v] = true;
        }

        for (int u : adj[v]) {
            if (!removed[u] && !in_R[u]) {
                R.push_back(u);
                in_R[u] = true;
            }
        }
        
        w_to_update.clear();

        for (int u : R) {
            for (int w : adj[u]) {
                if (!removed[w] && !in_R[w]) {
                    if (delta_deg[w] == 0) {
                        w_to_update.push_back(w);
                    }
                    delta_deg[w]++;
                }
            }
        }

        for (int u : R) {
            if (!removed[u]) {
                buckets[degree[u]].erase(pos[u]);
                removed[u] = true;
                num_removed++;
            }
            in_R[u] = false; 
        }

        int min_w_deg = n;
        for (int w : w_to_update) {
            buckets[degree[w]].erase(pos[w]);
            degree[w] -= delta_deg[w];
            buckets[degree[w]].push_front(w);
            pos[w] = buckets[degree[w]].begin();
            min_w_deg = std::min(min_w_deg, degree[w]);
            delta_deg[w] = 0;
        }

        if (!w_to_update.empty()) {
            min_deg_ptr = std::min(min_deg_ptr, min_w_deg);
        }
    }

    for (int i = 1; i <= n; ++i) {
        std::cout << result[i] << "\n";
    }

    return 0;
}