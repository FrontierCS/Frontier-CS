#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());

    for (int tc = 0; tc < t; ++tc) {
        int n, m, start, base_move_count;
        if (!(cin >> n >> m >> start >> base_move_count)) return 0;
        for (int i = 0; i < m; ++i) {
            int u, v;
            cin >> u >> v;
        }

        while (true) {
            string tok;
            if (!(cin >> tok)) return 0;
            if (tok == "AC" || tok == "F") {
                break;
            }

            int d = stoi(tok);
            vector<int> deg(d), flag(d);
            for (int i = 0; i < d; ++i) {
                cin >> deg[i] >> flag[i];
            }

            int choose = -1;
            int bestDeg = -1;

            // Prefer unvisited neighbors, pick with highest degree (random tie-break)
            for (int i = 0; i < d; ++i) {
                if (flag[i] == 0) {
                    if (deg[i] > bestDeg) {
                        bestDeg = deg[i];
                        choose = i;
                    } else if (deg[i] == bestDeg) {
                        if (uniform_int_distribution<int>(0, 1)(rng)) choose = i;
                    }
                }
            }

            // If none unvisited, pick visited neighbor with highest degree
            if (choose == -1) {
                bestDeg = -1;
                for (int i = 0; i < d; ++i) {
                    if (deg[i] > bestDeg) {
                        bestDeg = deg[i];
                        choose = i;
                    } else if (deg[i] == bestDeg) {
                        if (uniform_int_distribution<int>(0, 1)(rng)) choose = i;
                    }
                }
            }

            cout << (choose + 1) << endl;
            cout.flush();
        }
    }

    return 0;
}