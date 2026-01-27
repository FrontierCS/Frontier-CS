#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>

using namespace std;

struct Edge {
    int u, v, id;
};

// Query the evaluator. Returns 1 if a path exists from hidden s to Y, 0 otherwise.
int query(int u, int v) {
    cout << "? 2 " << u << " " << v << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
}

// Block road x
void block(int id) {
    cout << "- " << id << endl;
}

// Unblock road x
void unblock(int id) {
    cout << "+ " << id << endl;
}

// Check connectivity between u and v using K repetitions.
// Since the query response is probabilistic when disconnected (0.5 chance of 0),
// repeating K times reduces error probability to 2^-K.
// With K=13, error prob is ~1e-4, sufficient for competitive programming constraints.
bool check_conn(int u, int v) {
    int K = 13;
    for (int i = 0; i < K; ++i) {
        if (query(u, v) == 0) return false;
    }
    return true;
}

vector<vector<pair<int, int>>> adj;
vector<int> path_edges;
bool found_path = false;

// DFS to find path in the tree
void find_path_dfs(int u, int target, int p = -1) {
    if (u == target) {
        found_path = true;
        return;
    }
    for (auto& edge : adj[u]) {
        int v = edge.first;
        int idx = edge.second;
        if (v == p) continue;
        path_edges.push_back(idx);
        find_path_dfs(v, target, u);
        if (found_path) return;
        path_edges.pop_back();
    }
}

void solve() {
    int n, m;
    if (!(cin >> n >> m)) return;

    vector<Edge> edges(m);
    for (int i = 0; i < m; ++i) {
        cin >> edges[i].u >> edges[i].v;
        edges[i].id = i + 1;
    }

    // Initially, all roads are unblocked.
    
    // Process edges in random order. This effectively implements a randomized "Reverse Delete" algorithm.
    vector<int> p(m);
    iota(p.begin(), p.end(), 0);
    mt19937 rng(1337);
    shuffle(p.begin(), p.end(), rng);

    vector<int> is_repaired(m, 0);
    vector<int> in_tree(m, 0);
    vector<int> discarded;

    // Phase 1: Identify a Spanning Tree of the repaired graph.
    // We maintain a set of unblocked edges that connects the graph (initially all).
    // We try to block each edge. If the graph remains connected, the edge is not critical (not a bridge in current set).
    // If it becomes disconnected, it's a bridge, so it MUST be a repaired edge. We unblock it.
    for (int i : p) {
        block(edges[i].id);
        // Note: When edge i is blocked, u and v become disconnected iff i was a bridge.
        // check_conn(u, v) returns false if disconnected (with high probability).
        if (check_conn(edges[i].u, edges[i].v)) {
            // Still connected, so i is not needed for connectivity. Keep it blocked.
            // We'll check later if it's a repaired back-edge.
            discarded.push_back(i);
        } else {
            // Disconnected. Edge i is critical. It must be repaired.
            unblock(edges[i].id);
            in_tree[i] = 1;
            is_repaired[i] = 1;
        }
    }

    // Phase 2: Check all discarded edges.
    // The set of edges marked `in_tree` forms a Spanning Tree T of the repaired graph.
    // For each discarded edge e, we check if it is in R.
    // We do this by swapping e with a tree edge f on the fundamental cycle of e.
    // If e is in R, connectivity is preserved. If not, it breaks.
    
    adj.assign(n + 1, vector<pair<int, int>>());
    for (int i = 0; i < m; ++i) {
        if (in_tree[i]) {
            adj[edges[i].u].push_back({edges[i].v, i});
            adj[edges[i].v].push_back({edges[i].u, i});
        }
    }

    for (int i : discarded) {
        path_edges.clear();
        found_path = false;
        find_path_dfs(edges[i].u, edges[i].v);
        
        if (path_edges.empty()) {
            is_repaired[i] = 0; 
            continue;
        }
        
        // Pick the first edge on the path to swap
        int f_idx = path_edges[0];
        int f_id = edges[f_idx].id;
        int e_id = edges[i].id;
        
        // Swap f with e
        block(f_id);
        unblock(e_id);
        
        // Check connectivity of endpoints of f (the edge we removed from tree)
        if (check_conn(edges[f_idx].u, edges[f_idx].v)) {
            is_repaired[i] = 1;
        } else {
            is_repaired[i] = 0;
        }
        
        // Restore state: Block e, Unblock f (to restore T)
        block(e_id);
        unblock(f_id);
    }

    cout << "!";
    for (int i = 0; i < m; ++i) {
        cout << " " << is_repaired[i];
    }
    cout << endl;
    
    int correct;
    cin >> correct;
    if (correct == 0) exit(0);
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