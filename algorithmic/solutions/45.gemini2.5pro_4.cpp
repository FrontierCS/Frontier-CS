#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

// Globals for problem parameters
int n, k;
double eps;
long long m_in;
long long max_part_size;

// Graph
std::vector<std::vector<int>> adj;

// Partition state
std::vector<int> part;
std::vector<long long> part_size;
std::vector<std::vector<int>> neighbor_part_counts;
std::vector<int> F;
std::vector<long long> Comm;
long long current_EC;
long long current_CV;

// Top 2 Comm values for faster gain calculation
long long max1_comm, max2_comm;
int max1_p, max2_p;

// Randomness
std::mt19937 rng;

void find_top2_comm() {
    max1_p = -1; max2_p = -1;
    max1_comm = -1; max2_comm = -1;
    for (int p = 1; p <= k; ++p) {
        if (Comm[p] > max1_comm) {
            max2_comm = max1_comm;
            max2_p = max1_p;
            max1_comm = Comm[p];
            max1_p = p;
        } else if (Comm[p] > max2_comm) {
            max2_comm = Comm[p];
            max2_p = p;
        }
    }
    current_CV = (max1_comm > 0) ? max1_comm : 0;
}

void apply_move(int v, int p_u) {
    int p_v = part[v];

    std::vector<std::pair<int, int>> F_changes;
    Comm[p_v] -= F[v];

    for (int w : adj[v]) {
        int p_w = part[w];
        int delta_F_w = 0;
        if (p_w != p_v) {
            if (neighbor_part_counts[w][p_v] == 1) delta_F_w--;
        }
        if (p_w != p_u) {
            if (neighbor_part_counts[w][p_u] == 0) delta_F_w++;
        }
        if (delta_F_w != 0) {
            F_changes.push_back({w, delta_F_w});
        }
        neighbor_part_counts[w][p_v]--;
        neighbor_part_counts[w][p_u]++;
    }

    current_EC -= (neighbor_part_counts[v][p_v] - neighbor_part_counts[v][p_u]);

    part_size[p_v]--;
    part[v] = p_u;
    part_size[p_u]++;

    int distinct_neighbor_parts = 0;
    for (int q = 1; q <= k; ++q) {
        if (neighbor_part_counts[v][q] > 0) {
            distinct_neighbor_parts++;
        }
    }
    F[v] = distinct_neighbor_parts - (neighbor_part_counts[v][p_u] > 0);
    Comm[p_u] += F[v];

    for (const auto& change : F_changes) {
        int w = change.first;
        int delta = change.second;
        F[w] += delta;
        Comm[part[w]] += delta;
    }

    find_top2_comm();
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    auto start_time = std::chrono::high_resolution_clock::now();
    rng.seed(std::chrono::duration_cast<std::chrono::nanoseconds>(start_time.time_since_epoch()).count());

    std::cin >> n >> m_in >> k >> eps;

    adj.resize(n + 1);
    std::vector<std::pair<int, int>> edges;
    edges.reserve(m_in);
    for (int i = 0; i < m_in; ++i) {
        int u, v;
        std::cin >> u >> v;
        if (u == v) continue;
        if (u > v) std::swap(u, v);
        edges.push_back({u, v});
    }

    std::sort(edges.begin(), edges.end());
    edges.erase(std::unique(edges.begin(), edges.end()), edges.end());

    for (const auto& edge : edges) {
        adj[edge.first].push_back(edge.second);
        adj[edge.second].push_back(edge.first);
    }

    max_part_size = floor((1.0 + eps) * ceil((double)n / k));

    part.resize(n + 1);
    part_size.assign(k + 1, 0);
    std::vector<int> vertices(n);
    std::iota(vertices.begin(), vertices.end(), 1);
    std::shuffle(vertices.begin(), vertices.end(), rng);

    for (int i = 0; i < n; ++i) {
        int v = vertices[i];
        int p = i % k + 1;
        part[v] = p;
        part_size[p]++;
    }

    neighbor_part_counts.assign(n + 1, std::vector<int>(k + 1, 0));
    F.resize(n + 1);
    Comm.assign(k + 1, 0);
    current_EC = 0;

    for (int v = 1; v <= n; ++v) {
        for (int u : adj[v]) {
            neighbor_part_counts[v][part[u]]++;
        }
    }

    long long total_degree_sum = 0;
    for (int v = 1; v <= n; ++v) {
        total_degree_sum += (long long)adj[v].size() - neighbor_part_counts[v][part[v]];
    }
    current_EC = total_degree_sum / 2;

    for (int v = 1; v <= n; ++v) {
        int p_v = part[v];
        int f_v = 0;
        for (int q = 1; q <= k; ++q) {
            if (q != p_v && neighbor_part_counts[v][q] > 0) {
                f_v++;
            }
        }
        F[v] = f_v;
        Comm[p_v] += F[v];
    }
    
    find_top2_comm();
    
    long long initial_EC = current_EC;
    long long initial_CV = current_CV;

    double w_EC = 1.0;
    double w_CV = 1.0;
    if (initial_EC > 0 && initial_CV > 0) {
        w_CV = (double)initial_EC / initial_CV;
    }
    
    while (true) {
        auto now = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double> elapsed = now - start_time;
        if (elapsed.count() > 0.98) break;

        std::shuffle(vertices.begin(), vertices.end(), rng);
        bool improved_in_pass = false;

        for (int v : vertices) {
            int p_v = part[v];
            int best_p_u = -1;
            double best_gain = 1e-9;

            int distinct_neighbor_parts = 0;
            for (int q = 1; q <= k; ++q) {
                if (neighbor_part_counts[v][q] > 0) {
                    distinct_neighbor_parts++;
                }
            }

            for (int p_u = 1; p_u <= k; ++p_u) {
                if (p_u == p_v) continue;
                if (part_size[p_u] >= max_part_size) continue;

                long long delta_EC = neighbor_part_counts[v][p_v] - neighbor_part_counts[v][p_u];

                int F_v_at_pv = F[v];
                int F_v_at_pu = distinct_neighbor_parts - (neighbor_part_counts[v][p_u] > 0);

                long long comm_new_pv = Comm[p_v] - F_v_at_pv;
                long long comm_new_pu = Comm[p_u] + F_v_at_pu;

                long long cv_after_move;
                if (p_v == max1_p) {
                    cv_after_move = std::max({max2_comm, comm_new_pv, comm_new_pu});
                } else {
                    cv_after_move = std::max({max1_comm, comm_new_pv, comm_new_pu});
                }
                
                double gain = w_EC * delta_EC + w_CV * (current_CV - cv_after_move);

                if (gain > best_gain) {
                    best_gain = gain;
                    best_p_u = p_u;
                }
            }
            if (best_p_u != -1) {
                apply_move(v, best_p_u);
                improved_in_pass = true;
            }
        }
        if (!improved_in_pass) {
            if(current_EC > 0 && current_CV > 0) {
                std::uniform_real_distribution<> dist(0.8, 1.2);
                w_CV = ((double)current_EC / current_CV) * dist(rng);
            }
        }
    }

    for (int i = 1; i <= n; ++i) {
        std::cout << part[i] << (i == n ? "" : " ");
    }
    std::cout << "\n";

    return 0;
}