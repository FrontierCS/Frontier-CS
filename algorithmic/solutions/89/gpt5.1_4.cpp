#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    const int MAXN = 1005;
    vector< bitset<MAXN> > path(n + 1);
    vector<int> depth(n + 1, 0);
    vector<int> parent(n + 1, 0);

    if (n == 1) {
        cout << "!" << '\n';
        cout.flush();
        return 0;
    }

    for (int i = 1; i <= n; ++i) path[i].reset();

    path[1].set(1);
    depth[1] = 0;

    for (int v = 2; v <= n; ++v) {
        path[v].reset();
        path[v].set(1);
        path[v].set(v);
        for (int u = 2; u <= n; ++u) {
            if (u == v) continue;
            cout << "? 2 " << u << " 1 " << v << '\n';
            cout.flush();
            int ans;
            if (!(cin >> ans)) return 0;
            if (ans == -1) return 0;
            if (ans == 1) path[v].set(u);
        }
    }

    for (int v = 2; v <= n; ++v) {
        depth[v] = (int)path[v].count() - 1;
    }

    parent[1] = 0;
    for (int v = 2; v <= n; ++v) {
        int targetDepth = depth[v] - 1;
        int p = 0;
        for (int u = 1; u <= n; ++u) {
            if (!path[v].test(u)) continue;
            if (depth[u] == targetDepth) {
                p = u;
                break;
            }
        }
        if (p == 0) p = 1; // Fallback, should not happen in valid interaction
        parent[v] = p;
    }

    cout << "!" << '\n';
    for (int v = 2; v <= n; ++v) {
        cout << parent[v] << ' ' << v << '\n';
    }
    cout.flush();

    return 0;
}