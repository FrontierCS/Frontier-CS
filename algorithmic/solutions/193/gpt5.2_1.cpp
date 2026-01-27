#include <bits/stdc++.h>
using namespace std;

struct Clause {
    int a, b;
    int v1, v2;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;

    if (m == 0) {
        for (int i = 1; i <= n; i++) {
            cout << 0 << (i == n ? '\n' : ' ');
        }
        return 0;
    }

    vector<Clause> cls(m);
    vector<vector<int>> occ(n + 1);
    for (int i = 0; i < m; i++) {
        int a, b;
        cin >> a >> b;
        cls[i] = {a, b, abs(a), abs(b)};
        occ[cls[i].v1].push_back(i);
        if (cls[i].v2 != cls[i].v1) occ[cls[i].v2].push_back(i);
    }

    mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> bit01(0, 1);

    vector<uint8_t> val(n + 1, 0), bestVal(n + 1, 0);
    vector<uint8_t> clauseSat(m, 0);
    vector<uint8_t> numTrue(m, 0);
    vector<int> posUnsat(m, -1);
    vector<int> unsat;
    vector<int> breakCnt(n + 1, 0), makeCnt(n + 1, 0);
    int curSat = 0, bestSat = -1;

    auto computeT1T2Sat = [&](int ci, int &t1, int &t2, int &sat) {
        const auto &c = cls[ci];
        t1 = int(val[c.v1] ^ uint8_t(c.a < 0));
        t2 = int(val[c.v2] ^ uint8_t(c.b < 0));
        sat = t1 | t2;
    };

    auto addUnsat = [&](int ci) {
        if (posUnsat[ci] != -1) return;
        posUnsat[ci] = (int)unsat.size();
        unsat.push_back(ci);
    };

    auto removeUnsat = [&](int ci) {
        int p = posUnsat[ci];
        if (p == -1) return;
        int last = unsat.back();
        unsat[p] = last;
        posUnsat[last] = p;
        unsat.pop_back();
        posUnsat[ci] = -1;
    };

    auto applyContrib = [&](int ci, int sign, int t1, int t2, int sat) {
        const auto &c = cls[ci];
        int v1 = c.v1, v2 = c.v2;

        auto applyVar = [&](int x) {
            int satFlip;
            if (v1 == v2) {
                satFlip = (!t1) | (!t2);
            } else if (x == v1) {
                satFlip = (!t1) | t2;
            } else { // x == v2
                satFlip = t1 | (!t2);
            }
            int br = (sat && !satFlip) ? 1 : 0;
            int mk = (!sat && satFlip) ? 1 : 0;
            breakCnt[x] += sign * br;
            makeCnt[x] += sign * mk;
        };

        applyVar(v1);
        if (v2 != v1) applyVar(v2);
    };

    auto initState = [&]() {
        fill(breakCnt.begin(), breakCnt.end(), 0);
        fill(makeCnt.begin(), makeCnt.end(), 0);
        unsat.clear();
        fill(posUnsat.begin(), posUnsat.end(), -1);
        curSat = 0;

        for (int i = 0; i < m; i++) {
            int t1, t2, sat;
            computeT1T2Sat(i, t1, t2, sat);
            clauseSat[i] = uint8_t(sat);
            numTrue[i] = uint8_t(t1 + t2);
            if (sat) curSat++;
            else addUnsat(i);
            applyContrib(i, +1, t1, t2, sat);
        }
    };

    auto flipVar = [&](int v) {
        // remove old contributions
        for (int ci : occ[v]) {
            int t1, t2, sat;
            computeT1T2Sat(ci, t1, t2, sat);
            applyContrib(ci, -1, t1, t2, sat);
        }

        val[v] ^= 1;

        // add new contributions + update clause sats / unsat list
        for (int ci : occ[v]) {
            int oldSat = clauseSat[ci];
            int t1, t2, sat;
            computeT1T2Sat(ci, t1, t2, sat);
            clauseSat[ci] = uint8_t(sat);
            numTrue[ci] = uint8_t(t1 + t2);

            if (!oldSat && sat) {
                curSat++;
                removeUnsat(ci);
            } else if (oldSat && !sat) {
                curSat--;
                addUnsat(ci);
            }

            applyContrib(ci, +1, t1, t2, sat);
        }
    };

    auto start = chrono::steady_clock::now();
    auto deadline = start + chrono::milliseconds(1700);

    // At least one run
    for (int i = 1; i <= n; i++) val[i] = uint8_t(bit01(rng));
    initState();
    bestSat = curSat;
    bestVal = val;

    const int greedyMax = 2000;
    const int walkMax = 10000;
    const uint32_t RAND_TH = uint32_t(double(numeric_limits<uint32_t>::max()) * 0.25);

    int restarts = 0;
    while (chrono::steady_clock::now() < deadline && restarts < 100) {
        restarts++;

        for (int i = 1; i <= n; i++) val[i] = uint8_t(bit01(rng));
        initState();

        // Greedy hillclimb on gain
        for (int step = 0; step < greedyMax; step++) {
            if ((step & 255) == 0 && chrono::steady_clock::now() >= deadline) break;
            int bestV = -1, bestGain = 0;
            for (int v = 1; v <= n; v++) {
                int gain = makeCnt[v] - breakCnt[v];
                if (gain > bestGain) {
                    bestGain = gain;
                    bestV = v;
                }
            }
            if (bestGain <= 0 || bestV == -1) break;
            flipVar(bestV);
            if (curSat > bestSat) {
                bestSat = curSat;
                bestVal = val;
                if (bestSat == m) break;
            }
        }

        // WalkSAT-style local search
        for (int step = 0; step < walkMax && !unsat.empty(); step++) {
            if ((step & 255) == 0 && chrono::steady_clock::now() >= deadline) break;

            int ci = unsat[(size_t)(rng() % unsat.size())];
            int v1 = cls[ci].v1, v2 = cls[ci].v2;

            int chosen;
            if (v1 == v2) {
                chosen = v1;
            } else if (rng() < RAND_TH) {
                chosen = (rng() & 1) ? v1 : v2;
            } else {
                int b1 = breakCnt[v1], b2 = breakCnt[v2];
                if (b1 < b2) chosen = v1;
                else if (b2 < b1) chosen = v2;
                else {
                    int g1 = makeCnt[v1] - breakCnt[v1];
                    int g2 = makeCnt[v2] - breakCnt[v2];
                    if (g1 > g2) chosen = v1;
                    else if (g2 > g1) chosen = v2;
                    else chosen = (rng() & 1) ? v1 : v2;
                }
            }

            flipVar(chosen);
            if (curSat > bestSat) {
                bestSat = curSat;
                bestVal = val;
                if (bestSat == m) break;
            }
        }

        if (bestSat == m) break;
    }

    for (int i = 1; i <= n; i++) {
        cout << int(bestVal[i]) << (i == n ? '\n' : ' ');
    }
    return 0;
}