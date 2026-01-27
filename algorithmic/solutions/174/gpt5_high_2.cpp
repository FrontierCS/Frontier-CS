#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<pair<int,int>> edges;
    edges.reserve(m);
    vector<int> deg(n, 0);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        edges.emplace_back(u, v);
        deg[u]++; deg[v]++;
    }
    if (n == 0) return 0;
    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << 1;
        }
        cout << '\n';
        return 0;
    }
    vector<vector<int>> adj(n);
    for (int i = 0; i < n; ++i) adj[i].reserve(deg[i]);
    for (auto &e : edges) {
        int u = e.first, v = e.second;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    // RNG
    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    mt19937 rng((uint32_t)(seed ^ (seed >> 32)));
    
    // DSATUR-like initialization aiming for fewer conflicts.
    vector<int> color(n, -1);
    vector<int> colorCount(3, 0);
    vector<int> satMask(n, 0);
    vector<array<int,3>> dcnt(n); // counts of colored neighbors per color
    for (int i = 0; i < n; ++i) dcnt[i] = {0,0,0};
    
    for (int step = 0; step < n; ++step) {
        int best = -1, bestSat = -1, bestDeg = -1;
        for (int v = 0; v < n; ++v) {
            if (color[v] != -1) continue;
            int sat = __builtin_popcount((unsigned)satMask[v]);
            if (sat > bestSat) {
                bestSat = sat; bestDeg = deg[v]; best = v;
            } else if (sat == bestSat) {
                if (deg[v] > bestDeg) {
                    bestDeg = deg[v]; best = v;
                } else if (deg[v] == bestDeg) {
                    if (rng() & 1) best = v;
                }
            }
        }
        int v = best;
        int allowed = (~satMask[v]) & 7; // colors 0..2
        int chosen = 0;
        if (allowed) {
            // Choose allowed color balancing global counts
            int minCnt = INT_MAX;
            int choices[3], csz = 0;
            for (int k = 0; k < 3; ++k) if (allowed & (1<<k)) {
                if (colorCount[k] < minCnt) {
                    minCnt = colorCount[k];
                    csz = 0;
                    choices[csz++] = k;
                } else if (colorCount[k] == minCnt) {
                    choices[csz++] = k;
                }
            }
            chosen = choices[rng() % csz];
        } else {
            // All colors used among neighbors: choose color minimizing conflicts with already colored neighbors
            int bestVal = INT_MAX;
            int choices[3], csz = 0;
            for (int k = 0; k < 3; ++k) {
                int val = dcnt[v][k];
                if (val < bestVal) {
                    bestVal = val;
                    csz = 0;
                    choices[csz++] = k;
                } else if (val == bestVal) {
                    choices[csz++] = k;
                }
            }
            chosen = choices[rng() % csz];
        }
        color[v] = chosen;
        colorCount[chosen]++;
        for (int u : adj[v]) {
            if (color[u] == -1) {
                satMask[u] |= (1 << chosen);
                dcnt[u][chosen]++;
            }
        }
    }
    
    // Build neighbor color counts for the whole graph and compute initial conflicts
    vector<array<int,3>> cnt(n);
    for (int i = 0; i < n; ++i) cnt[i] = {0,0,0};
    int b = 0;
    for (auto &e : edges) {
        int u = e.first, v = e.second;
        cnt[u][color[v]]++;
        cnt[v][color[u]]++;
        if (color[u] == color[v]) b++;
    }
    
    // Local descent: recolor a vertex to color minimizing same-colored neighbors if it reduces conflicts.
    deque<int> q;
    vector<char> inq(n, 0);
    for (int v = 0; v < n; ++v) {
        if (cnt[v][color[v]] > 0) {
            q.push_back(v);
            inq[v] = 1;
        }
    }
    auto choose_best_color = [&](int v) -> pair<int,int> {
        int curr = color[v];
        int bestC = curr, bestVal = cnt[v][curr];
        int vals[3] = {cnt[v][0], cnt[v][1], cnt[v][2]};
        int minVal = min(vals[0], min(vals[1], vals[2]));
        // Random tie-break among minima
        int choices[3], csz = 0;
        for (int k = 0; k < 3; ++k) {
            if (vals[k] == minVal) choices[csz++] = k;
        }
        bestC = choices[rng() % csz];
        bestVal = vals[bestC];
        return {bestC, bestVal};
    };
    
    while (!q.empty()) {
        int v = q.front(); q.pop_front();
        inq[v] = 0;
        int currC = color[v];
        int currConf = cnt[v][currC];
        if (currConf == 0) continue;
        auto [bestC, bestVal] = choose_best_color(v);
        if (bestVal < currConf) {
            // apply move
            int oldC = currC;
            int newC = bestC;
            color[v] = newC;
            b += (bestVal - currConf);
            for (int u : adj[v]) {
                cnt[u][oldC]--;
                cnt[u][newC]++;
                if (!inq[u]) { q.push_back(u); inq[u] = 1; }
            }
            if (!inq[v]) { q.push_back(v); inq[v] = 1; }
        }
    }
    
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (color[i] + 1);
    }
    cout << '\n';
    return 0;
}