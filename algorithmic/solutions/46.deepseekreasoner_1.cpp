#include <bits/stdc++.h>
using namespace std;

struct Solution {
    vector<vector<int>> perms; // per machine
    int makespan;
};

// Global problem data
int J, M;
vector<vector<pair<int,int>>> job_ops; // for each job: vector of (machine, time)
vector<vector<int>> job_step; // job_step[j][m] = step index of job j on machine m

// Helper: compute position matrix
vector<vector<int>> get_pos_matrix(const vector<vector<int>>& perms) {
    vector<vector<int>> pos(J, vector<int>(M, -1));
    for (int m = 0; m < M; ++m) {
        for (int idx = 0; idx < J; ++idx) {
            int j = perms[m][idx];
            pos[j][m] = idx;
        }
    }
    return pos;
}

// Compute makespan from permutations, return -1 if infeasible
int compute_makespan(const vector<vector<int>>& perms) {
    vector<vector<int>> pos = get_pos_matrix(perms);
    vector<vector<int>> indeg(J, vector<int>(M, 0));
    vector<vector<int>> comp(J, vector<int>(M, 0));
    // Build indegrees by iterating over all operations as predecessors
    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            int m = job_ops[j][k].first;
            // job successor
            if (k < M-1) {
                indeg[j][k+1]++;
            }
            // machine successor
            int p = pos[j][m];
            if (p < J-1) {
                int j_next = perms[m][p+1];
                int k_next = job_step[j_next][m];
                indeg[j_next][k_next]++;
            }
        }
    }
    queue<pair<int,int>> q;
    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            if (indeg[j][k] == 0) {
                q.push({j, k});
            }
        }
    }
    int processed = 0;
    while (!q.empty()) {
        auto [j, k] = q.front(); q.pop();
        processed++;
        int m = job_ops[j][k].first;
        int pt = job_ops[j][k].second;
        // job successor
        if (k < M-1) {
            int j2 = j, k2 = k+1;
            comp[j2][k2] = max(comp[j2][k2], comp[j][k] + pt);
            indeg[j2][k2]--;
            if (indeg[j2][k2] == 0) q.push({j2, k2});
        }
        // machine successor
        int p = pos[j][m];
        if (p < J-1) {
            int j_next = perms[m][p+1];
            int k_next = job_step[j_next][m];
            comp[j_next][k_next] = max(comp[j_next][k_next], comp[j][k] + pt);
            indeg[j_next][k_next]--;
            if (indeg[j_next][k_next] == 0) q.push({j_next, k_next});
        }
    }
    if (processed != J * M) return -1; // cycle detected
    int makespan = 0;
    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            makespan = max(makespan, comp[j][k] + job_ops[j][k].second);
        }
    }
    return makespan;
}

// Generate initial solution using dispatcher with earliest completion time first
Solution generate_initial() {
    vector<int> next_op(J, 0);
    vector<int> job_ready(J, 0);
    vector<int> machine_free(M, 0);
    vector<vector<int>> perms(M);
    int scheduled = 0;
    while (scheduled < J * M) {
        int best_j = -1;
        int best_ect = INT_MAX;
        int best_pt = INT_MAX;
        for (int j = 0; j < J; ++j) {
            if (next_op[j] >= M) continue;
            int k = next_op[j];
            int m = job_ops[j][k].first;
            int pt = job_ops[j][k].second;
            int est = max(job_ready[j], machine_free[m]);
            int ect = est + pt;
            if (ect < best_ect || (ect == best_ect && pt < best_pt)) {
                best_ect = ect;
                best_pt = pt;
                best_j = j;
            }
        }
        int j = best_j;
        int k = next_op[j];
        int m = job_ops[j][k].first;
        int pt = job_ops[j][k].second;
        int est = max(job_ready[j], machine_free[m]);
        int ect = est + pt;
        machine_free[m] = ect;
        job_ready[j] = ect;
        next_op[j]++;
        perms[m].push_back(j);
        scheduled++;
    }
    int makespan = compute_makespan(perms);
    return {perms, makespan};
}

// Simulated annealing
Solution simulated_annealing(Solution initial, int iterations, double initial_temp, double cooling_rate) {
    Solution current = initial;
    Solution best = initial;
    double temp = initial_temp;
    random_device rd;
    mt19937 gen(rd());
    uniform_int_distribution<> machine_dist(0, M-1);
    uniform_int_distribution<> pos_dist(0, J-2);
    uniform_real_distribution<> prob(0.0, 1.0);
    
    for (int iter = 0; iter < iterations; ++iter) {
        int m = machine_dist(gen);
        int i = pos_dist(gen);
        if (current.perms[m].size() <= i+1) continue;
        vector<vector<int>> new_perms = current.perms;
        swap(new_perms[m][i], new_perms[m][i+1]);
        int new_makespan = compute_makespan(new_perms);
        if (new_makespan == -1) continue;
        int delta = new_makespan - current.makespan;
        if (delta < 0 || exp(-delta / temp) > prob(gen)) {
            current.perms = new_perms;
            current.makespan = new_makespan;
            if (current.makespan < best.makespan) {
                best = current;
            }
        }
        temp *= cooling_rate;
    }
    return best;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    cin >> J >> M;
    job_ops.resize(J, vector<pair<int,int>>(M));
    job_step.resize(J, vector<int>(M));
    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            int m, p;
            cin >> m >> p;
            job_ops[j][k] = {m, p};
            job_step[j][m] = k;
        }
    }
    
    Solution initial = generate_initial();
    
    int iterations = 50000;
    double initial_temp = 0.144 * initial.makespan;
    if (initial_temp < 1e-6) initial_temp = 1.0;
    double cooling_rate = 0.9995;
    
    Solution best = simulated_annealing(initial, iterations, initial_temp, cooling_rate);
    
    for (int m = 0; m < M; ++m) {
        for (int idx = 0; idx < J; ++idx) {
            cout << best.perms[m][idx];
            if (idx < J-1) cout << " ";
        }
        cout << "\n";
    }
    
    return 0;
}