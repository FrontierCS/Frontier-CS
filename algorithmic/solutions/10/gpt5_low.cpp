#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        if (!(cin >> n)) return 0;
        if (n <= 1) {
            cout << "!" << "\n" << flush;
            continue;
        }

        vector<vector<int>> dist(n + 1, vector<int>(n + 1, 0));

        for (int i = 1; i <= n; ++i) {
            for (int j = i + 1; j <= n; ++j) {
                cout << "? " << i << " " << j << "\n" << flush;
                int d;
                if (!(cin >> d)) return 0;
                dist[i][j] = dist[j][i] = d;
            }
        }

        vector<tuple<int,int,int>> edges;
        edges.reserve(n - 1);

        for (int i = 1; i <= n; ++i) {
            for (int j = i + 1; j <= n; ++j) {
                bool isEdge = true;
                int dij = dist[i][j];
                for (int k = 1; k <= n; ++k) {
                    if (k == i || k == j) continue;
                    if (dist[i][k] + dist[k][j] == dij) {
                        isEdge = false;
                        break;
                    }
                }
                if (isEdge) {
                    edges.emplace_back(i, j, dij);
                }
            }
        }

        cout << "!";
        for (auto &e : edges) {
            int u, v, w;
            tie(u, v, w) = e;
            cout << " " << u << " " << v << " " << w;
        }
        cout << "\n" << flush;
    }

    return 0;
}