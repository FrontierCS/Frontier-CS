#include <bits/stdc++.h>
using namespace std;

int n;

int query(int k, int v, const vector<int> &S) {
    cout << "? " << k << " " << v;
    for (int x : S) cout << " " << x;
    cout << '\n';
    cout.flush();
    int ans;
    if (!(cin >> ans)) exit(0);
    if (ans == -1) exit(0);
    return ans;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n)) return 0;

    if (n == 1) {
        cout << "!" << '\n';
        cout.flush();
        return 0;
    }

    int r = 1;

    // onPath[u][v] == 1 iff u lies on path from r to v (inclusive)
    vector<vector<unsigned char>> onPath(n + 1, vector<unsigned char>(n + 1, 0));

    onPath[r][r] = 1;

    for (int v = 1; v <= n; ++v) {
        if (v == r) continue;
        onPath[r][v] = 1;
        onPath[v][v] = 1;
        vector<int> S = {r, v};
        for (int u = 1; u <= n; ++u) {
            if (u == r || u == v) continue;
            int ans = query(2, u, S); // is u on path between r and v?
            onPath[u][v] = (ans == 1);
        }
    }

    vector<int> pathSize(n + 1, 0);
    for (int v = 1; v <= n; ++v) {
        int cnt = 0;
        for (int u = 1; u <= n; ++u) {
            if (onPath[u][v]) ++cnt;
        }
        pathSize[v] = cnt;
    }

    vector<int> parent(n + 1, -1);
    parent[r] = 0;

    for (int v = 1; v <= n; ++v) {
        if (v == r) continue;
        int targetSize = pathSize[v] - 1;
        int p = -1;
        for (int u = 1; u <= n; ++u) {
            if (u == v) continue;
            if (onPath[u][v] && pathSize[u] == targetSize) {
                p = u;
                break;
            }
        }
        parent[v] = p;
    }

    cout << "!" << '\n';
    for (int v = 1; v <= n; ++v) {
        if (v == r) continue;
        cout << v << " " << parent[v] << '\n';
    }
    cout.flush();

    return 0;
}