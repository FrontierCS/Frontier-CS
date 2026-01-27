#include <bits/stdc++.h>
using namespace std;

int local_search(const vector<vector<int>>& adj, const vector<int>& degree, vector<int>& s, mt19937& rng) {
    int n = (int)adj.size();
    vector<int> external(n, 0);

    // Initialize external counts
    for (int v = 0; v < n; ++v) {
        int e = 0;
        for (int u : adj[v]) {
            if (s[u] != s[v]) ++e;
        }
        external[v] = e;
    }

    int cut = 0;
    for (int v = 0; v < n; ++v) cut += external[v];
    cut /= 2;

    vector<int> order(n);
    iota(order.begin(), order.end(), 0);

    while (true) {
        bool improved = false;
        shuffle(order.begin(), order.end(), rng);

        for (int v : order) {
            int delta = degree[v] - 2 * external[v];
            if (delta > 0) {
                improved = true;
                cut += delta;
                s[v] ^= 1;
                external[v] = degree[v] - external[v]; // new external for v

                for (int u : adj[v]) {
                    if (s[u] == s[v]) {
                        // Edge (u,v) was cut, now not cut
                        --external[u];
                    } else {
                        // Edge (u,v) was not cut, now cut
                        ++external[u];
                    }
                }
            }
        }
        if (!improved) break;
    }
    return cut;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<vector<int>> adj(n);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << 0;
        }
        cout << '\n';
        return 0;
    }

    vector<int> degree(n);
    for (int i = 0; i < n; ++i) degree[i] = (int)adj[i].size();

    mt19937 rng((unsigned)chrono::steady_clock::now().time_since_epoch().count());

    int maxRestarts = 30;
    vector<int> bestS(n, 0);
    int bestCut = -1;

    for (int r = 0; r < maxRestarts; ++r) {
        vector<int> s(n);
        for (int i = 0; i < n; ++i) s[i] = rng() & 1;

        int cut = local_search(adj, degree, s, rng);
        if (cut > bestCut) {
            bestCut = cut;
            bestS = s;
        }
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << bestS[i];
    }
    cout << '\n';

    return 0;
}