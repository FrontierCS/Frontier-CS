#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>
#include <cmath>
#include <queue>

// Problem data
int J, M;
struct Operation {
    int machine, proc_time;
};
std::vector<std::vector<Operation>> jobs_data;
struct OpInfo {
    int k, proc_time;
};
std::vector<std::vector<OpInfo>> op_info_for_job_machine;
std::vector<int> op_proc_times;

// Random number generator
std::mt19937 rng;

void read_input() {
    std::cin >> J >> M;
    jobs_data.resize(J, std::vector<Operation>(M));
    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            std::cin >> jobs_data[j][k].machine >> jobs_data[j][k].proc_time;
        }
    }
}

void initialize_data_structures() {
    op_info_for_job_machine.resize(J, std::vector<OpInfo>(M));
    op_proc_times.resize(J * M);
    for (int j = 0; j < J; ++j) {
        for (int k = 0; k < M; ++k) {
            int m = jobs_data[j][k].machine;
            int p_time = jobs_data[j][k].proc_time;
            op_info_for_job_machine[j][m] = {k, p_time};
            op_proc_times[j * M + k] = p_time;
        }
    }
}

std::vector<std::vector<int>> generate_initial_solution() {
    std::vector<std::vector<int>> initial_solution(M);
    std::vector<int> job_op_idx(J, 0);
    std::vector<long long> machine_free_time(M, 0);
    std::vector<long long> job_completion_time(J, 0);

    int scheduled_count = 0;
    while (scheduled_count < J * M) {
        long long min_completion_time = -1;
        int best_job = -1;

        for (int j = 0; j < J; ++j) {
            if (job_op_idx[j] < M) {
                int k = job_op_idx[j];
                int m = jobs_data[j][k].machine;
                int p_time = jobs_data[j][k].proc_time;

                long long start_time = std::max(machine_free_time[m], job_completion_time[j]);
                long long completion_time = start_time + p_time;

                if (best_job == -1 || completion_time < min_completion_time) {
                    min_completion_time = completion_time;
                    best_job = j;
                }
            }
        }

        int k = job_op_idx[best_job];
        int m = jobs_data[best_job][k].machine;

        initial_solution[m].push_back(best_job);

        machine_free_time[m] = min_completion_time;
        job_completion_time[best_job] = min_completion_time;
        job_op_idx[best_job]++;
        scheduled_count++;
    }
    return initial_solution;
}

long long calculate_makespan(const std::vector<std::vector<int>>& solution) {
    int num_ops = J * M;
    int source = num_ops, sink = num_ops + 1;
    int num_nodes = num_ops + 2;

    std::vector<std::vector<std::pair<int, int>>> adj(num_nodes);

    for (int j = 0; j < J; ++j) {
        adj[source].push_back({j * M, 0});
        for (int k = 0; k < M - 1; ++k) {
            int u = j * M + k;
            int v = j * M + k + 1;
            adj[u].push_back({v, op_proc_times[u]});
        }
        int last_op = j * M + M - 1;
        adj[last_op].push_back({sink, op_proc_times[last_op]});
    }

    for (int m = 0; m < M; ++m) {
        for (size_t i = 0; i < J - 1; ++i) {
            int job1 = solution[m][i];
            int job2 = solution[m][i + 1];

            int k1 = op_info_for_job_machine[job1][m].k;
            int k2 = op_info_for_job_machine[job2][m].k;

            int u = job1 * M + k1;
            int v = job2 * M + k2;

            adj[u].push_back({v, op_proc_times[u]});
        }
    }

    std::vector<int> in_degree(num_nodes, 0);
    for (int u = 0; u < num_nodes; ++u) {
        for (const auto& edge : adj[u]) {
            in_degree[edge.first]++;
        }
    }

    std::vector<long long> dist(num_nodes, 0);
    std::queue<int> q;

    for (int i = 0; i < num_nodes; ++i) {
        if (in_degree[i] == 0) {
            q.push(i);
        }
    }

    int processed_nodes = 0;
    while (!q.empty()) {
        int u = q.front();
        q.pop();
        processed_nodes++;

        for (auto& edge : adj[u]) {
            int v = edge.first;
            int weight = edge.second;
            if (dist[v] < dist[u] + weight) {
                dist[v] = dist[u] + weight;
            }
            in_degree[v]--;
            if (in_degree[v] == 0) {
                q.push(v);
            }
        }
    }

    if (processed_nodes != num_nodes) return -1; // Cycle detected

    return dist[sink];
}

void print_solution(const std::vector<std::vector<int>>& solution) {
    for (int m = 0; m < M; ++m) {
        for (int j = 0; j < J; ++j) {
            std::cout << solution[m][j] << (j == J - 1 ? "" : " ");
        }
        std::cout << "\n";
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    auto seed = std::chrono::high_resolution_clock::now().time_since_epoch().count();
    rng.seed(seed);

    read_input();
    initialize_data_structures();

    std::vector<std::vector<int>> current_solution = generate_initial_solution();
    long long current_makespan = calculate_makespan(current_solution);

    std::vector<std::vector<int>> best_solution = current_solution;
    long long best_makespan = current_makespan;

    if (J <= 1) {
        print_solution(best_solution);
        return 0;
    }

    double temp = 0.05 * best_makespan;
    double min_temp = 1e-3;
    double cooling_rate = 0.99995;

    std::uniform_real_distribution<> dis(0.0, 1.0);
    std::uniform_int_distribution<> machine_dist(0, M - 1);

    auto start_time = std::chrono::high_resolution_clock::now();
    double time_limit_sec = 4.8;

    while (true) {
        auto current_time = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> elapsed = current_time - start_time;
        if (elapsed.count() > time_limit_sec) break;

        if (temp < min_temp) break;

        std::vector<std::vector<int>> neighbor_solution = current_solution;

        int m = machine_dist(rng);

        std::uniform_int_distribution<> job_idx_dist(0, J - 1);
        int idx1 = job_idx_dist(rng);
        int idx2 = job_idx_dist(rng);
        while (idx1 == idx2) {
            idx2 = job_idx_dist(rng);
        }
        std::swap(neighbor_solution[m][idx1], neighbor_solution[m][idx2]);

        long long neighbor_makespan = calculate_makespan(neighbor_solution);

        if (neighbor_makespan == -1) continue;

        long long delta = neighbor_makespan - current_makespan;

        if (delta < 0 || dis(rng) < std::exp(-static_cast<double>(delta) / temp)) {
            current_solution = std::move(neighbor_solution);
            current_makespan = neighbor_makespan;
            if (current_makespan < best_makespan) {
                best_solution = current_solution;
                best_makespan = current_makespan;
            }
        }

        temp *= cooling_rate;
    }

    print_solution(best_solution);

    return 0;
}