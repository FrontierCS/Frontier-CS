#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <random>

int J, M;
struct Operation {
    int machine;
    int duration;
};
std::vector<std::vector<Operation>> jobs;
std::vector<std::vector<int>> job_op_idx_on_machine;

struct MakespanResult {
    long long makespan;
    bool has_cycle;
    std::vector<int> critical_path_op_ids;
};

MakespanResult calculate_makespan(const std::vector<std::vector<int>>& schedules) {
    int N = J * M;
    std::vector<std::vector<int>> adj(N);
    std::vector<int> in_degree(N, 0);

    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M - 1; ++k) {
            int u = j * M + k;
            int v = j * M + k + 1;
            adj[u].push_back(v);
            in_degree[v]++;
        }
    }

    for (int m = 0; m < M; ++m) {
        for (int i = 0; i < J - 1; ++i) {
            int j1 = schedules[m][i];
            int j2 = schedules[m][i + 1];
            int k1 = job_op_idx_on_machine[j1][m];
            int k2 = job_op_idx_on_machine[j2][m];
            int u = j1 * M + k1;
            int v = j2 * M + k2;
            adj[u].push_back(v);
            in_degree[v]++;
        }
    }

    std::vector<int> q;
    q.reserve(N);
    for (int i = 0; i < N; ++i) {
        if (in_degree[i] == 0) {
            q.push_back(i);
        }
    }

    std::vector<long long> start_times(N, 0);
    std::vector<int> critical_pred(N, -1);
    int head = 0;

    while (head < q.size()) {
        int u = q[head++];
        int ju = u / M, ku = u % M;
        long long u_completion_time = start_times[u] + jobs[ju][ku].duration;

        for (int v : adj[u]) {
            if (u_completion_time > start_times[v]) {
                start_times[v] = u_completion_time;
                critical_pred[v] = u;
            }
            in_degree[v]--;
            if (in_degree[v] == 0) {
                q.push_back(v);
            }
        }
    }

    if (q.size() < N) {
        return {0, true, {}};
    }

    long long makespan = 0;
    int last_op = -1;
    for (int i = 0; i < N; ++i) {
        int ji = i / M, ki = i % M;
        long long completion_time = start_times[i] + jobs[ji][ki].duration;
        if (completion_time > makespan) {
            makespan = completion_time;
            last_op = i;
        }
    }

    std::vector<int> critical_path;
    if (last_op != -1) {
        int curr = last_op;
        while (curr != -1) {
            critical_path.push_back(curr);
            curr = critical_pred[curr];
        }
        std::reverse(critical_path.begin(), critical_path.end());
    }

    return {makespan, false, critical_path};
}

std::vector<std::vector<int>> generate_initial_solution() {
    std::vector<std::vector<int>> schedules(M, std::vector<int>(J));
    std::vector<std::vector<int>> proc_times(M, std::vector<int>(J));

    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            proc_times[jobs[j][k].machine][j] = jobs[j][k].duration;
        }
    }

    for (int m = 0; m < M; ++m) {
        std::vector<std::pair<int, int>> job_times;
        for (int j = 0; j < J; ++j) {
            job_times.push_back({proc_times[m][j], j});
        }
        std::sort(job_times.begin(), job_times.end());
        for (int j = 0; j < J; ++j) {
            schedules[m][j] = job_times[j].second;
        }
    }
    return schedules;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> J >> M;
    jobs.resize(J, std::vector<Operation>(M));
    job_op_idx_on_machine.assign(J, std::vector<int>(M));

    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            std::cin >> jobs[j][k].machine >> jobs[j][k].duration;
            job_op_idx_on_machine[j][jobs[j][k].machine] = k;
        }
    }

    std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());
    auto start_time_ch = std::chrono::high_resolution_clock::now();
    double time_limit_sec = 2.95;
    if (J * M > 1000) time_limit_sec = 4.95;

    auto current_schedule = generate_initial_solution();
    auto current_res = calculate_makespan(current_schedule);

    if (current_res.has_cycle) {
        for (int m = 0; m < M; ++m) {
            std::iota(current_schedule[m].begin(), current_schedule[m].end(), 0);
        }
        current_res = calculate_makespan(current_schedule);
    }

    long long current_makespan = current_res.makespan;

    auto best_schedule = current_schedule;
    long long best_makespan = current_makespan;

    double T_initial = static_cast<double>(current_makespan) / 10.0;
    if (T_initial < 1.0) T_initial = 1.0;

    while (true) {
        auto now = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> elapsed = now - start_time_ch;
        if (elapsed.count() > time_limit_sec) {
            break;
        }

        double temp_ratio = 1.0 - elapsed.count() / time_limit_sec;
        double T = T_initial * temp_ratio * temp_ratio;
        if (T < 1e-9) T = 1e-9;

        auto neighbor_schedule = current_schedule;
        bool generated_move = false;

        if (!current_res.critical_path_op_ids.empty()) {
            std::uniform_int_distribution<int> op_dist(0, current_res.critical_path_op_ids.size() - 1);
            int op_id = current_res.critical_path_op_ids[op_dist(rng)];
            int j_move = op_id / M;
            int k_move = op_id % M;
            int m = jobs[j_move][k_move].machine;

            int pos = -1;
            for (int i = 0; i < J; ++i) {
                if (neighbor_schedule[m][i] == j_move) {
                    pos = i;
                    break;
                }
            }

            if (pos != -1) {
                bool swap_with_prev = (pos > 0 && (pos == J - 1 || rng() % 2));
                if (swap_with_prev) {
                    std::swap(neighbor_schedule[m][pos], neighbor_schedule[m][pos - 1]);
                    generated_move = true;
                } else if (pos < J - 1) {
                    std::swap(neighbor_schedule[m][pos], neighbor_schedule[m][pos + 1]);
                    generated_move = true;
                }
            }
        }

        if (!generated_move) {
            std::uniform_int_distribution<int> m_dist(0, M - 1);
            int m = m_dist(rng);
            if (J > 1) {
                std::uniform_int_distribution<int> pos_dist(0, J - 2);
                int pos = pos_dist(rng);
                std::swap(neighbor_schedule[m][pos], neighbor_schedule[m][pos + 1]);
            } else continue;
        }

        auto neighbor_res = calculate_makespan(neighbor_schedule);
        if (neighbor_res.has_cycle) continue;

        long long neighbor_makespan = neighbor_res.makespan;
        long long delta = neighbor_makespan - current_makespan;

        if (delta < 0 || (std::uniform_real_distribution<double>(0.0, 1.0)(rng) < exp(-(double)delta / T))) {
            current_schedule = neighbor_schedule;
            current_makespan = neighbor_makespan;
            current_res = neighbor_res;
            if (current_makespan < best_makespan) {
                best_makespan = current_makespan;
                best_schedule = current_schedule;
            }
        }
    }

    for (int m = 0; m < M; ++m) {
        for (int j = 0; j < J; ++j) {
            std::cout << best_schedule[m][j] << (j == J - 1 ? "" : " ");
        }
        std::cout << "\n";
    }

    return 0;
}