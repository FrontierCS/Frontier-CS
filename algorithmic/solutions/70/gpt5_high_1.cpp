#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    mt19937 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());

    int t;
    if (!(cin >> t)) return 0;
    for (int tc = 0; tc < t; ++tc) {
        int n, m, start, base_move_count;
        if (!(cin >> n >> m >> start >> base_move_count)) return 0;
        for (int i = 0; i < m; ++i) {
            int u, v;
            cin >> u >> v;
        }

        int stagnation = 0;

        while (true) {
            string token;
            if (!(cin >> token)) return 0;
            if (token == "AC" || token == "F") {
                break;
            }

            int d = stoi(token);
            vector<int> deg(d), flag(d);
            for (int i = 0; i < d; ++i) {
                int di, fi;
                cin >> di >> fi;
                deg[i] = di;
                flag[i] = fi;
            }

            int choice = 1;
            vector<int> unvis;
            for (int i = 0; i < d; ++i) if (flag[i] == 0) unvis.push_back(i);

            if (!unvis.empty()) {
                stagnation = 0;
                int bestd = -1, cnt = 0;
                for (int idx : unvis) {
                    if (deg[idx] > bestd) {
                        bestd = deg[idx];
                        cnt = 1;
                        choice = idx + 1;
                    } else if (deg[idx] == bestd) {
                        ++cnt;
                        if ((int)(rng() % cnt) == 0) choice = idx + 1;
                    }
                }
            } else {
                stagnation++;
                double p_random = 0.05 + min(0.45, 0.02 * stagnation);
                int threshold = (int)(p_random * 1000.0 + 0.5);
                bool doRandom = (int)(rng() % 1000) < threshold;

                if (doRandom) {
                    choice = (int)(rng() % d) + 1;
                } else {
                    int bestd = -1, cnt = 0;
                    for (int i = 0; i < d; ++i) {
                        if (deg[i] > bestd) {
                            bestd = deg[i];
                            cnt = 1;
                            choice = i + 1;
                        } else if (deg[i] == bestd) {
                            ++cnt;
                            if ((int)(rng() % cnt) == 0) choice = i + 1;
                        }
                    }
                }
            }

            cout << choice << endl;
            cout.flush();
        }
    }
    return 0;
}