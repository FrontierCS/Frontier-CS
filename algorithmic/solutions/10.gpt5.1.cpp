#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;

    while (T--) {
        int n;
        if (!(cin >> n)) return 0;

        if (n <= 1) {
            cout << "!" << '\n';
            cout.flush();
            continue;
        }

        const long long INF = (1LL << 60);
        vector<long long> key(n + 1, INF);
        vector<int> parent(n + 1, -1);
        vector<char> inMST(n + 1, false);
        vector<tuple<int, int, long long>> edges;

        int root = 1;
        inMST[root] = true;
        int inCount = 1;

        // Initial queries from root to all other vertices
        for (int v = 1; v <= n; ++v) {
            if (v == root) continue;
            cout << "? " << root << " " << v << '\n';
            cout.flush();
            long long d;
            if (!(cin >> d)) return 0;
            key[v] = d;
            parent[v] = root;
        }

        // Prim's algorithm on complete graph defined by distance oracle
        while (inCount < n) {
            int u = -1;
            long long best = INF;
            for (int v = 1; v <= n; ++v) {
                if (!inMST[v] && key[v] < best) {
                    best = key[v];
                    u = v;
                }
            }
            if (u == -1) break; // safety

            inMST[u] = true;
            inCount++;
            edges.emplace_back(parent[u], u, key[u]);

            for (int v = 1; v <= n; ++v) {
                if (inMST[v] || v == u) continue;
                cout << "? " << u << " " << v << '\n';
                cout.flush();
                long long d;
                if (!(cin >> d)) return 0;
                if (d < key[v]) {
                    key[v] = d;
                    parent[v] = u;
                }
            }
        }

        cout << "!";
        for (auto &e : edges) {
            int u, v;
            long long w;
            tie(u, v, w) = e;
            cout << " " << u << " " << v << " " << w;
        }
        cout << '\n';
        cout.flush();
    }

    return 0;
}