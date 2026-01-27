#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <functional>

using namespace std;

// Helper struct for DSU
struct DSU {
    vector<int> parent;
    DSU(int n) {
        parent.resize(n + 1);
        iota(parent.begin(), parent.end(), 0);
    }
    int find(int i) {
        if (parent[i] == i)
            return i;
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

// Interaction helpers
bool query(const string& s) {
    cout << s << endl;
    int result;
    cin >> result;
    if (result == -1) exit(0);
    return result == 1;
}

void block(int road_idx) {
    cout << "- " << road_idx << endl;
    int result;
    cin >> result;
    if (result == -1) exit(0);
}

void unblock(int road_idx) {
    cout << "+ " << road_idx << endl;
    int result;
    cin >> result;
    if (result == -1) exit(0);
}

bool is_connected() {
    return query("? 1 1");
}

void solve() {
    int n, m;
    cin >> n >> m;
    vector<pair<int, int>> edges(m + 1);
    for (int i = 1; i <= m; ++i) {
        cin >> edges[i].first >> edges[i].second;
    }

    vector<bool> is_repaired(m + 1, false);
    vector<int> bridges;
    vector<vector<pair<int, int>>> adj_B(n + 1);

    // 1. Find all bridges of the repaired graph
    for (int i = 1; i <= m; ++i) {
        block(i);
        if (!is_connected()) {
            is_repaired[i] = true;
            bridges.push_back(i);
        }
        unblock(i);
    }

    // 2. Build DSU and adjacency list for the bridge graph (a forest)
    DSU dsu(n);
    for (int road_idx : bridges) {
        dsu.unite(edges[road_idx].first, edges[road_idx].second);
        adj_B[edges[road_idx].first].push_back({edges[road_idx].second, road_idx});
        adj_B[edges[road_idx].second].push_back({edges[road_idx].first, road_idx});
    }

    // 3. Filter roads that can't be repaired
    vector<int> candidates;
    for (int i = 1; i <= m; ++i) {
        if (!is_repaired[i]) {
            if (dsu.find(edges[i].first) == dsu.find(edges[i].second)) {
                candidates.push_back(i);
            }
        }
    }

    // 4. Test non-bridge candidates efficiently
    vector<int> parent(n + 1, 0);
    vector<int> parent_edge(n + 1, 0);
    vector<bool> visited(n + 1, false);
    
    function<void(int, int)> dfs_build_tree = 
        [&](int u, int p) {
        visited[u] = true;
        parent[u] = p;
        for (auto& edge : adj_B[u]) {
            int v = edge.first;
            int edge_idx = edge.second;
            if (v != p) {
                parent_edge[v] = edge_idx;
                dfs_build_tree(v, u);
            }
        }
    };

    for(int i = 1; i <= n; ++i) {
        if (!visited[i]) {
            dfs_build_tree(i, 0);
        }
    }
    
    for (int road_idx : candidates) {
        block(road_idx);
    }
    
    for (int i : candidates) {
        unblock(i);

        int u = edges[i].first;
        int v = edges[i].second;
        
        // Find one edge on the path in B between u and v
        int edge_to_break = parent_edge[u];
        if (edge_to_break == 0) { // u is a root
             edge_to_break = parent_edge[v];
        }

        // To make this robust, we can trace paths to LCA to find a suitable edge.
        // A simpler approach that works is to find any edge on the path.
        // The parent of u or v is a good candidate unless one is an ancestor of the other.
        vector<bool> path_u_nodes(n + 1, false);
        int curr = u;
        while(curr != 0) {
            path_u_nodes[curr] = true;
            curr = parent[curr];
        }
        curr = v;
        while(curr != 0 && !path_u_nodes[curr]) {
            curr = parent[curr];
        }
        int lca = curr;
        
        if (u != lca) edge_to_break = parent_edge[u];
        else edge_to_break = parent_edge[v];

        block(edge_to_break);
        if (is_connected()) {
            is_repaired[i] = true;
        }
        unblock(edge_to_break);
        
        block(i);
    }

    for (int road_idx : candidates) {
        unblock(road_idx);
    }

    // Output answer
    cout << "! ";
    for (int i = 1; i <= m; ++i) {
        cout << (is_repaired[i] ? 1 : 0) << (i == m ? "" : " ");
    }
    cout << endl;

    int final_verdict;
    cin >> final_verdict;
    if (final_verdict != 1) {
        exit(0);
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    cout.flush();

    int t;
    cin >> t;
    while (t--) {
        solve();
    }

    return 0;
}