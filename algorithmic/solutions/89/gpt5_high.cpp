#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    int r = 1; // root

    vector<vector<char>> M(n + 1, vector<char>(n + 1, 0));
    vector<int> depth(n + 1, 0);

    // Initialize for v = r
    M[r][r] = 1;
    for (int w = 1; w <= n; ++w) {
        if (w != r) M[w][r] = 0;
    }
    depth[r] = 0;

    // Queries to fill M[w][v] = 1 iff w lies on path(r, v)
    for (int v = 1; v <= n; ++v) {
        if (v == r) continue;
        int len = 2; // counts r and v
        M[r][v] = 1;
        M[v][v] = 1;
        for (int w = 1; w <= n; ++w) {
            if (w == r || w == v) continue;
            cout << "? 2 " << w << " " << r << " " << v << "\n" << flush;
            int ans;
            if (!(cin >> ans)) return 0;
            if (ans == -1) return 0;
            M[w][v] = (ans ? 1 : 0);
            if (ans) ++len;
        }
        depth[v] = len - 1;
    }

    // Reconstruct edges using depths and membership
    vector<pair<int, int>> edges;
    edges.reserve(n - 1);
    for (int v = 1; v <= n; ++v) {
        if (v == r) continue;
        int targetDepth = depth[v] - 1;
        int p = -1;
        for (int x = 1; x <= n; ++x) {
            if (depth[x] == targetDepth && M[x][v]) {
                p = x;
                break;
            }
        }
        if (p == -1) {
            // Fallback: pick deepest ancestor on path(r, v) if exact depth not found
            int best = -1, bestDepth = -1;
            for (int x = 1; x <= n; ++x) {
                if (depth[x] < depth[v] && M[x][v]) {
                    if (depth[x] > bestDepth) {
                        bestDepth = depth[x];
                        best = x;
                    }
                }
            }
            p = best;
        }
        edges.emplace_back(p, v);
    }

    cout << "!\n";
    for (auto &e : edges) {
        cout << e.first << " " << e.second << "\n";
    }
    cout.flush();

    return 0;
}