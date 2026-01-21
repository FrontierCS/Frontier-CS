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

        // Read and ignore the full graph description (not needed for strategy)
        for (int i = 0; i < m; ++i) {
            int u, v;
            cin >> u >> v;
        }

        while (true) {
            string s;
            if (!(cin >> s)) return 0;  // EOF or error

            if (s == "AC" || s == "F") {
                // Map finished (either success or failure)
                break;
            } else {
                int d = stoi(s);
                vector<int> deg(d), flag(d);
                for (int i = 0; i < d; ++i) {
                    cin >> deg[i] >> flag[i];
                }

                vector<int> unvisited_indices;
                unvisited_indices.reserve(d);
                for (int i = 0; i < d; ++i) {
                    if (flag[i] == 0) {
                        unvisited_indices.push_back(i + 1); // 1-based index
                    }
                }

                int move_index;
                if (!unvisited_indices.empty()) {
                    move_index = unvisited_indices[rng() % unvisited_indices.size()];
                } else {
                    move_index = (rng() % d) + 1;
                }

                cout << move_index << endl;  // endl flushes
            }
        }
    }

    return 0;
}