#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <random>
#include <chrono>
#include <queue>

// Main class to solve the Job Shop Scheduling Problem
class JSSPSolver {
public:
    void solve() {
        std::ios_base::sync_with_stdio(false);
        std::cin.tie(NULL);

        read_input();
        preprocess_data();

        auto start_time_ch = std::chrono::high_resolution_clock::now();

        auto current_schedule = generate_initial_solution();
        long long current_makespan = calculate_makespan(current_schedule);
        
        auto best_schedule = current_schedule;
        long long best_makespan = current_makespan;

        std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());

        double temperature = static_cast<double>(best_makespan) * 0.25;
        double min_temperature = 1e-2;
        double cooling_rate = 0.99999;
        
        while (true) {
            auto now = std::chrono::high_resolution_clock::now();
            if (std::chrono::duration_cast<std::chrono::milliseconds>(now - start_time_ch).count() > 1950) {
                break;
            }

            auto next_schedule = current_schedule;
            
            std::uniform_int_distribution<int> m_dist(0, M - 1);
            int m = m_dist(rng);
            
            if (J > 1) {
                std::uniform_int_distribution<int> pos_dist(0, J - 1);
                int pos1 = pos_dist(rng);
                int pos2 = pos_dist(rng);
                while (pos1 == pos2) {
                    pos2 = pos_dist(rng);
                }
                int job_to_move = next_schedule[m][pos1];
                next_schedule[m].erase(next_schedule[m].begin() + pos1);
                next_schedule[m].insert(next_schedule[m].begin() + pos2, job_to_move);
            } else {
                 // No moves possible if J=1
                break;
            }

            long long next_makespan = calculate_makespan(next_schedule);
            
            if (next_makespan < current_makespan) {
                current_schedule = next_schedule;
                current_makespan = next_makespan;
                if (current_makespan < best_makespan) {
                    best_schedule = current_schedule;
                    best_makespan = current_makespan;
                }
            } else {
                std::uniform_real_distribution<double> u_dist(0.0, 1.0);
                double p_accept = std::exp(-(double)(next_makespan - current_makespan) / temperature);
                if (u_dist(rng) < p_accept) {
                    current_schedule = next_schedule;
                    current_makespan = next_makespan;
                }
            }
            
            temperature *= cooling_rate;
            if (temperature < min_temperature) {
                 temperature = static_cast<double>(best_makespan) * 0.25;
            }
        }

        print_solution(best_schedule);
    }

private:
    int J, M;
    std::vector<std::vector<std::pair<int, int>>> jobs;
    std::vector<std::vector<int>> job_op_by_machine;
    std::vector<std::vector<int>> job_op_machine;
    std::vector<std::vector<int>> job_op_proc_time;

    void read_input() {
        std::cin >> J >> M;
        jobs.resize(J);
        for (int j = 0; j < J; ++j) {
            jobs[j].resize(M);
            for (int k = 0; k < M; ++k) {
                std::cin >> jobs[j][k].first >> jobs[j][k].second;
            }
        }
    }

    void preprocess_data() {
        job_op_by_machine.assign(J, std::vector<int>(M));
        job_op_machine.assign(J, std::vector<int>(M));
        job_op_proc_time.assign(J, std::vector<int>(M));
        for (int j = 0; j < J; ++j) {
            for (int k = 0; k < M; ++k) {
                int machine = jobs[j][k].first;
                int p_time = jobs[j][k].second;
                job_op_by_machine[j][machine] = k;
                job_op_machine[j][k] = machine;
                job_op_proc_time[j][k] = p_time;
            }
        }
    }

    std::vector<std::vector<int>> generate_initial_solution() {
        std::vector<std::vector<int>> schedules(M);
        std::vector<int> next_op_idx(J, 0);
        std::vector<long long> job_ready_time(J, 0);
        std::vector<long long> machine_ready_time(M, 0);

        int scheduled_count = 0;
        while (scheduled_count < J * M) {
            long long min_completion_time = -1;
            int best_j = -1;

            for (int j = 0; j < J; ++j) {
                if (next_op_idx[j] < M) {
                    int k = next_op_idx[j];
                    int m = job_op_machine[j][k];
                    long long start_time = std::max(job_ready_time[j], machine_ready_time[m]);
                    long long completion_time = start_time + job_op_proc_time[j][k];
                    if (best_j == -1 || completion_time < min_completion_time) {
                        min_completion_time = completion_time;
                        best_j = j;
                    }
                }
            }
            
            int j = best_j;
            int k = next_op_idx[j];
            int m = job_op_machine[j][k];
            
            schedules[m].push_back(j);
            job_ready_time[j] = min_completion_time;
            machine_ready_time[m] = min_completion_time;
            next_op_idx[j]++;
            scheduled_count++;
        }
        return schedules;
    }

    long long calculate_makespan(const std::vector<std::vector<int>>& schedules) {
        std::vector<std::vector<long long>> completion_times(J, std::vector<long long>(M));
        std::vector<std::vector<int>> in_degree(J, std::vector<int>(M, 0));
        std::queue<std::pair<int, int>> q;
        
        std::vector<std::vector<int>> job_pos_on_machine(J, std::vector<int>(M));
        for (int m = 0; m < M; ++m) {
            for (int i = 0; i < J; ++i) {
                job_pos_on_machine[schedules[m][i]][m] = i;
            }
        }

        for (int j = 0; j < J; ++j) {
            for (int k = 0; k < M; ++k) {
                int m = job_op_machine[j][k];
                int pos = job_pos_on_machine[j][m];
                if (k > 0) in_degree[j][k]++;
                if (pos > 0) in_degree[j][k]++;
                if (in_degree[j][k] == 0) q.push({j, k});
            }
        }

        int processed_ops = 0;
        while (!q.empty()) {
            auto [j, k] = q.front(); q.pop();
            processed_ops++;

            int m = job_op_machine[j][k];
            int pos = job_pos_on_machine[j][m];
            
            long long job_pred_ct = (k > 0) ? completion_times[j][k - 1] : 0;
            
            long long machine_pred_ct = 0;
            if (pos > 0) {
                int prev_j = schedules[m][pos - 1];
                int prev_k = job_op_by_machine[prev_j][m];
                machine_pred_ct = completion_times[prev_j][prev_k];
            }

            completion_times[j][k] = std::max(job_pred_ct, machine_pred_ct) + job_op_proc_time[j][k];

            if (k + 1 < M) {
                in_degree[j][k + 1]--;
                if (in_degree[j][k + 1] == 0) q.push({j, k + 1});
            }
            if (pos + 1 < J) {
                int next_j = schedules[m][pos + 1];
                int next_k = job_op_by_machine[next_j][m];
                in_degree[next_j][next_k]--;
                if (in_degree[next_j][next_k] == 0) q.push({next_j, next_k});
            }
        }

        if (processed_ops < J * M) return -1;

        long long makespan = 0;
        for (int j = 0; j < J; ++j) {
            makespan = std::max(makespan, completion_times[j][M - 1]);
        }
        return makespan;
    }

    void print_solution(const std::vector<std::vector<int>>& schedules) {
        for (int m = 0; m < M; ++m) {
            for (int j = 0; j < J; ++j) {
                std::cout << schedules[m][j] << (j == J - 1 ? "" : " ");
            }
            std::cout << "\n";
        }
    }
};

int main() {
    JSSPSolver solver;
    solver.solve();
    return 0;
}