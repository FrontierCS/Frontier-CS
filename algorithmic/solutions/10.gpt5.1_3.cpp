#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        cin >> n;
        if (n <= 0) {
            cout << "\n";
            continue;
        }

        vector<vector<int>> D(n, vector<int>(n, 0));
        // Read upper triangle distances in lex order: (1,2),(1,3),...,(1,n),(2,3),...
        for (int i = 0; i < n; ++i) {
            D[i][i] = 0;
        }
        for (int i = 0; i < n; ++i) {
            for (int j = i + 1; j < n; ++j) {
                int x;
                cin >> x;
                D[i][j] = D[j][i] = x;
            }
        }

        if (n == 1) {
            // No edges
            cout << "\n";
            continue;
        }

        const int INF = 1000000007;
        vector<int> key(n, INF);
        vector<int> parent(n, -1);
        vector<char> used(n, 0);

        key[0] = 0;
        for (int it = 0; it < n; ++it) {
            int u = -1;
            int best = INF;
            for (int i = 0; i < n; ++i) {
                if (!used[i] && key[i] < best) {
                    best = key[i];
                    u = i;
                }
            }
            if (u == -1) break;
            used[u] = 1;

            for (int v = 0; v < n; ++v) {
                if (!used[v] && D[u][v] < key[v]) {
                    key[v] = D[u][v];
                    parent[v] = u;
                }
            }
        }

        // Output n-1 edges as "u v w" (1-based indices)
        for (int v = 1; v < n; ++v) {
            int u = parent[v];
            int w = D[u][v];
            cout << (u + 1) << ' ' << (v + 1) << ' ' << w << '\n';
        }
    }
    return 0;
}