#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <cstdlib>

using namespace std;

struct Edge {
    int to;
    int id;
};

int n;
vector<int> p;
vector<vector<Edge>> adj;
vector<vector<int>> dists;
vector<pair<int, int>> edges_list;

// BFS to compute all-pairs distances
void bfs_all() {
    dists.assign(n + 1, vector<int>(n + 1, 0));
    for (int i = 1; i <= n; ++i) {
        queue<int> q;
        q.push(i);
        vector<int> d(n + 1, -1);
        d[i] = 0;
        while (!q.empty()) {
            int u = q.front();
            q.pop();
            dists[i][u] = d[u];
            for (auto& e : adj[u]) {
                if (d[e.to] == -1) {
                    d[e.to] = d[u] + 1;
                    q.push(e.to);
                }
            }
        }
    }
}

struct Step {
    int k;
    vector<int> ids;
};

long long dp[1005][2];
int choice[1005]; 
long long edge_weight[1005]; 

void dfs_dp(int u, int parent) {
    long long sum_max = 0;
    for (auto& e : adj[u]) {
        if (e.to == parent) continue;
        dfs_dp(e.to, u);
        sum_max += max(dp[e.to][0], dp[e.to][1]);
    }
    
    dp[u][0] = sum_max;
    
    dp[u][1] = -1e18; 
    choice[u] = -1;
    
    for (auto& e : adj[u]) {
        if (e.to == parent) continue;
        long long val = sum_max - max(dp[e.to][0], dp[e.to][1]) + dp[e.to][0] + edge_weight[e.id];
        
        if (val > dp[u][1]) {
            dp[u][1] = val;
            choice[u] = e.to;
        }
    }
}

vector<int> selected_edges;
void reconstruct(int u, int parent, int state) {
    if (state == 0) {
        for (auto& e : adj[u]) {
            if (e.to == parent) continue;
            if (dp[e.to][1] > dp[e.to][0]) {
                reconstruct(e.to, u, 1);
            } else {
                reconstruct(e.to, u, 0);
            }
        }
    } else {
        int v_matched = choice[u];
        for (auto& e : adj[u]) {
            if (e.to == parent) continue;
            if (e.to == v_matched) {
                selected_edges.push_back(e.id);
                reconstruct(e.to, u, 0);
            } else {
                if (dp[e.to][1] > dp[e.to][0]) {
                    reconstruct(e.to, u, 1);
                } else {
                    reconstruct(e.to, u, 0);
                }
            }
        }
    }
}

void solve() {
    if (!(cin >> n)) return;
    p.assign(n + 1, 0);
    for (int i = 1; i <= n; ++i) cin >> p[i];
    
    adj.assign(n + 1, vector<Edge>());
    edges_list.assign(n, {0, 0});
    for (int i = 1; i < n; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back({v, i});
        adj[v].push_back({u, i});
        edges_list[i] = {u, v};
    }
    
    bfs_all();
    
    vector<Step> ans;
    // Limit operations to avoid infinite loops, though it should converge
    int max_ops = 4 * n; 
    
    for (int iter = 0; iter < max_ops; ++iter) {
        bool sorted = true;
        for (int i = 1; i <= n; ++i) {
            if (p[i] != i) {
                sorted = false;
                break;
            }
        }
        if (sorted) break;
        
        for (int i = 1; i < n; ++i) {
            int u = edges_list[i].first;
            int v = edges_list[i].second;
            
            int val_u = p[u];
            int val_v = p[v];
            
            int d_before = dists[u][val_u] + dists[v][val_v];
            int d_after = dists[v][val_u] + dists[u][val_v];
            int gain = d_before - d_after;
            
            if (gain == 2) {
                edge_weight[i] = 100000;
            } else if (gain == 0) {
                // Add randomness to break cycles and potential stagnation
                edge_weight[i] = 200 + (rand() % 50);
                // Prefer swaps that help items far from destination
                edge_weight[i] += (dists[u][val_u] + dists[v][val_v]);
            } else {
                edge_weight[i] = -1000000;
            }
        }
        
        dfs_dp(1, 0);
        
        selected_edges.clear();
        if (dp[1][1] > dp[1][0]) {
            reconstruct(1, 0, 1);
        } else {
            reconstruct(1, 0, 0);
        }
        
        if (selected_edges.empty()) break;
        
        Step s;
        s.k = selected_edges.size();
        s.ids = selected_edges;
        ans.push_back(s);
        
        for (int id : selected_edges) {
            int u = edges_list[id].first;
            int v = edges_list[id].second;
            swap(p[u], p[v]);
        }
    }
    
    cout << ans.size() << "\n";
    for (auto& s : ans) {
        cout << s.k;
        for (int id : s.ids) cout << " " << id;
        cout << "\n";
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    srand(5489); 
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}