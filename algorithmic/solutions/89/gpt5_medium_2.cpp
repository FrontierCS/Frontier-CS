#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    int r = 1;
    if (n == 1) {
        cout << "!\n" << flush;
        return 0;
    }

    vector<vector<char>> A(n + 1, vector<char>(n + 1, 0));
    // Pre-fill known values:
    for (int v = 1; v <= n; ++v) {
        A[r][v] = 1; // root is on path(r, v) for all v
        A[v][v] = 1; // v is on path(r, v)
        A[v][r] = (v == r); // only r is on path(r, r)
    }

    auto query = [&](int u, int a, int b) -> int {
        // Assumes a != b
        cout << "? 2 " << u << " " << a << " " << b << "\n" << flush;
        int ans;
        if (!(cin >> ans)) exit(0);
        if (ans == -1) exit(0);
        return ans;
    };

    for (int v = 1; v <= n; ++v) {
        if (v == r) continue; // A[u][r] already set
        for (int u = 1; u <= n; ++u) {
            if (u == r || u == v) continue; // known without query
            int ans = query(u, r, v);
            A[u][v] = (ans ? 1 : 0);
        }
    }

    vector<pair<int,int>> edges;
    edges.reserve(n - 1);
    for (int v = 1; v <= n; ++v) {
        if (v == r) continue;
        int parent = r;
        for (int u = 1; u <= n; ++u) {
            if (u == v) continue;
            if (!A[u][v]) continue; // not an ancestor of v
            // if current parent is ancestor of u and u != parent, then u is deeper
            if (A[parent][u] && parent != u) parent = u;
        }
        edges.emplace_back(parent, v);
    }

    cout << "!\n";
    for (auto &e : edges) {
        cout << e.first << " " << e.second << "\n";
    }
    cout << flush;

    return 0;
}