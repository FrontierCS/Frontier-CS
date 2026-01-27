#include <bits/stdc++.h>
using namespace std;

static inline uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

struct FastRNG {
    uint64_t x;
    FastRNG() {
        uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
        x = splitmix64(seed);
    }
    inline uint64_t nextU64() { return x = splitmix64(x); }
    inline uint32_t nextU32() { return (uint32_t)nextU64(); }
    inline int nextInt(int mod) { return (int)(nextU64() % (uint64_t)mod); }
    inline bool nextBit() { return (bool)(nextU64() & 1ULL); }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;

    vector<int> A(m), B(m);
    vector<vector<int>> adj(n + 1);
    adj.shrink_to_fit();

    for (int i = 0; i < m; i++) {
        int a, b;
        cin >> a >> b;
        A[i] = a;
        B[i] = b;
        adj[abs(a)].push_back(i);
        adj[abs(b)].push_back(i);
    }

    if (m == 0) {
        for (int i = 1; i <= n; i++) {
            if (i > 1) cout << ' ';
            cout << 0;
        }
        cout << "\n";
        return 0;
    }

    FastRNG rng;

    vector<unsigned char> satCount(m);
    vector<int> pos(m, -1);
    vector<int> unsat;
    unsat.reserve(m);

    vector<int> mark(m, 0);
    int stamp = 0;

    vector<char> assign(n + 1, 0), bestAssign(n + 1, 0);
    int satisfied = 0, bestSatisfied = -1;

    auto litTrue = [&](int lit, const vector<char>& asg) -> bool {
        int v = abs(lit);
        bool val = (asg[v] != 0);
        return (lit > 0) ? val : !val;
    };

    auto clauseCount = [&](int i, const vector<char>& asg) -> unsigned char {
        return (unsigned char)((litTrue(A[i], asg) ? 1 : 0) + (litTrue(B[i], asg) ? 1 : 0));
    };

    auto addUnsat = [&](int i) {
        pos[i] = (int)unsat.size();
        unsat.push_back(i);
    };
    auto removeUnsat = [&](int i) {
        int p = pos[i];
        if (p < 0) return;
        int last = unsat.back();
        unsat[p] = last;
        pos[last] = p;
        unsat.pop_back();
        pos[i] = -1;
    };
    auto syncUnsat = [&](int i) {
        if (satCount[i] == 0) {
            if (pos[i] < 0) addUnsat(i);
        } else {
            if (pos[i] >= 0) removeUnsat(i);
        }
    };

    auto computeDelta = [&](int v) -> int {
        bool cur = (assign[v] != 0);
        bool flipVal = !cur;
        int delta = 0;
        ++stamp;
        for (int ci : adj[v]) {
            if (mark[ci] == stamp) continue;
            mark[ci] = stamp;

            bool oldSat = satCount[ci] > 0;

            auto litTrueHypo = [&](int lit) -> bool {
                int var = abs(lit);
                bool val = (var == v) ? flipVal : (assign[var] != 0);
                return (lit > 0) ? val : !val;
            };

            bool newSat = litTrueHypo(A[ci]) || litTrueHypo(B[ci]);
            delta += (int)newSat - (int)oldSat;
        }
        return delta;
    };

    auto flipVar = [&](int v) {
        assign[v] ^= 1;
        ++stamp;
        for (int ci : adj[v]) {
            if (mark[ci] == stamp) continue;
            mark[ci] = stamp;

            bool oldSat = satCount[ci] > 0;
            unsigned char nc = (unsigned char)(
                (litTrue(A[ci], assign) ? 1 : 0) + (litTrue(B[ci], assign) ? 1 : 0)
            );
            satCount[ci] = nc;
            bool newSat = nc > 0;

            if (oldSat && !newSat) --satisfied;
            else if (!oldSat && newSat) ++satisfied;

            syncUnsat(ci);
        }
    };

    const double TIME_LIMIT_SEC = 0.95;
    auto tStart = chrono::steady_clock::now();

    auto timeExceeded = [&]() -> bool {
        chrono::duration<double> dt = chrono::steady_clock::now() - tStart;
        return dt.count() >= TIME_LIMIT_SEC;
    };

    int restarts = 0;
    while (!timeExceeded()) {
        ++restarts;

        for (int v = 1; v <= n; v++) assign[v] = rng.nextBit() ? 1 : 0;

        unsat.clear();
        fill(pos.begin(), pos.end(), -1);

        satisfied = 0;
        for (int i = 0; i < m; i++) {
            unsigned char c = clauseCount(i, assign);
            satCount[i] = c;
            if (c == 0) addUnsat(i);
            else ++satisfied;
        }

        if (satisfied > bestSatisfied) {
            bestSatisfied = satisfied;
            bestAssign = assign;
            if (bestSatisfied == m) break;
        }

        int maxSteps = max(20000, 50 * n);
        for (int step = 0; step < maxSteps && !unsat.empty(); step++) {
            if ((step & 255) == 0 && timeExceeded()) break;

            int ci = unsat[rng.nextInt((int)unsat.size())];
            int v1 = abs(A[ci]);
            int v2 = abs(B[ci]);

            int chosenV;
            if (v1 == v2) {
                chosenV = v1;
            } else {
                if ((rng.nextU32() % 1000) < 300) {
                    chosenV = (rng.nextBit() ? v1 : v2);
                } else {
                    int d1 = computeDelta(v1);
                    int d2 = computeDelta(v2);
                    if (d1 > d2) chosenV = v1;
                    else if (d2 > d1) chosenV = v2;
                    else chosenV = (rng.nextBit() ? v1 : v2);
                }
            }

            flipVar(chosenV);

            if (satisfied > bestSatisfied) {
                bestSatisfied = satisfied;
                bestAssign = assign;
                if (bestSatisfied == m) break;
            }
        }

        if (bestSatisfied == m) break;
    }

    for (int i = 1; i <= n; i++) {
        if (i > 1) cout << ' ';
        cout << (bestAssign[i] ? 1 : 0);
    }
    cout << "\n";
    return 0;
}