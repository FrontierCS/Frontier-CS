#include <bits/stdc++.h>
using namespace std;

static uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    uint64_t seed = splitmix64((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    std::mt19937_64 rng(seed);

    int t;
    if (!(cin >> t)) return 0;

    for (int tc = 0; tc < t; tc++) {
        int n, m, start;
        long long base_move_count;
        cin >> n >> m >> start >> base_move_count;

        vector<int> degKnown(n + 1, 0);
        for (int i = 0; i < m; i++) {
            int u, v;
            cin >> u >> v;
            degKnown[u]++, degKnown[v]++;
        }

        long long moves = 0;
        int visitedCount = 1;
        int prevDeg = -1;

        while (true) {
            string tok;
            if (!(cin >> tok)) return 0;

            if (tok == "AC" || tok == "F") {
                break;
            }

            int d = stoi(tok);
            vector<int> ndegs(d), flags(d);
            for (int i = 0; i < d; i++) cin >> ndegs[i] >> flags[i];

            vector<int> candidates;
            int bestDeg = -1;

            bool hasUnvisited = false;
            for (int i = 0; i < d; i++) {
                if (flags[i] == 0) {
                    hasUnvisited = true;
                    bestDeg = max(bestDeg, ndegs[i]);
                }
            }

            if (hasUnvisited) {
                for (int i = 0; i < d; i++) {
                    if (flags[i] == 0 && ndegs[i] == bestDeg) candidates.push_back(i);
                }
            } else {
                bool hasDiff = false;
                if (prevDeg != -1) {
                    for (int i = 0; i < d; i++) if (ndegs[i] != prevDeg) { hasDiff = true; break; }
                }

                for (int i = 0; i < d; i++) {
                    if (prevDeg != -1 && hasDiff && ndegs[i] == prevDeg) continue;
                    bestDeg = max(bestDeg, ndegs[i]);
                }

                for (int i = 0; i < d; i++) {
                    if (prevDeg != -1 && hasDiff && ndegs[i] == prevDeg) continue;
                    if (ndegs[i] == bestDeg) candidates.push_back(i);
                }

                if (candidates.empty()) {
                    for (int i = 0; i < d; i++) candidates.push_back(i);
                }
            }

            int pickIdx = candidates[0];
            if (candidates.size() > 1) {
                uint64_t r = rng();
                pickIdx = candidates[(size_t)(r % candidates.size())];
            }

            cout << (pickIdx + 1) << '\n' << flush;

            moves++;
            if (pickIdx >= 0 && pickIdx < d && flags[pickIdx] == 0) visitedCount++;
            prevDeg = d;
        }
    }

    return 0;
}