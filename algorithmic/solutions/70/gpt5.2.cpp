#include <bits/stdc++.h>
using namespace std;

static inline bool isNumber(const string& s) {
    if (s.empty()) return false;
    size_t i = 0;
    if (s[0] == '-') i = 1;
    for (; i < s.size(); ++i) if (!isdigit((unsigned char)s[i])) return false;
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());

    int t;
    if (!(cin >> t)) return 0;

    for (int tc = 0; tc < t; ++tc) {
        int n, m, start, base_move_count;
        cin >> n >> m >> start >> base_move_count;

        vector<int> degGraph(n + 1, 0);
        for (int i = 0; i < m; ++i) {
            int u, v;
            cin >> u >> v;
            degGraph[u]++;
            degGraph[v]++;
        }

        int prevFromDeg = -1;
        int stepsSinceProgress = 0;
        long long moves = 0;

        while (true) {
            string tok;
            if (!(cin >> tok)) return 0;

            if (tok == "AC" || tok == "F") break;
            if (!isNumber(tok)) return 0;

            int d = stoi(tok);
            vector<int> ndegs(d), vis(d);
            for (int i = 0; i < d; ++i) cin >> ndegs[i] >> vis[i];

            int avoid = -1;
            if (prevFromDeg != -1) {
                int cnt = 0, last = -1;
                for (int i = 0; i < d; ++i) {
                    if (vis[i] == 1 && ndegs[i] == prevFromDeg) {
                        cnt++;
                        last = i;
                    }
                }
                if (cnt == 1) avoid = last;
            }

            vector<int> unvis;
            unvis.reserve(d);
            for (int i = 0; i < d; ++i) if (vis[i] == 0) unvis.push_back(i);

            int choice = 0;
            if (!unvis.empty()) {
                int bestDeg = INT_MAX;
                for (int i : unvis) bestDeg = min(bestDeg, ndegs[i]);
                vector<int> cand;
                for (int i : unvis) if (ndegs[i] == bestDeg) cand.push_back(i);
                choice = cand[uniform_int_distribution<int>(0, (int)cand.size() - 1)(rng)];
            } else {
                vector<int> cand;
                cand.reserve(d);
                for (int i = 0; i < d; ++i) if (!(d > 1 && i == avoid)) cand.push_back(i);
                if (cand.empty()) cand.push_back(0);

                bool doRandom = (stepsSinceProgress >= 300);
                if (!doRandom) {
                    // small randomization to escape adversarial-ish patterns
                    doRandom = (uniform_int_distribution<int>(0, 9)(rng) == 0);
                }

                if (doRandom) {
                    choice = cand[uniform_int_distribution<int>(0, (int)cand.size() - 1)(rng)];
                } else {
                    int bestDeg = INT_MAX;
                    for (int i : cand) bestDeg = min(bestDeg, ndegs[i]);
                    vector<int> best;
                    for (int i : cand) if (ndegs[i] == bestDeg) best.push_back(i);
                    choice = best[uniform_int_distribution<int>(0, (int)best.size() - 1)(rng)];
                }
            }

            if (vis[choice] == 0) stepsSinceProgress = 0;
            else stepsSinceProgress++;

            cout << (choice + 1) << '\n' << flush;

            prevFromDeg = d;
            moves++;
            (void)moves;
        }
    }

    return 0;
}