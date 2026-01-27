#include <bits/stdc++.h>
using namespace std;

long long hill_climb(vector<int>& side,
                     const vector<vector<int>>& adj,
                     const vector<pair<int,int>>& edges,
                     const vector<int>& deg,
                     mt19937_64 &rng) {
    int n = (int)side.size();
    vector<int> degOpp(n, 0);
    long long cut = 0;

    // Initialize degOpp and cut value
    for (const auto &e : edges) {
        int u = e.first;
        int v = e.second;
        if (side[u] != side[v]) {
            degOpp[u]++;
            degOpp[v]++;
            cut++;
        }
    }

    vector<int> order(n);
    iota(order.begin(), order.end(), 0);

    bool improved = true;
    while (improved) {
        improved = false;
        shuffle(order.begin(), order.end(), rng);
        for (int idx = 0; idx < n; ++idx) {
            int v = order[idx];
            int E = degOpp[v];
            int d = deg[v];
            int delta = d - 2 * E; // gain in cut if we flip v
            if (delta > 0) {
                improved = true;
                cut += delta;
                int oldSide = side[v];
                // update neighbors
                for (int u : adj[v]) {
                    if (side[u] == oldSide) {
                        // edge was internal, now becomes cut
                        degOpp[u]++;
                    } else {
                        // edge was cut, now becomes internal
                        degOpp[u]--;
                    }
                }
                // flip v
                side[v] ^= 1;
                degOpp[v] = d - E; // new #neighbors on opposite side
            }
        }
    }
    return cut;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<vector<int>> adj(n);
    vector<pair<int,int>> edges;
    edges.reserve(m);
    vector<int> deg(n, 0);

    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        adj[u].push_back(v);
        adj[v].push_back(u);
        edges.emplace_back(u, v);
        deg[u]++;
        deg[v]++;
    }

    if (m == 0) {
        // Any partition is optimal; output all zeros
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << 0;
        }
        cout << '\n';
        return 0;
    }

    unsigned long long seed =
        chrono::steady_clock::now().time_since_epoch().count();
    mt19937_64 rng(seed);

    vector<int> bestSide(n, 0);
    long long bestCut = -1;

    // BFS-based initialization
    {
        vector<int> side(n, -1);
        queue<int> q;
        for (int i = 0; i < n; ++i) {
            if (side[i] == -1) {
                side[i] = (int)(rng() & 1ULL);
                q.push(i);
                while (!q.empty()) {
                    int v = q.front();
                    q.pop();
                    for (int u : adj[v]) {
                        if (side[u] == -1) {
                            side[u] = side[v] ^ 1;
                            q.push(u);
                        }
                    }
                }
            }
        }
        long long cut = hill_climb(side, adj, edges, deg, rng);
        bestCut = cut;
        bestSide = side;
    }

    // Random restarts
    int restarts;
    if (n <= 100) restarts = 80;
    else if (n <= 300) restarts = 60;
    else restarts = 40;

    vector<int> side(n);
    for (int s = 0; s < restarts; ++s) {
        for (int i = 0; i < n; ++i)
            side[i] = (int)(rng() & 1ULL);
        long long cut = hill_climb(side, adj, edges, deg, rng);
        if (cut > bestCut) {
            bestCut = cut;
            bestSide = side;
        }
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << bestSide[i];
    }
    cout << '\n';

    return 0;
}