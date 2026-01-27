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
        if (!(cin >> n >> m >> start >> base_move_count)) return 0;
        for (int i = 0; i < m; ++i) {
            int u, v;
            cin >> u >> v;
        }

        while (true) {
            string s;
            if (!(cin >> s)) return 0;
            if (s == "AC" || s == "F") {
                break;
            } else {
                int d = stoi(s);
                vector<int> deg(d), flag(d);
                for (int i = 0; i < d; ++i) {
                    cin >> deg[i] >> flag[i];
                }
                int choice = 1;
                for (int i = 0; i < d; ++i) {
                    if (flag[i] == 0) {
                        choice = i + 1;
                        break;
                    }
                }
                cout << choice << endl;
            }
        }
    }
    return 0;
}