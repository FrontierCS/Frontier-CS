#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<vector<unsigned char>> M(n + 1, vector<unsigned char>(n + 1, 0));

    // For v = 1, we know the path from 1 to 1 is just {1}
    if (n >= 1) {
        M[1][1] = 1;
        for (int u = 2; u <= n; ++u) M[u][1] = 0;
    }

    // For v = 2..n, fill column v: M[u][v] = (u lies on path(1, v))
    for (int v = 2; v <= n; ++v) {
        for (int u = 1; u <= n; ++u) {
            cout << "? 2 " << u << " 1 " << v << endl;
            int res;
            if (!(cin >> res)) return 0;
            if (res == -1) return 0;
            M[u][v] = (res ? 1 : 0);
        }
    }

    // Compute size[u] = |path(1, u)| = sum_x M[x][u]
    vector<int> sz(n + 1, 0);
    for (int u = 1; u <= n; ++u) {
        int s = 0;
        for (int x = 1; x <= n; ++x) s += M[x][u];
        sz[u] = s;
    }

    vector<pair<int,int>> edges;
    edges.reserve(max(0, n - 1));

    for (int v = 2; v <= n; ++v) {
        int best = -1, bestSize = -1;
        for (int u = 1; u <= n; ++u) {
            if (u == v) continue;
            if (M[u][v]) {
                if (sz[u] > bestSize) {
                    bestSize = sz[u];
                    best = u;
                }
            }
        }
        if (best == -1) {
            // Fallback: should not happen, but to avoid invalid output if interaction failed
            best = 1;
        }
        edges.emplace_back(best, v);
    }

    cout << "!" << endl;
    for (auto &e : edges) {
        cout << e.first << " " << e.second << endl;
    }
    cout.flush();
    return 0;
}