#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <cstdlib>
#include <ctime>
#include <climits>
#include <cmath>

using namespace std;

typedef long long ll;

int J, M;
vector<vector<int>> job_machine; // job_machine[j][k] = machine for k-th operation of job j
vector<vector<int>> job_time;    // processing time
vector<vector<int>> step_on_machine; // step_on_machine[j][m] = step index k for job j on machine m

// Compute makespan from machine orders (each machine: permutation of jobs)
// Returns -1 if the orders induce a cycle
ll compute_makespan(const vector<vector<int>>& orders) {
    int N = J * M;
    vector<ll> proc(N);
    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            int id = j * M + k;
            proc[id] = job_time[j][k];
        }
    }

    vector<vector<int>> adj(N);
    vector<int> indeg(N, 0);

    // Job precedence arcs
    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M - 1; ++k) {
            int u = j * M + k;
            int v = j * M + k + 1;
            adj[u].push_back(v);
            indeg[v]++;
        }
    }

    // Machine precedence arcs from orders
    for (int m = 0; m < M; ++m) {
        for (int p = 1; p < J; ++p) {
            int j1 = orders[m][p - 1];
            int j2 = orders[m][p];
            int k1 = step_on_machine[j1][m];
            int k2 = step_on_machine[j2][m];
            int u = j1 * M + k1;
            int v = j2 * M + k2;
            adj[u].push_back(v);
            indeg[v]++;
        }
    }

    // Topological sort with longest path calculation
    queue<int> q;
    vector<ll> start(N, 0);
    int processed = 0;
    for (int i = 0; i < N; ++i) {
        if (indeg[i] == 0) q.push(i);
    }
    while (!q.empty()) {
        int u = q.front(); q.pop();
        processed++;
        for (int v : adj[u]) {
            if (start[v] < start[u] + proc[u]) {
                start[v] = start[u] + proc[u];
            }
            indeg[v]--;
            if (indeg[v] == 0) q.push(v);
        }
    }
    if (processed != N) return -1; // cycle detected

    ll makespan = 0;
    for (int i = 0; i < N; ++i) {
        makespan = max(makespan, start[i] + proc[i]);
    }
    return makespan;
}

// Giffler-Thompson with given priority rule
// rule: 0=SPT, 1=LPT, 2=MWKR, 3=LWKR, 4=random
pair<vector<vector<int>>, ll> gt_schedule(int rule) {
    vector<int> next_op(J, 0);
    vector<ll> job_ready(J, 0);
    vector<ll> machine_ready(M, 0);
    vector<vector<int>> orders(M);
    vector<ll> work_rem(J, 0);
    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            work_rem[j] += job_time[j][k];
        }
    }

    while (true) {
        // Find machine with minimal earliest completion time
        vector<ll> machine_ect(M, LLONG_MAX);
        for (int j = 0; j < J; ++j) {
            if (next_op[j] == M) continue;
            int k = next_op[j];
            int m = job_machine[j][k];
            ll est = max(job_ready[j], machine_ready[m]);
            ll ect = est + job_time[j][k];
            if (ect < machine_ect[m]) {
                machine_ect[m] = ect;
            }
        }
        ll min_ect = LLONG_MAX;
        int m_star = -1;
        for (int m = 0; m < M; ++m) {
            if (machine_ect[m] < min_ect) {
                min_ect = machine_ect[m];
                m_star = m;
            }
        }
        if (m_star == -1) break; // all scheduled

        // Collect candidate jobs on m_star with est < min_ect
        vector<int> cand_jobs;
        for (int j = 0; j < J; ++j) {
            if (next_op[j] == M) continue;
            int k = next_op[j];
            if (job_machine[j][k] != m_star) continue;
            ll est = max(job_ready[j], machine_ready[m_star]);
            if (est < min_ect) {
                cand_jobs.push_back(j);
            }
        }

        int chosen_job = -1;
        if (rule == 0) { // SPT
            ll min_time = LLONG_MAX;
            for (int j : cand_jobs) {
                int k = next_op[j];
                ll t = job_time[j][k];
                if (t < min_time) {
                    min_time = t;
                    chosen_job = j;
                }
            }
        } else if (rule == 1) { // LPT
            ll max_time = 0;
            for (int j : cand_jobs) {
                int k = next_op[j];
                ll t = job_time[j][k];
                if (t > max_time) {
                    max_time = t;
                    chosen_job = j;
                }
            }
        } else if (rule == 2) { // MWKR
            ll max_work = -1;
            for (int j : cand_jobs) {
                if (work_rem[j] > max_work) {
                    max_work = work_rem[j];
                    chosen_job = j;
                }
            }
        } else if (rule == 3) { // LWKR
            ll min_work = LLONG_MAX;
            for (int j : cand_jobs) {
                if (work_rem[j] < min_work) {
                    min_work = work_rem[j];
                    chosen_job = j;
                }
            }
        } else { // random
            chosen_job = cand_jobs[rand() % cand_jobs.size()];
        }

        // Schedule chosen_job on m_star
        int k = next_op[chosen_job];
        ll start = max(job_ready[chosen_job], machine_ready[m_star]);
        job_ready[chosen_job] = start + job_time[chosen_job][k];
        machine_ready[m_star] = start + job_time[chosen_job][k];
        next_op[chosen_job]++;
        work_rem[chosen_job] -= job_time[chosen_job][k];
        orders[m_star].push_back(chosen_job);
    }

    ll makespan = compute_makespan(orders);
    return {orders, makespan};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    srand(time(0));

    // Read input
    cin >> J >> M;
    job_machine.assign(J, vector<int>(M));
    job_time.assign(J, vector<int>(M));
    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            cin >> job_machine[j][k] >> job_time[j][k];
        }
    }

    // Build step_on_machine
    step_on_machine.assign(J, vector<int>(M, -1));
    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            int m = job_machine[j][k];
            step_on_machine[j][m] = k;
        }
    }

    // Generate initial solutions with different rules
    vector<vector<int>> best_orders;
    ll best_makespan = LLONG_MAX;
    for (int rule = 0; rule < 5; ++rule) {
        auto [orders, makespan] = gt_schedule(rule);
        if (makespan != -1 && makespan < best_makespan) {
            best_makespan = makespan;
            best_orders = orders;
        }
    }

    // Simulated annealing improvement
    vector<vector<int>> current_orders = best_orders;
    ll current_makespan = best_makespan;
    double temperature = current_makespan * 0.1;
    const double cooling_rate = 0.9995;
    const int iterations = 20000;

    for (int iter = 0; iter < iterations; ++iter) {
        int m = rand() % M;
        if (J <= 1) continue;
        int i = rand() % (J - 1);
        vector<vector<int>> new_orders = current_orders;
        swap(new_orders[m][i], new_orders[m][i + 1]);
        ll new_makespan = compute_makespan(new_orders);
        if (new_makespan == -1) continue; // invalid swap

        ll delta = new_makespan - current_makespan;
        if (delta < 0 || (temperature > 0 && exp(-delta / temperature) > (rand() / (RAND_MAX + 1.0)))) {
            current_orders = new_orders;
            current_makespan = new_makespan;
            if (current_makespan < best_makespan) {
                best_makespan = current_makespan;
                best_orders = current_orders;
            }
        }
        temperature *= cooling_rate;
    }

    // Output best found orders
    for (int m = 0; m < M; ++m) {
        for (int i = 0; i < J; ++i) {
            cout << best_orders[m][i];
            if (i < J - 1) cout << ' ';
        }
        cout << '\n';
    }

    return 0;
}