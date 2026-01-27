#include <bits/stdc++.h>
using namespace std;

struct Instance {
    int J, M;
    vector<vector<int>> machine_of;        // [j][k] -> machine index at position k in job j
    vector<vector<long long>> proc;        // [j][k] -> processing time
    vector<vector<int>> pos_of;            // [j][m] -> position k in job j where machine m is processed
    vector<long long> machine_total_load;  // [m] -> total processing time on machine m
    vector<long long> job_total_load;      // [j] -> total processing time of job j
    vector<long long> dur;                 // flat durations size J*M: id(j,k) = j*M + k
};

static inline int op_id(int j, int k, int M) { return j * M + k; }

struct Evaluator {
    const Instance* inst;
    int J, M, N;
    Evaluator(const Instance* in) : inst(in), J(in->J), M(in->M), N(in->J * in->M) {}

    // Evaluate makespan for given machine orders. Returns pair(valid, makespan).
    pair<bool, long long> evaluate(const vector<vector<int>>& seq) const {
        int N = J * M;
        vector<int> indeg(N, 0);
        vector<int> mach_succ(N, -1);
        // job indegree: each operation except first in its job has one incoming job edge
        for (int j = 0; j < J; ++j) {
            for (int k = 1; k < M; ++k) {
                indeg[op_id(j, k, M)] += 1;
            }
        }
        // machine edges and indegrees
        for (int m = 0; m < M; ++m) {
            const vector<int>& order = seq[m];
            for (int t = 0; t < (int)order.size(); ++t) {
                int j = order[t];
                int k = inst->pos_of[j][m];
                int u = op_id(j, k, M);
                if (t > 0) {
                    indeg[u] += 1; // incoming from previous on machine
                }
                if (t + 1 < (int)order.size()) {
                    int j2 = order[t + 1];
                    int k2 = inst->pos_of[j2][m];
                    int v = op_id(j2, k2, M);
                    mach_succ[u] = v;
                }
            }
        }
        // Kahn's algorithm with longest path DP
        vector<long long> ES(N, 0);
        deque<int> q;
        for (int u = 0; u < N; ++u) if (indeg[u] == 0) q.push_back(u);
        int visited = 0;
        long long cmax = 0;
        while (!q.empty()) {
            int u = q.front(); q.pop_front();
            visited++;
            cmax = max(cmax, ES[u] + inst->dur[u]);
            int j = u / M;
            int k = u % M;
            // job successor
            if (k + 1 < M) {
                int v = op_id(j, k + 1, M);
                if (ES[v] < ES[u] + inst->dur[u]) ES[v] = ES[u] + inst->dur[u];
                if (--indeg[v] == 0) q.push_back(v);
            }
            // machine successor
            int v = mach_succ[u];
            if (v != -1) {
                if (ES[v] < ES[u] + inst->dur[u]) ES[v] = ES[u] + inst->dur[u];
                if (--indeg[v] == 0) q.push_back(v);
            }
        }
        if (visited != N) return {false, (long long)4e18};
        return {true, cmax};
    }
};

struct GreedyScheduler {
    const Instance* inst;
    mt19937_64 rng;
    GreedyScheduler(const Instance* in, uint64_t seed) : inst(in), rng(seed) {}

    // rule_id in [0..5]
    pair<vector<vector<int>>, long long> schedule(int rule_id) {
        int J = inst->J, M = inst->M;
        vector<vector<int>> seq(M);
        vector<int> nextk(J, 0);
        vector<long long> ready(J, 0), avail(M, 0), rem_job = inst->job_total_load;
        long long makespan = 0;
        int N = J * M;
        uniform_int_distribution<int> coin(0, 1);

        for (int step = 0; step < N; ++step) {
            int best_j = -1;
            long long best_primary = LLONG_MAX;
            long long best_secondary = LLONG_MAX;
            long long best_tertiary = LLONG_MAX;
            long long best_quaternary = LLONG_MAX;

            for (int j = 0; j < J; ++j) {
                int k = nextk[j];
                if (k >= M) continue;
                int m = inst->machine_of[j][k];
                long long p = inst->proc[j][k];
                long long est = max(ready[j], avail[m]);
                long long eft = est + p;

                long long primary = 0, secondary = 0, tertiary = 0, quaternary = 0;
                switch (rule_id) {
                    case 0:
                        // minimize est, then p, then -rem_job
                        primary = est;
                        secondary = p;
                        tertiary = -rem_job[j];
                        quaternary = j;
                        break;
                    case 1:
                        // minimize eft, then p
                        primary = eft;
                        secondary = p;
                        tertiary = -inst->machine_total_load[m];
                        quaternary = j;
                        break;
                    case 2: {
                        // est with light randomization, then eft
                        // Add small discrete noise by using coin flips scaled by p
                        long long noise = coin(rng) ? (p & 1LL) : 0LL;
                        primary = est + noise;
                        secondary = eft;
                        tertiary = p;
                        quaternary = j;
                        break;
                    }
                    case 3:
                        // est, then prioritize bottleneck machines (higher load first)
                        primary = est;
                        secondary = -inst->machine_total_load[m];
                        tertiary = p;
                        quaternary = j;
                        break;
                    case 4:
                        // est, then remaining job (more remaining first), then p
                        primary = est;
                        secondary = -rem_job[j];
                        tertiary = p;
                        quaternary = j;
                        break;
                    default:
                    case 5:
                        // est, then LPT on p, then -rem_job
                        primary = est;
                        secondary = -p;
                        tertiary = -rem_job[j];
                        quaternary = j;
                        break;
                }

                bool better = false;
                if (primary < best_primary) better = true;
                else if (primary == best_primary) {
                    if (secondary < best_secondary) better = true;
                    else if (secondary == best_secondary) {
                        if (tertiary < best_tertiary) better = true;
                        else if (tertiary == best_tertiary) {
                            if (quaternary < best_quaternary) better = true;
                        }
                    }
                }
                if (better) {
                    best_j = j;
                    best_primary = primary;
                    best_secondary = secondary;
                    best_tertiary = tertiary;
                    best_quaternary = quaternary;
                }
            }

            // schedule best_j's next operation
            int j = best_j;
            int k = nextk[j];
            int m = inst->machine_of[j][k];
            long long p = inst->proc[j][k];
            long long est = max(ready[j], avail[m]);
            long long fin = est + p;
            ready[j] = fin;
            avail[m] = fin;
            seq[m].push_back(j);
            nextk[j]++;
            rem_job[j] -= p;
            if (ready[j] > makespan) makespan = ready[j];
        }

        return {seq, makespan};
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    Instance inst;
    if (!(cin >> inst.J >> inst.M)) {
        return 0;
    }
    int J = inst.J, M = inst.M;
    inst.machine_of.assign(J, vector<int>(M));
    inst.proc.assign(J, vector<long long>(M));
    inst.pos_of.assign(J, vector<int>(M, -1));
    inst.machine_total_load.assign(M, 0);
    inst.job_total_load.assign(J, 0);
    inst.dur.assign(J * M, 0);

    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            int m; long long p;
            cin >> m >> p;
            inst.machine_of[j][k] = m;
            inst.proc[j][k] = p;
            inst.pos_of[j][m] = k;
            inst.machine_total_load[m] += p;
            inst.job_total_load[j] += p;
            inst.dur[op_id(j, k, M)] = p;
        }
    }

    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    GreedyScheduler scheduler(&inst, seed);
    Evaluator evaluator(&inst);

    // Time management
    auto t_start = chrono::high_resolution_clock::now();
    const double TIME_LIMIT = 1.7; // seconds
    auto time_spent = [&]() -> double {
        auto t_now = chrono::high_resolution_clock::now();
        return chrono::duration<double>(t_now - t_start).count();
    };

    // Initial solution with a couple of deterministic rules
    vector<vector<int>> best_seq;
    long long best_makespan = (long long)4e18;

    for (int rule = 0; rule <= 2; ++rule) {
        auto res = scheduler.schedule(rule);
        // Greedy schedule is feasible, but evaluate via evaluator to match judge's interpretation
        auto eval = evaluator.evaluate(res.first);
        if (eval.first && eval.second < best_makespan) {
            best_makespan = eval.second;
            best_seq = move(res.first);
        }
    }

    // Randomized restarts with different rules
    mt19937_64 rng(seed ^ 0x9e3779b97f4a7c15ULL);
    uniform_int_distribution<int> rule_dist(0, 5);
    while (time_spent() < TIME_LIMIT * 0.65) {
        int rule = rule_dist(rng);
        auto res = scheduler.schedule(rule);
        auto eval = evaluator.evaluate(res.first);
        if (eval.first && eval.second < best_makespan) {
            best_makespan = eval.second;
            best_seq = move(res.first);
        }
    }

    // Local improvement: adjacent swaps hill-climbing
    auto try_improve = [&](vector<vector<int>>& seq, long long& cur_mk) {
        bool improved = true;
        while (improved && time_spent() < TIME_LIMIT) {
            improved = false;
            for (int m = 0; m < M && time_spent() < TIME_LIMIT; ++m) {
                vector<int>& order = seq[m];
                for (int i = 0; i + 1 < (int)order.size() && time_spent() < TIME_LIMIT; ++i) {
                    swap(order[i], order[i + 1]);
                    auto eval = evaluator.evaluate(seq);
                    if (eval.first && eval.second < cur_mk) {
                        cur_mk = eval.second;
                        improved = true;
                    } else {
                        swap(order[i], order[i + 1]); // revert
                    }
                }
            }
        }
    };

    if (!best_seq.empty()) {
        try_improve(best_seq, best_makespan);
    } else {
        // Fallback: produce a simple identity order per machine
        best_seq.assign(M, vector<int>(J));
        for (int m = 0; m < M; ++m) {
            for (int j = 0; j < J; ++j) best_seq[m][j] = j;
        }
    }

    // Output
    for (int m = 0; m < M; ++m) {
        for (int t = 0; t < J; ++t) {
            if (t) cout << ' ';
            cout << best_seq[m][t];
        }
        cout << '\n';
    }

    return 0;
}