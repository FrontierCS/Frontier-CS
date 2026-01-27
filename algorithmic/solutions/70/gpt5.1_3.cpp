#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;

    std::mt19937 rng((unsigned)chrono::steady_clock::now().time_since_epoch().count());

    auto rnd_int = [&](int l, int r) {
        std::uniform_int_distribution<int> dist(l, r);
        return dist(rng);
    };

    for (int tc = 0; tc < t; ++tc) {
        int n, m, start, base_move_count;
        if (!(cin >> n >> m >> start >> base_move_count)) return 0;
        for (int i = 0; i < m; ++i) {
            int u, v;
            cin >> u >> v;
        }

        while (true) {
            string s;
            if (!(cin >> s)) return 0;
            if (!s.empty() && (s[0] == 'A' || s[0] == 'F')) {
                // "AC" or "F"
                break;
            }

            int d = stoi(s);
            vector<int> deg(d), flag(d);
            for (int i = 0; i < d; ++i) {
                cin >> deg[i] >> flag[i];
            }

            vector<int> unvisited;
            for (int i = 0; i < d; ++i) {
                if (flag[i] == 0) unvisited.push_back(i);
            }

            int idx;
            if (!unvisited.empty()) {
                int k = rnd_int(0, (int)unvisited.size() - 1);
                idx = unvisited[k];
            } else {
                idx = rnd_int(0, d - 1);
            }

            cout << (idx + 1) << '\n';
            cout.flush();
        }
    }

    return 0;
}