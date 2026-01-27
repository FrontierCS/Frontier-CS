#include <iostream>
#include <vector>
#include <algorithm>
#include <set>
#include <utility>
#include <random>
#include <chrono>

void solve() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    int m;
    std::cin >> n >> m;

    std::vector<std::vector<int>> adj(n + 1);
    for (int i = 0; i < m; ++i) {
        int u, v;
        std::cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    for (int i = 1; i <= n; ++i) {
        std::sort(adj[i].begin(), adj[i].end());
        adj[i].erase(std::unique(adj[i].begin(), adj[i].end()), adj[i].end());
    }

    std::vector<int> degree(n + 1);
    std::set<std::pair<int, int>> pq;
    for (int i = 1; i <= n; ++i) {
        degree[i] = adj[i].size();
        if (degree[i] > 0) {
            pq.insert({-degree[i], i});
        }
    }

    std::vector<bool> in_cover(n + 1, false);
    
    while (!pq.empty()) {
        auto top_it = pq.begin();
        int d_neg = top_it->first;
        int u = top_it->second;
        pq.erase(top_it);
        
        if (d_neg == 0) break;

        // If the degree in pq is outdated, skip.
        // This is a lazy-update style check which is not strictly necessary with
        // eager updates via set::erase/insert, but acts as a safeguard.
        if (degree[u] != -d_neg) {
            continue;
        }
        
        in_cover[u] = true;

        for (int v : adj[u]) {
            if (!in_cover[v]) {
                auto it = pq.find({-degree[v], v});
                if (it != pq.end()) {
                    pq.erase(it);
                    degree[v]--;
                    pq.insert({-degree[v], v});
                }
            }
        }
    }

    std::vector<int> cover_nodes;
    for (int i = 1; i <= n; ++i) {
        if (in_cover[i]) {
            cover_nodes.push_back(i);
        }
    }

    std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());

    bool changed = true;
    while (changed) {
        changed = false;
        std::shuffle(cover_nodes.begin(), cover_nodes.end(), rng);
        
        std::vector<int> next_cover_nodes;
        next_cover_nodes.reserve(cover_nodes.size());
        for (int u : cover_nodes) {
            bool is_redundant = true;
            for (int v : adj[u]) {
                if (!in_cover[v]) {
                    is_redundant = false;
                    break;
                }
            }
            if (is_redundant) {
                in_cover[u] = false;
                changed = true;
            } else {
                next_cover_nodes.push_back(u);
            }
        }
        cover_nodes = std::move(next_cover_nodes);
    }

    for (int i = 1; i <= n; ++i) {
        std::cout << (in_cover[i] ? 1 : 0) << "\n";
    }
}

int main() {
    solve();
    return 0;
}