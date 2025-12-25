#include <iostream>
#include <vector>
#include <algorithm>
#include <queue>
#include <random>
#include <chrono>
#include <climits>

using namespace std;

typedef long long ll;

const ll INF = 1LL << 60;

enum class Rule { SPT, LPT, MWKR, LWKR, EST, ECT, RANDOM };

struct Candidate {
    int j;      // job index
    int k;      // operation index within job
    int m;      // machine
    ll s;       // earliest possible start time
    int p;      // processing time
    ll rem;     // remaining work of the job
};

// Compute makespan from machine orders.
// Returns INF if orders induce a cycle.
ll compute_makespan(const vector<vector<int>>& orders,
                    const vector<vector<int>>& machine,
                    const vector<vector<int>>& proc,
                    const vector<vector<int>>& job_mac_idx,
                    int J, int M) {
    int N = J * M;
    vector<int> machine_of(N), proc_of(N);
    vector<int> prev_job(N, -1), next_job(N, -1);
    vector<int> prev_mach(N, -1), next_mach(N, -1);

    // Build job chains and store machine & processing time per operation.
    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            int id = j * M + k;
            machine_of[id] = machine[j][k];
            proc_of[id] = proc[j][k];
            if (k > 0) prev_job[id] = id - 1;
            if (k < M - 1) next_job[id] = id + 1;
        }
    }

    // Build machine chains from orders.
    for (int m = 0; m < M; ++m) {
        const vector<int>& ord = orders[m];
        vector<int> op_ids;
        for (int pos = 0; pos < J; ++pos) {
            int j = ord[pos];
            int k = job_mac_idx[j][m];
            int id = j * M + k;
            op_ids.push_back(id);
        }
        for (int pos = 0; pos < J; ++pos) {
            int id = op_ids[pos];
            if (pos > 0) prev_mach[id] = op_ids[pos - 1];
            if (pos < J - 1) next_mach[id] = op_ids[pos + 1];
        }
    }

    // Topological sort (longest path).
    vector<int> indeg(N, 0);
    for (int id = 0; id < N; ++id) {
        if (prev_job[id] != -1) indeg[id]++;
        if (prev_mach[id] != -1) indeg[id]++;
    }
    queue<int> q;
    for (int id = 0; id < N; ++id)
        if (indeg[id] == 0) q.push(id);

    vector<ll> start(N, 0);
    int processed = 0;
    while (!q.empty()) {
        int id = q.front(); q.pop();
        processed++;
        ll finish = start[id] + proc_of[id];
        if (next_job[id] != -1) {
            int sid = next_job[id];
            start[sid] = max(start[sid], finish);
            if (--indeg[sid] == 0) q.push(sid);
        }
        if (next_mach[id] != -1) {
            int sid = next_mach[id];
            start[sid] = max(start[sid], finish);
            if (--indeg[sid] == 0) q.push(sid);
        }
    }
    if (processed != N) return INF; // cycle detected

    ll makespan = 0;
    for (int id = 0; id < N; ++id)
        makespan = max(makespan, start[id] + proc_of[id]);
    return makespan;
}

// Constructive heuristic: greedy dispatch with a given rule.
pair<ll, vector<vector<int>>> simulate(Rule rule,
                                       const vector<vector<int>>& machine,
                                       const vector<vector<int>>& proc,
                                       const vector<vector<int>>& job_mac_idx,
                                       const vector<ll>& total_work,
                                       int J, int M, int seed) {
    vector<int> job_next(J, 0);
    vector<ll> job_ready(J, 0);
    vector<ll> machine_free(M, 0);
    vector<ll> remaining_work = total_work;
    vector<vector<ll>> start(J, vector<ll>(M, -1));

    mt19937 rng(seed);
    int unscheduled = J * M;

    while (unscheduled > 0) {
        vector<Candidate> cand;
        for (int j = 0; j < J; ++j) {
            if (job_next[j] >= M) continue;
            int k = job_next[j];
            int m = machine[j][k];
            ll s = max(job_ready[j], machine_free[m]);
            int p = proc[j][k];
            cand.push_back({j, k, m, s, p, remaining_work[j]});
        }

        int idx = 0;
        if (rule == Rule::SPT) {
            idx = min_element(cand.begin(), cand.end(),
                              [](const Candidate& a, const Candidate& b) { return a.p < b.p; }) - cand.begin();
        } else if (rule == Rule::LPT) {
            idx = max_element(cand.begin(), cand.end(),
                              [](const Candidate& a, const Candidate& b) { return a.p < b.p; }) - cand.begin();
        } else if (rule == Rule::MWKR) {
            idx = max_element(cand.begin(), cand.end(),
                              [](const Candidate& a, const Candidate& b) { return a.rem < b.rem; }) - cand.begin();
        } else if (rule == Rule::LWKR) {
            idx = min_element(cand.begin(), cand.end(),
                              [](const Candidate& a, const Candidate& b) { return a.rem < b.rem; }) - cand.begin();
        } else if (rule == Rule::EST) {
            idx = min_element(cand.begin(), cand.end(),
                              [](const Candidate& a, const Candidate& b) { return a.s < b.s; }) - cand.begin();
        } else if (rule == Rule::ECT) {
            idx = min_element(cand.begin(), cand.end(),
                              [](const Candidate& a, const Candidate& b) { return a.s + a.p < b.s + b.p; }) - cand.begin();
        } else if (rule == Rule::RANDOM) {
            uniform_int_distribution<int> dist(0, cand.size() - 1);
            idx = dist(rng);
        }

        Candidate best = cand[idx];
        start[best.j][best.k] = best.s;
        job_ready[best.j] = best.s + best.p;
        machine_free[best.m] = best.s + best.p;
        remaining_work[best.j] -= best.p;
        job_next[best.j]++;
        unscheduled--;
    }

    // Extract machine orders from start times.
    vector<vector<int>> orders(M);
    for (int m = 0; m < M; ++m) {
        vector<pair<ll, int>> list;
        for (int j = 0; j < J; ++j) {
            int k = job_mac_idx[j][m];
            ll st = start[j][k];
            list.emplace_back(st, j);
        }
        sort(list.begin(), list.end());
        orders[m].resize(J);
        for (int i = 0; i < J; ++i) orders[m][i] = list[i].second;
    }

    ll makespan = 0;
    for (int j = 0; j < J; ++j) makespan = max(makespan, job_ready[j]);
    return {makespan, orders};
}

// Hill climbing with adjacent swaps (first improvement).
void hill_climbing(vector<vector<int>>& orders, ll& best_makespan,
                   const vector<vector<int>>& machine,
                   const vector<vector<int>>& proc,
                   const vector<vector<int>>& job_mac_idx,
                   int J, int M) {
    bool improved = true;
    while (improved) {
        improved = false;
        for (int m = 0; m < M && !improved; ++m) {
            for (int i = 0; i < J - 1 && !improved; ++i) {
                swap(orders[m][i], orders[m][i + 1]);
                ll new_makespan = compute_makespan(orders, machine, proc, job_mac_idx, J, M);
                if (new_makespan < best_makespan) {
                    best_makespan = new_makespan;
                    improved = true;
                } else {
                    swap(orders[m][i], orders[m][i + 1]); // revert
                }
            }
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int J, M;
    cin >> J >> M;

    vector<vector<int>> machine(J, vector<int>(M));
    vector<vector<int>> proc(J, vector<int>(M));
    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            cin >> machine[j][k] >> proc[j][k];
        }
    }

    // Precompute for each job the operation index on each machine.
    vector<vector<int>> job_mac_idx(J, vector<int>(M));
    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            int m = machine[j][k];
            job_mac_idx[j][m] = k;
        }
    }

    // Total work per job.
    vector<ll> total_work(J, 0);
    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            total_work[j] += proc[j][k];
        }
    }

    // Try deterministic rules.
    vector<Rule> det_rules = {Rule::SPT, Rule::LPT, Rule::MWKR, Rule::LWKR, Rule::EST, Rule::ECT};
    ll best_makespan = INF;
    vector<vector<int>> best_orders;

    for (Rule rule : det_rules) {
        auto [makespan, orders] = simulate(rule, machine, proc, job_mac_idx, total_work, J, M, 0);
        if (makespan < best_makespan) {
            best_makespan = makespan;
            best_orders = orders;
        }
    }

    // Try random dispatches (5 times).
    unsigned seed = chrono::system_clock::now().time_since_epoch().count();
    for (int r = 0; r < 5; ++r) {
        auto [makespan, orders] = simulate(Rule::RANDOM, machine, proc, job_mac_idx, total_work, J, M, seed + r);
        if (makespan < best_makespan) {
            best_makespan = makespan;
            best_orders = orders;
        }
    }

    // Improve by local search.
    hill_climbing(best_orders, best_makespan, machine, proc, job_mac_idx, J, M);

    // Output.
    for (int m = 0; m < M; ++m) {
        for (int i = 0; i < J; ++i) {
            cout << best_orders[m][i];
            if (i < J - 1) cout << ' ';
        }
        cout << '\n';
    }

    return 0;
}