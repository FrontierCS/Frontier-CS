#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

    int t;
    if (!(cin >> t)) return 0;
    for (int tc = 0; tc < t; ++tc) {
        int n, m, start, base;
        if (!(cin >> n >> m >> start >> base)) return 0;
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
            // tok is degree d
            int d;
            try {
                d = stoi(tok);
            } catch (...) {
                // Unexpected token; terminate gracefully
                return 0;
            }
            vector<int> deg(d), flg(d);
            for (int i = 0; i < d; ++i) {
                cin >> deg[i] >> flg[i];
            }

            int choice = 1;
            vector<int> unvis;
            for (int i = 0; i < d; ++i) {
                if (flg[i] == 0) unvis.push_back(i);
            }
            if (!unvis.empty()) {
                int bestDeg = -1;
                vector<int> cand;
                for (int idx : unvis) {
                    if (deg[idx] > bestDeg) {
                        bestDeg = deg[idx];
                        cand.clear();
                        cand.push_back(idx);
                    } else if (deg[idx] == bestDeg) {
                        cand.push_back(idx);
                    }
                }
                uniform_int_distribution<int> dist(0, (int)cand.size() - 1);
                choice = cand[dist(rng)] + 1;
            } else {
                int bestDeg = -1;
                vector<int> cand;
                for (int i = 0; i < d; ++i) {
                    if (deg[i] > bestDeg) {
                        bestDeg = deg[i];
                        cand.clear();
                        cand.push_back(i);
                    } else if (deg[i] == bestDeg) {
                        cand.push_back(i);
                    }
                }
                if (!cand.empty()) {
                    uniform_int_distribution<int> dist(0, (int)cand.size() - 1);
                    choice = cand[dist(rng)] + 1;
                } else {
                    choice = 1;
                }
            }

            cout << choice << endl;
        }
    }
    return 0;
}