#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>
#include <map>
#include <queue>
#include <set>

void solve() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int N;
    std::cin >> N;

    std::vector<std::vector<int>> tree_adj(N + 1);
    std::vector<std::pair<int, int>> all_edges;

    for (int i = 2; i <= N; ++i) {
        int p;
        std::cin >> p;
        tree_adj[p].push_back(i);
        tree_adj[i].push_back(p);
        all_edges.push_back({p, i});
    }

    std::vector<int> leaves;
    // For N >= 4, root 1 has degree >= 2 and is not a leaf.
    for (int i = 2; i <= N; ++i) {
        if (tree_adj[i].size() == 1) {
            leaves.push_back(i);
        }
    }

    int k = leaves.size();
    if (k >= 2) {
        for (int i = 0; i < k; ++i) {
            int u = leaves[i];
            int v = leaves[(i + 1) % k];
            all_edges.push_back({u, v});
        }
    }

    std::vector<std::vector<int>> bags;
    std::map<std::pair<int, int>, int> edge_to_id;
    int current_id = N;

    for (int i = 1; i <= N; ++i) {
        bags.push_back({i});
    }

    std::set<std::pair<int, int>> unique_edges;
    for(auto& edge : all_edges) {
        if (edge.first > edge.second) {
            std::swap(edge.first, edge.second);
        }
        unique_edges.insert(edge);
    }
    
    all_edges.assign(unique_edges.begin(), unique_edges.end());

    for (const auto& edge : all_edges) {
        current_id++;
        edge_to_id[edge] = current_id;
        bags.push_back({edge.first, edge.second});
    }

    int K = current_id;
    std::vector<std::vector<int>> g_prime_adj(K + 1);
    for (const auto& edge : all_edges) {
        int u = edge.first;
        int v = edge.second;
        int eid = edge_to_id[edge];
        g_prime_adj[u].push_back(eid);
        g_prime_adj[eid].push_back(u);
        g_prime_adj[v].push_back(eid);
        g_prime_adj[eid].push_back(v);
    }
    
    std::vector<std::pair<int, int>> new_tree_edges;
    std::vector<bool> visited(K + 1, false);
    std::queue<int> q;

    for (int i = 1; i <= K; ++i) {
        if (!visited[i] && !g_prime_adj[i].empty()) {
            q.push(i);
            visited[i] = true;
            while (!q.empty()) {
                int u = q.front();
                q.pop();
                for (int v : g_prime_adj[u]) {
                    if (!visited[v]) {
                        visited[v] = true;
                        q.push(v);
                        new_tree_edges.push_back({u, v});
                    }
                }
            }
        }
    }

    std::cout << K << "\n";
    for (int i = 0; i < K; ++i) {
        std::cout << bags[i].size();
        for (int node : bags[i]) {
            std::cout << " " << node;
        }
        std::cout << "\n";
    }

    for (const auto& edge : new_tree_edges) {
        std::cout << edge.first << " " << edge.second << "\n";
    }
}

int main() {
    solve();
    return 0;
}