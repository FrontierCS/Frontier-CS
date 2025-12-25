#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        cin >> n;
        if (n <= 0) {
            cout << "\n";
            continue;
        }

        vector<vector<long long>> D(n + 1, vector<long long>(n + 1, 0));
        for (int i = 1; i <= n; ++i) D[i][i] = 0;

        // Read upper triangle distances: D[i][j] for 1 <= i < j <= n
        for (int i = 1; i <= n; ++i) {
            for (int j = i + 1; j <= n; ++j) {
                long long x;
                cin >> x;
                D[i][j] = D[j][i] = x;
            }
        }

        if (n == 1) {
            cout << "\n";
            continue;
        }

        int root = 1; // arbitrary root
        vector<long long> depth(n + 1);
        for (int i = 1; i <= n; ++i) {
            depth[i] = D[root][i];
        }

        vector<int> order(n);
        for (int i = 0; i < n; ++i) order[i] = i + 1;
        sort(order.begin(), order.end(), [&](int a, int b) {
            return depth[a] < depth[b];
        });

        vector<tuple<int,int,long long>> edges;
        edges.reserve(n - 1);

        for (int idx = 0; idx < n; ++idx) {
            int v = order[idx];
            if (v == root) continue;
            long long bestDist = LLONG_MAX;
            int best = -1;
            for (int u = 1; u <= n; ++u) {
                if (depth[u] < depth[v]) {
                    long long d = D[v][u];
                    if (d < bestDist) {
                        bestDist = d;
                        best = u;
                    }
                }
            }
            if (best != -1) {
                edges.emplace_back(v, best, bestDist);
            }
        }

        // Output edges as sequence of triples (any order)
        for (auto &e : edges) {
            int u, v;
            long long w;
            tie(u, v, w) = e;
            cout << u << ' ' << v << ' ' << w << ' ';
        }
        cout << "\n";
    }

    return 0;
}