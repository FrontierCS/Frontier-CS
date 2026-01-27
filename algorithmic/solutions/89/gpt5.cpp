#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    int r = 1;

    vector<vector<unsigned char>> M(n + 1, vector<unsigned char>(n + 1, 0));
    vector<int> depth(n + 1, 0);

    // Initialize column for root r
    for (int u = 1; u <= n; ++u) {
        M[u][r] = (u == r) ? 1 : 0;
    }
    depth[r] = 0;

    // Collect M[u][x] for all x != r
    for (int x = 1; x <= n; ++x) {
        if (x == r) continue;
        int countOnPath = 0;
        for (int u = 1; u <= n; ++u) {
            cout << "? 2 " << u << ' ' << r << ' ' << x << endl;
            cout.flush();
            int ans;
            if (!(cin >> ans)) return 0;
            if (ans == -1) return 0;
            M[u][x] = (ans == 1 ? 1 : 0);
            if (M[u][x]) ++countOnPath;
        }
        depth[x] = countOnPath - 1;
    }

    vector<int> parent(n + 1, -1);
    parent[r] = 0;

    for (int x = 1; x <= n; ++x) {
        if (x == r) continue;
        int targetDepth = depth[x] - 1;
        int p = -1;
        for (int u = 1; u <= n; ++u) {
            if (M[u][x] && depth[u] == targetDepth) {
                p = u;
                break;
            }
        }
        if (p == -1) {
            // Should not happen in correct interaction; if it does, exit gracefully.
            return 0;
        }
        parent[x] = p;
    }

    cout << "!" << endl;
    for (int x = 1; x <= n; ++x) {
        if (x == r) continue;
        cout << parent[x] << ' ' << x << endl;
    }
    cout.flush();

    return 0;
}