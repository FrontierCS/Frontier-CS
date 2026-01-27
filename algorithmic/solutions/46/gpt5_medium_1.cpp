#include <bits/stdc++.h>
using namespace std;

struct Op {
    int m;
    long long p;
};

struct ScheduleResult {
    vector<vector<int>> order; // per machine: sequence of jobs
    long long makespan;
};

enum Rule {
    SPT = 0,
    LPT = 1,
    MIN_REM = 2,
    MAX_REM = 3,
    EARLIEST_START = 4,
    EARLIEST_FINISH = 5,
    RANDOM_RULE = 6,
    HYBRID = 7
};

struct Data {
    int J, M;
    vector<vector<Op>> ops;              // ops[j][k] = {m, p}
    vector<vector<int>> pos;             // pos[j][m] = k
    vector<vector<long long>> remsum;    // remsum[j][k] = sum_{t=k}^{M-1} p
    vector<long long> machineLoad;       // sum of processing times per machine
    vector<char> heavyMachine;           // mark heavy machines
};

static inline long long nowMicros() {
    using namespace std::chrono;
    return duration_cast<microseconds>(steady_clock::now().time_since_epoch()).count();
}

ScheduleResult gifflerThompson(const Data& D, Rule rule, std::mt19937_64& rng) {
    int J = D.J, M = D.M;
    int N = J * M;

    vector<int> kJ(J, 0);                     // next operation index for each job
    vector<long long> rJ(J, 0);               // ready time of each job
    vector<long long> Rm(M, 0);               // ready time of each machine
    vector<vector<int>> order(M);             // machine order result
    order.assign(M, {});

    // Pre-allocated temporaries
    vector<long long> es(J, 0), ef(J, 0);
    vector<int> om(J, -1);
    vector<long long> op(J, 0);

    int scheduled = 0;

    while (scheduled < N) {
        // Compute earliest start and finish for next operations of all jobs
        long long bestEF = LLONG_MAX;
        int bestJob = -1;
        for (int j = 0; j < J; ++j) {
            if (kJ[j] >= M) continue;
            int k = kJ[j];
            int m = D.ops[j][k].m;
            long long p = D.ops[j][k].p;
            long long s = max(rJ[j], Rm[m]);
            long long f = s + p;

            es[j] = s;
            ef[j] = f;
            om[j] = m;
            op[j] = p;

            if (f < bestEF) {
                bestEF = f;
                bestJob = j;
            } else if (f == bestEF) {
                // tie-break: earlier start, then smaller job id
                if (s < es[bestJob] || (s == es[bestJob] && j < bestJob)) {
                    bestJob = j;
                }
            }
        }

        int mstar = om[bestJob];
        long long cstar = bestEF;

        // Build conflict set S: operations requiring mstar with es < cstar
        vector<int> S;
        S.reserve(J);
        for (int j = 0; j < J; ++j) {
            if (kJ[j] >= M) continue;
            if (om[j] != mstar) continue;
            if (es[j] < cstar) {
                S.push_back(j);
            }
        }
        if (S.empty()) {
            // Should not happen since bestJob must be in S
            S.push_back(bestJob);
        }

        auto chooseByRule = [&](const vector<int>& cand)->int {
            if (cand.size() == 1) return cand[0];

            auto pick_min = [&](auto keyFunc)->int {
                long long bestVal = LLONG_MAX;
                int pick = -1;
                for (int j : cand) {
                    long long v = keyFunc(j);
                    if (v < bestVal) {
                        bestVal = v;
                        pick = j;
                    } else if (v == bestVal) {
                        // tie-break: earlier start, then smaller p, then job id
                        if (es[j] < es[pick] ||
                            (es[j] == es[pick] && op[j] < op[pick]) ||
                            (es[j] == es[pick] && op[j] == op[pick] && j < pick)) {
                            pick = j;
                        }
                    }
                }
                return pick;
            };
            auto pick_max = [&](auto keyFunc)->int {
                long long bestVal = LLONG_MIN;
                int pick = -1;
                for (int j : cand) {
                    long long v = keyFunc(j);
                    if (v > bestVal) {
                        bestVal = v;
                        pick = j;
                    } else if (v == bestVal) {
                        // tie-break: earlier start, then larger p, then job id
                        if (es[j] < es[pick] ||
                            (es[j] == es[pick] && op[j] > op[pick]) ||
                            (es[j] == es[pick] && op[j] == op[pick] && j < pick)) {
                            pick = j;
                        }
                    }
                }
                return pick;
            };

            switch (rule) {
                case SPT:
                    return pick_min([&](int j){ return op[j]; });
                case LPT:
                    return pick_max([&](int j){ return op[j]; });
                case MIN_REM:
                    return pick_min([&](int j){ return D.remsum[j][kJ[j]]; });
                case MAX_REM:
                    return pick_max([&](int j){ return D.remsum[j][kJ[j]]; });
                case EARLIEST_START:
                    return pick_min([&](int j){ return es[j]; });
                case EARLIEST_FINISH:
                    return pick_min([&](int j){ return ef[j]; });
                case RANDOM_RULE: {
                    std::uniform_int_distribution<int> dist(0, (int)cand.size() - 1);
                    return cand[dist(rng)];
                }
                case HYBRID: {
                    // If machine is heavy -> prefer LPT, else prefer earliest finish
                    if (D.heavyMachine[mstar]) {
                        return pick_max([&](int j){ return op[j]; });
                    } else {
                        return pick_min([&](int j){ return ef[j]; });
                    }
                }
                default:
                    return pick_min([&](int j){ return ef[j]; });
            }
        };

        int jsel = chooseByRule(S);

        // Schedule selected operation
        long long start = es[jsel];
        long long finish = start + op[jsel];
        Rm[mstar] = finish;
        rJ[jsel] = finish;
        order[mstar].push_back(jsel);
        kJ[jsel] += 1;
        scheduled += 1;
    }

    long long makespan = 0;
    for (int j = 0; j < J; ++j) makespan = max(makespan, rJ[j]);

    ScheduleResult res;
    res.order = std::move(order);
    res.makespan = makespan;
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int J, M;
    if (!(cin >> J >> M)) {
        return 0;
    }

    vector<vector<Op>> ops(J, vector<Op>(M));
    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            int m; long long p;
            cin >> m >> p;
            ops[j][k] = {m, p};
        }
    }

    Data D;
    D.J = J; D.M = M;
    D.ops = ops;
    D.pos.assign(J, vector<int>(M, -1));
    D.remsum.assign(J, vector<long long>(M + 1, 0));
    D.machineLoad.assign(M, 0);
    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            int m = ops[j][k].m;
            D.pos[j][m] = k;
            D.machineLoad[m] += ops[j][k].p;
        }
        for (int k = M - 1; k >= 0; --k) {
            D.remsum[j][k] = D.remsum[j][k + 1] + ops[j][k].p;
        }
    }

    // Determine heavy machines (top ~25% by load, at least 1)
    vector<int> idx(M);
    iota(idx.begin(), idx.end(), 0);
    sort(idx.begin(), idx.end(), [&](int a, int b){ return D.machineLoad[a] > D.machineLoad[b]; });
    int heavyCount = max(1, M / 4);
    D.heavyMachine.assign(M, 0);
    for (int i = 0; i < heavyCount; ++i) D.heavyMachine[idx[i]] = 1;

    std::mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    // Time budget
    long long startTime = nowMicros();
    long long timeLimitUs;
    int N = J * M;
    if (N <= 200) timeLimitUs = 200000;      // 0.20s
    else if (N <= 600) timeLimitUs = 400000; // 0.40s
    else if (N <= 1200) timeLimitUs = 700000; // 0.70s
    else timeLimitUs = 900000;               // 0.90s

    vector<Rule> rules = {HYBRID, LPT, SPT, MAX_REM, MIN_REM, EARLIEST_FINISH, EARLIEST_START, RANDOM_RULE};

    // Initial baseline with a couple of deterministic runs
    ScheduleResult best;
    best.makespan = LLONG_MAX;

    for (Rule r : {HYBRID, EARLIEST_FINISH, LPT, SPT}) {
        ScheduleResult cur = gifflerThompson(D, r, rng);
        if ((int)cur.order.size() == M) {
            if (cur.makespan < best.makespan) best = std::move(cur);
        }
    }

    // Multi-start with different rules until time budget
    size_t ridx = 0;
    while (nowMicros() - startTime < timeLimitUs) {
        Rule r = rules[ridx % rules.size()];
        ridx++;

        ScheduleResult cur = gifflerThompson(D, r, rng);
        if ((int)cur.order.size() == M) {
            if (cur.makespan < best.makespan) best = std::move(cur);
        }
    }

    // Fallback: ensure each machine has a permutation (should be the case)
    if (best.order.empty()) {
        best.order.assign(M, vector<int>(J));
        for (int m = 0; m < M; ++m) {
            iota(best.order[m].begin(), best.order[m].end(), 0);
        }
    }

    // Output exactly M lines, each a permutation of 0..J-1
    for (int m = 0; m < M; ++m) {
        const auto& seq = best.order[m];
        if ((int)seq.size() != J) {
            // In rare unexpected case, pad missing jobs arbitrarily
            vector<int> seen(J, 0);
            for (int j : seq) if (0 <= j && j < J) seen[j] = 1;
            vector<int> out = seq;
            for (int j = 0; j < J; ++j) if (!seen[j]) out.push_back(j);
            for (int i = 0; i < J; ++i) {
                if (i) cout << ' ';
                cout << out[i];
            }
            cout << '\n';
        } else {
            for (int i = 0; i < J; ++i) {
                if (i) cout << ' ';
                cout << seq[i];
            }
            cout << '\n';
        }
    }
    return 0;
}