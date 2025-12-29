#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <climits>

using namespace std;

int J, M;
vector<vector<pair<int, int>>> job_ops; // for each job: list of (machine, processing)
vector<vector<int>> step_on_machine; // step_on_machine[j][m] = step index k for job j on machine m

// compute makespan from machine permutations, return -1 if infeasible
long long compute_makespan(const vector<vector<int>>& perms) {
    int N = J * M;
    vector<long long> proc(N, 0);
    vector<vector<int>> adj(N);
    vector<int> indeg(N, 0);
    
    // assign processing times to nodes
    for (int j = 0; j < J; j++) {
        for (int k = 0; k < M; k++) {
            int node = j * M + k;
            proc[node] = job_ops[j][k].second;
        }
    }
    
    // job precedence edges
    for (int j = 0; j < J; j++) {
        for (int k = 0; k < M-1; k++) {
            int u = j * M + k;
            int v = j * M + k + 1;
            adj[u].push_back(v);
            indeg[v]++;
        }
    }
    
    // machine edges from permutations
    for (int m = 0; m < M; m++) {
        const vector<int>& order = perms[m];
        for (int i = 0; i < J-1; i++) {
            int job_a = order[i];
            int job_b = order[i+1];
            int step_a = step_on_machine[job_a][m];
            int step_b = step_on_machine[job_b][m];
            int u = job_a * M + step_a;
            int v = job_b * M + step_b;
            adj[u].push_back(v);
            indeg[v]++;
        }
    }
    
    // topological sort with longest path
    vector<long long> dist(N, 0);
    queue<int> q;
    for (int i = 0; i < N; i++) {
        if (indeg[i] == 0) q.push(i);
    }
    int processed = 0;
    while (!q.empty()) {
        int u = q.front(); q.pop();
        processed++;
        for (int v : adj[u]) {
            if (dist[v] < dist[u] + proc[u]) {
                dist[v] = dist[u] + proc[u];
            }
            indeg[v]--;
            if (indeg[v] == 0) q.push(v);
        }
    }
    if (processed != N) {
        return -1; // cycle detected
    }
    long long makespan = 0;
    for (int i = 0; i < N; i++) {
        makespan = max(makespan, dist[i] + proc[i]);
    }
    return makespan;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    cin >> J >> M;
    job_ops.assign(J, vector<pair<int, int>>(M));
    step_on_machine.assign(J, vector<int>(M, -1));
    
    for (int j = 0; j < J; j++) {
        for (int k = 0; k < M; k++) {
            int m, p;
            cin >> m >> p;
            job_ops[j][k] = {m, p};
            step_on_machine[j][m] = k;
        }
    }
    
    // --- Initial heuristic: active schedule using earliest completion time ---
    vector<int> next_op(J, 0);
    vector<long long> job_release(J, 0);
    vector<long long> machine_avail(M, 0);
    vector<vector<int>> machine_order(M);
    int scheduled = 0;
    
    while (scheduled < J * M) {
        long long best_completion = LLONG_MAX;
        int best_j = -1;
        int best_m = -1;
        long long best_start = -1;
        int best_p = -1;
        
        for (int j = 0; j < J; j++) {
            if (next_op[j] == M) continue;
            int k = next_op[j];
            int m = job_ops[j][k].first;
            int p = job_ops[j][k].second;
            long long start = max(job_release[j], machine_avail[m]);
            long long completion = start + p;
            // tie-breaking: smaller processing time, then smaller job index
            if (completion < best_completion ||
                (completion == best_completion && p < best_p) ||
                (completion == best_completion && p == best_p && j < best_j)) {
                best_completion = completion;
                best_j = j;
                best_m = m;
                best_start = start;
                best_p = p;
            }
        }
        // schedule the selected operation
        machine_avail[best_m] = best_start + best_p;
        job_release[best_j] = best_start + best_p;
        next_op[best_j]++;
        machine_order[best_m].push_back(best_j);
        scheduled++;
    }
    
    // --- Local improvement by adjacent swaps ---
    vector<vector<int>> best_perms = machine_order;
    long long best_makespan = compute_makespan(best_perms);
    
    bool improved = true;
    while (improved) {
        improved = false;
        for (int m = 0; m < M; m++) {
            for (int i = 0; i < J-1; i++) {
                // try swapping positions i and i+1 on machine m
                swap(best_perms[m][i], best_perms[m][i+1]);
                long long new_makespan = compute_makespan(best_perms);
                if (new_makespan != -1 && new_makespan < best_makespan) {
                    best_makespan = new_makespan;
                    improved = true;
                    // keep the swap
                } else {
                    // revert
                    swap(best_perms[m][i], best_perms[m][i+1]);
                }
            }
        }
    }
    
    // --- Output permutations ---
    for (int m = 0; m < M; m++) {
        for (int i = 0; i < J; i++) {
            cout << best_perms[m][i];
            if (i != J-1) cout << ' ';
        }
        cout << '\n';
    }
    
    return 0;
}