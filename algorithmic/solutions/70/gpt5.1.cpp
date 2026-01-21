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
            string token;
            if (!(cin >> token)) return 0;

            if (token == "AC" || token == "F") {
                break;
            }

            int d = stoi(token);
            vector<int> deg(d), flag(d);
            for (int i = 0; i < d; ++i) {
                cin >> deg[i] >> flag[i];
            }

            int idx = -1;
            for (int i = 0; i < d; ++i) {
                if (flag[i] == 0) {
                    idx = i + 1; // 1-based
                    break;
                }
            }
            if (idx == -1) idx = 1;

            cout << idx << '\n' << flush;
        }
    }

    return 0;
}