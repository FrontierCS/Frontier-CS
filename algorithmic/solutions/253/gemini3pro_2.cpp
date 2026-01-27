#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <map>

using namespace std;

struct Edge {
    int u, v, id;
};

int n, m;
vector<Edge> edges;
vector<int> repaired;
vector<bool> current_blocked;
vector<vector<pair<int, int>>> adj; // u -> {v, edge_index}

// Helper to rebuild adjacency list from current unblocked edges
void rebuild_adj() {
    for (int i = 1; i <= n; ++i) adj[i].clear();
    for (int i = 0; i < m; ++i) {
        if (!current_blocked[i]) {
            adj[edges[i].u].push_back({edges[i].v, i});
            adj[edges[i].v].push_back({edges[i].u, i});
        }
    }
}

// Check bridges using Tarjan's bridge-finding algorithm or similar DFS
// Returns a vector of booleans where true means the edge is a bridge in the current graph
vector<bool> find_bridges() {
    vector<bool> is_bridge(m, false);
    vector<int> tin(n + 1, -1), low(n + 1, -1);
    int timer = 0;

    auto dfs = [&](auto&& self, int u, int p = -1, int edge_id = -1) -> void {
        tin[u] = low[u] = timer++;
        for (auto& edge : adj[u]) {
            int v = edge.first;
            int id = edge.second;
            if (id == edge_id) continue;
            if (tin[v] != -1) {
                low[u] = min(low[u], tin[v]);
            } else {
                self(self, v, u, id);
                low[u] = min(low[u], low[v]);
                if (low[v] > tin[u]) {
                    is_bridge[id] = true;
                }
            }
        }
    };

    for (int i = 1; i <= n; ++i) {
        if (tin[i] == -1) dfs(dfs, i);
    }
    return is_bridge;
}

// Find path in current unblocked graph (which is a tree/forest at this stage)
// Returns list of edge indices
bool get_path(int u, int target, int p, vector<int>& path, vector<int>& edge_path) {
    if (u == target) return true;
    for (auto& edge : adj[u]) {
        int v = edge.first;
        int id = edge.second;
        if (v == p) continue;
        path.push_back(v);
        edge_path.push_back(id);
        if (get_path(v, target, u, path, edge_path)) return true;
        path.pop_back();
        edge_path.pop_back();
    }
    return false;
}

// Interaction functions
void block_edge(int id) {
    cout << "- " << edges[id].id << endl;
    current_blocked[id] = true;
}

void unblock_edge(int id) {
    cout << "+ " << edges[id].id << endl;
    current_blocked[id] = false;
}

int query(int u, int v) {
    cout << "? 2 " << u << " " << v << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
}

void solve() {
    cin >> n >> m;
    edges.resize(m);
    for (int i = 0; i < m; ++i) {
        cin >> edges[i].u >> edges[i].v;
        edges[i].id = i + 1;
    }

    repaired.assign(m, 0);
    current_blocked.assign(m, false);
    adj.assign(n + 1, vector<pair<int, int>>());

    vector<int> p(m);
    iota(p.begin(), p.end(), 0);
    
    // Shuffle edges to avoid worst-case inputs
    mt19937 rng(1337);
    shuffle(p.begin(), p.end(), rng);

    // Initial check: all edges are unblocked in the system.
    // Our internal current_blocked is all false.
    
    vector<int> discarded;
    
    // Phase 1: Reduce to a spanning tree of R
    for (int i : p) {
        rebuild_adj();
        vector<bool> is_bridge = find_bridges();
        
        if (is_bridge[i]) {
            // Must keep
            continue;
        }

        // Try to block
        block_edge(i); // Internal blocked state updated
        
        bool connected = true;
        // Perform 10 checks
        for (int k = 0; k < 10; ++k) {
            if (query(edges[i].u, edges[i].v) == 0) {
                connected = false;
                break;
            }
        }

        if (!connected) {
            // It was critical
            unblock_edge(i);
        } else {
            // Redundant
            discarded.push_back(i);
        }
    }

    // Mark edges remaining in U as repaired
    for (int i = 0; i < m; ++i) {
        if (!current_blocked[i]) repaired[i] = 1;
    }

    // Phase 2: Check discarded edges
    rebuild_adj(); // Current U is a spanning tree (or forest) of R
    
    for (int i : discarded) {
        // Find path in U between u and v
        int u = edges[i].u;
        int v = edges[i].v;
        vector<int> path_nodes, path_edges;
        if (!get_path(u, v, -1, path_nodes, path_edges)) {
            // Should not happen if discarded correctly (unless graph disconnected initially?)
            // But problem guarantees connected R.
            // If path not found, it means u, v not connected in T.
            // This implies T is disconnected? But R is connected. 
            // If T is spanning tree of R, it must be connected.
            continue;
        }

        // Pick a random edge on path
        int idx = rng() % path_edges.size();
        int f = path_edges[idx];

        block_edge(f);
        unblock_edge(i);

        bool connected = true;
        for (int k = 0; k < 10; ++k) {
            if (query(u, v) == 0) {
                connected = false;
                break;
            }
        }

        if (connected) {
            repaired[i] = 1;
        } else {
            repaired[i] = 0;
        }

        // Restore
        block_edge(i);
        unblock_edge(f);
    }

    cout << "!";
    for (int i = 0; i < m; ++i) cout << " " << repaired[i];
    cout << endl;

    int res;
    cin >> res;
    if (res == 0) exit(0);
}

int main() {
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}