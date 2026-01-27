#include <bits/stdc++.h>
using namespace std;

struct SplitMix64 {
    uint64_t x;
    explicit SplitMix64(uint64_t seed = 0) : x(seed) {}
    uint64_t nextU64() {
        uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    uint32_t nextU32() { return (uint32_t)nextU64(); }
    int nextInt(int lo, int hi) { // inclusive
        return lo + (int)(nextU64() % (uint64_t)(hi - lo + 1));
    }
    double nextDouble() { // [0,1)
        return (nextU64() >> 11) * (1.0 / 9007199254740992.0);
    }
};

struct Clause {
    int v1, v2;
    uint8_t s1, s2; // literal true iff val[v]==s (s=1 for positive, 0 for negative)
};

struct Occ {
    int cid;
    uint8_t s;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;

    vector<Clause> clauses(m);
    vector<vector<Occ>> occs(n);
    occs.assign(n, {});
    for (int i = 0; i < m; i++) {
        int a, b;
        cin >> a >> b;
        int va = abs(a) - 1;
        int vb = abs(b) - 1;
        uint8_t sa = (a > 0) ? 1 : 0;
        uint8_t sb = (b > 0) ? 1 : 0;
        clauses[i] = {va, vb, sa, sb};
        occs[va].push_back({i, sa});
        occs[vb].push_back({i, sb});
    }

    if (m == 0) {
        for (int i = 0; i < n; i++) {
            if (i) cout << ' ';
            cout << 0;
        }
        cout << '\n';
        return 0;
    }

    vector<uint8_t> val(n, 0), bestVal(n, 0);
    vector<uint8_t> trueCnt(m, 0);

    vector<int> unsat;
    unsat.reserve(m);
    vector<int> posInUnsat(m, -1);

    auto addUnsat = [&](int cid) {
        if (posInUnsat[cid] != -1) return;
        posInUnsat[cid] = (int)unsat.size();
        unsat.push_back(cid);
    };
    auto remUnsat = [&](int cid) {
        int p = posInUnsat[cid];
        if (p == -1) return;
        int last = unsat.back();
        unsat[p] = last;
        posInUnsat[last] = p;
        unsat.pop_back();
        posInUnsat[cid] = -1;
    };

    long long satisfied = 0, bestSatisfied = -1;

    vector<int> seen(m, 0);
    vector<uint8_t> tmp(m, 0);
    int stamp = 1;

    auto computeDelta = [&](int v) -> int {
        if (++stamp == INT_MAX) {
            fill(seen.begin(), seen.end(), 0);
            stamp = 1;
        }
        int delta = 0;
        uint8_t cur = val[v];
        for (const auto &oc : occs[v]) {
            int cid = oc.cid;
            if (seen[cid] != stamp) {
                seen[cid] = stamp;
                tmp[cid] = trueCnt[cid];
            }
            bool before = tmp[cid] > 0;
            int litDelta = (cur == oc.s) ? -1 : +1; // flipping v toggles this literal
            tmp[cid] = (uint8_t)((int)tmp[cid] + litDelta);
            bool after = tmp[cid] > 0;
            if (before != after) delta += after ? 1 : -1;
        }
        return delta;
    };

    auto flipVar = [&](int v) {
        uint8_t oldv = val[v];
        uint8_t newv = oldv ^ 1;
        val[v] = newv;

        for (const auto &oc : occs[v]) {
            int cid = oc.cid;
            bool beforeSat = trueCnt[cid] > 0;

            bool oldTruth = (oldv == oc.s);
            bool newTruth = (newv == oc.s);
            if (oldTruth == newTruth) continue;

            if (oldTruth) trueCnt[cid]--;
            else trueCnt[cid]++;

            bool afterSat = trueCnt[cid] > 0;
            if (beforeSat != afterSat) {
                if (afterSat) {
                    satisfied++;
                    remUnsat(cid);
                } else {
                    satisfied--;
                    addUnsat(cid);
                }
            }
        }
    };

    auto initRandom = [&](SplitMix64 &rng) {
        for (int i = 0; i < n; i++) val[i] = (uint8_t)(rng.nextU64() & 1ULL);

        satisfied = 0;
        unsat.clear();
        fill(posInUnsat.begin(), posInUnsat.end(), -1);

        for (int cid = 0; cid < m; cid++) {
            const auto &c = clauses[cid];
            uint8_t cnt = (uint8_t)((val[c.v1] == c.s1) + (val[c.v2] == c.s2));
            trueCnt[cid] = cnt;
            if (cnt > 0) {
                satisfied++;
            } else {
                addUnsat(cid);
            }
        }
    };

    auto greedyPass = [&]() {
        for (int v = 0; v < n; v++) {
            int d = computeDelta(v);
            if (d > 0) flipVar(v);
        }
    };

    auto start = chrono::steady_clock::now();
    auto elapsedSec = [&]() -> double {
        return chrono::duration<double>(chrono::steady_clock::now() - start).count();
    };

    double TL = 1.85; // safe default
    SplitMix64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count() ^ (uint64_t)(uintptr_t)&rng);

    int restarts = 0;
    while (elapsedSec() < TL) {
        initRandom(rng);
        greedyPass();

        if (satisfied > bestSatisfied) {
            bestSatisfied = satisfied;
            bestVal = val;
            if (bestSatisfied == m) break;
        }

        const double noise = 0.25;
        int maxSteps = 250000; // time-limited anyway
        for (int step = 0; step < maxSteps && elapsedSec() < TL; step++) {
            if (unsat.empty()) break;

            int cid = unsat[(size_t)(rng.nextU64() % (uint64_t)unsat.size())];
            const auto &c = clauses[cid];
            int vA = c.v1, vB = c.v2;

            int chosen;
            if (vA == vB) {
                chosen = vA;
            } else if (rng.nextDouble() < noise) {
                chosen = (rng.nextU64() & 1ULL) ? vA : vB;
            } else {
                int dA = computeDelta(vA);
                int dB = computeDelta(vB);
                if (dA > dB) chosen = vA;
                else if (dB > dA) chosen = vB;
                else chosen = (rng.nextU64() & 1ULL) ? vA : vB;
            }

            flipVar(chosen);

            if (satisfied > bestSatisfied) {
                bestSatisfied = satisfied;
                bestVal = val;
                if (bestSatisfied == m) break;
            }
        }

        restarts++;
        if (bestSatisfied == m) break;
    }

    for (int i = 0; i < n; i++) {
        if (i) cout << ' ';
        cout << (int)bestVal[i];
    }
    cout << '\n';
    return 0;
}