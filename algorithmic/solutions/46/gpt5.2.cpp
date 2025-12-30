#include <bits/stdc++.h>
using namespace std;

struct Evaluator {
    int J, M, N;
    vector<long long> pNode;
    vector<pair<int,int>> jobEdges;
    vector<vector<int>> opIndexByMachine;
    int maxE;

    vector<int> head, indeg, q;
    vector<int> to, nxt;
    vector<long long> dist;

    Evaluator(int J_, int M_, vector<long long> pNode_,
              vector<pair<int,int>> jobEdges_,
              vector<vector<int>> opIndexByMachine_)
        : J(J_), M(M_), N(J_*M_), pNode(std::move(pNode_)),
          jobEdges(std::move(jobEdges_)),
          opIndexByMachine(std::move(opIndexByMachine_))
    {
        maxE = (int)jobEdges.size() + M * max(0, J - 1) + 5;
        head.assign(N, -1);
        indeg.assign(N, 0);
        dist.assign(N, 0);
        q.assign(N, 0);
        to.assign(maxE, 0);
        nxt.assign(maxE, 0);
    }

    inline void addEdge(int u, int v, int &ec) {
        to[ec] = v;
        nxt[ec] = head[u];
        head[u] = ec++;
        indeg[v]++;
    }

    pair<bool, long long> eval(const vector<vector<int>> &order) {
        fill(head.begin(), head.end(), -1);
        fill(indeg.begin(), indeg.end(), 0);
        copy(pNode.begin(), pNode.end(), dist.begin());
        int ec = 0;

        for (auto [u, v] : jobEdges) addEdge(u, v, ec);

        for (int m = 0; m < M; m++) {
            const auto &seq = order[m];
            for (int i = 0; i + 1 < J; i++) {
                int j1 = seq[i], j2 = seq[i + 1];
                int u = j1 * M + opIndexByMachine[j1][m];
                int v = j2 * M + opIndexByMachine[j2][m];
                addEdge(u, v, ec);
            }
        }

        int qh = 0, qt = 0;
        for (int i = 0; i < N; i++) if (indeg[i] == 0) q[qt++] = i;

        long long makespan = 0;
        int seen = 0;
        while (qh < qt) {
            int u = q[qh++];
            seen++;
            makespan = max(makespan, dist[u]);
            for (int e = head[u]; e != -1; e = nxt[e]) {
                int v = to[e];
                long long cand = dist[u] + pNode[v];
                if (cand > dist[v]) dist[v] = cand;
                if (--indeg[v] == 0) q[qt++] = v;
            }
        }

        if (seen != N) return {false, (long long)4e18};
        return {true, makespan};
    }
};

struct ScheduleResult {
    long long makespan = (long long)4e18;
    vector<vector<int>> order;
};

struct Event {
    long long t;
    int m;
    int j;
};
struct EventCmp {
    bool operator()(const Event &a, const Event &b) const {
        return a.t > b.t;
    }
};

static inline uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int J, M;
    if (!(cin >> J >> M)) return 0;

    vector<vector<int>> route(J, vector<int>(M));
    vector<vector<long long>> proc(J, vector<long long>(M));
    vector<vector<int>> opIndexByMachine(J, vector<int>(M, -1));
    vector<long long> machineTotalWork(M, 0);

    for (int j = 0; j < J; j++) {
        for (int k = 0; k < M; k++) {
            int m;
            long long p;
            cin >> m >> p;
            route[j][k] = m;
            proc[j][k] = p;
            opIndexByMachine[j][m] = k;
            machineTotalWork[m] += p;
        }
    }

    vector<vector<long long>> remWork(J, vector<long long>(M + 1, 0));
    vector<long long> avgP(J, 0);
    for (int j = 0; j < J; j++) {
        for (int k = M - 1; k >= 0; k--) remWork[j][k] = remWork[j][k + 1] + proc[j][k];
        avgP[j] = remWork[j][0] / max(1, M);
    }

    vector<int> machines(M);
    iota(machines.begin(), machines.end(), 0);
    sort(machines.begin(), machines.end(), [&](int a, int b) {
        return machineTotalWork[a] > machineTotalWork[b];
    });
    vector<char> heavy(M, 0);
    int heavyCnt = max(1, M / 3);
    for (int i = 0; i < heavyCnt && i < M; i++) heavy[machines[i]] = 1;

    vector<long long> pNode(J * M);
    for (int j = 0; j < J; j++) for (int k = 0; k < M; k++) pNode[j * M + k] = proc[j][k];

    vector<pair<int,int>> jobEdges;
    jobEdges.reserve(J * max(0, M - 1));
    for (int j = 0; j < J; j++) {
        for (int k = 0; k + 1 < M; k++) {
            int u = j * M + k;
            int v = j * M + (k + 1);
            jobEdges.push_back({u, v});
        }
    }

    Evaluator evaluator(J, M, pNode, jobEdges, opIndexByMachine);

    uint64_t baseSeed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    baseSeed = splitmix64(baseSeed ^ (uint64_t)J * 1315423911ULL ^ (uint64_t)M * 2654435761ULL);

    auto buildSchedule = [&](int rule, uint64_t seed) -> ScheduleResult {
        mt19937_64 rng(seed);

        int wp = 0, wr = 0, ww = 0, wo = 0;
        if (rule == 5) {
            auto rint = [&](int lo, int hi) -> int {
                uniform_int_distribution<int> dist(lo, hi);
                return dist(rng);
            };
            wp = rint(-12, 12);
            wr = rint(-12, 12);
            ww = rint(-12, 12);
            wo = rint(-6, 6);
            if (wp == 0 && wr == 0 && ww == 0 && wo == 0) wp = 1;
        }

        vector<int> jobNext(J, 0);
        vector<long long> jobReady(J, 0);
        vector<char> jobBusy(J, 0);
        vector<char> machBusy(M, 0);

        ScheduleResult res;
        res.order.assign(M, {});
        for (int m = 0; m < M; m++) res.order[m].reserve(J);

        priority_queue<Event, vector<Event>, EventCmp> pq;
        long long t = 0;
        int done = 0;
        const int total = J * M;
        long long makespan = 0;

        auto pickJob = [&](int m, long long tnow) -> int {
            int bestJ = -1;
            __int128 bestK1 = 0;
            long long bestK2 = 0;
            uint64_t bestTie = 0;

            for (int j = 0; j < J; j++) {
                if (jobBusy[j]) continue;
                int k = jobNext[j];
                if (k >= M) continue;
                if (route[j][k] != m) continue;
                if (jobReady[j] > tnow) continue;

                long long p = proc[j][k];
                long long rem = remWork[j][k];
                long long wait = tnow - jobReady[j];
                int opsRem = M - k;

                __int128 k1;
                long long k2;

                switch (rule) {
                    case 0: // SPT, tie MWKR
                        k1 = (__int128)p;
                        k2 = -rem;
                        break;
                    case 1: // LPT, tie MWKR
                        k1 = -(__int128)p;
                        k2 = -rem;
                        break;
                    case 2: // MWKR, tie SPT
                        k1 = -(__int128)rem;
                        k2 = p;
                        break;
                    case 3: // Most ops remaining, tie SPT
                        k1 = -(__int128)opsRem;
                        k2 = p;
                        break;
                    case 4: { // bottleneck-aware: heavy->LPT else SPT, tie MWKR
                        __int128 primary = heavy[m] ? -(__int128)p : (__int128)p;
                        k1 = primary;
                        k2 = -rem;
                        break;
                    }
                    case 5: { // random linear
                        __int128 val = 0;
                        val += (__int128)wp * p;
                        val += (__int128)wr * rem;
                        val += (__int128)ww * wait;
                        val += (__int128)wo * (__int128)opsRem * (__int128)(avgP[j] + 1);
                        k1 = val;
                        k2 = p;
                        break;
                    }
                    default:
                        k1 = (__int128)p;
                        k2 = -rem;
                        break;
                }

                uint64_t tie = rng();
                if (bestJ == -1 || k1 < bestK1 || (k1 == bestK1 && (k2 < bestK2 || (k2 == bestK2 && tie < bestTie)))) {
                    bestJ = j;
                    bestK1 = k1;
                    bestK2 = k2;
                    bestTie = tie;
                }
            }
            return bestJ;
        };

        while (done < total) {
            // Dispatch at time t
            for (int m = 0; m < M; m++) {
                if (machBusy[m]) continue;
                int j = pickJob(m, t);
                if (j == -1) continue;

                int k = jobNext[j];
                long long p = proc[j][k];
                machBusy[m] = 1;
                jobBusy[j] = 1;
                res.order[m].push_back(j);

                long long endt = t + p;
                pq.push(Event{endt, m, j});
            }

            if (done >= total) break;
            if (pq.empty()) break;

            t = pq.top().t;
            while (!pq.empty() && pq.top().t == t) {
                auto e = pq.top();
                pq.pop();
                done++;
                makespan = max(makespan, e.t);
                machBusy[e.m] = 0;
                jobBusy[e.j] = 0;
                jobReady[e.j] = e.t;
                jobNext[e.j]++;
            }
        }

        res.makespan = makespan;
        return res;
    };

    auto startTime = chrono::steady_clock::now();
    auto elapsed = [&]() -> double {
        return chrono::duration<double>(chrono::steady_clock::now() - startTime).count();
    };
    const double TL = 1.85;

    ScheduleResult best;
    best.makespan = (long long)4e18;
    best.order.assign(M, vector<int>());

    auto consider = [&](const ScheduleResult &cand) {
        if ((int)cand.order.size() != M) return;
        for (int m = 0; m < M; m++) if ((int)cand.order[m].size() != J) return;
        auto ev = evaluator.eval(cand.order);
        if (!ev.first) return;
        long long ms = ev.second;
        if (ms < best.makespan) {
            best = cand;
            best.makespan = ms;
        }
    };

    // Deterministic runs with different seeds
    for (int r = 0; r < 10 && elapsed() < TL * 0.25; r++) {
        for (int rule = 0; rule <= 4; rule++) {
            ScheduleResult cand = buildSchedule(rule, splitmix64(baseSeed + (uint64_t)rule * 10007ULL + (uint64_t)r * 1000003ULL));
            consider(cand);
            if (elapsed() >= TL * 0.25) break;
        }
    }

    // Random weighted runs
    int randomRuns = 0;
    while (elapsed() < TL * 0.45 && randomRuns < 80) {
        ScheduleResult cand = buildSchedule(5, splitmix64(baseSeed + 7777777ULL + (uint64_t)randomRuns * 10000019ULL));
        consider(cand);
        randomRuns++;
    }

    if (best.makespan >= (long long)4e18) {
        // Fallback: simple identity order (always feasible if M==1 or J==1, but may cycle otherwise).
        // Better fallback: build a schedule with rule 0.
        best = buildSchedule(0, splitmix64(baseSeed ^ 0xabcdefULL));
        auto ev = evaluator.eval(best.order);
        if (ev.first) best.makespan = ev.second;
    }

    // Local search: adjacent swaps hill-climb on permutations (cycle-checked)
    vector<vector<int>> cur = best.order;
    long long curMs = best.makespan;

    long long sumW = 0;
    for (int m = 0; m < M; m++) sumW += max(1LL, machineTotalWork[m]);
    vector<long long> prefW(M + 1, 0);
    for (int m = 0; m < M; m++) prefW[m + 1] = prefW[m] + max(1LL, machineTotalWork[m]);

    mt19937_64 rng(splitmix64(baseSeed ^ 0x123456789ULL));
    auto pickMachineWeighted = [&]() -> int {
        if (M == 1) return 0;
        long long r = (long long)(rng() % (uint64_t)prefW[M]);
        int m = int(upper_bound(prefW.begin(), prefW.end(), r) - prefW.begin()) - 1;
        if (m < 0) m = 0;
        if (m >= M) m = M - 1;
        return m;
    };

    int stall = 0;
    int it = 0;
    while (elapsed() < TL * 0.98) {
        it++;
        int m = pickMachineWeighted();
        if (J <= 1) break;
        int pos = (int)(rng() % (uint64_t)(J - 1));
        swap(cur[m][pos], cur[m][pos + 1]);

        auto ev = evaluator.eval(cur);
        if (ev.first && ev.second < curMs) {
            curMs = ev.second;
            stall = 0;
            if (curMs < best.makespan) {
                best.makespan = curMs;
                best.order = cur;
            }
        } else {
            swap(cur[m][pos], cur[m][pos + 1]);
            stall++;
        }

        if (stall > 12000) break;
        if ((it & 63) == 0 && elapsed() >= TL * 0.98) break;
    }

    for (int m = 0; m < M; m++) {
        for (int i = 0; i < J; i++) {
            if (i) cout << ' ';
            cout << best.order[m][i];
        }
        cout << '\n';
    }

    return 0;
}