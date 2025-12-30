#include <bits/stdc++.h>
using namespace std;

struct Problem {
    int J, M, N;
    vector<vector<int>> machine;        // [j][pos] -> machine index
    vector<vector<long long>> proc;     // [j][pos] -> processing time
    vector<vector<int>> posOfMachine;   // [j][m] -> position in job route
    vector<int> jobOf, machOf, posOf;   // per op id
    vector<long long> ptime;            // per op id
    vector<vector<long long>> sufRem;   // [j][pos] -> sum of remaining processing times from pos
};

struct ScheduleResult {
    bool feasible;
    long long makespan;
    vector<long long> est;    // earliest start
    vector<long long> fin;    // finish
    vector<int> cpred;        // critical predecessor
};

struct MachineOrder {
    vector<vector<int>> seq; // [m] -> list of jobs in order
};

static inline long long llmax(long long a, long long b) { return (a > b) ? a : b; }

ScheduleResult compute_schedule(const Problem& P, const MachineOrder& order) {
    int N = P.N;
    vector<vector<int>> adj(N);
    vector<int> indeg(N, 0);

    // Job precedence edges
    for (int j = 0; j < P.J; ++j) {
        for (int k = 0; k < P.M - 1; ++k) {
            int u = j * P.M + k;
            int v = j * P.M + (k + 1);
            adj[u].push_back(v);
            indeg[v]++;
        }
    }
    // Machine order edges
    for (int m = 0; m < P.M; ++m) {
        const auto& ord = order.seq[m];
        for (int k = 0; k + 1 < (int)ord.size(); ++k) {
            int j1 = ord[k];
            int j2 = ord[k + 1];
            int pos1 = P.posOfMachine[j1][m];
            int pos2 = P.posOfMachine[j2][m];
            int u = j1 * P.M + pos1;
            int v = j2 * P.M + pos2;
            adj[u].push_back(v);
            indeg[v]++;
        }
    }

    vector<long long> est(N, 0), fin(N, 0);
    vector<int> cpred(N, -1);
    deque<int> dq;
    for (int i = 0; i < N; ++i) if (indeg[i] == 0) dq.push_back(i);

    int processed = 0;
    long long Cmax = 0;
    while (!dq.empty()) {
        int u = dq.front(); dq.pop_front();
        processed++;
        long long fu = est[u] + P.ptime[u];
        fin[u] = fu;
        if (fu > Cmax) Cmax = fu;
        for (int v : adj[u]) {
            if (fu >= est[v]) { // >= to keep last pred for deterministic tie-breaking
                est[v] = fu;
                cpred[v] = u;
            }
            if (--indeg[v] == 0) dq.push_back(v);
        }
    }
    ScheduleResult res;
    res.feasible = (processed == N);
    res.makespan = res.feasible ? Cmax : (long long)4e18;
    res.est = move(est);
    res.fin = move(fin);
    res.cpred = move(cpred);
    return res;
}

// Giffler-Thompson heuristic
MachineOrder giffler_thompson(const Problem& P, int rule, std::mt19937_64& rng) {
    MachineOrder mo;
    mo.seq.assign(P.M, vector<int>());
    for (int m = 0; m < P.M; ++m) mo.seq[m].reserve(P.J);

    vector<int> pos(P.J, 0);
    vector<long long> job_ready(P.J, 0);
    vector<long long> mach_ready(P.M, 0);

    // Precompute remaining work per job and pos
    vector<vector<long long>> rem = P.sufRem; // [j][pos]

    int total_ops = P.N;
    for (int step = 0; step < total_ops; ++step) {
        // Find operation with minimal earliest completion time among ready operations
        long long mu = LLONG_MAX;
        int best_j = -1, best_m = -1;
        long long best_est = 0;
        for (int j = 0; j < P.J; ++j) {
            if (pos[j] >= P.M) continue;
            int m = P.machine[j][pos[j]];
            long long p = P.proc[j][pos[j]];
            long long est = max(job_ready[j], mach_ready[m]);
            long long ect = est + p;
            if (ect < mu || (ect == mu && (est < best_est || (est == best_est && j < best_j)))) {
                mu = ect;
                best_j = j;
                best_m = m;
                best_est = est;
            }
        }

        // Conflict set S: ready ops on machine best_m with est < mu
        vector<int> cand;
        cand.reserve(P.J);
        for (int j = 0; j < P.J; ++j) {
            if (pos[j] >= P.M) continue;
            int m = P.machine[j][pos[j]];
            if (m != best_m) continue;
            long long est = max(job_ready[j], mach_ready[m]);
            if (est < mu) cand.push_back(j);
        }
        if (cand.empty()) cand.push_back(best_j); // should not happen

        auto choose_job = [&](const vector<int>& C) -> int {
            int chosen = C[0];
            // Score smaller is better unless noted
            auto get_score = [&](int j)->long double {
                int pj = pos[j];
                int m = P.machine[j][pj];
                long long p = P.proc[j][pj];
                long long est = max(job_ready[j], mach_ready[m]);
                long long rw = rem[j][pj]; // remaining including current
                switch (rule) {
                    case 0: // MWKR: choose max remaining work
                        return (long double)(-rw);
                    case 1: // SPT
                        return (long double)p;
                    case 2: // LPT
                        return (long double)(-p);
                    case 3: // EDD-like: earliest est
                        return (long double)est;
                    case 4: // SRPT: smallest remaining work
                        return (long double)rw;
                    case 5: { // Random
                        uniform_real_distribution<long double> dist(0.0L, 1.0L);
                        return dist(rng);
                    }
                    default: { // Hybrid
                        long double sc = 0.5L * (long double)est + 0.3L * (long double)p - 0.2L * (long double)rw;
                        return sc;
                    }
                }
            };
            long double best_sc = get_score(chosen);
            for (size_t i = 1; i < C.size(); ++i) {
                long double sc = get_score(C[i]);
                if (sc < best_sc - 1e-18L || (fabsl(sc - best_sc) <= 1e-18L && C[i] < chosen)) {
                    best_sc = sc;
                    chosen = C[i];
                }
            }
            return chosen;
        };

        int js = choose_job(cand);
        int m = P.machine[js][pos[js]];
        long long p = P.proc[js][pos[js]];
        long long st = max(job_ready[js], mach_ready[m]);
        long long ct = st + p;
        mo.seq[m].push_back(js);
        job_ready[js] = ct;
        mach_ready[m] = ct;
        pos[js]++;
    }
    return mo;
}

// Identify critical blocks and propose swap moves at block ends
vector<pair<int,int>> propose_moves(const Problem& P, const MachineOrder& order, const ScheduleResult& sched) {
    vector<pair<int,int>> moves;
    for (int m = 0; m < P.M; ++m) {
        const auto& seq = order.seq[m];
        if ((int)seq.size() <= 1) continue;
        vector<int> ops(seq.size());
        for (size_t k = 0; k < seq.size(); ++k) {
            int j = seq[k];
            int pos = P.posOfMachine[j][m];
            ops[k] = j * P.M + pos;
        }
        vector<char> critEdge(seq.size() - 1, 0);
        for (size_t k = 0; k + 1 < seq.size(); ++k) {
            int u = ops[k];
            int v = ops[k + 1];
            if (sched.cpred[v] == u) critEdge[k] = 1;
        }
        // Find contiguous blocks of critEdge==1
        int k = 0;
        while (k < (int)critEdge.size()) {
            if (!critEdge[k]) { k++; continue; }
            int start = k;
            while (k < (int)critEdge.size() && critEdge[k]) k++;
            int end = k - 1;
            int lpos = start;
            int rpos = end + 1; // last index in ops included
            // block positions in seq: from lpos to rpos inclusive
            int block_len = rpos - lpos + 1;
            if (block_len >= 2) {
                // propose swap at the beginning and at the end of the block
                moves.emplace_back(m, lpos);       // swap positions lpos and lpos+1
                moves.emplace_back(m, rpos - 1);   // swap positions rpos-1 and rpos
            }
        }
    }
    // Deduplicate moves
    sort(moves.begin(), moves.end());
    moves.erase(unique(moves.begin(), moves.end()), moves.end());
    return moves;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    Problem P;
    if (!(cin >> P.J >> P.M)) {
        return 0;
    }
    P.N = P.J * P.M;
    P.machine.assign(P.J, vector<int>(P.M));
    P.proc.assign(P.J, vector<long long>(P.M));
    P.posOfMachine.assign(P.J, vector<int>(P.M, -1));
    for (int j = 0; j < P.J; ++j) {
        for (int k = 0; k < P.M; ++k) {
            int m; long long p;
            cin >> m >> p;
            P.machine[j][k] = m;
            P.proc[j][k] = p;
            P.posOfMachine[j][m] = k;
        }
    }
    P.jobOf.resize(P.N);
    P.machOf.resize(P.N);
    P.posOf.resize(P.N);
    P.ptime.resize(P.N);
    for (int j = 0; j < P.J; ++j) {
        for (int k = 0; k < P.M; ++k) {
            int id = j * P.M + k;
            P.jobOf[id] = j;
            P.posOf[id] = k;
            P.machOf[id] = P.machine[j][k];
            P.ptime[id] = P.proc[j][k];
        }
    }
    // Precompute remaining sums
    P.sufRem.assign(P.J, vector<long long>(P.M + 1, 0));
    for (int j = 0; j < P.J; ++j) {
        for (int k = P.M - 1; k >= 0; --k) {
            P.sufRem[j][k] = P.proc[j][k] + P.sufRem[j][k + 1];
        }
    }

    // Time management
    auto t_start = chrono::steady_clock::now();
    auto now = [&]() { return chrono::steady_clock::now(); };
    auto elapsed = [&](double limit_sec) {
        chrono::duration<double> d = now() - t_start;
        return d.count() >= limit_sec;
    };
    double TIME_LIMIT = 1.85; // seconds, conservative

    std::mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    // Generate multiple initial solutions with various GT rules
    vector<int> rules = {0,1,2,3,4,5,6};
    MachineOrder best_order;
    long long best_makespan = LLONG_MAX;

    for (int r : rules) {
        if (elapsed(TIME_LIMIT * 0.4)) break; // reserve time for improvement
        MachineOrder mo = giffler_thompson(P, r, rng);
        ScheduleResult sr = compute_schedule(P, mo);
        if (sr.feasible && sr.makespan < best_makespan) {
            best_makespan = sr.makespan;
            best_order = move(mo);
        }
    }
    // If nothing generated (shouldn't happen), create a feasible GT with default
    if (best_order.seq.empty()) {
        best_order = giffler_thompson(P, 0, rng);
        ScheduleResult sr = compute_schedule(P, best_order);
        best_makespan = sr.makespan;
    }

    // Local improvement by swapping adjacent pairs at ends of critical blocks
    ScheduleResult best_sr = compute_schedule(P, best_order);
    best_makespan = best_sr.makespan;

    while (!elapsed(TIME_LIMIT)) {
        auto moves = propose_moves(P, best_order, best_sr);
        if (moves.empty()) break;
        bool improved = false;
        // First-improvement strategy
        for (auto [m, i] : moves) {
            MachineOrder cand = best_order;
            if (i < 0 || i + 1 >= (int)cand.seq[m].size()) continue;
            swap(cand.seq[m][i], cand.seq[m][i + 1]);
            ScheduleResult sr = compute_schedule(P, cand);
            if (!sr.feasible) continue;
            if (sr.makespan < best_makespan) {
                best_makespan = sr.makespan;
                best_order = move(cand);
                best_sr = move(sr);
                improved = true;
                break;
            }
            if (elapsed(TIME_LIMIT)) break;
        }
        if (!improved) break;
        if (elapsed(TIME_LIMIT)) break;
    }

    // Output machine orders
    for (int m = 0; m < P.M; ++m) {
        for (int jidx = 0; jidx < P.J; ++jidx) {
            if (jidx) cout << ' ';
            cout << best_order.seq[m][jidx];
        }
        cout << '\n';
    }
    return 0;
}