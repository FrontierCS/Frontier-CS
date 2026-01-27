#include <bits/stdc++.h>
using namespace std;

struct Instance {
    int J, M, N;
    vector<int> op_job, op_idx, op_m;
    vector<long long> op_p;
    vector<vector<int>> id_of_job_index; // J x M
    vector<vector<long long>> tail;      // J x (M+1): tail[j][k] = sum of op_p from k to M-1
};

struct Result {
    vector<vector<int>> machine_jobs; // M vectors of J jobs (order on each machine)
    long long makespan = (1LL<<62);
};

static inline uint64_t now_ns() {
    using namespace std::chrono;
    return duration_cast<nanoseconds>(high_resolution_clock::now().time_since_epoch()).count();
}

struct Strategy {
    int mode;        // 0..6
    double w_r, w_p, w_tail, w_sum;
    int topK;
};

static Result scheduleGT(const Instance& inst, const Strategy& strat, std::mt19937_64& rng) {
    int J = inst.J, M = inst.M, N = inst.N;
    vector<long long> jobReady(J, 0), machReady(M, 0);
    vector<int> jobNext(J, 0);
    vector<vector<int>> mach_jobs(M);
    for (int m = 0; m < M; ++m) mach_jobs[m].reserve(J);

    long long makespan = 0;
    int scheduled = 0;

    auto earliestStart = [&](int j, int m) -> long long {
        return max(jobReady[j], machReady[m]);
    };

    uniform_real_distribution<double> urand(0.0, 1.0);

    while (scheduled < N) {
        // Choose operation 'a' with minimal completion time c = r + p among ready set A (one per job)
        long long bestC = (1LL<<62);
        long long bestR = (1LL<<62);
        int a = -1;
        int aJob = -1;

        for (int j = 0; j < J; ++j) {
            if (jobNext[j] >= inst.id_of_job_index[j].size()) continue;
            int o = inst.id_of_job_index[j][jobNext[j]];
            int m = inst.op_m[o];
            long long r = earliestStart(j, m);
            long long c = r + inst.op_p[o];
            if (c < bestC || (c == bestC && r < bestR)) {
                bestC = c; bestR = r; a = o; aJob = j;
            }
        }

        int mA = inst.op_m[a];
        long long cA = bestC;

        // Build conflict set K = {o in A on machine mA with r[o] < cA}
        struct Cand { int op; int j; long long r; double score; };
        vector<Cand> K;
        K.reserve(J);

        for (int j = 0; j < J; ++j) {
            if (jobNext[j] >= inst.id_of_job_index[j].size()) continue;
            int o = inst.id_of_job_index[j][jobNext[j]];
            if (inst.op_m[o] != mA) continue;
            long long r = earliestStart(j, mA);
            if (r < cA) {
                double score = 0.0;
                long long p = inst.op_p[o];
                long long tail_after = inst.tail[j][jobNext[j] + 1];
                long long sum_job = inst.tail[j][0];

                switch (strat.mode) {
                    case 0: // earliest r
                        score = (double)r + 1e-9 * (double)p;
                        break;
                    case 1: // shortest p
                        score = (double)p + 1e-9 * (double)r;
                        break;
                    case 2: // earliest completion r+p
                        score = (double)(r + p) + 1e-9 * (double)tail_after;
                        break;
                    case 3: // r + remaining tail
                        score = (double)r + (double)tail_after;
                        break;
                    case 4: // prioritize long remaining (LPT-like on job), via negative weight
                        score = (double)r - 0.5 * (double)tail_after + 1e-9 * (double)p;
                        break;
                    case 5: // random weighted
                    case 6:
                    default:
                        score = strat.w_r * (double)r + strat.w_p * (double)p + strat.w_tail * (double)tail_after + strat.w_sum * (double)sum_job;
                        break;
                }
                // small random noise for tie-breaking
                score += urand(rng) * 1e-12;
                K.push_back({o, j, r, score});
            }
        }

        if (K.empty()) {
            // Fallback: if for some numerical reason K is empty, schedule 'a'
            K.push_back({a, aJob, bestR, 0.0});
        }

        // Choose candidate from top strat.topK according to score
        int chooseIdx = 0;
        if ((int)K.size() > 1) {
            // sort by score
            sort(K.begin(), K.end(), [](const Cand& A, const Cand& B){
                if (A.score != B.score) return A.score < B.score;
                if (A.r != B.r) return A.r < B.r;
                return A.op < B.op;
            });
            int kk = min(strat.topK, (int)K.size());
            if (kk > 1) {
                // probabilistic pick among top kk
                double r = urand(rng);
                if (kk >= 3) {
                    if (r < 0.70) chooseIdx = 0;
                    else if (r < 0.90) chooseIdx = 1;
                    else chooseIdx = 2;
                } else if (kk == 2) {
                    chooseIdx = (r < 0.80) ? 0 : 1;
                }
            }
        }

        // Schedule selected candidate
        int s = K[chooseIdx].op;
        int js = K[chooseIdx].j;
        int ms = inst.op_m[s];
        long long p = inst.op_p[s];
        long long start = max(jobReady[js], machReady[ms]);
        long long finish = start + p;

        jobReady[js] = finish;
        machReady[ms] = finish;
        mach_jobs[ms].push_back(js);
        jobNext[js]++;

        if (finish > makespan) makespan = finish;
        scheduled++;
    }

    Result res;
    res.machine_jobs = move(mach_jobs);
    res.makespan = makespan;
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    Instance inst;
    if (!(cin >> inst.J >> inst.M)) {
        return 0;
    }
    inst.N = inst.J * inst.M;
    inst.op_job.assign(inst.N, 0);
    inst.op_idx.assign(inst.N, 0);
    inst.op_m.assign(inst.N, 0);
    inst.op_p.assign(inst.N, 0);
    inst.id_of_job_index.assign(inst.J, vector<int>(inst.M));
    for (int j = 0; j < inst.J; ++j) {
        for (int k = 0; k < inst.M; ++k) {
            int m; long long p;
            cin >> m >> p;
            int id = j * inst.M + k;
            inst.op_job[id] = j;
            inst.op_idx[id] = k;
            inst.op_m[id] = m;
            inst.op_p[id] = p;
            inst.id_of_job_index[j][k] = id;
        }
    }
    inst.tail.assign(inst.J, vector<long long>(inst.M + 1, 0));
    for (int j = 0; j < inst.J; ++j) {
        for (int k = inst.M - 1; k >= 0; --k) {
            int id = inst.id_of_job_index[j][k];
            inst.tail[j][k] = inst.op_p[id] + inst.tail[j][k + 1];
        }
    }

    uint64_t seed = now_ns() ^ (uint64_t)(uintptr_t)&seed;
    std::mt19937_64 rng(seed);
    uniform_real_distribution<double> urand(0.0, 1.0);

    // Time limit (in milliseconds)
    const double TIME_LIMIT_MS = 1900.0;
    auto tStart = chrono::high_resolution_clock::now();

    // Initial deterministic run
    Strategy baseStrat;
    baseStrat.mode = 2; // earliest completion
    baseStrat.w_r = 1.0; baseStrat.w_p = 1.0; baseStrat.w_tail = 0.0; baseStrat.w_sum = 0.0;
    baseStrat.topK = 1;

    Result best = scheduleGT(inst, baseStrat, rng);

    // Multi-start randomized GT
    int iter = 0;
    while (true) {
        auto tNow = chrono::high_resolution_clock::now();
        double elapsed = chrono::duration<double, std::milli>(tNow - tStart).count();
        if (elapsed > TIME_LIMIT_MS) break;

        Strategy s;
        // Randomly choose mode
        int mode = (int)(rng() % 7ULL);
        s.mode = mode;
        if (mode >= 5) {
            s.w_r = 0.5 + urand(rng) * 1.5;   // [0.5, 2.0]
            s.w_p = urand(rng) * 1.0;         // [0.0, 1.0]
            s.w_tail = urand(rng) * 0.8;      // [0.0, 0.8]
            s.w_sum = urand(rng) * 0.2;       // small effect
        } else {
            s.w_r = s.w_p = s.w_tail = s.w_sum = 0.0;
        }
        s.topK = 2 + (rng() % 2); // 2 or 3

        Result r = scheduleGT(inst, s, rng);
        if (r.makespan < best.makespan) {
            best = move(r);
        }

        iter++;
        // occasional fallback exact mode runs
        if (iter % 50 == 0) {
            Strategy s2 = baseStrat;
            s2.topK = 1;
            Result r2 = scheduleGT(inst, s2, rng);
            if (r2.makespan < best.makespan) best = move(r2);
        }
    }

    // Output exactly M lines, each with J job indices (permutation)
    for (int m = 0; m < inst.M; ++m) {
        for (int i = 0; i < (int)best.machine_jobs[m].size(); ++i) {
            if (i) cout << ' ';
            cout << best.machine_jobs[m][i];
        }
        // If for some rare reason the schedule didn't include all jobs on machine m (should not happen), fill missing.
        if ((int)best.machine_jobs[m].size() < inst.J) {
            // Build a set
            vector<int> seen(inst.J, 0);
            for (int j : best.machine_jobs[m]) if (j >= 0 && j < inst.J) seen[j] = 1;
            for (int j = 0; j < inst.J; ++j) {
                if (!seen[j]) {
                    if (!best.machine_jobs[m].empty() || j > 0) cout << ' ';
                    cout << j;
                }
            }
        }
        cout << '\n';
    }

    return 0;
}