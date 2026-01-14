#include <bits/stdc++.h>
using namespace std;

struct SplitMix64 {
    uint64_t x;
    explicit SplitMix64(uint64_t seed = 0) : x(seed) {}
    uint64_t next() {
        uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    uint64_t next(uint64_t mod) { return mod ? next() % mod : 0; }
    uint32_t nextU32() { return (uint32_t)next(); }
};

struct Occ {
    int cl;
    int lit; // signed literal
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;
    if (!cin) return 0;

    if (m == 0) {
        for (int i = 0; i < n; i++) {
            if (i) cout << ' ';
            cout << 0;
        }
        cout << '\n';
        return 0;
    }

    vector<array<int, 3>> clauses(m);
    vector<vector<Occ>> occ(n);
    occ.reserve(n);

    for (int i = 0; i < m; i++) {
        int a, b, c;
        cin >> a >> b >> c;
        clauses[i] = {a, b, c};
        int lits[3] = {a, b, c};
        for (int k = 0; k < 3; k++) {
            int lit = lits[k];
            int v = abs(lit) - 1;
            occ[v].push_back({i, lit});
        }
    }

    uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    seed ^= (uint64_t)(uintptr_t)&seed;
    SplitMix64 rng(seed);

    vector<uint8_t> val(n), bestVal(n);
    vector<uint8_t> isUnsat(m, 0);
    vector<int> posInUnsat(m, -1);
    vector<int> unsatList;
    unsatList.reserve(m);

    vector<int8_t> tcount(m, 0);

    vector<int> mark(m, 0);
    vector<int8_t> tmpDelta(m, 0);
    int stamp = 1;

    int sat = 0;
    int bestSat = -1;

    auto addUnsat = [&](int cl) {
        if (isUnsat[cl]) return;
        isUnsat[cl] = 1;
        posInUnsat[cl] = (int)unsatList.size();
        unsatList.push_back(cl);
    };
    auto removeUnsat = [&](int cl) {
        if (!isUnsat[cl]) return;
        int p = posInUnsat[cl];
        int last = unsatList.back();
        unsatList[p] = last;
        posInUnsat[last] = p;
        unsatList.pop_back();
        isUnsat[cl] = 0;
        posInUnsat[cl] = -1;
    };

    auto initRandom = [&]() {
        for (int i = 0; i < n; i++) val[i] = (uint8_t)(rng.next() & 1ULL);

        unsatList.clear();
        sat = 0;
        for (int i = 0; i < m; i++) {
            int cnt = 0;
            auto &cl = clauses[i];
            for (int k = 0; k < 3; k++) {
                int lit = cl[k];
                int v = abs(lit) - 1;
                bool truth = (lit > 0) ? (val[v] != 0) : (val[v] == 0);
                cnt += truth ? 1 : 0;
            }
            tcount[i] = (int8_t)cnt;
            if (cnt == 0) {
                isUnsat[i] = 1;
                posInUnsat[i] = (int)unsatList.size();
                unsatList.push_back(i);
            } else {
                isUnsat[i] = 0;
                posInUnsat[i] = -1;
                sat++;
            }
        }
    };

    auto flipVar = [&](int v) {
        uint8_t oldVal = val[v];
        uint8_t newVal = oldVal ^ 1U;

        for (const auto &o : occ[v]) {
            int cl = o.cl;
            int lit = o.lit;

            bool oldLitTrue = (lit > 0) ? (oldVal != 0) : (oldVal == 0);
            int before = (int)tcount[cl];

            if (oldLitTrue) tcount[cl]--;
            else tcount[cl]++;

            int after = (int)tcount[cl];

            if (before == 0 && after > 0) {
                sat++;
                removeUnsat(cl);
            } else if (before > 0 && after == 0) {
                sat--;
                addUnsat(cl);
            }
        }

        val[v] = newVal;
    };

    vector<int> touched;
    touched.reserve(256);

    auto deltaSatIfFlip = [&](int v) -> int {
        if (++stamp == INT_MAX) {
            fill(mark.begin(), mark.end(), 0);
            stamp = 1;
        }
        touched.clear();

        uint8_t oldVal = val[v];
        for (const auto &o : occ[v]) {
            int cl = o.cl;
            if (mark[cl] != stamp) {
                mark[cl] = stamp;
                touched.push_back(cl);
                tmpDelta[cl] = 0;
            }
            int lit = o.lit;
            bool oldLitTrue = (lit > 0) ? (oldVal != 0) : (oldVal == 0);
            tmpDelta[cl] += (int8_t)(oldLitTrue ? -1 : +1);
        }

        int ds = 0;
        for (int cl : touched) {
            int before = (int)tcount[cl];
            int after = before + (int)tmpDelta[cl];
            if (before == 0 && after > 0) ds++;
            else if (before > 0 && after == 0) ds--;
            tmpDelta[cl] = 0;
        }
        return ds;
    };

    auto updateBest = [&]() {
        if (sat > bestSat) {
            bestSat = sat;
            bestVal = val;
        }
    };

    // Time limit (ms): keep conservative to avoid TLE under unknown limits
    const long long TIME_LIMIT_MS = 900;
    auto tStart = chrono::steady_clock::now();

    auto elapsedMs = [&]() -> long long {
        return chrono::duration_cast<chrono::milliseconds>(chrono::steady_clock::now() - tStart).count();
    };

    initRandom();
    updateBest();

    const int NOISE_PERCENT = 45; // random move probability
    const int MAX_STEPS_PER_RESTART = 120000;

    while (elapsedMs() < TIME_LIMIT_MS && bestSat < m) {
        initRandom();
        updateBest();

        for (int step = 0; step < MAX_STEPS_PER_RESTART; step++) {
            if (unsatList.empty()) break;
            if ((step & 63) == 0 && elapsedMs() >= TIME_LIMIT_MS) break;

            int clIdx = unsatList[(size_t)rng.next((uint64_t)unsatList.size())];
            auto &cl = clauses[clIdx];

            int vars[3] = {abs(cl[0]) - 1, abs(cl[1]) - 1, abs(cl[2]) - 1};
            int chosen = vars[0];

            if ((int)(rng.next(100)) < NOISE_PERCENT) {
                chosen = vars[(int)rng.next(3)];
            } else {
                int uniq[3];
                int u = 0;
                for (int i = 0; i < 3; i++) {
                    int v = vars[i];
                    bool seen = false;
                    for (int j = 0; j < u; j++) if (uniq[j] == v) { seen = true; break; }
                    if (!seen) uniq[u++] = v;
                }

                int bestD = INT_MIN;
                int cand[3];
                int cc = 0;
                for (int i = 0; i < u; i++) {
                    int v = uniq[i];
                    int d = deltaSatIfFlip(v);
                    if (d > bestD) {
                        bestD = d;
                        cc = 0;
                        cand[cc++] = v;
                    } else if (d == bestD) {
                        cand[cc++] = v;
                    }
                }
                chosen = cand[(int)rng.next((uint64_t)cc)];
            }

            flipVar(chosen);
            updateBest();
            if (bestSat == m) break;
        }
    }

    for (int i = 0; i < n; i++) {
        if (i) cout << ' ';
        cout << (int)bestVal[i];
    }
    cout << '\n';
    return 0;
}