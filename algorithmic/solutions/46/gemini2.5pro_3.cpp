#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <chrono>
#include <random>

// --- Configuration ---
const double TIME_LIMIT_SECONDS = 2.8;

// --- Global data structures ---
int J, M;

struct Operation {
    int machine;
    int duration;
};
std::vector<std::vector<Operation>> jobs_data;
std::vector<std::vector<int>> job_op_idx_on_machine; // [j][m] -> op_idx

struct OpNode {
    int job;
    int op_idx;
};
std::vector<OpNode> op_nodes;
int total_ops;

// --- Helper functions ---
inline int get_op_id(int job_idx, int op_idx) {
    return job_idx * M + op_idx;
}

// --- Makespan calculation ---
int calculate_makespan(const std::vector<std::vector<int>>& schedules, const std::vector<std::vector<int>>& job_pos_map) {
    std::vector<int> in_degree(total_ops, 0);
    // Precedence constraints
    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M - 1; ++k) {
            in_degree[get_op_id(j, k + 1)]++;
        }
    }
    // Resource constraints
    for (int m = 0; m < M; ++m) {
        for (int i = 0; i < J - 1; ++i) {
            int job_v = schedules[m][i + 1];
            int op_idx_v = job_op_idx_on_machine[job_v][m];
            in_degree[get_op_id(job_v, op_idx_v)]++;
        }
    }

    std::vector<int> q;
    q.reserve(total_ops);
    for (int i = 0; i < total_ops; ++i) {
        if (in_degree[i] == 0) {
            q.push_back(i);
        }
    }

    std::vector<int> earliest_start_times(total_ops, 0);
    int head = 0;
    while (head < q.size()) {
        int u_id = q[head++];
        int j = op_nodes[u_id].job;
        int k = op_nodes[u_id].op_idx;
        int u_completion_time = earliest_start_times[u_id] + jobs_data[j][k].duration;

        // Propagate to precedence successor
        if (k < M - 1) {
            int v_id = get_op_id(j, k + 1);
            earliest_start_times[v_id] = std::max(earliest_start_times[v_id], u_completion_time);
            in_degree[v_id]--;
            if (in_degree[v_id] == 0) q.push_back(v_id);
        }

        // Propagate to machine successor
        int m = jobs_data[j][k].machine;
        int pos = job_pos_map[m][j];
        if (pos < J - 1) {
            int next_job = schedules[m][pos + 1];
            int next_op_idx = job_op_idx_on_machine[next_job][m];
            int v_id = get_op_id(next_job, next_op_idx);
            earliest_start_times[v_id] = std::max(earliest_start_times[v_id], u_completion_time);
            in_degree[v_id]--;
            if (in_degree[v_id] == 0) q.push_back(v_id);
        }
    }

    int makespan = 0;
    for (int i = 0; i < total_ops; ++i) {
        makespan = std::max(makespan, earliest_start_times[i] + jobs_data[op_nodes[i].job][op_nodes[i].op_idx].duration);
    }
    return makespan;
}

// --- Main logic ---
void solve() {
    std::cin >> J >> M;
    jobs_data.resize(J, std::vector<Operation>(M));
    job_op_idx_on_machine.resize(J, std::vector<int>(M));
    for (int i = 0; i < J; ++i) {
        for (int k = 0; k < M; ++k) {
            std::cin >> jobs_data[i][k].machine >> jobs_data[i][k].duration;
            job_op_idx_on_machine[i][jobs_data[i][k].machine] = k;
        }
    }
    
    total_ops = J * M;
    op_nodes.resize(total_ops);
    for(int j=0; j<J; ++j) {
        for(int k=0; k<M; ++k) {
            int op_id = get_op_id(j, k);
            op_nodes[op_id].job = j;
            op_nodes[op_id].op_idx = k;
        }
    }

    std::vector<std::vector<int>> current_schedule(M, std::vector<int>(J));
    for (int m = 0; m < M; ++m) {
        std::vector<std::pair<int, int>> job_durations;
        for (int j = 0; j < J; ++j) {
            int op_idx = job_op_idx_on_machine[j][m];
            job_durations.push_back({jobs_data[j][op_idx].duration, j});
        }
        std::sort(job_durations.begin(), job_durations.end());
        for (int j = 0; j < J; ++j) {
            current_schedule[m][j] = job_durations[j].second;
        }
    }

    std::vector<std::vector<int>> job_pos_map(M, std::vector<int>(J));
    for (int m = 0; m < M; ++m) {
        for (int i = 0; i < J; ++i) {
            job_pos_map[m][current_schedule[m][i]] = i;
        }
    }

    std::vector<std::vector<int>> best_schedule = current_schedule;
    int current_makespan = calculate_makespan(current_schedule, job_pos_map);
    int best_makespan = current_makespan;

    std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());
    
    double T = 0.2 * best_makespan;
    double alpha = 0.9998;
    
    auto start_time = std::chrono::high_resolution_clock::now();
    
    int no_improve_iters = 0;
    const int reheat_threshold = 20000;

    while (true) {
        auto now = std::chrono::high_resolution_clock::now();
        if (std::chrono::duration<double>(now - start_time).count() > TIME_LIMIT_SECONDS) {
            break;
        }

        std::uniform_int_distribution<int> machine_dist(0, M - 1);
        int m = machine_dist(rng);

        if (J <= 1) continue;

        std::vector<std::vector<int>> next_schedule = current_schedule;
        std::vector<std::vector<int>> next_job_pos_map = job_pos_map;

        std::uniform_real_distribution<double> move_dist(0.0, 1.0);
        if (move_dist(rng) < 0.5 && J > 2) { // General swap
            std::uniform_int_distribution<int> pos_dist(0, J - 1);
            int pos1 = pos_dist(rng);
            int pos2 = pos_dist(rng);
            while (pos1 == pos2) pos2 = pos_dist(rng);
            
            int j1 = next_schedule[m][pos1];
            int j2 = next_schedule[m][pos2];
            std::swap(next_schedule[m][pos1], next_schedule[m][pos2]);
            next_job_pos_map[m][j1] = pos2;
            next_job_pos_map[m][j2] = pos1;
        } else { // Adjacent swap
            std::uniform_int_distribution<int> pos_dist(0, J - 2);
            int pos1 = pos_dist(rng);
            
            int j1 = next_schedule[m][pos1];
            int j2 = next_schedule[m][pos1+1];
            std::swap(next_schedule[m][pos1], next_schedule[m][pos1+1]);
            next_job_pos_map[m][j1] = pos1+1;
            next_job_pos_map[m][j2] = pos1;
        }
        
        int next_makespan = calculate_makespan(next_schedule, next_job_pos_map);
        int delta = next_makespan - current_makespan;

        bool accepted = false;
        if (delta < 0) {
            accepted = true;
        } else if (T > 1e-9) {
            std::uniform_real_distribution<double> accept_dist(0.0, 1.0);
            if (accept_dist(rng) < std::exp(-static_cast<double>(delta) / T)) {
                accepted = true;
            }
        }
        
        if (accepted) {
            current_schedule = std::move(next_schedule);
            job_pos_map = std::move(next_job_pos_map);
            current_makespan = next_makespan;

            if (current_makespan < best_makespan) {
                best_makespan = current_makespan;
                best_schedule = current_schedule;
                no_improve_iters = 0;
            } else {
                no_improve_iters++;
            }
        }
        
        T *= alpha;
        if(no_improve_iters > reheat_threshold) {
            T = 0.1 * best_makespan;
            current_schedule = best_schedule;
            for (int m_reheat = 0; m_reheat < M; ++m_reheat) {
                for (int i = 0; i < J; ++i) {
                    job_pos_map[m_reheat][current_schedule[m_reheat][i]] = i;
                }
            }
            current_makespan = best_makespan;
            no_improve_iters = 0;
        }
    }

    for (int m = 0; m < M; ++m) {
        for (int j = 0; j < J; ++j) {
            std::cout << best_schedule[m][j] << (j == J - 1 ? "" : " ");
        }
        std::cout << "\n";
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    solve();
    return 0;
}