#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    if (n == 1) {
        cout << 1 << '\n';
        cout.flush();
        return 0;
    }

    auto query = [&](int a, int b, int c) -> int {
        cout << 0 << ' ' << a << ' ' << b << ' ' << c << '\n';
        cout.flush();
        int ans;
        if (!(cin >> ans)) exit(0);
        return ans;
    };

    // lca[i][j] with root = 1
    vector<vector<int>> lca(n + 1, vector<int>(n + 1, 0));
    for (int i = 2; i <= n; ++i) {
        lca[1][i] = 1;
        lca[i][1] = 1;
    }
    for (int i = 2; i <= n; ++i) {
        for (int j = i + 1; j <= n; ++j) {
            int l = query(1, i, j);
            lca[i][j] = l;
            lca[j][i] = l;
        }
    }

    // anc[u][v] = true if u is ancestor of v (including u==v) in tree rooted at 1
    vector<vector<char>> anc(n + 1, vector<char>(n + 1, 0));
    for (int v = 1; v <= n; ++v) anc[v][v] = 1;
    for (int i = 1; i <= n; ++i) {
        for (int j = i + 1; j <= n; ++j) {
            int l = lca[i][j];
            if (l == i) anc[i][j] = 1;
            else if (l == j) anc[j][i] = 1;
        }
    }

    // depth[v] = number of ancestors (including itself) - 1
    vector<int> depth(n + 1, 0);
    for (int v = 1; v <= n; ++v) {
        int cnt = 0;
        for (int u = 1; u <= n; ++u) {
            if (anc[u][v]) ++cnt;
        }
        depth[v] = cnt - 1;
    }

    // parent[v]: immediate ancestor at depth-1
    vector<int> parent(n + 1, 0);
    parent[1] = 0;
    for (int v = 2; v <= n; ++v) {
        int targetDepth = depth[v] - 1;
        int par = 1;
        for (int u = 1; u <= n; ++u) {
            if (depth[u] == targetDepth && anc[u][v]) {
                par = u;
                break;
            }
        }
        parent[v] = par;
    }

    cout << 1;
    for (int v = 2; v <= n; ++v) {
        cout << ' ' << v << ' ' << parent[v];
    }
    cout << '\n';
    cout.flush();

    return 0;
}