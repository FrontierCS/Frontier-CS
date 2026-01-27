#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
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
            if (tok == "AC" || tok == "F") break;
            int d = stoi(tok);
            vector<int> deg(d), flg(d);
            for (int i = 0; i < d; ++i) {
                cin >> deg[i] >> flg[i];
            }
            int choice = 1;
            vector<int> unvis;
            for (int i = 0; i < d; ++i) if (flg[i] == 0) unvis.push_back(i);
            if (!unvis.empty()) {
                int best = unvis[0];
                for (int idx : unvis) {
                    if (deg[idx] < deg[best]) best = idx;
                }
                choice = best + 1;
            } else {
                int best = 0;
                for (int i = 1; i < d; ++i) {
                    if (deg[i] > deg[best]) best = i;
                }
                choice = best + 1;
            }
            cout << choice << '\n' << flush;
        }
    }
    return 0;
}