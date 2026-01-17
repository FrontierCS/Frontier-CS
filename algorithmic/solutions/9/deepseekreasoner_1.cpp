#include <iostream>
#include <vector>
#include <algorithm>
#include <queue>
#include <cstring>
using namespace std;

const int MAXN = 1005;

int dist[MAXN][MAXN];
vector<int> adj[MAXN];

void bfs(int start, int n) {
    vector<int>& d = dist[start];
    for (int i = 1; i <= n; i++) d[i] = -1;
    queue<int> q;
    q.push(start);
    d[start] = 0;
    while (!q.empty()) {
        int u = q.front(); q.pop();
        for (int v : adj[u]) {
            if (d[v] == -1) {
                d[v] = d[u] + 1;
                q.push(v);
            }
        }
    }
}

void solve() {
    int n;
    cin >> n;
    vector<int> p(n+1);
    for (int i = 1; i <= n; i++) cin >> p[i];
    
    vector<pair<int,int>> edges(n-1);
    for (int i = 1; i <= n; i++) adj[i].clear();
    for (int i = 0; i < n-1; i++) {
        int u, v;
        cin >> u >> v;
        edges[i] = {u, v};
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    
    // compute all-pairs distances
    for (int i = 1; i <= n; i++) bfs(i, n);
    
    // current token at each vertex
    vector<int> a = p;
    // phi[t] = vertex where token t is located
    vector<int> phi(n+1);
    for (int v = 1; v <= n; v++) phi[a[v]] = v;
    
    vector<vector<int>> operations;
    
    while (true) {
        // check if sorted
        bool sorted = true;
        for (int v = 1; v <= n; v++) if (a[v] != v) { sorted = false; break; }
        if (sorted) break;
        
        // find cycles in phi
        vector<int> cycle_id(n+1, -1);
        int cycle_cnt = 0;
        for (int i = 1; i <= n; i++) {
            if (cycle_id[i] == -1) {
                int j = i;
                do {
                    cycle_id[j] = cycle_cnt;
                    j = phi[j];
                } while (j != i);
                cycle_cnt++;
            }
        }
        
        // candidate edges
        struct Cand {
            int eid, gain, u, v;
            bool same_cycle;
        };
        vector<Cand> candidates;
        for (int eid = 0; eid < n-1; eid++) {
            int u = edges[eid].first, v = edges[eid].second;
            int i = a[u], j = a[v];
            int cur_dist = dist[u][i] + dist[v][j];
            int new_dist = dist[v][i] + dist[u][j];
            int gain = cur_dist - new_dist;
            bool same_cycle = (cycle_id[i] == cycle_id[j]);
            // consider edges that either have positive gain or are in same cycle
            if (gain > 0 || same_cycle) {
                candidates.push_back({eid, gain, u, v, same_cycle});
            }
        }
        
        // sort: positive gain first (higher gain first), then same_cycle edges
        sort(candidates.begin(), candidates.end(), [](const Cand& x, const Cand& y) {
            if (x.gain > 0 && y.gain > 0) return x.gain > y.gain;
            if (x.gain > 0) return true;
            if (y.gain > 0) return false;
            if (x.same_cycle && !y.same_cycle) return true;
            if (!x.same_cycle && y.same_cycle) return false;
            return x.gain > y.gain; // both zero gain and same_cycle status
        });
        
        vector<bool> used(n+1, false);
        vector<int> matching;
        for (auto& cand : candidates) {
            if (!used[cand.u] && !used[cand.v]) {
                used[cand.u] = used[cand.v] = true;
                matching.push_back(cand.eid);
            }
        }
        
        // if no edge selected, force an edge with at least one incorrect token
        if (matching.empty()) {
            for (int eid = 0; eid < n-1; eid++) {
                int u = edges[eid].first, v = edges[eid].second;
                if ((a[u] != u || a[v] != v) && !used[u] && !used[v]) {
                    matching.push_back(eid);
                    break;
                }
            }
        }
        
        // still empty (should not happen if not sorted), take first edge
        if (matching.empty() && n-1 > 0) {
            matching.push_back(0);
        }
        
        // apply the swaps
        for (int eid : matching) {
            int u = edges[eid].first, v = edges[eid].second;
            swap(a[u], a[v]);
        }
        
        // update phi
        for (int v = 1; v <= n; v++) phi[a[v]] = v;
        
        operations.push_back(matching);
    }
    
    // output
    cout << operations.size() << "\n";
    for (auto& op : operations) {
        cout << op.size();
        for (int eid : op) cout << " " << eid+1; // 1-based index
        cout << "\n";
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int T;
    cin >> T;
    while (T--) {
        solve();
    }
    return 0;
}