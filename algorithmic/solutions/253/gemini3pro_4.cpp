#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <set>
#include <map>

using namespace std;

// Globals
int n, m;
struct Edge {
    int u, v;
    int id;
};
vector<Edge> edges;
vector<int> adj[2005];
int is_repaired[2005];
int edge_status[2005]; // 0: unblocked, 1: blocked

// Cost tracking (for local debugging, not used in submission)
// double total_cost = 0;

void block_road(int id) {
    if (edge_status[id] == 1) return;
    cout << "- " << id << endl;
    edge_status[id] = 1;
    // total_cost += 2;
}

void unblock_road(int id) {
    if (edge_status[id] == 0) return;
    cout << "+ " << id << endl;
    edge_status[id] = 0;
    // total_cost += 2;
}

int query(int k, const vector<int>& y) {
    cout << "? " << k;
    for (int v : y) cout << " " << v;
    cout << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    // total_cost += 0.5 + log2(k + 1);
    return res;
}

// Check if subset S of cand_edges contains at least one repaired edge
// connecting C to V \ C.
// Precondition: All edges in cand_edges are currently UNBLOCKED.
// All other edges in cand_edges \ S must be blocked for the check.
// Returns true if S has repaired edge.
bool has_repaired(const vector<int>& S, const vector<int>& all_cand, const vector<bool>& in_C) {
    // We need to block all edges in all_cand that are NOT in S.
    // Optimization: Diff them.
    // Since S is usually a sub-segment, we can iterate.
    // However, for simplicity, iterate all_cand.
    
    // Mark S for fast lookup
    vector<bool> in_S(m + 1, false);
    for (int id : S) in_S[id] = true;

    vector<int> to_block;
    for (int id : all_cand) {
        if (!in_S[id]) {
            to_block.push_back(id);
        }
    }

    for (int id : to_block) block_road(id);

    // Query 1: ? 1 1
    // We use node 1 as representative of C (since C grows from 1)
    vector<int> q1_nodes = {1};
    int r1 = query(1, q1_nodes);

    bool result = false;
    if (r1 == 0) {
        result = false;
    } else {
        // Query 2: ? |V\C| (V\C)
        vector<int> outside;
        for (int i = 1; i <= n; i++) {
            if (!in_C[i]) outside.push_back(i);
        }
        if (outside.empty()) {
            // Should not happen if loop condition correct
            result = false; 
        } else {
            int r2 = query(outside.size(), outside);
            result = (r2 == 1);
        }
    }

    // Restore: Unblock
    for (int id : to_block) unblock_road(id);

    return result;
}

// Recursive function to find one repaired edge in current candidate set
// S: current subset of candidates to search
// all_cand: full set of boundary edges (needed for has_repaired blocking logic)
// in_C: mask of nodes in component C
int find_repaired_edge(vector<int>& S, const vector<int>& all_cand, const vector<bool>& in_C) {
    if (S.empty()) return -1;
    if (S.size() == 1) {
        if (has_repaired(S, all_cand, in_C)) return S[0];
        else return -1;
    }

    int mid = S.size() / 2;
    vector<int> L1(S.begin(), S.begin() + mid);
    vector<int> L2(S.begin() + mid, S.end());

    // Check L1
    if (has_repaired(L1, all_cand, in_C)) {
        int res = find_repaired_edge(L1, all_cand, in_C);
        if (res != -1) return res;
        // If L1 turned out empty (shouldn't happen if has_repaired is correct, 
        // but has_repaired is probabilistic-free so it is exact), 
        // then try L2.
        // Actually has_repaired IS exact with the 2-query method.
        // So this branch won't fail to find if has_repaired returned true.
        return -1; 
    } else {
        // L1 has no repaired edges. Discard L1.
        return find_repaired_edge(L2, all_cand, in_C);
    }
}

void solve() {
    cin >> n >> m;
    edges.clear();
    edges.resize(m + 1);
    for (int i = 1; i <= n; i++) adj[i].clear();
    for (int i = 1; i <= m; i++) {
        cin >> edges[i].u >> edges[i].v;
        edges[i].id = i;
        adj[edges[i].u].push_back(i);
        adj[edges[i].v].push_back(i);
        is_repaired[i] = 0;
        edge_status[i] = 0;
    }

    // Phase 1: Build Spanning Tree of Repaired edges
    vector<bool> in_C(n + 1, false);
    in_C[1] = true;
    int c_size = 1;
    
    vector<int> st_edges;
    vector<int> cand_edges; // Boundary edges
    vector<bool> in_cand(m + 1, false);

    // Init candidates
    for (int id : adj[1]) {
        cand_edges.push_back(id);
        in_cand[id] = true;
    }

    while (c_size < n) {
        // Filter cand_edges: remove internal edges
        vector<int> next_cand;
        for (int id : cand_edges) {
            int u = edges[id].u;
            int v = edges[id].v;
            if (in_C[u] && in_C[v]) {
                in_cand[id] = false;
                continue; // Internal
            }
            next_cand.push_back(id);
        }
        cand_edges = next_cand;

        // Find one repaired edge
        int found = find_repaired_edge(cand_edges, cand_edges, in_C);
        
        if (found == -1) {
            // Should not happen
            break; 
        }

        is_repaired[found] = 1;
        st_edges.push_back(found);
        
        int u = edges[found].u;
        int v = edges[found].v;
        int new_node = in_C[u] ? v : u;
        
        in_C[new_node] = true;
        c_size++;

        // Add new candidates
        for (int id : adj[new_node]) {
            int neighbor = (edges[id].u == new_node) ? edges[id].v : edges[id].u;
            if (!in_C[neighbor] && !in_cand[id]) {
                cand_edges.push_back(id);
                in_cand[id] = true;
            }
        }
    }

    // Phase 2: Check non-tree edges
    // ST structure needed for Phase 2 check
    // Rebuild adjacency for ST
    vector<vector<pair<int, int>>> st_adj(n + 1);
    for (int id : st_edges) {
        st_adj[edges[id].u].push_back({edges[id].v, id});
        st_adj[edges[id].v].push_back({edges[id].u, id});
    }

    // Precompute paths in ST? Or just do DFS per query.
    // N, M <= 2000. DFS per query is O(N). Total O(MN) ~ 4e6. Fast enough.
    // Baseline state: T unblocked, others blocked.
    // Currently all unblocked.
    // Block all non-tree edges.
    for (int i = 1; i <= m; i++) {
        bool in_st = false;
        for (int sid : st_edges) if (sid == i) in_st = true;
        if (!in_st) block_road(i);
    }

    for (int i = 1; i <= m; i++) {
        if (is_repaired[i]) continue; // Already in ST

        int u = edges[i].u;
        int v = edges[i].v;

        // Find path in ST
        vector<int> path_edges;
        vector<int> parent_edge(n + 1, 0);
        vector<int> q;
        vector<int> visited(n + 1, 0);
        q.push_back(u);
        visited[u] = 1;
        bool found_path = false;
        while (!q.empty()) {
            int curr = q.front(); q.erase(q.begin());
            if (curr == v) {
                found_path = true;
                break;
            }
            for (auto& edge : st_adj[curr]) {
                int nxt = edge.first;
                int id = edge.second;
                if (!visited[nxt]) {
                    visited[nxt] = 1;
                    parent_edge[nxt] = id;
                    q.push_back(nxt);
                }
            }
        }
        
        // Pick first edge on path
        int f = parent_edge[v];
        if (f == 0) continue; // Should not happen

        // Cut f
        block_road(f);
        unblock_road(i);

        // Determine component of u
        // BFS from u in ST \ {f}
        // Since f connects some node to v in the BFS tree from u? 
        // Wait, parent pointers were from u to v. So f is incident to v.
        // So removing f disconnects v from the component containing u (in ST).
        // So u is in one component, v is in the other (in ST \ {f}).
        // Actually we need representatives. u is rep of Comp1, v is rep of Comp2.
        
        vector<int> q_u = {u};
        vector<int> q_v = {v};
        int r_u = query(1, q_u);
        int r_v = query(1, q_v);

        if (r_u == 1 && r_v == 1) {
            is_repaired[i] = 1;
        } else {
            is_repaired[i] = 0;
        }

        // Restore
        unblock_road(f);
        block_road(i);
    }

    cout << "!";
    for (int i = 1; i <= m; i++) cout << " " << is_repaired[i];
    cout << endl;
    
    int correct;
    cin >> correct;
    if (correct == 0) exit(0);
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