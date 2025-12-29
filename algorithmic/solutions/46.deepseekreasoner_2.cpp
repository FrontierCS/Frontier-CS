#include <bits/stdc++.h>
using namespace std;

int J, M;
vector<vector<int>> route; // [J][M]
vector<vector<int>> proc;  // [J][M]
vector<vector<int>> job_mach_step; // [J][M] -> step index

const int INF = 1e9;

enum Rule { LPT, SPT, MWR, RANDOM };

vector<vector<int>> generate_GT(Rule rule) {
    vector<int> next_op(J, 0);
    vector<long long> job_available(J, 0);
    vector<long long> machine_available(M, 0);
    vector<vector<int>> mach_orders(M);
    vector<long long> remaining_work(J);
    for (int j = 0; j < J; j++) {
        remaining_work[j] = accumulate(proc[j].begin(), proc[j].end(), 0LL);
    }

    mt19937 rng(12345);

    int scheduled = 0;
    while (scheduled < J * M) {
        long long c_min = 1LL << 62;
        int m_star = -1;
        for (int j = 0; j < J; j++) {
            if (next_op[j] >= M) continue;
            int k = next_op[j];
            int m = route[j][k];
            long long s = max(job_available[j], machine_available[m]);
            long long c = s + proc[j][k];
            if (c < c_min) {
                c_min = c;
                m_star = m;
            }
        }
        vector<int> conflict;
        for (int j = 0; j < J; j++) {
            if (next_op[j] >= M) continue;
            int k = next_op[j];
            if (route[j][k] != m_star) continue;
            long long s = max(job_available[j], machine_available[m_star]);
            if (s < c_min) {
                conflict.push_back(j);
            }
        }
        int chosen_j = -1;
        if (rule == LPT) {
            int best_p = -1;
            for (int j : conflict) {
                int k = next_op[j];
                if (proc[j][k] > best_p) {
                    best_p = proc[j][k];
                    chosen_j = j;
                }
            }
        } else if (rule == SPT) {
            int best_p = INF;
            for (int j : conflict) {
                int k = next_op[j];
                if (proc[j][k] < best_p) {
                    best_p = proc[j][k];
                    chosen_j = j;
                }
            }
        } else if (rule == MWR) {
            long long best_r = -1;
            for (int j : conflict) {
                if (remaining_work[j] > best_r) {
                    best_r = remaining_work[j];
                    chosen_j = j;
                }
            }
        } else if (rule == RANDOM) {
            uniform_int_distribution<int> dist(0, conflict.size()-1);
            chosen_j = conflict[dist(rng)];
        }
        int k = next_op[chosen_j];
        long long start = max(job_available[chosen_j], machine_available[m_star]);
        next_op[chosen_j]++;
        job_available[chosen_j] = start + proc[chosen_j][k];
        machine_available[m_star] = start + proc[chosen_j][k];
        remaining_work[chosen_j] -= proc[chosen_j][k];
        mach_orders[m_star].push_back(chosen_j);
        scheduled++;
    }
    return mach_orders;
}

int compute_makespan(const vector<vector<int>>& orders) {
    int N = J * M;
    vector<vector<pair<int, int>>> graph(N);
    vector<int> indeg(N, 0);
    for (int j = 0; j < J; j++) {
        for (int k = 0; k < M-1; k++) {
            int u = j * M + k;
            int v = j * M + k + 1;
            int w = proc[j][k];
            graph[u].emplace_back(v, w);
            indeg[v]++;
        }
    }
    for (int m = 0; m < M; m++) {
        const vector<int>& seq = orders[m];
        for (int idx = 0; idx < J-1; idx++) {
            int j1 = seq[idx];
            int j2 = seq[idx+1];
            int k1 = job_mach_step[j1][m];
            int k2 = job_mach_step[j2][m];
            int u = j1 * M + k1;
            int v = j2 * M + k2;
            int w = proc[j1][k1];
            graph[u].emplace_back(v, w);
            indeg[v]++;
        }
    }
    vector<int> dist(N, 0);
    queue<int> q;
    for (int i = 0; i < N; i++) {
        if (indeg[i] == 0) q.push(i);
    }
    int processed = 0;
    while (!q.empty()) {
        int u = q.front(); q.pop();
        processed++;
        for (auto& edge : graph[u]) {
            int v = edge.first;
            int w = edge.second;
            if (dist[u] + w > dist[v]) {
                dist[v] = dist[u] + w;
            }
            indeg[v]--;
            if (indeg[v] == 0) {
                q.push(v);
            }
        }
    }
    if (processed != N) {
        return INF;
    }
    int makespan = 0;
    for (int j = 0; j < J; j++) {
        for (int k = 0; k < M; k++) {
            int node = j * M + k;
            makespan = max(makespan, dist[node] + proc[j][k]);
        }
    }
    return makespan;
}

void local_search(vector<vector<int>>& orders, int& makespan) {
    bool improved = true;
    while (improved) {
        improved = false;
        int best_new_makespan = makespan;
        int best_m = -1, best_i = -1;
        for (int m = 0; m < M; m++) {
            for (int i = 0; i < J-1; i++) {
                swap(orders[m][i], orders[m][i+1]);
                int new_make = compute_makespan(orders);
                if (new_make < best_new_makespan) {
                    best_new_makespan = new_make;
                    best_m = m;
                    best_i = i;
                }
                swap(orders[m][i], orders[m][i+1]);
            }
        }
        if (best_new_makespan < makespan) {
            swap(orders[best_m][best_i], orders[best_m][best_i+1]);
            makespan = best_new_makespan;
            improved = true;
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    cin >> J >> M;
    route.assign(J, vector<int>(M));
    proc.assign(J, vector<int>(M));
    job_mach_step.assign(J, vector<int>(M, -1));
    for (int j = 0; j < J; j++) {
        for (int k = 0; k < M; k++) {
            int m, p;
            cin >> m >> p;
            route[j][k] = m;
            proc[j][k] = p;
            job_mach_step[j][m] = k;
        }
    }

    vector<vector<int>> best_orders;
    int best_makespan = INF;

    vector<Rule> rules = {LPT, SPT, MWR, RANDOM};
    for (Rule rule : rules) {
        vector<vector<int>> orders = generate_GT(rule);
        bool ok = true;
        for (int m = 0; m < M; m++) {
            if ((int)orders[m].size() != J) {
                ok = false;
                break;
            }
            vector<bool> seen(J, false);
            for (int j : orders[m]) {
                if (j < 0 || j >= J || seen[j]) {
                    ok = false;
                    break;
                }
                seen[j] = true;
            }
            if (!ok) break;
        }
        if (!ok) continue;

        int makespan = compute_makespan(orders);
        if (makespan == INF) continue;

        local_search(orders, makespan);

        if (makespan < best_makespan) {
            best_makespan = makespan;
            best_orders = orders;
        }
    }

    for (int m = 0; m < M; m++) {
        for (int i = 0; i < J; i++) {
            if (i) cout << ' ';
            cout << best_orders[m][i];
        }
        cout << '\n';
    }

    return 0;
}