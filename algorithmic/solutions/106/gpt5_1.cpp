#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<long long> vals;
    long long x;
    while (cin >> x) vals.push_back(x);
    if (vals.empty()) return 0;

    int n = (int)vals[0];
    vector<long long> R;
    for (size_t i = 1; i < vals.size(); ++i) R.push_back(vals[i]);

    vector<vector<int>> g(n + 1);

    auto add_edge = [&](int u, int v) {
        if (u == v) return;
        if (u < 1 || u > n || v < 1 || v > n) return;
        g[u].push_back(v);
        g[v].push_back(u);
    };

    bool built = false;
    long long K = (long long)R.size();

    // Case 1: n m then m pairs
    if (!built && K >= 1) {
        long long m = R[0];
        if (m >= 0 && 1 + 2 * m <= K && m <= 1LL * n * (n - 1) / 2) {
            for (long long i = 0; i < m; ++i) {
                int u = (int)R[1 + 2 * i];
                int v = (int)R[1 + 2 * i + 1];
                add_edge(u, v);
            }
            built = true;
        }
    }

    // Case 2: adjacency matrix (n*n numbers)
    if (!built && K >= 1 && K == 1LL * n * n) {
        size_t idx = 0;
        for (int i = 1; i <= n; ++i) {
            for (int j = 1; j <= n; ++j) {
                long long val = R[idx++];
                if (i < j && val != 0) add_edge(i, j);
            }
        }
        built = true;
    }

    // Case 3: upper triangular adjacency (n*(n-1)/2 numbers)
    if (!built && K == 1LL * n * (n - 1) / 2) {
        size_t idx = 0;
        for (int i = 1; i <= n; ++i) {
            for (int j = i + 1; j <= n; ++j) {
                long long val = R[idx++];
                if (val != 0) add_edge(i, j);
            }
        }
        built = true;
    }

    // Case 4: just edge pairs without m
    if (!built && K % 2 == 0 && K / 2 <= 1LL * n * (n - 1) / 2) {
        for (long long i = 0; i < K / 2; ++i) {
            int u = (int)R[2 * i];
            int v = (int)R[2 * i + 1];
            add_edge(u, v);
        }
        built = true;
    }

    // Deduplicate adjacency
    for (int i = 1; i <= n; ++i) {
        auto &vec = g[i];
        sort(vec.begin(), vec.end());
        vec.erase(unique(vec.begin(), vec.end()), vec.end());
    }

    // If not built, assume empty graph
    vector<int> color(n + 1, -1), parent(n + 1, -1), depth(n + 1, 0);

    auto output_cycle = [&](int u, int v) {
        vector<int> pu, pv;
        int uu = u, vv = v;
        while (uu != vv) {
            if (depth[uu] >= depth[vv]) {
                pu.push_back(uu);
                uu = parent[uu];
            } else {
                pv.push_back(vv);
                vv = parent[vv];
            }
        }
        pu.push_back(uu); // LCA
        vector<int> cyc = pu;
        for (int i = (int)pv.size() - 1; i >= 0; --i) cyc.push_back(pv[i]);
        cout << "N " << cyc.size() << "\n";
        for (size_t i = 0; i < cyc.size(); ++i) {
            if (i) cout << " ";
            cout << cyc[i];
        }
        cout << "\n";
        return;
    };

    queue<int> q;
    for (int s = 1; s <= n; ++s) {
        if (color[s] != -1) continue;
        color[s] = 0;
        parent[s] = -1;
        depth[s] = 0;
        q.push(s);
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : g[u]) {
                if (color[v] == -1) {
                    color[v] = color[u] ^ 1;
                    parent[v] = u;
                    depth[v] = depth[u] + 1;
                    q.push(v);
                } else if (v != parent[u] && color[v] == color[u]) {
                    output_cycle(u, v);
                    return 0;
                }
            }
        }
    }

    vector<int> part;
    for (int i = 1; i <= n; ++i) if (color[i] == 0) part.push_back(i);

    cout << "Y " << part.size() << "\n";
    for (size_t i = 0; i < part.size(); ++i) {
        if (i) cout << " ";
        cout << part[i];
    }
    cout << "\n";

    return 0;
}