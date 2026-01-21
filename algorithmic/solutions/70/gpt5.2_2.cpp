#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;

    std::mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());

    for (int tc = 0; tc < t; tc++) {
        int n, m, start, base_move_count;
        cin >> n >> m >> start >> base_move_count;
        for (int i = 0; i < m; i++) {
            int u, v;
            cin >> u >> v;
        }

        int prevDeg = -1;

        while (true) {
            string first;
            if (!(cin >> first)) return 0;

            if (first == "AC" || first == "F") break;

            int d = stoi(first);
            vector<int> ndegs(d), flags(d);
            for (int i = 0; i < d; i++) cin >> ndegs[i] >> flags[i];

            int chosen = 0;

            vector<int> unvis;
            unvis.reserve(d);
            for (int i = 0; i < d; i++) if (flags[i] == 0) unvis.push_back(i);

            if (!unvis.empty()) {
                int bestDeg = INT_MAX;
                for (int idx : unvis) bestDeg = min(bestDeg, ndegs[idx]);
                vector<int> cand;
                for (int idx : unvis) if (ndegs[idx] == bestDeg) cand.push_back(idx);
                chosen = cand[uniform_int_distribution<int>(0, (int)cand.size() - 1)(rng)];
            } else {
                int bestDeg = -1;
                for (int i = 0; i < d; i++) {
                    if (ndegs[i] == prevDeg) continue;
                    bestDeg = max(bestDeg, ndegs[i]);
                }
                if (bestDeg == -1) {
                    for (int i = 0; i < d; i++) bestDeg = max(bestDeg, ndegs[i]);
                }
                vector<int> cand;
                for (int i = 0; i < d; i++) if (ndegs[i] == bestDeg) cand.push_back(i);
                chosen = cand[uniform_int_distribution<int>(0, (int)cand.size() - 1)(rng)];
            }

            prevDeg = d;
            cout << (chosen + 1) << "\n";
            cout.flush();
        }
    }

    return 0;
}