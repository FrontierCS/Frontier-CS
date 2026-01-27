#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if(!(cin >> n >> m)) return 0;
    vector<vector<int>> adj(n);
    vector<pair<int,int>> edges;
    edges.reserve(m);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
        edges.emplace_back(u, v);
    }
    m = (int)edges.size();
    
    mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    
    auto solve_once = [&](vector<int> &bestColor, long long &bestConf) {
        vector<int> color(n, 0);
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        shuffle(order.begin(), order.end(), rng);
        for (int v : order) {
            int cnt[4] = {0,0,0,0};
            for (int u : adj[v]) {
                int cu = color[u];
                if (cu) cnt[cu]++;
            }
            int bestC = 1, bestVal = cnt[1];
            for (int c = 2; c <= 3; ++c) {
                if (cnt[c] < bestVal) {
                    bestVal = cnt[c];
                    bestC = c;
                } else if (cnt[c] == bestVal) {
                    // random tie-break
                    if (uniform_int_distribution<int>(0,1)(rng)) bestC = c;
                }
            }
            color[v] = bestC;
        }
        vector<array<int,4>> nbCnt(n);
        for (int i = 0; i < n; ++i) nbCnt[i] = {0,0,0,0};
        long long b = 0;
        for (auto &e : edges) {
            int u = e.first, v = e.second;
            nbCnt[u][ color[v] ]++;
            nbCnt[v][ color[u] ]++;
            if (color[u] == color[v]) b++;
        }
        deque<int> q;
        vector<char> inq(n, 0);
        auto currConf = [&](int v){ return nbCnt[v][ color[v] ]; };
        auto bestMove = [&](int v, int &bestC, int &bestVal){
            bestC = color[v];
            bestVal = nbCnt[v][ color[v] ];
            for (int c = 1; c <= 3; ++c) {
                int val = nbCnt[v][c];
                if (val < bestVal) {
                    bestVal = val;
                    bestC = c;
                }
            }
        };
        for (int v = 0; v < n; ++v) {
            int bc, bv;
            bestMove(v, bc, bv);
            if (bv < nbCnt[v][ color[v] ]) {
                q.push_back(v);
                inq[v] = 1;
            }
        }
        while (!q.empty()) {
            int v = q.front(); q.pop_front();
            inq[v] = 0;
            int oldC = color[v];
            int oldConf = nbCnt[v][ oldC ];
            int newC, newConf;
            bestMove(v, newC, newConf);
            if (newConf < oldConf) {
                color[v] = newC;
                b += (newConf - oldConf);
                for (int u : adj[v]) {
                    nbCnt[u][oldC]--;
                    nbCnt[u][newC]++;
                    if (!inq[u]) {
                        int bc, bv;
                        bestMove(u, bc, bv);
                        if (bv < nbCnt[u][ color[u] ]) {
                            q.push_back(u);
                            inq[u] = 1;
                        }
                    }
                }
                if (!inq[v]) {
                    int bc, bv;
                    bestMove(v, bc, bv);
                    if (bv < nbCnt[v][ color[v] ]) {
                        q.push_back(v);
                        inq[v] = 1;
                    }
                }
            }
        }
        if (b < bestConf) {
            bestConf = b;
            bestColor = color;
        }
    };
    
    vector<int> bestColor(n, 1);
    long long bestConf = (long long)m + 1;
    int restarts = 5;
    for (int r = 0; r < restarts; ++r) {
        solve_once(bestColor, bestConf);
    }
    
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << bestColor[i];
    }
    cout << '\n';
    return 0;
}