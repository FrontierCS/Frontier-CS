#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;

    mt19937 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());

    for (int cs = 0; cs < t; ++cs) {
        int n, m, start;
        long long base_move_count;
        cin >> n >> m >> start >> base_move_count;
        for (int i = 0; i < m; ++i) {
            int u, v;
            cin >> u >> v; // edges are not used in this strategy
        }

        while (true) {
            string first;
            if (!(cin >> first)) return 0; // EOF or error

            if (first == "AC" || first == "F") {
                // Finished this map
                break;
            }

            int d = stoi(first);
            vector<int> deg(d), flag(d);
            for (int i = 0; i < d; ++i) {
                cin >> deg[i] >> flag[i];
            }

            vector<int> unvisited;
            unvisited.reserve(d);
            for (int i = 0; i < d; ++i) {
                if (flag[i] == 0) unvisited.push_back(i + 1); // 1-based index
            }

            int choice;
            if (!unvisited.empty()) {
                uniform_int_distribution<int> dist(0, (int)unvisited.size() - 1);
                choice = unvisited[dist(rng)];
            } else {
                uniform_int_distribution<int> dist(1, d);
                choice = dist(rng);
            }

            cout << choice << '\n' << flush;
        }
    }

    return 0;
}