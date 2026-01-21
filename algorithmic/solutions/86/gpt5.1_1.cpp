#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    const int R = 1; // chosen root

    vector<vector<int>> lca(n + 1, vector<int>(n + 1, 0));

    // Initialize diagonal and pairs with root
    for (int i = 1; i <= n; ++i) lca[i][i] = i;
    for (int v = 2; v <= n; ++v) {
        lca[R][v] = R;
        lca[v][R] = R;
    }

    // Query LCAs for all pairs u, v > 1
    for (int u = 2; u <= n; ++u) {
        for (int v = u + 1; v <= n; ++v) {
            cout << 0 << ' ' << u << ' ' << v << ' ' << R << endl;
            cout.flush();
            int ans;
            if (!(cin >> ans)) return 0;
            lca[u][v] = lca[v][u] = ans;
        }
    }

    // Compute ancestor matrix: anc[u][v] = true iff u is ancestor of v (in tree rooted at R)
    vector<vector<char>> anc(n + 1, vector<char>(n + 1, 0));
    for (int u = 1; u <= n; ++u) {
        for (int v = 1; v <= n; ++v) {
            if (lca[u][v] == u) anc[u][v] = 1;
        }
    }

    // Compute depths: depth[v] = number of ancestors of v minus 1
    vector<int> depth(n + 1, 0);
    for (int v = 1; v <= n; ++v) {
        int cnt = 0;
        for (int u = 1; u <= n; ++u) {
            if (anc[u][v]) ++cnt;
        }
        depth[v] = cnt - 1;
    }

    // Determine parents
    vector<int> parent(n + 1, 0);
    parent[R] = 0;
    for (int v = 1; v <= n; ++v) {
        if (v == R) continue;
        int targetDepth = depth[v] - 1;
        int par = R;
        for (int u = 1; u <= n; ++u) {
            if (anc[u][v] && depth[u] == targetDepth) {
                par = u;
                break;
            }
        }
        parent[v] = par;
    }

    // Output the reconstructed tree
    cout << 1;
    for (int v = 1; v <= n; ++v) {
        if (v == R) continue;
        cout << ' ' << parent[v] << ' ' << v;
    }
    cout << '\n';
    cout.flush();

    return 0;
}