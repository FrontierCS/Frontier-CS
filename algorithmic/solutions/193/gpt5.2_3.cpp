#include <bits/stdc++.h>
using namespace std;

struct Clause {
    int v1, v2;
    bool n1, n2;
};

struct RNG {
    uint64_t s;
    explicit RNG(uint64_t seed = 88172645463325252ull) : s(seed) {}
    inline uint64_t nextU64() {
        s ^= s << 7;
        s ^= s >> 9;
        return s;
    }
    inline uint32_t nextU32() { return (uint32_t)nextU64(); }
    inline int nextInt(int mod) { return (int)(nextU32() % (uint32_t)mod); }
};

static inline bool litTruth(uint8_t varVal, bool neg) {
    return neg ? !varVal : (bool)varVal;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<Clause> clauses;
    clauses.reserve(m);

    vector<vector<int>> occ(n + 1);
    occ.shrink_to_fit(); // no-op, but keeps intent clear

    for (int i = 0; i < m; i++) {
        int a, b;
        cin >> a >> b;
        Clause c;
        c.v1 = abs(a); c.n1 = (a < 0);
        c.v2 = abs(b); c.n2 = (b < 0);
        clauses.push_back(c);

        if (c.v1 == c.v2) {
            occ[c.v1].push_back(i);
        } else {
            occ[c.v1].push_back(i);
            occ[c.v2].push_back(i);
        }
    }

    vector<uint8_t> bestVal(n + 1, 0);
    int bestSat = -1;

    if (m == 0) {
        for (int i = 1; i <= n; i++) {
            if (i > 1) cout << ' ';
            cout << 0;
        }
        cout << '\n';
        return 0;
    }

    vector<uint8_t> val(n + 1, 0);
    vector<int> makeCnt(n + 1, 0), brkCnt(n + 1, 0);
    vector<int> unsatPos(m, -1);
    vector<int> unsatList;
    unsatList.reserve(m);

    auto addUnsat = [&](int ci) {
        if (unsatPos[ci] != -1) return;
        unsatPos[ci] = (int)unsatList.size();
        unsatList.push_back(ci);
    };
    auto removeUnsat = [&](int ci) {
        int p = unsatPos[ci];
        if (p == -1) return;
        int last = unsatList.back();
        unsatList[p] = last;
        unsatPos[last] = p;
        unsatList.pop_back();
        unsatPos[ci] = -1;
    };

    auto initState = [&](RNG &rng, int &satCnt) {
        for (int i = 1; i <= n; i++) val[i] = (uint8_t)(rng.nextU32() & 1u);
        fill(makeCnt.begin(), makeCnt.end(), 0);
        fill(brkCnt.begin(), brkCnt.end(), 0);
        fill(unsatPos.begin(), unsatPos.end(), -1);
        unsatList.clear();

        satCnt = 0;
        for (int i = 0; i < m; i++) {
            const Clause &c = clauses[i];
            bool t1 = litTruth(val[c.v1], c.n1);
            bool t2 = litTruth(val[c.v2], c.n2);
            bool sat = t1 || t2;
            if (sat) satCnt++;
            else addUnsat(i);

            auto processVar = [&](int u) {
                bool newt1 = (c.v1 == u) ? !t1 : t1;
                bool newt2 = (c.v2 == u) ? !t2 : t2;
                bool newsat = newt1 || newt2;
                if (sat && !newsat) brkCnt[u]++;
                if (!sat && newsat) makeCnt[u]++;
            };
            processVar(c.v1);
            if (c.v2 != c.v1) processVar(c.v2);
        }
    };

    auto flipVar = [&](int x, int &satCnt) {
        uint8_t oldVal = val[x];
        uint8_t newVal = oldVal ^ 1u;

        for (int ci : occ[x]) {
            const Clause &c = clauses[ci];

            bool t1_old = litTruth((c.v1 == x) ? oldVal : val[c.v1], c.n1);
            bool t2_old = litTruth((c.v2 == x) ? oldVal : val[c.v2], c.n2);
            bool sat_old = t1_old || t2_old;

            bool t1_new = (c.v1 == x) ? !t1_old : t1_old;
            bool t2_new = (c.v2 == x) ? !t2_old : t2_old;
            bool sat_new = t1_new || t2_new;

            if (sat_old && !sat_new) {
                satCnt--;
                addUnsat(ci);
            } else if (!sat_old && sat_new) {
                satCnt++;
                removeUnsat(ci);
            }

            auto processVarOld = [&](int u) {
                bool newt1 = (c.v1 == u) ? !t1_old : t1_old;
                bool newt2 = (c.v2 == u) ? !t2_old : t2_old;
                bool newsat = newt1 || newt2;
                if (sat_old && !newsat) brkCnt[u]--;
                if (!sat_old && newsat) makeCnt[u]--;
            };
            auto processVarNew = [&](int u) {
                bool newt1 = (c.v1 == u) ? !t1_new : t1_new;
                bool newt2 = (c.v2 == u) ? !t2_new : t2_new;
                bool newsat = newt1 || newt2;
                if (sat_new && !newsat) brkCnt[u]++;
                if (!sat_new && newsat) makeCnt[u]++;
            };

            processVarOld(c.v1);
            if (c.v2 != c.v1) processVarOld(c.v2);

            processVarNew(c.v1);
            if (c.v2 != c.v1) processVarNew(c.v2);
        }

        val[x] = newVal;
    };

    uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    seed ^= (uint64_t)(uintptr_t)&seed;
    seed ^= (uint64_t)(uintptr_t)&clauses;
    RNG rng(seed);

    auto start = chrono::steady_clock::now();
    auto endTime = start + chrono::milliseconds(1850);

    const int maxStepsPerRestart = 200000;
    int globalBestPossible = m;

    while (chrono::steady_clock::now() < endTime) {
        int satCnt = 0;
        initState(rng, satCnt);

        if (satCnt > bestSat) {
            bestSat = satCnt;
            bestVal = val;
            if (bestSat == globalBestPossible) break;
        }

        for (int step = 0; step < maxStepsPerRestart; step++) {
            if (chrono::steady_clock::now() >= endTime) break;
            if (unsatList.empty()) break;

            int ci = unsatList[rng.nextInt((int)unsatList.size())];
            const Clause &c = clauses[ci];

            int chosen;
            if (c.v1 == c.v2) {
                chosen = c.v1;
            } else {
                int vA = c.v1, vB = c.v2;
                uint32_t r = rng.nextU32() % 100u;
                if (r < 30u) {
                    chosen = (rng.nextU32() & 1u) ? vA : vB;
                } else {
                    int dA = makeCnt[vA] - brkCnt[vA];
                    int dB = makeCnt[vB] - brkCnt[vB];
                    if (dA > dB) chosen = vA;
                    else if (dB > dA) chosen = vB;
                    else chosen = (rng.nextU32() & 1u) ? vA : vB;
                }
            }

            flipVar(chosen, satCnt);

            if (satCnt > bestSat) {
                bestSat = satCnt;
                bestVal = val;
                if (bestSat == globalBestPossible) break;
            }
        }

        if (bestSat == globalBestPossible) break;
    }

    for (int i = 1; i <= n; i++) {
        if (i > 1) cout << ' ';
        cout << (int)bestVal[i];
    }
    cout << '\n';
    return 0;
}