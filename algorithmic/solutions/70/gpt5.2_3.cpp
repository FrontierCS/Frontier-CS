#include <bits/stdc++.h>
using namespace std;

struct Walker {
    mt19937 rng;
    long long steps = 0;
    long long lastFrontierSeen = 0;
    int prevDeg = -1;

    Walker() : rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count()) {}

    int pickByDeg(const vector<int>& cand, const vector<int>& ndegs, bool pickMax) {
        int bestVal = ndegs[cand[0]];
        vector<int> best{cand[0]};
        for (int idx : cand) {
            int v = ndegs[idx];
            if ((pickMax && v > bestVal) || (!pickMax && v < bestVal)) {
                bestVal = v;
                best.clear();
                best.push_back(idx);
            } else if (v == bestVal) {
                best.push_back(idx);
            }
        }
        uniform_int_distribution<int> dist(0, (int)best.size() - 1);
        return best[dist(rng)];
    }

    int chooseMove(int d, const vector<int>& ndegs, const vector<int>& flags) {
        vector<int> unv;
        unv.reserve(d);
        for (int i = 0; i < d; i++) if (flags[i] == 0) unv.push_back(i);

        if (!unv.empty()) {
            lastFrontierSeen = steps;
            int idx = pickByDeg(unv, ndegs, true);
            return idx + 1;
        }

        vector<int> cand(d);
        iota(cand.begin(), cand.end(), 0);

        if (d > 1 && prevDeg != -1) {
            vector<int> nonBack;
            nonBack.reserve(d);
            for (int i = 0; i < d; i++) if (ndegs[i] != prevDeg) nonBack.push_back(i);
            if (!nonBack.empty()) {
                uniform_real_distribution<double> dist(0.0, 1.0);
                if (dist(rng) < 0.75) cand.swap(nonBack);
            }
        }

        long long delta = steps - lastFrontierSeen;
        double pMin = 0.0;
        if (delta > 30) pMin = min(0.85, 0.15 + (double)(delta - 30) / 150.0);

        uniform_real_distribution<double> dist(0.0, 1.0);
        bool pickMax = !(dist(rng) < pMin);

        int idx = pickByDeg(cand, ndegs, pickMax);
        return idx + 1;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;

    for (int tc = 0; tc < t; tc++) {
        int n, m, start;
        long long base_move_count;
        cin >> n >> m >> start >> base_move_count;
        for (int i = 0; i < m; i++) {
            int u, v;
            cin >> u >> v;
        }

        Walker w;

        while (true) {
            string tok;
            if (!(cin >> tok)) return 0;

            if (tok == "AC" || tok == "F") {
                break;
            }

            int d = stoi(tok);
            vector<int> ndegs(d), flags(d);
            for (int i = 0; i < d; i++) cin >> ndegs[i] >> flags[i];

            int moveIdx = w.chooseMove(d, ndegs, flags);
            cout << moveIdx << "\n" << flush;

            w.steps++;
            w.prevDeg = d;
        }
    }

    return 0;
}