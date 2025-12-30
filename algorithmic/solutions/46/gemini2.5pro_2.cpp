#include <iostream>
#include <vector>
#include <algorithm>
#include <chrono>
#include <random>
#include <cmath>
#include <numeric>
#include <tuple>

using namespace std;

// Problem data
int J, M;
vector<vector<pair<int, int>>> jobs; // jobs[j][k] = {machine, proc_time}

// Precomputed data for faster access
vector<vector<int>> op_k_on_machine; // op_k_on_machine[j][m] = k

struct Solution {
    vector<vector<int>> machine_perms;
    long long makespan;
};

// Global best solution found
Solution best_solution;

// For SA
mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

void precompute_data() {
    op_k_on_machine.assign(J, vector<int>(M, 0));
    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            int machine = jobs[j][k].first;
            op_k_on_machine[j][machine] = k;
        }
    }
}

void calculate_makespan(Solution& sol, vector<pair<int, int>>* critical_path = nullptr) {
    vector<vector<int>> pos_on_machine(M, vector<int>(J));
    for (int m = 0; m < M; ++m) {
        for (int i = 0; i < J; ++i) {
            pos_on_machine[m][sol.machine_perms[m][i]] = i;
        }
    }

    vector<vector<long long>> completion_times(J, vector<long long>(M, 0));

    for (int iter = 0; iter < J * M + 2; ++iter) {
        bool changed = false;
        for (int j = 0; j < J; ++j) {
            for (int k = 0; k < M; ++k) {
                int m = jobs[j][k].first;
                int p = jobs[j][k].second;

                long long job_prec_completion = (k > 0) ? completion_times[j][k - 1] : 0;
                
                long long machine_prec_completion = 0;
                int pos = pos_on_machine[m][j];
                if (pos > 0) {
                    int prev_job = sol.machine_perms[m][pos - 1];
                    int prev_job_k = op_k_on_machine[prev_job][m];
                    machine_prec_completion = completion_times[prev_job][prev_job_k];
                }

                long long new_completion_time = max(job_prec_completion, machine_prec_completion) + p;
                if (completion_times[j][k] != new_completion_time) {
                    completion_times[j][k] = new_completion_time;
                    changed = true;
                }
            }
        }
        if (!changed && iter > 0) break;
    }

    long long max_completion_time = 0;
    int last_job = -1;
    for (int j = 0; j < J; ++j) {
        if (completion_times[j][M - 1] > max_completion_time) {
            max_completion_time = completion_times[j][M - 1];
            last_job = j;
        }
    }
    sol.makespan = max_completion_time;

    if (critical_path) {
        critical_path->clear();
        if (last_job == -1) return;
        pair<int, int> current_op = {last_job, M - 1};
        
        while (current_op.first != -1) {
            critical_path->push_back(current_op);
            int j = current_op.first;
            int k = current_op.second;

            long long p = jobs[j][k].second;
            long long start_time = completion_times[j][k] - p;
            
            long long job_prec_completion = (k > 0) ? completion_times[j][k - 1] : 0;
            
            if (job_prec_completion == start_time) {
                if (k > 0) {
                    current_op = {j, k - 1};
                } else {
                    current_op = {-1, -1};
                }
            } else {
                int m = jobs[j][k].first;
                int pos = pos_on_machine[m][j];
                if (pos > 0) {
                    int prev_job = sol.machine_perms[m][pos - 1];
                    int prev_job_k = op_k_on_machine[prev_job][m];
                    current_op = {prev_job, prev_job_k};
                } else {
                    current_op = {-1, -1};
                }
            }
        }
        reverse(critical_path->begin(), critical_path->end());
    }
}

Solution generate_initial_solution() {
    Solution sol;
    sol.machine_perms.assign(M, vector<int>());
    vector<int> job_op_idx(J, 0);
    vector<long long> job_release_time(J, 0);
    vector<long long> machine_free_time(M, 0);

    int ops_scheduled = 0;
    while (ops_scheduled < J * M) {
        long long min_ect = -1;
        int min_ect_machine = -1;

        for (int j = 0; j < J; ++j) {
            if (job_op_idx[j] < M) {
                int k = job_op_idx[j];
                int m = jobs[j][k].first;
                int p = jobs[j][k].second;
                long long est = max(job_release_time[j], machine_free_time[m]);
                long long ect = est + p;
                if (min_ect == -1 || ect < min_ect) {
                    min_ect = ect;
                    min_ect_machine = m;
                }
            }
        }
        
        vector<tuple<int, int, int>> conflict_set;
        for (int j = 0; j < J; ++j) {
            if (job_op_idx[j] < M) {
                int k = job_op_idx[j];
                int m = jobs[j][k].first;
                if (m == min_ect_machine) {
                    long long est = max(job_release_time[j], machine_free_time[m]);
                    if (est < min_ect) {
                        int p = jobs[j][k].second;
                        conflict_set.emplace_back(p, j, k);
                    }
                }
            }
        }
        sort(conflict_set.begin(), conflict_set.end());
        
        auto& chosen_op_tuple = conflict_set[0];
        int j_chosen = get<1>(chosen_op_tuple);
        int k_chosen = get<2>(chosen_op_tuple);
        int m_chosen = jobs[j_chosen][k_chosen].first;
        int p_chosen = jobs[j_chosen][k_chosen].second;
        
        long long start_time = max(job_release_time[j_chosen], machine_free_time[m_chosen]);
        long long completion_time = start_time + p_chosen;

        sol.machine_perms[m_chosen].push_back(j_chosen);
        job_release_time[j_chosen] = completion_time;
        machine_free_time[m_chosen] = completion_time;
        job_op_idx[j_chosen]++;
        ops_scheduled++;
    }
    
    calculate_makespan(sol);
    return sol;
}

Solution get_neighbor(const Solution& current_sol) {
    Solution next_sol = current_sol;
    vector<pair<int, int>> critical_path;
    calculate_makespan(next_sol, &critical_path);

    vector<pair<int, int>> crit_block_swaps;
    for (size_t i = 0; i + 1 < critical_path.size(); ++i) {
        int j1 = critical_path[i].first;
        int k1 = critical_path[i].second;
        int m1 = jobs[j1][k1].first;

        int j2 = critical_path[i + 1].first;
        int k2 = critical_path[i + 1].second;
        int m2 = jobs[j2][k2].first;
        
        if (m1 == m2) {
            crit_block_swaps.push_back({(int)i, (int)i+1});
        }
    }

    if (crit_block_swaps.empty()) {
        int m = uniform_int_distribution<int>(0, M - 1)(rng);
        if (J > 1) {
            int pos = uniform_int_distribution<int>(0, J - 2)(rng);
            swap(next_sol.machine_perms[m][pos], next_sol.machine_perms[m][pos + 1]);
        }
    } else {
        int swap_idx = uniform_int_distribution<int>(0, crit_block_swaps.size() - 1)(rng);
        pair<int,int> ops_to_swap_indices = crit_block_swaps[swap_idx];

        int j1 = critical_path[ops_to_swap_indices.first].first;
        int k1 = critical_path[ops_to_swap_indices.first].second;
        int j2 = critical_path[ops_to_swap_indices.second].first;
        int m = jobs[j1][k1].first;
        
        int pos1 = -1, pos2 = -1;
        for(int i=0; i<J; ++i) {
            if (next_sol.machine_perms[m][i] == j1) pos1 = i;
            if (next_sol.machine_perms[m][i] == j2) pos2 = i;
        }
        swap(next_sol.machine_perms[m][pos1], next_sol.machine_perms[m][pos2]);
    }
    
    calculate_makespan(next_sol);
    return next_sol;
}

void solve() {
    auto start_time = chrono::steady_clock::now();
    
    cin >> J >> M;
    jobs.assign(J, vector<pair<int, int>>(M));
    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            cin >> jobs[j][k].first >> jobs[j][k].second;
        }
    }

    precompute_data();
    
    Solution current_sol = generate_initial_solution();
    best_solution = current_sol;

    double T = best_solution.makespan * 0.2;
    double T_min = 0.1;
    double alpha = 0.995;
    
    int time_limit_ms = 1950;
    if (J * M > 800) {
        time_limit_ms = 4800;
    }
    
    int iters = 0;
    while (true) {
        if (iters % 100 == 0) {
            auto now = chrono::steady_clock::now();
            if(chrono::duration_cast<chrono::milliseconds>(now - start_time).count() > time_limit_ms) {
                break;
            }
        }
        
        Solution next_sol = get_neighbor(current_sol);
        
        long long delta = next_sol.makespan - current_sol.makespan;

        if (delta < 0) {
            current_sol = next_sol;
            if (current_sol.makespan < best_solution.makespan) {
                best_solution = current_sol;
            }
        } else {
            if (T > T_min) {
                double prob = exp(-delta / T);
                if (uniform_real_distribution<double>(0.0, 1.0)(rng) < prob) {
                    current_sol = next_sol;
                }
            }
        }
        
        if (T > T_min) {
            T *= alpha;
        } else {
            T = T_min;
        }
        iters++;
    }

    for (int m = 0; m < M; ++m) {
        for (int j = 0; j < J; ++j) {
            cout << best_solution.machine_perms[m][j] << (j == J - 1 ? "" : " ");
        }
        cout << endl;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    solve();
    return 0;
}