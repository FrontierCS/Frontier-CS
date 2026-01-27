#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<int> init(n), target(n);
    for (int i = 0; i < n; ++i) cin >> init[i];
    for (int i = 0; i < n; ++i) cin >> target[i];
    vector<vector<int>> adj(n);
    for (int i = 0; i < m; ++i) {
        int u, v; cin >> u >> v; --u; --v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    const int INF = 1e9;
    auto bfs = [&](int color){
        vector<int> dist(n, INF), par(n, -1);
        queue<int> q;
        for (int i = 0; i < n; ++i) {
            if (init[i] == color) {
                dist[i] = 0;
                par[i] = i;
                q.push(i);
            }
        }
        while(!q.empty()){
            int u = q.front(); q.pop();
            for(int v: adj[u]){
                if(dist[v] == INF){
                    dist[v] = dist[u] + 1;
                    par[v] = u;
                    q.push(v);
                }
            }
        }
        return pair<vector<int>, vector<int>>(dist, par);
    };

    auto [dist0, par0] = bfs(0);
    auto [dist1, par1] = bfs(1);

    vector<int> pred(n), needDist(n);
    int K = 0;
    for (int i = 0; i < n; ++i) {
        if (target[i] == 0) {
            needDist[i] = dist0[i];
            if (needDist[i] >= INF) needDist[i] = 0; // safety
            // choose a neighbor one step toward a 0-source
            if (needDist[i] == 0) pred[i] = i;
            else {
                // find neighbor with dist one less
                int best = -1;
                for (int v: adj[i]) {
                    if (dist0[v] == dist0[i] - 1) { best = v; break; }
                }
                if (best == -1) pred[i] = i;
                else pred[i] = best;
            }
        } else {
            needDist[i] = dist1[i];
            if (needDist[i] >= INF) needDist[i] = 0; // safety
            if (needDist[i] == 0) pred[i] = i;
            else {
                int best = -1;
                for (int v: adj[i]) {
                    if (dist1[v] == dist1[i] - 1) { best = v; break; }
                }
                if (best == -1) pred[i] = i;
                else pred[i] = best;
            }
        }
        K = max(K, needDist[i]);
    }

    vector<vector<int>> states;
    states.push_back(init);
    vector<int> cur = init;
    for (int t = 0; t < K; ++t) {
        vector<int> nxt = cur;
        for (int i = 0; i < n; ++i) {
            // keep pulling from pred regardless; sources have pred[i]=i
            nxt[i] = cur[pred[i]];
        }
        states.push_back(nxt);
        cur.swap(nxt);
    }

    // Output
    cout << K << "\n";
    for (int s = 0; s <= K; ++s) {
        for (int i = 0; i < n; ++i) {
            cout << states[s][i] << (i + 1 == n ? '\n' : ' ');
        }
    }
    return 0;
}