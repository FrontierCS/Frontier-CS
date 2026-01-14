#include <iostream>
#include <vector>
#include <queue>
#include <set>
#include <algorithm>
#include <climits>

using namespace std;

const long long INF = 9e18;

struct Node {
    int id, x, y;
    char type;
};

long long compute_weight(const Node& a, const Node& b) {
    if (a.type == 'C' && b.type == 'C') return INF; // forbidden
    long long dx = a.x - b.x;
    long long dy = a.y - b.y;
    long long d2 = dx * dx + dy * dy;
    if (a.type != 'C' && b.type != 'C') {
        // both robots
        if (a.type == 'S' || b.type == 'S') {
            return d2 * 4;   // 0.8 = 4/5
        } else {
            return d2 * 5;   // 1.0 = 5/5
        }
    } else {
        // at least one is C
        return d2 * 5;       // 1.0
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, K;
    cin >> N >> K;
    int M = N + K;
    vector<Node> nodes(M);
    for (int i = 0; i < M; ++i) {
        cin >> nodes[i].id >> nodes[i].x >> nodes[i].y >> nodes[i].type;
    }

    // Prim's MST on all nodes (C-C edges forbidden)
    vector<long long> min_edge(M, INF);
    vector<int> parent(M, -1);
    vector<bool> in_tree(M, false);
    min_edge[0] = 0;
    for (int iter = 0; iter < M; ++iter) {
        int u = -1;
        for (int v = 0; v < M; ++v) {
            if (!in_tree[v] && (u == -1 || min_edge[v] < min_edge[u])) {
                u = v;
            }
        }
        if (min_edge[u] == INF) break; // should not happen
        in_tree[u] = true;
        for (int v = 0; v < M; ++v) {
            if (!in_tree[v] && !(nodes[u].type == 'C' && nodes[v].type == 'C')) {
                long long w = compute_weight(nodes[u], nodes[v]);
                if (w < min_edge[v]) {
                    min_edge[v] = w;
                    parent[v] = u;
                }
            }
        }
    }

    // Build MST edges
    vector<pair<int, int>> mst_edges;
    for (int i = 1; i < M; ++i) {
        if (parent[i] != -1) {
            mst_edges.emplace_back(parent[i], i);
        }
    }

    // Build adjacency of the tree
    vector<set<int>> tree_adj(M);
    for (auto& e : mst_edges) {
        int u = e.first, v = e.second;
        tree_adj[u].insert(v);
        tree_adj[v].insert(u);
    }

    // Prune leaf C nodes
    queue<int> leaf_c;
    for (int i = 0; i < M; ++i) {
        if (nodes[i].type == 'C' && tree_adj[i].size() == 1) {
            leaf_c.push(i);
        }
    }
    while (!leaf_c.empty()) {
        int u = leaf_c.front(); leaf_c.pop();
        if (tree_adj[u].size() != 1) continue; // might have changed
        int v = *tree_adj[u].begin();
        tree_adj[u].erase(v);
        tree_adj[v].erase(u);
        if (nodes[v].type == 'C' && tree_adj[v].size() == 1) {
            leaf_c.push(v);
        }
    }

    // Collect selected relay stations and final edges
    vector<int> selected_relays;
    for (int i = 0; i < M; ++i) {
        if (nodes[i].type == 'C' && !tree_adj[i].empty()) {
            selected_relays.push_back(nodes[i].id);
        }
    }
    vector<pair<int, int>> final_edges;
    for (int i = 0; i < M; ++i) {
        for (int j : tree_adj[i]) {
            if (i < j) {
                final_edges.emplace_back(nodes[i].id, nodes[j].id);
            }
        }
    }

    // Output
    if (selected_relays.empty()) {
        cout << "#\n";
    } else {
        sort(selected_relays.begin(), selected_relays.end());
        for (size_t i = 0; i < selected_relays.size(); ++i) {
            if (i > 0) cout << "#";
            cout << selected_relays[i];
        }
        cout << "\n";
    }
    if (final_edges.empty()) {
        cout << "\n";
    } else {
        sort(final_edges.begin(), final_edges.end());
        for (size_t i = 0; i < final_edges.size(); ++i) {
            if (i > 0) cout << "#";
            cout << final_edges[i].first << "-" << final_edges[i].second;
        }
        cout << "\n";
    }

    return 0;
}