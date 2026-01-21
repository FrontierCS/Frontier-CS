#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    int r = 1;

    vector<vector<char>> A(n + 1, vector<char>(n + 1, 0));
    // For x = r, only A[r][r] = 1
    A[r][r] = 1;

    // Query A[u][x] = (u lies on path(r, x)) for all x != r and all u
    for (int x = 1; x <= n; ++x) {
        if (x == r) continue;
        for (int u = 1; u <= n; ++u) {
            cout << "? 2 " << u << " " << r << " " << x << '\n' << flush;
            int ans;
            if (!(cin >> ans)) return 0;
            if (ans == -1) return 0;
            A[u][x] = (ans == 1);
        }
    }

    vector<int> depth(n + 1, 0);
    for (int x = 1; x <= n; ++x) {
        int cnt = 0;
        for (int u = 1; u <= n; ++u) cnt += (A[u][x] ? 1 : 0);
        depth[x] = cnt - 1;
    }

    vector<pair<int,int>> edges;
    edges.reserve(n - 1);
    for (int x = 1; x <= n; ++x) {
        if (x == r) continue;
        int p = -1;
        for (int u = 1; u <= n; ++u) {
            if (u == x) continue;
            if (A[u][x] && depth[u] == depth[x] - 1) {
                p = u;
                break;
            }
        }
        if (p == -1) return 0; // should not happen
        edges.emplace_back(p, x);
    }

    cout << "!\n";
    for (auto &e : edges) {
        cout << e.first << " " << e.second << "\n";
    }
    cout << flush;

    return 0;
}