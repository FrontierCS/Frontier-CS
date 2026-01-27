#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    for (int tc = 0; tc < t; ++tc) {
        int n, m, start;
        long long base_move_count;
        cin >> n >> m >> start >> base_move_count;
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
            // Prefer unvisited neighbors with maximum degree
            for (int i = 0; i < d; ++i) {
                if (flag[i] == 0) {
                    if (choose == -1 || deg[i] > deg[choose]) {
                        choose = i;
                    }
                }
            }
            if (choose == -1) {
                // All neighbors visited: choose one with maximum degree
                choose = 0;
                for (int i = 1; i < d; ++i) {
                    if (deg[i] > deg[choose]) {
                        choose = i;
                    }
                }
            }

            cout << (choose + 1) << '\n';
            cout.flush();
        }
    }

    return 0;
}