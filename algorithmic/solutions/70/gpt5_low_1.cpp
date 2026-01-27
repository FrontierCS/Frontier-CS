#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    for (int caseNum = 0; caseNum < t; ++caseNum) {
        int n, m, start, base_move_count;
        if (!(cin >> n >> m >> start >> base_move_count)) return 0;
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
            // token is degree d
            int d = stoi(token);
            vector<int> deg(d);
            vector<int> flag(d);
            for (int i = 0; i < d; ++i) {
                cin >> deg[i] >> flag[i];
            }

            int choice = 1;
            for (int i = 0; i < d; ++i) {
                if (flag[i] == 0) { choice = i + 1; break; }
            }

            cout << choice << '\n';
            cout.flush();
        }
    }
    return 0;
}