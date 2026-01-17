#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

const int MAXN = 1005;
vector<pair<int, int>> adj[MAXN];
int p[MAXN];
int n;
int edge_u[MAXN], edge_v[MAXN];
int edge_map[MAXN][MAXN];

vector<int> tree_adj[MAXN];
int next_hops[MAXN][MAXN];

void bfs_for_all_next_hops() {
    for (int i = 1; i <= n; ++i) { // destination node i
        vector<int> q;
        q.push_back(i);
        vector<bool> visited(n + 1, false);
        visited[i] = true;
        next_hops[i][i] = 0; // sentinel
        
        int head = 0;
        while(head < (int)q.size()){
            int u = q[head++]; // u is closer to i
            for(auto& edge : adj[u]){
                int v = edge.first; // v is further from i
                if(!visited[v]){
                    visited[v] = true;
                    next_hops[v][i] = u; // to get to i from v, first go to u
                    q.push_back(v);
                }
            }
        }
    }
}

void build_tree_dfs(int u, int p) {
    tree_adj[u].clear();
    for (auto& edge : adj[u]) {
        int v = edge.first;
        if (v != p) {
            tree_adj[u].push_back(v);
            build_tree_dfs(v, u);
        }
    }
}

pair<long long, vector<int>> merge(const pair<long long, vector<int>>& a, const pair<long long, vector<int>>& b) {
    vector<int> res_vec;
    res_vec.reserve(a.second.size() + b.second.size());
    res_vec.insert(res_vec.end(), a.second.begin(), a.second.end());
    res_vec.insert(res_vec.end(), b.second.begin(), b.second.end());
    return {a.first + b.first, res_vec};
}

pair<long long, vector<int>> dp_res[MAXN][2];
int weights[MAXN][MAXN];

void solve_mwm(int u) {
    for (int v : tree_adj[u]) {
        solve_mwm(v);
    }
    
    // Case where u is not matched with its parent.
    // Subcase 1: u is not matched with any child.
    pair<long long, vector<int>> val_unmatched_u = {0, {}};
    for (int v : tree_adj[u]) {
        val_unmatched_u = merge(val_unmatched_u, dp_res[v][1]);
    }

    // Subcase 2: u is matched with one of its children c.
    pair<long long, vector<int>> val_matched_u = {-1, {}};
    for (int c : tree_adj[u]) {
        long long current_w = weights[u][c];
        if (current_w <= 0) continue;

        pair<long long, vector<int>> current_res = {current_w, {edge_map[u][c]}};
        current_res = merge(current_res, dp_res[c][0]);
        for (int v : tree_adj[u]) {
            if (v != c) {
                current_res = merge(current_res, dp_res[v][1]);
            }
        }
        if (current_res.first > val_matched_u.first) {
            val_matched_u = current_res;
        }
    }
    
    if (val_unmatched_u.first >= val_matched_u.first) {
        dp_res[u][1] = val_unmatched_u;
    } else {
        dp_res[u][1] = val_matched_u;
    }

    // Case where u is matched with its parent. u cannot be matched with children.
    dp_res[u][0] = val_unmatched_u;
}

bool is_sorted() {
    for (int i = 1; i <= n; ++i) {
        if (p[i] != i) {
            return false;
        }
    }
    return true;
}

void solve() {
    cin >> n;
    for (int i = 1; i <= n; ++i) {
        cin >> p[i];
        adj[i].clear();
    }
    for (int i = 1; i < n; ++i) {
        int u_in, v_in;
        cin >> u_in >> v_in;
        adj[u_in].push_back({v_in, i});
        adj[v_in].push_back({u_in, i});
        edge_u[i] = u_in;
        edge_v[i] = v_in;
        edge_map[u_in][v_in] = edge_map[v_in][u_in] = i;
    }
    
    bfs_for_all_next_hops();
    
    vector<vector<int>> operations;
    while (!is_sorted()) {
        for(int i=1; i<n; ++i) {
            int u = edge_u[i], v = edge_v[i];
            int w = 0;
            if (p[u] != u && next_hops[u][p[u]] == v) w++;
            if (p[v] != v && next_hops[v][p[v]] == u) w++;
            weights[u][v] = weights[v][u] = w;
        }
        
        build_tree_dfs(1, 0);
        solve_mwm(1);
        
        vector<int> matching = dp_res[1][1].second;
        if (matching.empty()) {
            // Failsafe, should not be reached if permutation is not sorted.
            for (int i = 1; i <= n; ++i) {
                if (p[i] != i) {
                    int u = i;
                    int v = next_hops[u][p[i]];
                    matching.push_back(edge_map[u][v]);
                    break;
                }
            }
        }
        
        operations.push_back(matching);
        for (int edge_idx : matching) {
            swap(p[edge_u[edge_idx]], p[edge_v[edge_idx]]);
        }
    }

    cout << operations.size() << endl;
    for (const auto& op : operations) {
        cout << op.size();
        for (int edge_idx : op) {
            cout << " " << edge_idx;
        }
        cout << endl;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}