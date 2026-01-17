#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <queue>

using namespace std;

struct Edge {
    int u, v, id;
};

int n;
vector<int> p;
vector<vector<pair<int, int>>> adj;
vector<Edge> edges;
vector<vector<int>> dists;

// DP for matching
// dp[u][0]: max weight in subtree u, u NOT matched with children
// dp[u][1]: max weight in subtree u, u IS matched with a child
long long dp[1005][2];
long long edge_weights[1005]; // weight of edge with id i

void bfs(int start, vector<int>& d) {
    fill(d.begin(), d.end(), -1);
    d[start] = 0;
    queue<int> q;
    q.push(start);
    while(!q.empty()){
        int u = q.front();
        q.pop();
        for(auto& edge : adj[u]){
            int v = edge.first;
            if(d[v] == -1){
                d[v] = d[u] + 1;
                q.push(v);
            }
        }
    }
}

void solve_dp(int u, int parent) {
    long long sum_unmatched = 0;
    for(auto& edge : adj[u]){
        int v = edge.first;
        if(v == parent) continue;
        solve_dp(v, u);
        sum_unmatched += max(dp[v][0], dp[v][1]);
    }
    
    dp[u][0] = sum_unmatched;
    dp[u][1] = -2e18; // Initialize with a very small value
    
    for(auto& edge : adj[u]){
        int v = edge.first;
        int id = edge.second;
        if(v == parent) continue;
        
        long long w = edge_weights[id];
        // If we match u-v, we take dp[v][0] from v (since v is matched with u, v cannot match its children)
        // and sum_unmatched - max(dp[v][0], dp[v][1]) from other children
        long long val = sum_unmatched - max(dp[v][0], dp[v][1]) + dp[v][0] + w;
        
        if(val > dp[u][1]){
            dp[u][1] = val;
        }
    }
}

void get_matching(int u, int parent, int state, vector<int>& selected_edges) {
    if (state == 0) { // u is not matched with any child
        for(auto& edge : adj[u]){
            int v = edge.first;
            if(v == parent) continue;
            // v can be matched with its own children or not
            if(dp[v][1] > dp[v][0]) get_matching(v, u, 1, selected_edges);
            else get_matching(v, u, 0, selected_edges);
        }
    } else { // u is matched with a child
        long long sum_unmatched = dp[u][0];
        long long best_val = -2e18;
        int best_v = -1;
        int best_id = -1;

        // Re-find the best child
        for(auto& edge : adj[u]){
            int v = edge.first;
            int id = edge.second;
            if(v == parent) continue;
            long long w = edge_weights[id];
            long long val = sum_unmatched - max(dp[v][0], dp[v][1]) + dp[v][0] + w;
            if(val > best_val){
                best_val = val;
                best_v = v;
                best_id = id;
            }
        }
        
        if(best_id != -1) selected_edges.push_back(best_id);
        
        for(auto& edge : adj[u]){
            int v = edge.first;
            if(v == parent) continue;
            if(v == best_v) {
                // v is matched with u, so v acts as root of its subtree not matched with children
                get_matching(v, u, 0, selected_edges);
            } else {
                if(dp[v][1] > dp[v][0]) get_matching(v, u, 1, selected_edges);
                else get_matching(v, u, 0, selected_edges);
            }
        }
    }
}

void solve() {
    cin >> n;
    p.assign(n + 1, 0);
    for(int i = 1; i <= n; ++i) cin >> p[i];
    
    adj.assign(n + 1, vector<pair<int, int>>());
    edges.clear();
    for(int i = 0; i < n - 1; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back({v, i + 1});
        adj[v].push_back({u, i + 1});
        edges.push_back({u, v, i + 1});
    }
    
    dists.assign(n + 1, vector<int>(n + 1));
    for(int i = 1; i <= n; ++i) bfs(i, dists[i]);
    
    struct Op {
        vector<int> edge_indices;
    };
    vector<Op> ops;
    
    while(true) {
        bool sorted = true;
        for(int i = 1; i <= n; ++i) {
            if(p[i] != i) {
                sorted = false;
                break;
            }
        }
        if(sorted) break;
        
        for(const auto& e : edges) {
            int u = e.u;
            int v = e.v;
            int pu = p[u];
            int pv = p[v];
            
            bool u_wants_cross = (dists[v][pu] < dists[u][pu]);
            bool v_wants_cross = (dists[u][pv] < dists[v][pv]);
            
            long long w = -1e15; 
            
            if(u_wants_cross && v_wants_cross) {
                w = 100000;
            } else if(!u_wants_cross && !v_wants_cross) {
                w = -100000;
            } else if(u_wants_cross && !v_wants_cross) {
                int d_pu = dists[u][pu] - 1;
                int d_pv = dists[v][pv];
                if(d_pu > d_pv) {
                    w = 1000 + (d_pu - d_pv);
                } else if(d_pu == d_pv) {
                    if(pu < pv) w = 1000; 
                    else w = -1000;
                } else {
                    w = -100000;
                }
            } else { // !u_wants_cross && v_wants_cross
                int d_pu = dists[u][pu];
                int d_pv = dists[v][pv] - 1;
                if(d_pv > d_pu) {
                    w = 1000 + (d_pv - d_pu);
                } else if(d_pv == d_pu) {
                    if(pv < pu) w = 1000;
                    else w = -1000;
                } else {
                    w = -100000;
                }
            }
            
            edge_weights[e.id] = w;
        }
        
        solve_dp(1, 0);
        
        vector<int> selected;
        if(dp[1][1] > dp[1][0]) get_matching(1, 0, 1, selected);
        else get_matching(1, 0, 0, selected);
        
        if(selected.empty()) break;
        
        ops.push_back({selected});
        
        for(int id : selected) {
            int u = edges[id-1].u;
            int v = edges[id-1].v;
            swap(p[u], p[v]);
        }
    }
    
    cout << ops.size() << "\n";
    for(const auto& op : ops) {
        cout << op.edge_indices.size();
        for(int id : op.edge_indices) {
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
        while(t--) {
            solve();
        }
    }
    return 0;
}