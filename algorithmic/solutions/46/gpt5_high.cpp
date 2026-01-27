#include <bits/stdc++.h>
using namespace std;

using ll = long long;

struct EvalResult {
    bool feasible;
    long long makespan;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int J, M;
    if (!(cin >> J >> M)) {
        return 0;
    }
    vector<vector<int>> mach(J, vector<int>(M));
    vector<vector<int>> proc(J, vector<int>(M));
    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            int m, p;
            cin >> m >> p;
            mach[j][k] = m;
            proc[j][k] = p;
        }
    }

    // Precompute mappings
    int N = J * M;
    auto nodeId = [&](int j, int k) { return j * M + k; };

    vector<vector<int>> posInJob(J, vector<int>(M, -1));
    vector<vector<int>> nodeOfJobMachine(J, vector<int>(M, -1));
    vector<int> nodeMachine(N), nodeProc(N), nodeJob(N), nodeK(N);
    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            int id = nodeId(j, k);
            int m = mach[j][k];
            posInJob[j][m] = k;
            nodeOfJobMachine[j][m] = id;
            nodeMachine[id] = m;
            nodeProc[id] = proc[j][k];
            nodeJob[id] = j;
            nodeK[id] = k;
        }
    }

    // Job predecessor/successor (constant across evaluations)
    vector<int> prevJob(N, -1), nextJob(N, -1);
    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            int id = nodeId(j, k);
            if (k > 0) prevJob[id] = nodeId(j, k - 1);
            if (k + 1 < M) nextJob[id] = nodeId(j, k + 1);
        }
    }

    // Machine total loads and job totals
    vector<ll> machineTotal(M, 0), jobTotal(J, 0);
    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            machineTotal[mach[j][k]] += proc[j][k];
            jobTotal[j] += proc[j][k];
        }
    }

    auto evaluate = [&](const vector<vector<int>>& orders) -> EvalResult {
        vector<int> prevMach(N, -1), nextMach(N, -1);
        for (int m = 0; m < M; ++m) {
            const auto& seq = orders[m];
            int prev = -1;
            for (int i = 0; i < (int)seq.size(); ++i) {
                int j = seq[i];
                int id = nodeOfJobMachine[j][m];
                if (prev != -1) {
                    prevMach[id] = prev;
                    nextMach[prev] = id;
                }
                prev = id;
            }
        }
        vector<int> indeg(N, 0);
        for (int id = 0; id < N; ++id) {
            if (prevJob[id] != -1) indeg[id]++;
            if (prevMach[id] != -1) indeg[id]++;
        }
        deque<int> dq;
        for (int id = 0; id < N; ++id) if (indeg[id] == 0) dq.push_back(id);

        vector<ll> finish(N, 0);
        int processed = 0;
        ll makespan = 0;
        while (!dq.empty()) {
            int u = dq.front(); dq.pop_front();
            ++processed;
            ll s = 0;
            if (prevJob[u] != -1) s = max(s, finish[prevJob[u]]);
            if (prevMach[u] != -1) s = max(s, finish[prevMach[u]]);
            finish[u] = s + nodeProc[u];
            makespan = max(makespan, finish[u]);
            int vj = nextJob[u];
            if (vj != -1) {
                if (--indeg[vj] == 0) dq.push_back(vj);
            }
            int vm = nextMach[u];
            if (vm != -1) {
                if (--indeg[vm] == 0) dq.push_back(vm);
            }
        }
        if (processed != N) return {false, (ll)0};
        return {true, makespan};
    };

    // Serial SGS with various dispatching rules
    std::mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    auto generate_schedule = [&](int strategy, int rcl_size) -> vector<vector<int>> {
        vector<vector<int>> orders(M);
        vector<int> k(J, 0);
        vector<ll> jobReady(J, 0), machineReady(M, 0);
        vector<ll> sumRemJob = jobTotal;
        vector<ll> sumRemMach = machineTotal;

        int remaining = N;
        while (remaining > 0) {
            vector<pair<double, int>> cand; // (score, job)
            cand.reserve(J);
            for (int j = 0; j < J; ++j) {
                if (k[j] >= M) continue;
                int m = mach[j][k[j]];
                int p = proc[j][k[j]];
                ll s = max(jobReady[j], machineReady[m]);
                ll c = s + p;
                double score = 0.0;
                switch (strategy) {
                    case 0: // ECT
                        score = (double)c;
                        break;
                    case 1: // ERD
                        score = (double)s;
                        break;
                    case 2: // SPT
                        score = (double)p;
                        break;
                    case 3: // LPT
                        score = -(double)p;
                        break;
                    case 4: // MIN remaining job
                        score = (double)sumRemJob[j];
                        break;
                    case 5: // MAX remaining job
                        score = -(double)sumRemJob[j];
                        break;
                    case 6: // Machine criticality first
                        score = -(double)sumRemMach[m] + 0.001 * (double)s;
                        break;
                    case 7: // ECT + remaining job
                        score = (double)c + 0.2 * (double)sumRemJob[j];
                        break;
                    default: { // randomized weighted
                        double w1 = uniform_real_distribution<double>(0.0, 1.0)(rng);
                        double w2 = uniform_real_distribution<double>(0.0, 1.0)(rng);
                        double w3 = uniform_real_distribution<double>(0.0, 1.0)(rng);
                        double w4 = uniform_real_distribution<double>(0.0, 1.0)(rng);
                        score = w1 * (double)s + w2 * (double)c + w3 * (double)p - w4 * (double)sumRemMach[m];
                        break;
                    }
                }
                // small noise to break ties
                score += uniform_real_distribution<double>(-1e-7, 1e-7)(rng);
                cand.emplace_back(score, j);
            }
            int nAvail = (int)cand.size();
            if (nAvail == 0) break; // should not happen
            int ksel = min(max(1, rcl_size), nAvail);
            nth_element(cand.begin(), cand.begin() + (ksel - 1), cand.end(), [](const auto& a, const auto& b) {
                if (a.first != b.first) return a.first < b.first;
                return a.second < b.second;
            });
            double cutoff = cand[ksel - 1].first;
            vector<int> pool;
            pool.reserve(ksel);
            for (auto &pr : cand) {
                if ((int)pool.size() >= ksel) break;
                if (pr.first <= cutoff) pool.push_back(pr.second);
            }
            int chosenIdx = pool[uniform_int_distribution<int>(0, (int)pool.size() - 1)(rng)];
            int j = chosenIdx;
            int kk = k[j];
            int m = mach[j][kk];
            int p = proc[j][kk];
            ll s = max(jobReady[j], machineReady[m]);
            ll f = s + p;
            // schedule
            orders[m].push_back(j);
            jobReady[j] = f;
            machineReady[m] = f;
            sumRemJob[j] -= p;
            sumRemMach[m] -= p;
            k[j]++;
            remaining--;
        }
        // Ensure orders contain all jobs for each machine (should be true)
        for (int m = 0; m < M; ++m) {
            if ((int)orders[m].size() < J) {
                // Fill any missing jobs in arbitrary order
                vector<char> seen(J, false);
                for (int x : orders[m]) seen[x] = true;
                for (int j = 0; j < J; ++j) if (!seen[j]) orders[m].push_back(j);
            }
        }
        return orders;
    };

    // Time management
    auto start_time = chrono::steady_clock::now();
    auto time_limit = start_time + chrono::milliseconds(1900);

    // Multiple runs with different strategies
    vector<vector<int>> bestOrders;
    ll bestMakespan = (1LL<<62);
    bool hasBest = false;

    vector<int> strategies = {0, 4, 7, 2, 3, 6, 1, 8};
    int run_count = 0;

    auto try_schedule = [&](int strategy, int rcl) {
        auto orders = generate_schedule(strategy, rcl);
        EvalResult er = evaluate(orders);
        if (er.feasible) {
            if (!hasBest || er.makespan < bestMakespan) {
                bestMakespan = er.makespan;
                bestOrders = orders;
                hasBest = true;
            }
        }
    };

    // Deterministic seeds: a few specific runs
    for (int s : strategies) {
        if (chrono::steady_clock::now() > time_limit) break;
        try_schedule(s, 1);
        run_count++;
        if (chrono::steady_clock::now() > time_limit) break;
        try_schedule(s, 3);
        run_count++;
    }

    // Randomized extra runs
    while (chrono::steady_clock::now() < time_limit) {
        int s = strategies[uniform_int_distribution<int>(0, (int)strategies.size() - 1)(rng)];
        int rcl = uniform_int_distribution<int>(1, 5)(rng);
        try_schedule(s, rcl);
        run_count++;
        if (run_count > 400) break; // safety bound
    }

    if (!hasBest) {
        // Fallback: simple order by job id on every machine
        bestOrders.assign(M, vector<int>(J));
        for (int m = 0; m < M; ++m) {
            iota(bestOrders[m].begin(), bestOrders[m].end(), 0);
        }
        // No need to evaluate here
    } else {
        // Local improvement via adjacent swaps (first improvement), within remaining time
        auto now = chrono::steady_clock::now();
        while (now < time_limit) {
            bool improved = false;
            for (int m = 0; m < M && chrono::steady_clock::now() < time_limit; ++m) {
                auto &seq = bestOrders[m];
                for (int i = 0; i + 1 < (int)seq.size(); ++i) {
                    swap(seq[i], seq[i + 1]);
                    EvalResult er = evaluate(bestOrders);
                    if (er.feasible && er.makespan < bestMakespan) {
                        bestMakespan = er.makespan;
                        improved = true;
                        break; // keep this swap
                    } else {
                        swap(seq[i], seq[i + 1]); // revert
                    }
                }
                if (improved) break;
            }
            if (!improved) break;
            now = chrono::steady_clock::now();
        }
    }

    // Output exactly M lines, each a permutation of 0..J-1
    for (int m = 0; m < M; ++m) {
        for (int i = 0; i < J; ++i) {
            if (i) cout << ' ';
            cout << bestOrders[m][i];
        }
        cout << '\n';
    }
    return 0;
}