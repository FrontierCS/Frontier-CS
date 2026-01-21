#include <bits/stdc++.h>
using namespace std;

struct XorShift64 {
    uint64_t s;
    XorShift64(uint64_t seed = 88172645463325252ull) : s(seed ? seed : 88172645463325252ull) {}
    uint64_t next() {
        s ^= s << 7;
        s ^= s >> 9;
        return s;
    }
    int nextInt(int n) {
        return (int)(next() % n);
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    XorShift64 rng(chrono::high_resolution_clock::now().time_since_epoch().count());

    int t;
    if (!(cin >> t)) return 0;
    for (int tc = 0; tc < t; ++tc) {
        int n, m, start, base_move_count;
        cin >> n >> m >> start >> base_move_count;
        for (int i = 0; i < m; ++i) {
            int u, v;
            cin >> u >> v;
        }

        bool done = false;
        int prevDeg = -1;

        while (!done) {
            string tok;
            if (!(cin >> tok)) return 0;
            if (tok == "AC" || tok == "F") {
                done = true;
                prevDeg = -1;
                continue;
            }

            int d = stoi(tok);
            vector<pair<int,int>> neigh(d);
            for (int i = 0; i < d; ++i) {
                int dg, fl;
                cin >> dg >> fl;
                neigh[i] = {dg, fl};
            }

            int move_idx = 1;
            vector<int> unvis;
            for (int i = 0; i < d; ++i) if (neigh[i].second == 0) unvis.push_back(i);

            if (!unvis.empty()) {
                // Choose unvisited neighbor with smallest degree, tie break randomly
                int best = unvis[0];
                int bestDeg = neigh[best].first;
                for (int j = 1; j < (int)unvis.size(); ++j) {
                    int idx = unvis[j];
                    int dg = neigh[idx].first;
                    if (dg < bestDeg) {
                        best = idx;
                        bestDeg = dg;
                    } else if (dg == bestDeg) {
                        if (rng.nextInt(2)) best = idx;
                    }
                }
                move_idx = best + 1;
            } else {
                // All neighbors visited
                vector<int> backCand;
                if (prevDeg != -1) {
                    for (int i = 0; i < d; ++i) {
                        if (neigh[i].first == prevDeg) backCand.push_back(i);
                    }
                }
                if (backCand.size() == 1) {
                    move_idx = backCand[0] + 1;
                } else {
                    // Choose visited neighbor with smallest degree, tie break randomly
                    int best = 0;
                    int bestDeg = neigh[0].first;
                    for (int i = 1; i < d; ++i) {
                        int dg = neigh[i].first;
                        if (dg < bestDeg) {
                            best = i;
                            bestDeg = dg;
                        } else if (dg == bestDeg) {
                            if (rng.nextInt(2)) best = i;
                        }
                    }
                    move_idx = best + 1;
                }
            }

            cout << move_idx << endl;
            cout.flush();

            prevDeg = d;
        }
    }

    return 0;
}