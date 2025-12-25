#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

// Structure to represent an edge
struct Edge {
    int u, v, id;
};

int n;
vector<int> p; // Permutation
vector<vector<int>> adj; // Adjacency list
vector<Edge> edges; // List of all edges
vector<int> tin, tout; // DFS entry and exit times for subtree checks
int timer;

// DFS to compute entry/exit times
void dfs_tin(int u, int parent) {
    tin[u] = ++timer;
    for (int idx : adj[u]) {
        int v = (edges[idx].u == u) ? edges[idx].v : edges[idx].u;
        if (v != parent) {
            dfs_tin(v, u);
        }
    }
    tout[u] = timer;
}

// Check if u is an ancestor of v
bool is_ancestor(int u, int v) {
    return tin[u] <= tin[v] && tout[u] >= tout[v];
}

// Check if value val (currently at u_curr) wants to move towards neighbor v_next
bool wants_to_move(int u_curr, int v_next, int val) {
    int target = val; // value x wants to go to node x
    // If v_next is a child of u_curr
    if (is_ancestor(u_curr, v_next)) {
        // v_next is child. val wants to go to v_next if target is in v_next's subtree
        return is_ancestor(v_next, target);
    } else {
        // v_next is parent. val wants to go to v_next if target is NOT in u_curr's subtree
        return !is_ancestor(u_curr, target);
    }
}

void solve() {
    if (!(cin >> n)) return;
    p.assign(n + 1, 0);
    for (int i = 1; i <= n; ++i) cin >> p[i];
    
    adj.assign(n + 1, vector<int>());
    edges.clear();
    for (int i = 0; i < n - 1; ++i) {
        int u, v;
        cin >> u >> v;
        edges.push_back({u, v, i + 1}); // Store 1-based index
        adj[u].push_back(i);
        adj[v].push_back(i);
    }

    tin.assign(n + 1, 0);
    tout.assign(n + 1, 0);
    timer = 0;
    // Root the tree at 1 for parent/child relationships
    dfs_tin(1, 0);

    vector<vector<int>> ops;
    
    while (true) {
        bool sorted = true;
        for(int i = 1; i <= n; ++i) {
            if(p[i] != i) { 
                sorted = false; 
                break; 
            }
        }
        if (sorted) break;

        vector<int> type1; // Indices of edges where both want to cross (Priority 1)
        vector<int> type2; // Indices of edges where one wants to cross (Priority 2)

        for (int i = 0; i < edges.size(); ++i) {
            int u = edges[i].u;
            int v = edges[i].v;
            int pu = p[u];
            int pv = p[v];
            
            bool u_wants_v = wants_to_move(u, v, pu);
            bool v_wants_u = wants_to_move(v, u, pv);

            if (u_wants_v && v_wants_u) {
                type1.push_back(i);
            } else if (u_wants_v || v_wants_u) {
                type2.push_back(i);
            }
        }

        if (type1.empty() && type2.empty()) break; // Should not happen if not sorted

        vector<bool> matched(n + 1, false);
        vector<int> current_op_edges;

        // Greedy matching for Type 1
        for (int idx : type1) {
            int u = edges[idx].u;
            int v = edges[idx].v;
            if (!matched[u] && !matched[v]) {
                matched[u] = true;
                matched[v] = true;
                current_op_edges.push_back(edges[idx].id);
                swap(p[u], p[v]);
            }
        }

        // To avoid cycles with Type 2 swaps, vary the order (e.g., reverse every other round)
        if (ops.size() % 2 != 0) {
            reverse(type2.begin(), type2.end());
        }

        // Greedy matching for Type 2
        for (int idx : type2) {
            int u = edges[idx].u;
            int v = edges[idx].v;
            if (!matched[u] && !matched[v]) {
                matched[u] = true;
                matched[v] = true;
                current_op_edges.push_back(edges[idx].id);
                swap(p[u], p[v]);
            }
        }
        
        if (current_op_edges.empty()) break;

        ops.push_back(current_op_edges);
    }

    cout << ops.size() << "\n";
    for (const auto& op : ops) {
        cout << op.size();
        for (int id : op) cout << " " << id;
        cout << "\n";
    }
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