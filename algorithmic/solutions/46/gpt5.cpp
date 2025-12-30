#include <bits/stdc++.h>
using namespace std;

using ll = long long;

struct JSSP {
    int J, M, N;
    vector<vector<pair<int,ll>>> jobRoute; // [J][M] -> (machine, proc)
    vector<vector<int>> opIdByJobIdx;      // [J][M] -> opId
    vector<vector<int>> opIdByJobMachine;  // [J][M] -> opId
    vector<int> jobOf, machOf, idxInJob;   // [N]
    vector<ll> pTime;                      // [N]
    vector<ll> sumProcJob;                 // [J]
    vector<ll> sumProcMachine;             // [M]
};

static inline void addEdge(vector<vector<int>>& adj, vector<int>& indeg, int u, int v) {
    adj[u].push_back(v);
    indeg[v]++;
}

struct Evaluator {
    JSSP* inst;
    Evaluator(JSSP* I): inst(I) {}

    bool evalOrders(const vector<vector<int>>& orders, ll& Cmax) {
        int N = inst->N, J = inst->J, M = inst->M;
        vector<vector<int>> adj(N);
        vector<int> indeg(N, 0);
        // Job edges
        for (int j = 0; j < J; ++j) {
            for (int k = 0; k + 1 < inst->M; ++k) {
                int u = inst->opIdByJobIdx[j][k];
                int v = inst->opIdByJobIdx[j][k+1];
                addEdge(adj, indeg, u, v);
            }
        }
        // Machine edges
        for (int m = 0; m < M; ++m) {
            int prev = -1;
            for (int i = 0; i < J; ++i) {
                int j = orders[m][i];
                int u = inst->opIdByJobMachine[j][m];
                if (prev != -1) addEdge(adj, indeg, prev, u);
                prev = u;
            }
        }
        deque<int> dq;
        vector<ll> est(N, 0);
        for (int i = 0; i < N; ++i) if (indeg[i] == 0) dq.push_back(i);
        int cnt = 0;
        ll maxEF = 0;
        while (!dq.empty()) {
            int u = dq.front(); dq.pop_front();
            cnt++;
            ll ef = est[u] + inst->pTime[u];
            if (ef > maxEF) maxEF = ef;
            for (int v: adj[u]) {
                if (est[v] < ef) est[v] = ef;
                if (--indeg[v] == 0) dq.push_back(v);
            }
        }
        if (cnt != N) return false; // cycle
        Cmax = maxEF;
        return true;
    }
};

struct GTBuilder {
    JSSP* inst;
    mt19937_64 rng;
    GTBuilder(JSSP* I): inst(I) {
        uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
        rng.seed(seed ^ (uint64_t)(uintptr_t)this);
    }

    int chooseByRule(const vector<int>& S, int mstar, const vector<ll>& jobReady, const vector<ll>& machReady,
                     const vector<int>& nextIdx, const vector<ll>& rem, int ruleType) {
        if (S.empty()) return -1;
        if (ruleType == 5) { // random
            uniform_int_distribution<int> dist(0, (int)S.size()-1);
            return S[dist(rng)];
        }
        double bestVal = numeric_limits<double>::infinity();
        int bestJob = S[0];
        for (int j: S) {
            int k = nextIdx[j];
            ll p = inst->jobRoute[j][k].second;
            ll s = max(jobReady[j], machReady[mstar]);
            ll tail = rem[j] - p; // remaining after this op
            double val = 0.0;
            switch (ruleType) {
                case 0: // SPT
                    val = (double)p;
                    break;
                case 1: // LPT
                    val = -(double)p;
                    break;
                case 2: // MIN tail
                    val = (double)tail;
                    break;
                case 3: // MAX tail
                    val = -(double)tail;
                    break;
                case 4: // earliest job ready
                    val = (double)jobReady[j];
                    break;
                case 6: // earliest job completion (head + p + tail)
                    val = (double)(max(jobReady[j], machReady[mstar]) + p + tail);
                    break;
                default:
                    val = (double)p;
            }
            // small random noise to diversify tie-breaking
            val += uniform_real_distribution<double>(-1e-9, 1e-9)(rng);
            if (val < bestVal) {
                bestVal = val;
                bestJob = j;
            }
        }
        return bestJob;
    }

    vector<vector<int>> buildGT(int ruleType) {
        int J = inst->J, M = inst->M, N = inst->N;
        vector<vector<int>> order(M);
        vector<int> nextIdx(J, 0);
        vector<ll> jobReady(J, 0), machReady(M, 0);
        vector<ll> rem(J, 0);
        for (int j = 0; j < J; ++j) {
            ll s = 0;
            for (int k = 0; k < M; ++k) s += inst->jobRoute[j][k].second;
            rem[j] = s;
        }
        int scheduled = 0;
        vector<ll> candS(J, 0), candC(J, 0);
        vector<int> candM(J, -1);
        while (scheduled < N) {
            // compute earliest start and completion for next op of each job
            ll minC = (1LL<<62);
            int argj = -1;
            for (int j = 0; j < J; ++j) {
                if (nextIdx[j] >= M) { candM[j] = -1; continue; }
                int k = nextIdx[j];
                int m = inst->jobRoute[j][k].first;
                ll p = inst->jobRoute[j][k].second;
                ll s = max(jobReady[j], machReady[m]);
                ll c = s + p;
                candS[j] = s; candC[j] = c; candM[j] = m;
                if (c < minC) { minC = c; argj = j; }
            }
            int mstar = candM[argj];
            ll tstar = candC[argj];
            // build conflict set
            vector<int> S;
            for (int j = 0; j < J; ++j) {
                if (candM[j] == mstar) {
                    if (candS[j] < tstar) S.push_back(j);
                }
            }
            if (S.empty()) S.push_back(argj);
            int chosen = chooseByRule(S, mstar, jobReady, machReady, nextIdx, rem, ruleType);
            // schedule chosen
            int k = nextIdx[chosen];
            ll p = inst->jobRoute[chosen][k].second;
            ll s = max(jobReady[chosen], machReady[mstar]);
            ll f = s + p;
            order[mstar].push_back(chosen);
            jobReady[chosen] = f;
            machReady[mstar] = f;
            nextIdx[chosen] = k + 1;
            rem[chosen] -= p;
            scheduled++;
        }
        return order;
    }
};

struct LocalSearch {
    JSSP* inst;
    Evaluator* eval;
    mt19937_64 rng;
    LocalSearch(JSSP* I, Evaluator* E): inst(I), eval(E) {
        uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
        rng.seed(seed ^ 0x9e3779b97f4a7c15ULL);
    }

    void improveAdjacent(vector<vector<int>>& orders, ll& bestC, int maxPasses, double timeLimitSec) {
        auto t0 = chrono::high_resolution_clock::now();
        int passes = 0;
        int M = inst->M, J = inst->J;
        while (passes < maxPasses) {
            bool improved = false;
            vector<int> ms(M);
            iota(ms.begin(), ms.end(), 0);
            shuffle(ms.begin(), ms.end(), rng);
            for (int mm = 0; mm < M; ++mm) {
                int m = ms[mm];
                vector<int> idx(J);
                iota(idx.begin(), idx.end(), 0);
                shuffle(idx.begin(), idx.end(), rng);
                for (int it = 0; it < J-1; ++it) {
                    int i = idx[it];
                    if (i >= J-1) continue;
                    vector<vector<int>> cand = orders;
                    swap(cand[m][i], cand[m][i+1]);
                    ll c;
                    if (eval->evalOrders(cand, c)) {
                        if (c < bestC) {
                            orders.swap(cand);
                            bestC = c;
                            improved = true;
                            break;
                        }
                    }
                    auto now = chrono::high_resolution_clock::now();
                    double elapsed = chrono::duration<double>(now - t0).count();
                    if (elapsed > timeLimitSec) return;
                }
                if (improved) break;
            }
            if (!improved) break;
            passes++;
            auto now = chrono::high_resolution_clock::now();
            double elapsed = chrono::duration<double>(now - t0).count();
            if (elapsed > timeLimitSec) return;
        }
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    JSSP inst;
    if (!(cin >> inst.J >> inst.M)) {
        return 0;
    }
    int J = inst.J, M = inst.M;
    inst.N = J * M;
    inst.jobRoute.assign(J, vector<pair<int,ll>>(M));
    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            int m; long long p;
            cin >> m >> p;
            inst.jobRoute[j][k] = {m, p};
        }
    }
    inst.opIdByJobIdx.assign(J, vector<int>(M, -1));
    inst.opIdByJobMachine.assign(J, vector<int>(M, -1));
    inst.jobOf.resize(inst.N);
    inst.machOf.resize(inst.N);
    inst.idxInJob.resize(inst.N);
    inst.pTime.resize(inst.N);
    inst.sumProcJob.assign(J, 0);
    inst.sumProcMachine.assign(M, 0);
    int id = 0;
    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            int m = inst.jobRoute[j][k].first;
            ll p = inst.jobRoute[j][k].second;
            inst.jobOf[id] = j;
            inst.machOf[id] = m;
            inst.idxInJob[id] = k;
            inst.pTime[id] = p;
            inst.opIdByJobIdx[j][k] = id;
            inst.opIdByJobMachine[j][m] = id;
            inst.sumProcJob[j] += p;
            inst.sumProcMachine[m] += p;
            id++;
        }
    }

    Evaluator evaluator(&inst);
    GTBuilder builder(&inst);
    LocalSearch improver(&inst, &evaluator);

    // Baseline: same job order on all machines
    vector<vector<int>> bestOrders(M, vector<int>(J));
    for (int m = 0; m < M; ++m) {
        for (int j = 0; j < J; ++j) bestOrders[m][j] = j;
    }
    ll bestC;
    evaluator.evalOrders(bestOrders, bestC);

    // Multi-start GT with various rules
    vector<int> rules = {0,1,2,3,4,5,6};
    int runs = 60;
    for (int r = 0; r < runs; ++r) {
        int rule = rules[r % (int)rules.size()];
        auto ord = builder.buildGT(rule);
        ll c;
        if (evaluator.evalOrders(ord, c)) {
            if (c < bestC) {
                bestC = c;
                bestOrders.swap(ord);
            }
        }
    }

    // Local search improvement
    improver.improveAdjacent(bestOrders, bestC, 50, 1.2); // up to ~1.2s local search

    // Output orders
    for (int m = 0; m < M; ++m) {
        for (int i = 0; i < J; ++i) {
            if (i) cout << ' ';
            cout << bestOrders[m][i];
        }
        cout << '\n';
    }
    return 0;
}