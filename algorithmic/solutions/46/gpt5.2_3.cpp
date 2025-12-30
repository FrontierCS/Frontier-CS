#include <bits/stdc++.h>
using namespace std;

using ll = long long;

struct SplitMix64 {
    uint64_t x;
    explicit SplitMix64(uint64_t seed = 0) : x(seed) {}
    uint64_t next() {
        uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    uint64_t operator()() { return next(); }
    uint64_t nextU64(uint64_t lim) { return lim ? next() % lim : 0; }
    int nextInt(int lim) { return lim ? int(next() % (uint64_t)lim) : 0; }
    double nextDouble() { return (next() >> 11) * (1.0 / 9007199254740992.0); }
};

struct Param {
    ll wP = 0, wR = 0, wL = 0, wO = 0;
    bool maximize = false;
    bool randomPick = false;
};

static int J, M, N;
static vector<vector<int>> mach;
static vector<vector<ll>> ptime;
static vector<vector<ll>> remsum;
static vector<vector<int>> opIndex;
static vector<ll> machineLoad;
static vector<ll> nodeDur;

static vector<array<int,2>> succs;
static vector<unsigned char> outdeg;
static vector<int> indeg;
static vector<ll> predMaxC;
static vector<ll> compl;

static inline void addEdge(int u, int v) {
    succs[u][outdeg[u]++] = v;
    ++indeg[v];
}

static ll computeMakespan(const vector<vector<int>>& order, bool &acyclic) {
    for (int u = 0; u < N; ++u) {
        outdeg[u] = 0;
        indeg[u] = 0;
        predMaxC[u] = 0;
    }

    // Job precedence edges
    for (int j = 0; j < J; ++j) {
        int base = j * M;
        for (int k = 0; k + 1 < M; ++k) {
            addEdge(base + k, base + k + 1);
        }
    }

    // Machine order edges
    for (int m = 0; m < M; ++m) {
        const auto &line = order[m];
        for (int t = 0; t + 1 < J; ++t) {
            int j1 = line[t];
            int j2 = line[t + 1];
            int u = j1 * M + opIndex[j1][m];
            int v = j2 * M + opIndex[j2][m];
            addEdge(u, v);
        }
    }

    deque<int> q;
    q.clear();
    for (int u = 0; u < N; ++u) if (indeg[u] == 0) q.push_back(u);

    int processed = 0;
    ll makespan = 0;

    while (!q.empty()) {
        int u = q.front();
        q.pop_front();
        ++processed;

        ll cu = predMaxC[u] + nodeDur[u];
        compl[u] = cu;
        if (cu > makespan) makespan = cu;

        for (int i = 0; i < (int)outdeg[u]; ++i) {
            int v = succs[u][i];
            if (predMaxC[v] < cu) predMaxC[v] = cu;
            if (--indeg[v] == 0) q.push_back(v);
        }
    }

    acyclic = (processed == N);
    if (!acyclic) return (ll)4e18;
    return makespan;
}

static inline __int128 metricFor(const Param& par, int j, int k, int m) {
    ll p = ptime[j][k];
    ll r = remsum[j][k];
    ll l = machineLoad[m];
    ll o = (ll)(M - k);
    __int128 met = 0;
    met += (__int128)par.wP * p;
    met += (__int128)par.wR * r;
    met += (__int128)par.wL * l;
    met += (__int128)par.wO * o;
    return met;
}

static void buildSchedule(const Param& par, SplitMix64& rng, vector<vector<int>>& order) {
    order.assign(M, {});
    for (int m = 0; m < M; ++m) order[m].reserve(J);

    vector<int> idx(J, 0);
    vector<ll> jobReady(J, 0), macReady(M, 0);

    for (int step = 0; step < N; ++step) {
        ll minEst = LLONG_MAX;
        int bestJ = -1;
        __int128 bestMet = 0;
        int cntMin = 0;

        for (int j = 0; j < J; ++j) {
            int k = idx[j];
            if (k >= M) continue;
            int m = mach[j][k];
            ll est = jobReady[j] > macReady[m] ? jobReady[j] : macReady[m];

            if (est < minEst) {
                minEst = est;
                bestJ = j;
                cntMin = 1;
                if (!par.randomPick) bestMet = metricFor(par, j, k, m);
            } else if (est == minEst) {
                if (par.randomPick) {
                    ++cntMin;
                    if ((int)(rng.nextU64((uint64_t)cntMin)) == 0) bestJ = j;
                } else {
                    __int128 met = metricFor(par, j, k, m);
                    bool better = par.maximize ? (met > bestMet) : (met < bestMet);
                    if (better || (met == bestMet && (rng() & 1ULL))) {
                        bestJ = j;
                        bestMet = met;
                    }
                }
            }
        }

        int k = idx[bestJ];
        int m = mach[bestJ][k];
        ll start = jobReady[bestJ] > macReady[m] ? jobReady[bestJ] : macReady[m];
        ll finish = start + ptime[bestJ][k];
        jobReady[bestJ] = finish;
        macReady[m] = finish;
        idx[bestJ]++;

        order[m].push_back(bestJ);
    }

    // Ensure each machine line has size J (should hold).
    for (int m = 0; m < M; ++m) {
        if ((int)order[m].size() != J) {
            // Fallback: fill missing with unused jobs
            vector<char> used(J, 0);
            for (int x : order[m]) if (0 <= x && x < J) used[x] = 1;
            for (int j = 0; j < J; ++j) if (!used[j]) order[m].push_back(j);
            if ((int)order[m].size() > J) order[m].resize(J);
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> J >> M;
    N = J * M;

    mach.assign(J, vector<int>(M));
    ptime.assign(J, vector<ll>(M));
    remsum.assign(J, vector<ll>(M + 1, 0));
    opIndex.assign(J, vector<int>(M, -1));
    machineLoad.assign(M, 0);
    nodeDur.assign(N, 0);

    uint64_t seed = 1469598103934665603ULL;

    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            int m;
            ll p;
            cin >> m >> p;
            mach[j][k] = m;
            ptime[j][k] = p;
            opIndex[j][m] = k;
            machineLoad[m] += p;
            nodeDur[j * M + k] = p;

            seed ^= (uint64_t)m + 0x9e3779b97f4a7c15ULL + (seed << 6) + (seed >> 2);
            seed ^= (uint64_t)p + 0x9e3779b97f4a7c15ULL + (seed << 6) + (seed >> 2);
        }
    }

    for (int j = 0; j < J; ++j) {
        remsum[j][M] = 0;
        for (int k = M - 1; k >= 0; --k) remsum[j][k] = remsum[j][k + 1] + ptime[j][k];
    }

    succs.assign(N, { -1, -1 });
    outdeg.assign(N, 0);
    indeg.assign(N, 0);
    predMaxC.assign(N, 0);
    compl.assign(N, 0);

    SplitMix64 rng(seed ^ 0x123456789abcdef0ULL);

    vector<vector<int>> bestOrder;
    ll bestMs = (ll)4e18;

    auto consider = [&](const vector<vector<int>>& order) {
        bool ac = false;
        ll ms = computeMakespan(order, ac);
        if (ac && ms < bestMs) {
            bestMs = ms;
            bestOrder = order;
        }
    };

    vector<Param> fixedParams;
    fixedParams.push_back({1,0,0,0,false,false}); // SPT on min-est set
    fixedParams.push_back({1,0,0,0,true,false});  // LPT
    fixedParams.push_back({0,1,0,0,false,false}); // min remaining
    fixedParams.push_back({0,1,0,0,true,false});  // max remaining (MWKR)
    fixedParams.push_back({0,0,1,0,false,false}); // min bottleneck load
    fixedParams.push_back({0,0,1,0,true,false});  // max bottleneck load
    fixedParams.push_back({1,1,0,0,false,false});
    fixedParams.push_back({1,1,1,0,false,false});
    fixedParams.push_back({1,1,1,1,false,false});
    fixedParams.push_back({0,0,0,0,false,true});  // random among min-est

    vector<vector<int>> order;

    for (const auto& par : fixedParams) {
        buildSchedule(par, rng, order);
        consider(order);
    }

    int baseRuns;
    if (N <= 400) baseRuns = 1200;
    else if (N <= 800) baseRuns = 900;
    else baseRuns = 700;

    for (int it = 0; it < baseRuns; ++it) {
        Param par;
        uint64_t r = rng();
        par.randomPick = (r % 20 == 0);
        par.maximize = ((r >> 8) & 1ULL);

        int maxW = 30;
        par.wP = (ll)(rng.nextU64(maxW + 1));
        par.wR = (ll)(rng.nextU64(maxW + 1));
        par.wL = (ll)(rng.nextU64(maxW + 1));
        par.wO = (ll)(rng.nextU64(maxW + 1));

        if (par.wP == 0 && par.wR == 0 && par.wL == 0 && par.wO == 0) par.wP = 1;

        buildSchedule(par, rng, order);
        consider(order);
    }

    if (bestOrder.empty()) {
        // Absolute fallback
        bestOrder.assign(M, vector<int>(J));
        for (int m = 0; m < M; ++m) {
            iota(bestOrder[m].begin(), bestOrder[m].end(), 0);
        }
    }

    // Local search: random adjacent swaps with occasional uphill acceptance
    vector<vector<int>> curOrder = bestOrder;
    bool ac = false;
    ll curMs = computeMakespan(curOrder, ac);
    if (!ac) curMs = bestMs;

    int maxSwaps = (N <= 400 ? 25000 : (N <= 800 ? 18000 : 14000));
    for (int it = 0; it < maxSwaps; ++it) {
        int m = rng.nextInt(M);
        int i = rng.nextInt(max(1, J - 1));
        if (J <= 1) break;

        swap(curOrder[m][i], curOrder[m][i + 1]);
        bool ac2 = false;
        ll ms2 = computeMakespan(curOrder, ac2);

        bool accept = false;
        if (ac2) {
            if (ms2 <= curMs) accept = true;
            else {
                // small chance to accept worse
                accept = (rng.nextU64(1000) < 6); // 0.6%
            }
        }

        if (!accept) {
            swap(curOrder[m][i], curOrder[m][i + 1]);
        } else {
            curMs = ms2;
            if (ms2 < bestMs) {
                bestMs = ms2;
                bestOrder = curOrder;
            }
        }
    }

    for (int m = 0; m < M; ++m) {
        for (int i = 0; i < J; ++i) {
            if (i) cout << ' ';
            cout << bestOrder[m][i];
        }
        cout << "\n";
    }

    return 0;
}