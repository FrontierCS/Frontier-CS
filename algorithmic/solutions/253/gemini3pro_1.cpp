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
vector<int> current_st;
vector<int> parent_edge;
vector<int> parent_node;
vector<int> depth;
vector<vector<pair<int, int>>> adj;

// Helper to interact
// We maintain local state of blocked roads to minimize output
vector<bool> is_unblocked;

void set_blocked(int id, bool blocked) {
    if (is_unblocked[id] == !blocked) return;
    if (blocked) {
        cout << "- " << id << endl;
        is_unblocked[id] = false;
    } else {
        cout << "+ " << id << endl;
        is_unblocked[id] = true;
    }
}

// Query ? 2 u v
// Returns 1 if connected, 0 otherwise
int query(int u, int v) {
    cout << "? 2 " << u << " " << v << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
}

// Check if edge e connects u and v (assuming isolated component {u, v} or similar)
// Method: Query ? 2 u v multiple times.
// If e is repaired (connected), always returns 1.
// If e is broken (disconnected), returns 0 with prob 0.5 per query.
bool verify_edge(int u, int v) {
    // We assume the caller has set up the blocking correctly
    // i.e. ONLY the path we want to test is active.
    // For single edge test: only e is unblocked.
    // For cycle test: path P \ {g} + {e} is unblocked.
    
    // K=13 gives error prob 1/8192. M=2000, so reasonably safe.
    int K = 13; 
    for (int k = 0; k < K; ++k) {
        if (query(u, v) == 0) return false;
    }
    return true;
}

// DFS to build tree info for LCA / path finding
void dfs(int u, int p, int d, int pid) {
    depth[u] = d;
    parent_node[u] = p;
    parent_edge[u] = pid;
    for (auto& edge : adj[u]) {
        int v = edge.first;
        int id = edge.second;
        if (v != p) {
            dfs(v, u, d + 1, id);
        }
    }
}

void solve() {
    cin >> n >> m;
    edges.clear();
    edges.resize(m + 1);
    repaired.assign(m + 1, 0);
    is_unblocked.assign(m + 1, true); // Initially all unblocked

    for (int i = 1; i <= m; ++i) {
        cin >> edges[i].u >> edges[i].v;
        edges[i].id = i;
    }

    // Phase 1: Build Spanning Tree of R
    // Block all edges initially for our tracking (physically block them)
    // Actually, to save cost, we only block when needed. 
    // But verify_edge requires isolation.
    // Strategy: We keep "confirmed ST" edges unblocked. All others blocked.
    
    // Initially block ALL
    for (int i = 1; i <= m; ++i) set_blocked(i, true);

    vector<int> comp(n + 1);
    iota(comp.begin(), comp.end(), 0); // Initially each node in own component? 
    // No, let's grow a single component from node 1.
    
    vector<bool> in_tree(n + 1, false);
    in_tree[1] = true;
    vector<int> st_edges;
    int tree_size = 1;

    // Use random shuffle to avoid worst cases if any
    vector<int> p(m);
    iota(p.begin(), p.end(), 1);
    mt19937 rng(1337);
    shuffle(p.begin(), p.end(), rng);

    // We iterate until tree covers all nodes
    while (tree_size < n) {
        // Find an edge connecting in_tree to !in_tree
        // We iterate through all edges. If we find one, we add it and repeat.
        // To be efficient, we can iterate edges and keep "candidates"
        bool found = false;
        for (int i : p) {
            int u = edges[i].u;
            int v = edges[i].v;
            if (in_tree[u] && !in_tree[v]) {
                // Potential edge
                // Test it
                set_blocked(i, false); // Unblock e
                // Verify
                if (verify_edge(u, v)) {
                    // It works!
                    repaired[i] = 1;
                    st_edges.push_back(i);
                    in_tree[v] = true;
                    tree_size++;
                    found = true;
                    // Don't block it again, keep it for connectivity
                } else {
                    set_blocked(i, true); // Block it back
                }
            } else if (!in_tree[u] && in_tree[v]) {
                // Swap for convenience
                swap(u, v);
                // Same logic
                set_blocked(i, false);
                if (verify_edge(u, v)) {
                    repaired[i] = 1;
                    st_edges.push_back(i);
                    in_tree[v] = true;
                    tree_size++;
                    found = true;
                } else {
                    set_blocked(i, true);
                }
            }
            if (found) break;
        }
    }

    // Phase 2: Check remaining edges
    // Build adjacency for ST
    adj.assign(n + 1, vector<pair<int, int>>());
    for (int id : st_edges) {
        adj[edges[id].u].push_back({edges[id].v, id});
        adj[edges[id].v].push_back({edges[id].u, id});
    }

    depth.assign(n + 1, 0);
    parent_node.assign(n + 1, 0);
    parent_edge.assign(n + 1, 0);
    dfs(1, 0, 0, 0);

    for (int i = 1; i <= m; ++i) {
        if (repaired[i]) continue; // Already known (ST edge)
        
        int u = edges[i].u;
        int v = edges[i].v;
        
        // Find path in ST between u and v
        // Simple LCA approach or just walk up
        // Since N is small, naive walk up is fine
        vector<int> path_edges;
        int cur_u = u, cur_v = v;
        while (depth[cur_u] > depth[cur_v]) {
            path_edges.push_back(parent_edge[cur_u]);
            cur_u = parent_node[cur_u];
        }
        while (depth[cur_v] > depth[cur_u]) {
            path_edges.push_back(parent_edge[cur_v]);
            cur_v = parent_node[cur_v];
        }
        while (cur_u != cur_v) {
            path_edges.push_back(parent_edge[cur_u]);
            cur_u = parent_node[cur_u];
            path_edges.push_back(parent_edge[cur_v]);
            cur_v = parent_node[cur_v];
        }
        
        if (path_edges.empty()) {
            // Self loop or double edge?
            // If multiple edges between same pair, path is empty?
            // No, problem says no self-loop.
            // If u==v, impossible.
            // If u, v already connected by ST edge directly?
            // path_edges would be just that edge?
            // Wait, we are in Phase 2, so i is NOT in ST.
            // If parallel edge exists in ST, path_edges has size 1.
        }

        // Pick any edge on path to break
        int g = path_edges[0];
        
        // Setup: Block g, Unblock i.
        // Current state: ST edges unblocked, i blocked.
        set_blocked(g, true);
        set_blocked(i, false);
        
        // Verify
        if (verify_edge(u, v)) {
            repaired[i] = 1;
        } else {
            repaired[i] = 0;
        }
        
        // Restore
        set_blocked(i, true);
        set_blocked(g, false);
    }

    cout << "!";
    for (int i = 1; i <= m; ++i) {
        cout << " " << repaired[i];
    }
    cout << endl;
    
    int ok; cin >> ok;
    if (!ok) exit(0);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}