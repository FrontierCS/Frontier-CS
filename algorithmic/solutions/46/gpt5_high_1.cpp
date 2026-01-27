#include <bits/stdc++.h>
using namespace std;

using ll = long long;

struct Evaluator {
    int J, M, N;
    vector<int> jobPred, jobSucc, nodeMachine;
    vector<ll> proc;
    vector<vector<int>> posInJob; // [j][m] -> k
    // scratch
    vector<int> machPred, machSucc, indeg, q;
    vector<ll> ES;

    Evaluator(int J_, int M_,
              const vector<vector<int>>& routeMach,
              const vector<vector<ll>>& routeTime,
              const vector<vector<int>>& posInJob_)
        : J(J_), M(M_), N(J_*M_), jobPred(N, -1), jobSucc(N, -1),
          nodeMachine(N, -1), proc(N, 0), posInJob(posInJob_),
          machPred(N, -1), machSucc(N, -1), indeg(N, 0), ES(N, 0) {
        for (int j = 0; j < J; ++j) {
            for (int k = 0; k < M; ++k) {
                int id = j * M + k;
                nodeMachine[id] = routeMach[j][k];
                proc[id] = routeTime[j][k];
                if (k > 0) {
                    int pid = j * M + (k - 1);
                    jobPred[id] = pid;
                    jobSucc[pid] = id;
                }
            }
        }
    }

    ll evaluate(const vector<vector<int>>& seq) {
        // Build machine predecessor/successor
        fill(machPred.begin(), machPred.end(), -1);
        fill(machSucc.begin(), machSucc.end(), -1);
        for (int m = 0; m < M; ++m) {
            const auto& order = seq[m];
            if ((int)order.size() != J) return (ll)4e18; // invalid
            int prevId = -1;
            for (int pos = 0; pos < J; ++pos) {
                int j = order[pos];
                int k = posInJob[j][m];
                int id = j * M + k;
                if (prevId != -1) {
                    machSucc[prevId] = id;
                    machPred[id] = prevId;
                }
                prevId = id;
            }
        }
        // indegree
        for (int i = 0; i < N; ++i) {
            int d = 0;
            if (jobPred[i] != -1) d++;
            if (machPred[i] != -1) d++;
            indeg[i] = d;
            ES[i] = 0;
        }
        q.clear(); q.reserve(N);
        for (int i = 0; i < N; ++i) if (indeg[i] == 0) q.push_back(i);
        size_t qi = 0;
        int processed = 0;
        ll makespan = 0;
        while (qi < q.size()) {
            int u = q[qi++];
            processed++;
            ll comp = ES[u] + proc[u];
            if (comp > makespan) makespan = comp;
            int vs[2] = { jobSucc[u], machSucc[u] };
            for (int t = 0; t < 2; ++t) {
                int v = vs[t];
                if (v != -1) {
                    if (ES[v] < comp) ES[v] = comp;
                    if (--indeg[v] == 0) q.push_back(v);
                }
            }
        }
        if (processed != N) return (ll)4e18; // cycle -> infeasible
        return makespan;
    }
};

struct GTBuilder {
    int J, M, N;
    const vector<vector<int>>& routeMach;
    const vector<vector<ll>>& routeTime;
    const vector<vector<int>>& posInJob;
    vector<vector<ll>> remSum; // [j][k] sum p[k..M-1]
    mt19937_64 rng;

    GTBuilder(int J_, int M_,
              const vector<vector<int>>& routeMach_,
              const vector<vector<ll>>& routeTime_,
              const vector<vector<int>>& posInJob_)
        : J(J_), M(M_), N(J_*M_), routeMach(routeMach_), routeTime(routeTime_), posInJob(posInJob_) {
        remSum.assign(J, vector<ll>(M + 1, 0));
        for (int j = 0; j < J; ++j) {
            for (int k = M - 1; k >= 0; --k) {
                remSum[j][k] = remSum[j][k + 1] + routeTime[j][k];
            }
        }
        rng.seed(chrono::high_resolution_clock::now().time_since_epoch().count());
    }

    enum Rule { MWKR = 0, SRPT = 1, SPT = 2, LPT = 3, EST = 4, RND = 5 };

    vector<vector<int>> buildGT(Rule rule) {
        vector<vector<int>> seq(M);
        vector<int> kidx(J, 0);
        vector<ll> jobReady(J, 0), machReady(M, 0);

        for (int t = 0; t < N; ++t) {
            // Pick operation with minimum earliest completion time
            ll bestEComp = LLONG_MAX;
            int bestJ = -1, bestM = -1;
            ll bestEst = 0, bestP = 0;
            for (int j = 0; j < J; ++j) {
                if (kidx[j] >= M) continue;
                int m = routeMach[j][kidx[j]];
                ll p = routeTime[j][kidx[j]];
                ll est = max(jobReady[j], machReady[m]);
                ll ecomp = est + p;
                if (ecomp < bestEComp ||
                    (ecomp == bestEComp && (est < bestEst ||
                     (est == bestEst && (p < bestP ||
                      (p == bestP && j < bestJ))))))
                {
                    bestEComp = ecomp;
                    bestJ = j;
                    bestM = m;
                    bestEst = est;
                    bestP = p;
                }
            }
            int mStar = bestM;
            // Conflict set: ops on mStar with est < bestEComp
            vector<int> conf;
            conf.reserve(J);
            for (int j = 0; j < J; ++j) {
                if (kidx[j] >= M) continue;
                if (routeMach[j][kidx[j]] != mStar) continue;
                ll est = max(jobReady[j], machReady[mStar]);
                if (est < bestEComp) conf.push_back(j);
            }
            // Choose among conflict set
            int chosen = -1;
            if (conf.empty()) {
                chosen = bestJ; // fallback
            } else {
                if (rule == RND) {
                    uniform_int_distribution<int> dist(0, (int)conf.size() - 1);
                    chosen = conf[dist(rng)];
                } else {
                    // compute scores
                    auto better = [&](int a, int b)->bool {
                        int ka = kidx[a], kb = kidx[b];
                        ll pa = routeTime[a][ka], pb = routeTime[b][kb];
                        ll esta = max(jobReady[a], machReady[mStar]);
                        ll estb = max(jobReady[b], machReady[mStar]);
                        ll ra = remSum[a][ka], rb = remSum[b][kb];
                        switch (rule) {
                            case MWKR:
                                if (ra != rb) return ra > rb;
                                if (pa != pb) return pa > pb;
                                if (esta != estb) return esta < estb;
                                return a < b;
                            case SRPT:
                                if (ra != rb) return ra < rb;
                                if (pa != pb) return pa < pb;
                                if (esta != estb) return esta < estb;
                                return a < b;
                            case SPT:
                                if (pa != pb) return pa < pb;
                                if (esta != estb) return esta < estb;
                                if (ra != rb) return ra < rb;
                                return a < b;
                            case LPT:
                                if (pa != pb) return pa > pb;
                                if (esta != estb) return esta < estb;
                                if (ra != rb) return ra > rb;
                                return a < b;
                            case EST:
                                if (esta != estb) return esta < estb;
                                if (pa != pb) return pa < pb;
                                if (ra != rb) return ra < rb;
                                return a < b;
                            default:
                                return a < b;
                        }
                    };
                    chosen = conf[0];
                    for (size_t i = 1; i < conf.size(); ++i) {
                        int c = conf[i];
                        if (better(c, chosen)) chosen = c;
                    }
                }
            }
            // Schedule chosen on mStar
            int jSel = chosen;
            int k = kidx[jSel];
            ll p = routeTime[jSel][k];
            ll s = max(jobReady[jSel], machReady[mStar]);
            ll f = s + p;
            seq[mStar].push_back(jSel);
            jobReady[jSel] = f;
            kidx[jSel]++;
            machReady[mStar] = f;
        }
        return seq;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int J, M;
    if (!(cin >> J >> M)) return 0;
    vector<vector<int>> routeMach(J, vector<int>(M));
    vector<vector<ll>> routeTime(J, vector<ll>(M));
    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            int m; long long p;
            cin >> m >> p;
            routeMach[j][k] = m;
            routeTime[j][k] = p;
        }
    }
    vector<vector<int>> posInJob(J, vector<int>(M, -1));
    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            int m = routeMach[j][k];
            posInJob[j][m] = k;
        }
    }
    Evaluator evaluator(J, M, routeMach, routeTime, posInJob);
    GTBuilder builder(J, M, routeMach, routeTime, posInJob);

    auto now = chrono::high_resolution_clock::now;
    auto t_start = now();
    const double TIME_LIMIT = 0.95; // seconds
    auto elapsed = [&]() {
        return chrono::duration<double>(now() - t_start).count();
    };

    // Candidate solutions
    vector<vector<vector<int>>> candidates;
    vector<ll> candCost;

    // 1) GT with different rules
    vector<GTBuilder::Rule> rules = {
        GTBuilder::MWKR, GTBuilder::SRPT, GTBuilder::SPT,
        GTBuilder::LPT, GTBuilder::EST, GTBuilder::RND
    };
    for (auto r : rules) {
        auto seq = builder.buildGT(r);
        ll cost = evaluator.evaluate(seq);
        candidates.push_back(move(seq));
        candCost.push_back(cost);
        if (elapsed() > TIME_LIMIT * 0.5) break;
    }

    // 2) Flow-like: order by position in job (ascending)
    vector<vector<int>> flowSeq(M, vector<int>(J));
    for (int m = 0; m < M; ++m) {
        vector<pair<int,int>> arr;
        arr.reserve(J);
        for (int j = 0; j < J; ++j) {
            arr.emplace_back(posInJob[j][m], j);
        }
        sort(arr.begin(), arr.end());
        for (int i = 0; i < J; ++i) flowSeq[m][i] = arr[i].second;
    }
    {
        ll cost = evaluator.evaluate(flowSeq);
        candidates.push_back(flowSeq);
        candCost.push_back(cost);
    }

    // 3) Maybe reverse flow
    vector<vector<int>> flowRSeq = flowSeq;
    for (int m = 0; m < M; ++m) reverse(flowRSeq[m].begin(), flowRSeq[m].end());
    {
        ll cost = evaluator.evaluate(flowRSeq);
        candidates.push_back(flowRSeq);
        candCost.push_back(cost);
    }

    // Choose best
    int bestIdx = 0;
    for (int i = 1; i < (int)candidates.size(); ++i) {
        if (candCost[i] < candCost[bestIdx]) bestIdx = i;
    }
    vector<vector<int>> bestSeq = candidates[bestIdx];
    ll bestCost = candCost[bestIdx];

    // Local improvement: adjacent swaps
    // First-improvement hill climbing with time limit
    vector<vector<int>> curSeq = bestSeq;
    ll curCost = bestCost;
    bool improved = true;
    while (improved && elapsed() < TIME_LIMIT) {
        improved = false;
        for (int m = 0; m < M; ++m) {
            for (int i = 0; i + 1 < J; ++i) {
                if (elapsed() >= TIME_LIMIT) break;
                swap(curSeq[m][i], curSeq[m][i+1]);
                ll cost = evaluator.evaluate(curSeq);
                if (cost < curCost) {
                    curCost = cost;
                    if (curCost < bestCost) {
                        bestCost = curCost;
                        bestSeq = curSeq;
                    }
                    improved = true;
                } else {
                    swap(curSeq[m][i], curSeq[m][i+1]);
                }
            }
            if (elapsed() >= TIME_LIMIT) break;
        }
    }

    // Output best sequence
    for (int m = 0; m < M; ++m) {
        for (int i = 0; i < J; ++i) {
            if (i) cout << ' ';
            cout << bestSeq[m][i];
        }
        cout << '\n';
    }
    return 0;
}