#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>

using namespace std;

const int MAXN = 1005;
vector<pair<int, int>> adj[MAXN];
int p[MAXN];
int parent[MAXN];
int tin[MAXN], tout[MAXN];
int timer;
int n;
pair<int, int> edges[MAXN];
map<pair<int, int>, int> edge_to_idx;

void dfs_precompute(int v, int p) {
    parent[v] = p;
    tin[v] = ++timer;
    for (auto& edge : adj[v]) {
        int to = edge.first;
        if (to != p) {
            dfs_precompute(to, v);
        }
    }
    tout[v] = ++timer;
}

bool is_in_subtree(int u, int v) {
    return tin[u] <= tin[v] && tout[u] >= tout[v];
}

vector<vector<pair<int, int>>> MWM_adj;
vector<int> MWM_visited;
pair<long long, vector<pair<int, int>>> dp[MAXN][2];

void MWM_dfs(int u, int p) {
    MWM_visited[u] = 1;
    dp[u][0] = {0, {}};
    dp[u][1] = {-2e9 - 7, {}}; 

    long long children_sum_val = 0;
    vector<pair<int, int>> children_sum_edges;

    for (auto& edge : MWM_adj[u]) {
        int v = edge.first;
        if (v == p) continue;
        MWM_dfs(v, u);
        long long v_max_val = max(dp[v][0].first, dp[v][1].first);
        children_sum_val += v_max_val;
        if (dp[v][0].first >= dp[v][1].first) {
            children_sum_edges.insert(children_sum_edges.end(), dp[v][0].second.begin(), dp[v][0].second.end());
        } else {
            children_sum_edges.insert(children_sum_edges.end(), dp[v][1].second.begin(), dp[v][1].second.end());
        }
    }

    dp[u][0] = {children_sum_val, children_sum_edges};

    for (auto& edge : MWM_adj[u]) {
        int v = edge.first;
        int w = edge.second;
        if (v == p) continue;

        long long v_max_val = max(dp[v][0].first, dp[v][1].first);
        long long current_val = (long long)w + dp[v][0].first + (children_sum_val - v_max_val);
        
        if (current_val > dp[u][1].first) {
            dp[u][1].first = current_val;
            vector<pair<int, int>> new_edges;
            new_edges.push_back({u, v});
            new_edges.insert(new_edges.end(), dp[v][0].second.begin(), dp[v][0].second.end());
            
            for (auto& other_edge : MWM_adj[u]) {
                int ov = other_edge.first;
                if (ov == p || ov == v) continue;
                if (dp[ov][0].first >= dp[ov][1].first) {
                    new_edges.insert(new_edges.end(), dp[ov][0].second.begin(), dp[ov][0].second.end());
                } else {
                    new_edges.insert(new_edges.end(), dp[ov][1].second.begin(), dp[ov][1].second.end());
                }
            }
            dp[u][1].second = new_edges;
        }
    }
}

void solve() {
    cin >> n;
    for (int i = 1; i <= n; ++i) {
        cin >> p[i];
        adj[i].clear();
    }
    edge_to_idx.clear();
    for (int i = 1; i < n; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back({v, i});
        adj[v].push_back({u, i});
        edges[i] = {u, v};
        if (u > v) swap(u,v);
        edge_to_idx[{u,v}] = i;
    }

    timer = 0;
    dfs_precompute(1, 0);

    vector<vector<int>> operations;
    while(true) {
        bool sorted = true;
        for (int i = 1; i <= n; ++i) {
            if (p[i] != i) {
                sorted = false;
                break;
            }
        }
        if (sorted) break;
        
        MWM_adj.assign(n + 1, vector<pair<int, int>>());
        for (int i = 1; i < n; ++i) {
            int u = edges[i].first;
            int v = edges[i].second;
            
            int u_p, v_c;
            if (parent[v] == u) {
                u_p = u; v_c = v;
            } else {
                u_p = v; v_c = u;
            }
            
            int weight = 0;
            if (p[u_p] != u_p) {
                weight += (is_in_subtree(v_c, p[u_p])) ? 1 : -1;
            }
            if (p[v_c] != v_c) {
                weight += (!is_in_subtree(v_c, p[v_c])) ? 1 : -1;
            }

            if (weight >= 0) {
                MWM_adj[u].push_back({v, weight});
                MWM_adj[v].push_back({u, weight});
            }
        }
        
        vector<pair<int, int>> current_matching;
        MWM_visited.assign(n + 1, 0);
        for (int i = 1; i <= n; ++i) {
            if (MWM_adj[i].empty()) {
                MWM_visited[i] = 1;
            }
        }

        for (int i = 1; i <= n; ++i) {
            if (!MWM_visited[i]) {
                MWM_dfs(i, 0);
                if (dp[i][0].first >= dp[i][1].first) {
                    current_matching.insert(current_matching.end(), dp[i][0].second.begin(), dp[i][0].second.end());
                } else {
                    current_matching.insert(current_matching.end(), dp[i][1].second.begin(), dp[i][1].second.end());
                }
            }
        }
        
        if (current_matching.empty()) {
             break;
        }

        vector<int> op_edges;
        for (auto& edge_pair : current_matching) {
            int u = edge_pair.first;
            int v = edge_pair.second;
            if (u > v) swap(u,v);
            op_edges.push_back(edge_to_idx[{u,v}]);
        }
        operations.push_back(op_edges);

        for (auto& edge_pair : current_matching) {
            swap(p[edge_pair.first], p[edge_pair.second]);
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