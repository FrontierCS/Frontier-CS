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
            if (tok == "AC" || tok == "F") {
                break;
            } else {
                int d = stoi(tok);
                vector<int> deg(d), flag(d);
                for (int i = 0; i < d; ++i) {
                    cin >> deg[i] >> flag[i];
                }
                int choice = -1;
                for (int i = 0; i < d; ++i) {
                    if (flag[i] == 0) { choice = i + 1; break; }
                }
                if (choice == -1) choice = 1;
                cout << choice << endl;
            }
        }
    }
    return 0;
}