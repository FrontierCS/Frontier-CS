#include <iostream>
#include <vector>
#include <algorithm>
#include <queue>

using namespace std;

const int MAXN = 1005;

struct EdgeInfo {
    int u, v, id;
};

int n;
int p[MAXN];
vector<pair<int, int>> adj[MAXN]; // neighbor, edge_index
vector<EdgeInfo> edges;
int next_node[MAXN][MAXN]; // next_node[u][target]
int dp[MAXN][2];
int best_child[MAXN];
int current_weights[MAXN];
vector<int> selected_edges;

void precompute_next() {
    for (int start = 1; start <= n; ++start) {
        // BFS to find parent pointers in tree rooted at 'start'
        // next_node[u][start] will be the parent of u in this tree
        // which corresponds to the first node on path from u to start
        vector<int> q;
        q.reserve(n);
        q.push_back(start);
        vector<bool> visited(n + 1, false);
        visited[start] = true;
        
        // For the root itself, next_node is 0 or undefined, we fill 0
        next_node[start][start] = 0;

        int head = 0;
        while(head < q.size()){
            int u = q[head++];
            for(auto& edge : adj[u]){
                int v = edge.first;
                if(!visited[v]){
                    visited[v] = true;
                    // In the tree rooted at 'start', u is parent of v
                    // So path from v to start goes through u
                    next_node[v][start] = u;
                    q.push_back(v);
                }
            }
        }
    }
}

void dfs_dp(int u, int p_node) {
    int sum_vals = 0;
    for (auto& edge : adj[u]) {
        int v = edge.first;
        if (v == p_node) continue;
        dfs_dp(v, u);
        sum_vals += max(dp[v][0], dp[v][1]);
    }
    
    dp[u][0] = sum_vals;
    dp[u][1] = -1e9;
    
    for (auto& edge : adj[u]) {
        int v = edge.first;
        int id = edge.second;
        if (v == p_node) continue;
        
        if (current_weights[id] > 0) {
            int val = sum_vals - max(dp[v][0], dp[v][1]) + dp[v][0] + current_weights[id];
            if (val > dp[u][1]) {
                dp[u][1] = val;
                best_child[u] = v;
            }
        }
    }
}

void reconstruct(int u, int p_node, bool matched_with_parent) {
    if (matched_with_parent) {
        for (auto& edge : adj[u]) {
            int v = edge.first;
            if (v == p_node) continue;
            reconstruct(v, u, false);
        }
    } else {
        if (dp[u][1] > dp[u][0]) {
            int v = best_child[u];
            int id = -1;
            for(auto& edge : adj[u]){
                if(edge.first == v) {
                    id = edge.second;
                    break;
                }
            }
            selected_edges.push_back(id);
            
            reconstruct(v, u, true);
            for (auto& edge : adj[u]) {
                int k = edge.first;
                if (k == p_node || k == v) continue;
                reconstruct(k, u, false);
            }
        } else {
            for (auto& edge : adj[u]) {
                int v = edge.first;
                if (v == p_node) continue;
                reconstruct(v, u, false);
            }
        }
    }
}

void solve() {
    cin >> n;
    for (int i = 1; i <= n; ++i) {
        cin >> p[i];
        adj[i].clear();
    }
    edges.clear();
    for (int i = 1; i < n; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back({v, i});
        adj[v].push_back({u, i});
        edges.push_back({u, v, i});
    }

    if (n > 1) precompute_next();

    vector<vector<int>> ans_ops;
    
    while (true) {
        bool sorted = true;
        for (int i = 1; i <= n; ++i) {
            if (p[i] != i) {
                sorted = false;
                break;
            }
        }
        if (sorted) break;

        for (const auto& e : edges) {
            int u = e.u;
            int v = e.v;
            int id = e.id;
            
            int target_u = p[u];
            int target_v = p[v];
            
            bool u_wants_v = (next_node[u][target_u] == v);
            bool v_wants_u = (next_node[v][target_v] == u);
            
            if (u_wants_v && v_wants_u) current_weights[id] = 2;
            else if (u_wants_v || v_wants_u) current_weights[id] = 1;
            else current_weights[id] = 0;
        }

        dfs_dp(1, 0);
        
        selected_edges.clear();
        reconstruct(1, 0, false);
        
        if (selected_edges.empty()) break;
        
        ans_ops.push_back(selected_edges);
        
        for (int id : selected_edges) {
            int u = edges[id-1].u;
            int v = edges[id-1].v;
            swap(p[u], p[v]);
        }
    }

    cout << ans_ops.size() << "\n";
    for (const auto& ops : ans_ops) {
        cout << ops.size();
        for (int id : ops) {
            cout << " " << id;
        }
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