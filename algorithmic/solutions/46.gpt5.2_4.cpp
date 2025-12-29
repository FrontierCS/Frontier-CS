#include <bits/stdc++.h>
using namespace std;

struct Weights {
    double wP, wRem, wEst;
};

struct Schedule {
    vector<vector<int>> order; // [machine][pos] -> job
    long long makespan = (1LL << 62);
};

static inline uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

struct RNG {
    uint64_t s;
    explicit RNG(uint64_t seed) : s(seed) {}
    uint32_t nextU32() { s = splitmix64(s); return (uint32_t)s; }
    double nextDouble01() { return (nextU32() + 0.5) * (1.0 / 4294967296.0); }
    double uniform(double a, double b) { return a + (b - a) * nextDouble01(); }
    int randInt(int l, int r) { return l + (int)(nextDouble01() * (double)(r - l + 1)); }
};

static long long evaluateMakespan(
    int J, int M,
    const vector<vector<int>>& machineOrder,
    const vector<vector<int>>& posInJob,
    const vector<long long>& opProc
) {
    const int V = J * M;
    const int Emax = J * (M - 1) + M * (J - 1);

    vector<int> head(V, -1);
    vector<int> to;
    vector<int> nxt;
    to.reserve(Emax);
    nxt.reserve(Emax);

    vector<int> indeg(V, 0);

    auto addEdge = [&](int u, int v) {
        int e = (int)to.size();
        to.push_back(v);
        nxt.push_back(head[u]);
        head[u] = e;
        indeg[v]++;
    };

    auto opId = [&](int j, int k) { return j * M + k; };

    // job edges
    for (int j = 0; j < J; j++) {
        for (int k = 0; k + 1 < M; k++) addEdge(opId(j, k), opId(j, k + 1));
    }

    // machine edges from permutations
    for (int m = 0; m < M; m++) {
        const auto& ord = machineOrder[m];
        for (int i = 0; i + 1 < J; i++) {
            int j1 = ord[i], j2 = ord[i + 1];
            int u = opId(j1, posInJob[j1][m]);
            int v = opId(j2, posInJob[j2][m]);
            addEdge(u, v);
        }
    }

    deque<int> q;
    q.clear();
    for (int v = 0; v < V; v++) if (indeg[v] == 0) q.push_back(v);

    vector<long long> start(V, 0);
    int cnt = 0;
    long long makespan = 0;

    while (!q.empty()) {
        int u = q.front();
        q.pop_front();
        cnt++;
        long long finish = start[u] + opProc[u];
        if (finish > makespan) makespan = finish;
        for (int e = head[u]; e != -1; e = nxt[e]) {
            int v = to[e];
            if (start[v] < finish) start[v] = finish;
            if (--indeg[v] == 0) q.push_back(v);
        }
    }

    if (cnt != V) return (1LL << 62); // cycle
    return makespan;
}

static Schedule constructGT(
    int J, int M,
    const vector<vector<int>>& machineOf,
    const vector<vector<long long>>& procOf,
    const vector<vector<long long>>& suffixWork,
    const vector<vector<int>>& posInJob,
    const vector<long long>& opProc,
    const Weights& w,
    RNG& rng
) {
    Schedule sched;
    sched.order.assign(M, {});
    for (int m = 0; m < M; m++) sched.order[m].reserve(J);

    vector<int> nextK(J, 0);
    vector<long long> jobReady(J, 0), machReady(M, 0);

    vector<int> mAvail(J), kAvail(J);
    vector<long long> pAvail(J), estAvail(J), ectAvail(J), remAvail(J);

    long long makespan = 0;
    const int totalOps = J * M;

    for (int step = 0; step < totalOps; step++) {
        long long bestEct = (1LL << 62);
        int starJ = -1;

        for (int j = 0; j < J; j++) {
            int k = nextK[j];
            if (k >= M) {
                mAvail[j] = -1;
                continue;
            }
            int m = machineOf[j][k];
            long long p = procOf[j][k];
            long long est = max(jobReady[j], machReady[m]);
            long long ect = est + p;

            mAvail[j] = m;
            kAvail[j] = k;
            pAvail[j] = p;
            estAvail[j] = est;
            ectAvail[j] = ect;
            remAvail[j] = suffixWork[j][k];

            if (ect < bestEct || (ect == bestEct && est < estAvail[starJ])) {
                bestEct = ect;
                starJ = j;
            }
        }

        int m0 = mAvail[starJ];
        long long t = bestEct;

        int chosenJ = -1;
        double bestPr = 1e300;

        for (int j = 0; j < J; j++) {
            if (mAvail[j] != m0) continue;
            if (estAvail[j] >= t) continue; // conflict set condition
            double pr = w.wP * (double)pAvail[j] + w.wRem * (double)remAvail[j] + w.wEst * (double)estAvail[j];
            pr += rng.uniform(0.0, 1.0) * 1e-9; // tie-break
            if (pr < bestPr) {
                bestPr = pr;
                chosenJ = j;
            }
        }

        // Should always have at least starJ in conflict set
        if (chosenJ == -1) chosenJ = starJ;

        int k = kAvail[chosenJ];
        int m = mAvail[chosenJ];
        long long st = estAvail[chosenJ];
        long long ft = st + pAvail[chosenJ];

        machReady[m] = ft;
        jobReady[chosenJ] = ft;
        sched.order[m].push_back(chosenJ);

        nextK[chosenJ]++;
        if (ft > makespan) makespan = ft;
    }

    // Consistency check + makespan from graph evaluation (also ensures feasibility)
    long long ms2 = evaluateMakespan(J, M, sched.order, posInJob, opProc);
    sched.makespan = ms2;
    return sched;
}

static void localImproveAdjacentSwaps(
    int J, int M,
    Schedule& best,
    const vector<vector<int>>& posInJob,
    const vector<long long>& opProc,
    chrono::steady_clock::time_point tEnd
) {
    int improvements = 0;
    const int maxImprovements = 400;

    while (improvements < maxImprovements && chrono::steady_clock::now() < tEnd) {
        bool improved = false;

        for (int m = 0; m < M && chrono::steady_clock::now() < tEnd; m++) {
            for (int i = 0; i + 1 < J && chrono::steady_clock::now() < tEnd; i++) {
                int a = best.order[m][i];
                int b = best.order[m][i + 1];
                if (a == b) continue;

                swap(best.order[m][i], best.order[m][i + 1]);
                long long ms = evaluateMakespan(J, M, best.order, posInJob, opProc);

                if (ms < best.makespan) {
                    best.makespan = ms;
                    improved = true;
                    improvements++;
                    break;
                } else {
                    swap(best.order[m][i], best.order[m][i + 1]);
                }
            }
            if (improved) break;
        }

        if (!improved) break;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int J, M;
    if (!(cin >> J >> M)) return 0;

    vector<vector<int>> machineOf(J, vector<int>(M));
    vector<vector<long long>> procOf(J, vector<long long>(M));
    vector<vector<int>> posInJob(J, vector<int>(M, -1));

    for (int j = 0; j < J; j++) {
        for (int k = 0; k < M; k++) {
            int m;
            long long p;
            cin >> m >> p;
            machineOf[j][k] = m;
            procOf[j][k] = p;
            posInJob[j][m] = k;
        }
    }

    vector<vector<long long>> suffixWork(J, vector<long long>(M + 1, 0));
    for (int j = 0; j < J; j++) {
        for (int k = M - 1; k >= 0; k--) suffixWork[j][k] = suffixWork[j][k + 1] + procOf[j][k];
    }

    const int V = J * M;
    vector<long long> opProc(V, 0);
    for (int j = 0; j < J; j++) {
        for (int k = 0; k < M; k++) opProc[j * M + k] = procOf[j][k];
    }

    uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    seed ^= (uint64_t)(uintptr_t)new int(1);
    RNG rng(seed);

    auto t0 = chrono::steady_clock::now();
    double TL = 0.95; // conservative
    auto tEnd = t0 + chrono::milliseconds((int)(TL * 1000));
    auto tConstructEnd = t0 + chrono::milliseconds((int)(TL * 800)); // ~80% construction

    vector<Weights> presets = {
        { 1.0,  0.0,  0.0}, // SPT
        {-1.0,  0.0,  0.0}, // LPT
        { 0.0, -1.0,  0.0}, // MWKR (maximize rem)
        { 0.0,  1.0,  0.0}, // LWKR
        { 0.6, -0.4,  0.02},
        { 0.2, -1.0,  0.05},
        { 1.0, -0.2,  0.01},
        {-0.3, -1.0,  0.02},
    };

    Schedule best;
    best.makespan = (1LL << 62);
    best.order.assign(M, vector<int>());

    // Always at least one schedule
    {
        Schedule s = constructGT(J, M, machineOf, procOf, suffixWork, posInJob, opProc, presets[0], rng);
        if (s.makespan < best.makespan) best = std::move(s);
    }

    for (const auto& w : presets) {
        if (chrono::steady_clock::now() >= tConstructEnd) break;
        Schedule s = constructGT(J, M, machineOf, procOf, suffixWork, posInJob, opProc, w, rng);
        if (s.makespan < best.makespan) best = std::move(s);
    }

    while (chrono::steady_clock::now() < tConstructEnd) {
        Weights w;
        w.wP = rng.uniform(-1.2, 1.2);
        w.wRem = rng.uniform(-1.2, 1.2);
        w.wEst = rng.uniform(0.0, 0.08);

        // Occasionally bias toward MWKR-ish
        if (rng.nextDouble01() < 0.25) {
            w.wRem = rng.uniform(-2.0, -0.2);
            w.wP = rng.uniform(-0.5, 0.9);
        }

        Schedule s = constructGT(J, M, machineOf, procOf, suffixWork, posInJob, opProc, w, rng);
        if (s.makespan < best.makespan) best = std::move(s);
    }

    localImproveAdjacentSwaps(J, M, best, posInJob, opProc, tEnd);

    // Output exactly M lines
    for (int m = 0; m < M; m++) {
        for (int i = 0; i < J; i++) {
            if (i) cout << ' ';
            cout << best.order[m][i];
        }
        cout << '\n';
    }
    return 0;
}