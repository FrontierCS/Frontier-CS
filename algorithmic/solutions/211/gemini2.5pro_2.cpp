#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>
#include <map>
#include <iomanip>
#include <queue>

using namespace std;

// Represents a device (robot or relay station)
struct Node {
    int id;
    long long x, y;
    char type;
    int index;
};

// Represents a potential communication link
struct Edge {
    int u, v;
    double cost;
    bool operator<(const Edge& other) const {
        return cost < other.cost;
    }
};

// Disjoint Set Union for Kruskal's algorithm
struct DSU {
    vector<int> parent;
    DSU(int n) {
        parent.resize(n);
        for (int i = 0; i < n; ++i) parent[i] = i;
    }
    int find(int i) {
        if (parent[i] == i) return i;
        return parent[i] = find(parent[i]);
    }
    void unite(int i, int j) {
        int root_i = find(i);
        int root_j = find(j);
        if (root_i != root_j) {
            parent[root_i] = root_j;
        }
    }
};

// Calculates the squared Euclidean distance between two nodes
long long distSq(const Node& a, const Node& b) {
    return (a.x - b.x) * (a.x - b.x) + (a.y - b.y) * (a.y - b.y);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n, k;
    cin >> n >> k;

    int total_nodes = n + k;
    vector<Node> nodes(total_nodes);
    map<int, int> id_to_index;
    vector<bool> is_relay(total_nodes, false);

    for (int i = 0; i < total_nodes; ++i) {
        cin >> nodes[i].id >> nodes[i].x >> nodes[i].y >> nodes[i].type;
        nodes[i].index = i;
        id_to_index[nodes[i].id] = i;
        if (nodes[i].type == 'C') {
            is_relay[i] = true;
        }
    }

    // Generate all valid edges
    vector<Edge> edges;
    for (int i = 0; i < total_nodes; ++i) {
        for (int j = i + 1; j < total_nodes; ++j) {
            if (nodes[i].type == 'C' && nodes[j].type == 'C') {
                continue;
            }

            long long d_sq = distSq(nodes[i], nodes[j]);
            double cost = d_sq;

            bool is_i_s = (nodes[i].type == 'S');
            bool is_j_s = (nodes[j].type == 'S');
            bool is_i_c = (nodes[i].type == 'C');
            bool is_j_c = (nodes[j].type == 'C');

            if (!is_i_c && !is_j_c) { // Robot-Robot
                if (is_i_s || is_j_s) {
                    cost *= 0.8;
                }
            }
            // Robot-Relay cost is 1.0 * D, which is the default
            edges.push_back({i, j, cost});
        }
    }

    // Run Kruskal's algorithm to find MST on all N+K nodes
    sort(edges.begin(), edges.end());

    DSU dsu(total_nodes);
    vector<Edge> mst_edges;
    
    for (const auto& edge : edges) {
        if (dsu.find(edge.u) != dsu.find(edge.v)) {
            dsu.unite(edge.u, edge.v);
            mst_edges.push_back(edge);
        }
    }

    // Build adjacency list and degrees for pruning
    vector<vector<int>> adj(total_nodes);
    vector<int> degree(total_nodes, 0);
    for (const auto& edge : mst_edges) {
        adj[edge.u].push_back(edge.v);
        adj[edge.v].push_back(edge.u);
        degree[edge.u]++;
        degree[edge.v]++;
    }

    // Prune leaf relays
    vector<bool> removed(total_nodes, false);
    queue<int> q;

    for (int i = 0; i < total_nodes; ++i) {
        if (is_relay[i] && degree[i] <= 1) {
            q.push(i);
            removed[i] = true;
        }
    }

    while (!q.empty()) {
        int u = q.front();
        q.pop();

        for (int v : adj[u]) {
            if (!removed[v]) {
                degree[v]--;
                if (is_relay[v] && degree[v] == 1) {
                    q.push(v);
                    removed[v] = true;
                }
            }
        }
    }

    // Output selected relays
    vector<int> selected_relays;
    for (int i = 0; i < total_nodes; ++i) {
        if (is_relay[i] && !removed[i]) {
            selected_relays.push_back(nodes[i].id);
        }
    }
    sort(selected_relays.begin(), selected_relays.end());

    if (selected_relays.empty()) {
        cout << "#\n";
    } else {
        for (size_t i = 0; i < selected_relays.size(); ++i) {
            cout << selected_relays[i] << (i == selected_relays.size() - 1 ? "" : "#");
        }
        cout << "\n";
    }

    // Output final communication links
    vector<string> final_links;
    for (const auto& edge : mst_edges) {
        if (!removed[edge.u] && !removed[edge.v]) {
            int id1 = nodes[edge.u].id;
            int id2 = nodes[edge.v].id;
            if (id1 > id2) swap(id1, id2);
            final_links.push_back(to_string(id1) + "-" + to_string(id2));
        }
    }
    sort(final_links.begin(), final_links.end());
    
    if (!final_links.empty()) {
        for (size_t i = 0; i < final_links.size(); ++i) {
            cout << final_links[i] << (i == final_links.size() - 1 ? "" : "#");
        }
    }
    cout << "\n";

    return 0;
}