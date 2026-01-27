#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>
#include <random>
#include <chrono>
#include <cmath>

int n, m;
std::vector<int> adj1[2001], adj2[2001];
bool adj_matrix1[2001][2001];

const int WL_ITERATIONS = 15;
std::vector<unsigned long long> h1, h2;

void compute_hashes() {
    h1.assign(n + 1, 0);
    h2.assign(n + 1, 0);

    for (int i = 1; i <= n; ++i) {
        h1[i] = adj1[i].size();
        h2[i] = adj2[i].size();
    }

    std::mt19937_64 rng(1337);
    std::uniform_int_distribution<unsigned long long> dist;

    for (int iter = 0; iter < WL_ITERATIONS; ++iter) {
        unsigned long long P1 = dist(rng) | 1;
        unsigned long long P2 = dist(rng) | 1;

        std::vector<unsigned long long> next_h1(n + 1), next_h2(n + 1);
        for (int i = 1; i <= n; ++i) {
            unsigned long long neighbor_hash_sum = 0;
            for (int neighbor : adj1[i]) {
                neighbor_hash_sum += h1[neighbor];
            }
            next_h1[i] = h1[i] * P1 + neighbor_hash_sum * P2;
        }
        for (int i = 1; i <= n; ++i) {
            unsigned long long neighbor_hash_sum = 0;
            for (int neighbor : adj2[i]) {
                neighbor_hash_sum += h2[neighbor];
            }
            next_h2[i] = h2[i] * P1 + neighbor_hash_sum * P2;
        }
        h1 = next_h1;
        h2 = next_h2;
    }
}

int calculate_score(const std::vector<int>& p) {
    int score = 0;
    for (int u = 1; u <= n; ++u) {
        for (int v : adj2[u]) {
            if (u < v) {
                if (adj_matrix1[p[u]][p[v]]) {
                    score++;
                }
            }
        }
    }
    return score;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> n >> m;
    for (int i = 0; i < m; ++i) {
        int u, v;
        std::cin >> u >> v;
        adj1[u].push_back(v);
        adj1[v].push_back(u);
        adj_matrix1[u][v] = adj_matrix1[v][u] = true;
    }
    for (int i = 0; i < m; ++i) {
        int u, v;
        std::cin >> u >> v;
        adj2[u].push_back(v);
        adj2[v].push_back(u);
    }

    compute_hashes();

    std::vector<int> p(n + 1);
    std::vector<bool> g1_used(n + 1, false);
    
    std::map<unsigned long long, std::vector<int>> buckets1, buckets2;
    for (int i = 1; i <= n; ++i) buckets1[h1[i]].push_back(i);
    for (int i = 1; i <= n; ++i) buckets2[h2[i]].push_back(i);

    std::vector<int> unmapped2;
    for (auto const& [hash_val, g2_nodes] : buckets2) {
        if (buckets1.count(hash_val)) {
            auto& g1_nodes_ref = buckets1.at(hash_val);
            std::vector<int> g1_nodes = g1_nodes_ref;
            std::vector<int> current_g2_nodes = g2_nodes;
            
            std::sort(g1_nodes.begin(), g1_nodes.end());
            std::sort(current_g2_nodes.begin(), current_g2_nodes.end());
            
            for (size_t i = 0; i < current_g2_nodes.size(); ++i) {
                if (i < g1_nodes.size()) {
                    p[current_g2_nodes[i]] = g1_nodes[i];
                    g1_used[g1_nodes[i]] = true;
                } else {
                    unmapped2.push_back(current_g2_nodes[i]);
                }
            }
        } else {
            unmapped2.insert(unmapped2.end(), g2_nodes.begin(), g2_nodes.end());
        }
    }

    std::vector<int> unmapped1;
    for (int i = 1; i <= n; ++i) {
        if (!g1_used[i]) {
            unmapped1.push_back(i);
        }
    }
    
    std::sort(unmapped1.begin(), unmapped1.end());
    std::sort(unmapped2.begin(), unmapped2.end());

    for (size_t i = 0; i < unmapped1.size(); ++i) {
        p[unmapped2[i]] = unmapped1[i];
    }
    
    auto start_time = std::chrono::high_resolution_clock::now();
    double time_limit_ms = 1950.0;
    
    std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());
    std::uniform_int_distribution<int> node_dist(1, n);
    std::uniform_real_distribution<double> prob_dist(0.0, 1.0);

    double initial_T = 10.0;
    
    while (true) {
        auto current_time = std::chrono::high_resolution_clock::now();
        double elapsed_ms = std::chrono::duration_cast<std::chrono::milliseconds>(current_time - start_time).count();
        if (elapsed_ms > time_limit_ms) break;
        
        double T = initial_T * (1.0 - elapsed_ms / time_limit_ms);
        if (T <= 1e-9) T = 1e-9;

        int u = node_dist(rng);
        int v = node_dist(rng);
        if (u == v) continue;
        
        int p_u = p[u];
        int p_v = p[v];
        
        int delta = 0;
        for (int neighbor : adj2[u]) {
            if (neighbor != v) {
                delta -= adj_matrix1[p_u][p[neighbor]];
                delta += adj_matrix1[p_v][p[neighbor]];
            }
        }
        for (int neighbor : adj2[v]) {
            if (neighbor != u) {
                delta -= adj_matrix1[p_v][p[neighbor]];
                delta += adj_matrix1[p_u][p[neighbor]];
            }
        }

        if (delta > 0 || prob_dist(rng) < exp(delta / T)) {
            std::swap(p[u], p[v]);
        }
    }

    for (int i = 1; i <= n; ++i) {
        std::cout << p[i] << (i == n ? "" : " ");
    }
    std::cout << std::endl;

    return 0;
}