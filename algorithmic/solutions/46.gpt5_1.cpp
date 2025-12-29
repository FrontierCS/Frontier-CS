#include <bits/stdc++.h>
using namespace std;

struct Instance {
    int J, M;
    vector<vector<int>> mach;           // mach[j][k] = machine of k-th op of job j
    vector<vector<long long>> proc;     // proc[j][k] = processing time
    vector<long long> machLoad;         // total load per machine
    vector<long long> jobTotal;         // total processing time per job
};

struct ScheduleResult {
    long long makespan = (1LL<<62);
    vector<vector<int>> order; // order[m] is permutation of jobs on machine m
};

struct Key {
    long long a, b, c;
    int job;
    bool operator<(const Key& o) const {
        if (a != o.a) return a < o.a;
        if (b != o.b) return b < o.b;
        if (c != o.c) return c < o.c;
        return job < o.job;
    }
};

// Build a schedule by serial schedule generation, appending operations at the end of each machine sequence
static ScheduleResult ssgs_run(const Instance& inst, mt19937_64& rng, int rule, int rclSize) {
    int J = inst.J, M = inst.M;
    vector<int> pos(J, 0);
    vector<long long> readyJob(J, 0), readyMach(M, 0), remJob(inst.jobTotal);
    vector<vector<int>> order(M);
    for (int m = 0; m < M; ++m) order[m].reserve(J);

    long long makespan = 0;
    int remaining = J * M;

    while (remaining > 0) {
        vector<Key> cand;
        cand.reserve(J);
        for (int j = 0; j < J; ++j) {
            if (pos[j] >= M) continue;
            int k = pos[j];
            int m = inst.mach[j][k];
            long long p = inst.proc[j][k];
            long long est = max(readyJob[j], readyMach[m]);
            long long finish = est + p;
            long long rem = remJob[j];
            long long load = inst.machLoad[m];
            Key key;
            key.job = j;
            switch (rule) {
                case 0: // ECT
                    key = {finish, est, p, j};
                    break;
                case 1: // SPT
                    key = {p, est, -load, j};
                    break;
                case 2: // LPT
                    key = {-p, est, -load, j};
                    break;
                case 3: // EST
                    key = {est, p, -load, j};
                    break;
                case 4: // MWR (most work remaining)
                    key = {-rem, est, p, j};
                    break;
                case 5: // LWR (least work remaining)
                    key = {rem, est, p, j};
                    break;
                case 6: // Bottleneck machine first
                    key = {-load, est, p, j};
                    break;
                case 7: // Finish then favor heavy remaining work
                    key = {finish, -rem, p, j};
                    break;
                case 8: { // Min machine waiting time
                    long long wait = 0;
                    if (readyMach[m] > readyJob[j]) wait = readyMach[m] - readyJob[j];
                    key = {wait, est, p, j};
                    break;
                }
                default: // fallback to ECT
                    key = {finish, est, p, j};
            }
            cand.push_back(key);
        }

        if (cand.empty()) break; // should not happen

        sort(cand.begin(), cand.end());
        int rcl = min<int>(rclSize, (int)cand.size());
        uniform_int_distribution<int> pick(0, rcl - 1);
        int idx = pick(rng);
        int jsel = cand[idx].job;

        int k = pos[jsel];
        int m = inst.mach[jsel][k];
        long long p = inst.proc[jsel][k];
        long long est = max(readyJob[jsel], readyMach[m]);
        long long finish = est + p;

        order[m].push_back(jsel);
        readyMach[m] = finish;
        readyJob[jsel] = finish;
        remJob[jsel] -= p;
        pos[jsel]++;

        if (finish > makespan) makespan = finish;
        remaining--;
    }

    ScheduleResult res;
    res.makespan = makespan;
    res.order = move(order);
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int J, M;
    if (!(cin >> J >> M)) return 0;
    Instance inst;
    inst.J = J; inst.M = M;
    inst.mach.assign(J, vector<int>(M));
    inst.proc.assign(J, vector<long long>(M));
    inst.machLoad.assign(M, 0);
    inst.jobTotal.assign(J, 0);

    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            int m; long long p;
            cin >> m >> p;
            inst.mach[j][k] = m;
            inst.proc[j][k] = p;
            inst.machLoad[m] += p;
            inst.jobTotal[j] += p;
        }
    }

    // Randomized multi-start over different rules with small RCL
    std::random_device rd;
    uint64_t seed = ((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count()) ^ ((uint64_t)rd());
    mt19937_64 rng(seed);

    vector<int> rules = {0,1,2,3,4,5,6,7,8};
    vector<int> rcls  = {1,2,3,4};

    // Baseline run (deterministic ECT)
    ScheduleResult best;
    best.makespan = (1LL<<62);
    {
        ScheduleResult r0 = ssgs_run(inst, rng, 0, 1);
        best = r0;
    }

    // Time budget for improvement
    auto t0 = chrono::steady_clock::now();
    const double TIME_LIMIT_SEC = 1.80;
    uniform_int_distribution<int> pickRule(0, (int)rules.size()-1);
    uniform_int_distribution<int> pickRcl(0, (int)rcls.size()-1);

    while (true) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - t0).count();
        if (elapsed > TIME_LIMIT_SEC) break;

        int rule = rules[pickRule(rng)];
        int rclSize = rcls[pickRcl(rng)];
        ScheduleResult r = ssgs_run(inst, rng, rule, rclSize);
        if (r.makespan < best.makespan) {
            best = move(r);
        }
    }

    // Output machine orders
    for (int m = 0; m < M; ++m) {
        // Ensure length J (some safety in rare cases)
        if ((int)best.order[m].size() < J) {
            // fill missing jobs arbitrarily to complete permutation
            vector<int> seen(J, 0);
            for (int x : best.order[m]) if (x >= 0 && x < J) seen[x] = 1;
            for (int j = 0; j < J; ++j) if (!seen[j]) best.order[m].push_back(j);
        }
        for (int i = 0; i < J; ++i) {
            if (i) cout << ' ';
            cout << best.order[m][i];
        }
        cout << '\n';
    }

    return 0;
}