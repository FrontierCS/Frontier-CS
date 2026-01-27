#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <chrono>
#include <random>
#include <cmath>
#include <map>

// Constants and globals
const int MAXN = 2001;
int N, M;
std::vector<int> adj1[MAXN], adj2[MAXN];
bool adj1_mat[MAXN][MAXN];
int p[MAXN]; // p[i] = j means G2 vertex i is mapped to G1 vertex j

std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());

// Weisfeiler-Leman hashing to get a good initial permutation
void get_initial_permutation() {
    std::uniform_int_distribution<unsigned long long> dist_ull;
    unsigned long long P1 = dist_ull(rng);
    if (P1 % 2 == 0) P1++;

    std::vector<unsigned long long> h1(N + 1), h2(N + 1);

    // Initial hashes are degrees
    for (int i = 1; i <= N; ++i) {
        h1[i] = adj1[i].size();
        h2[i] = adj2[i].size();
    }

    int iterations = 5;
    for (int iter = 0; iter < iterations; ++iter) {
        std::vector<unsigned long long> h1_new(N + 1), h2_new(N + 1);
        
        // G1
        for (int i = 1; i <= N; ++i) {
            std::vector<unsigned long long> neighbor_hashes;
            neighbor_hashes.reserve(adj1[i].size());
            for (int neighbor : adj1[i]) {
                neighbor_hashes.push_back(h1[neighbor]);
            }
            std::sort(neighbor_hashes.begin(), neighbor_hashes.end());
            unsigned long long current_hash = h1[i];
            for (unsigned long long nh : neighbor_hashes) {
                current_hash = current_hash * P1 + nh;
            }
            h1_new[i] = current_hash;
        }

        // G2
        for (int i = 1; i <= N; ++i) {
            std::vector<unsigned long long> neighbor_hashes;
            neighbor_hashes.reserve(adj2[i].size());
            for (int neighbor : adj2[i]) {
                neighbor_hashes.push_back(h2[neighbor]);
            }
            std::sort(neighbor_hashes.begin(), neighbor_hashes.end());
            unsigned long long current_hash = h2[i];
            for (unsigned long long nh : neighbor_hashes) {
                current_hash = current_hash * P1 + nh;
            }
            h2_new[i] = current_hash;
        }

        // Re-labeling to keep hash values small
        std::vector<unsigned long long> all_hashes;
        all_hashes.reserve(2 * N);
        for (int i = 1; i <= N; ++i) all_hashes.push_back(h1_new[i]);
        for (int i = 1; i <= N; ++i) all_hashes.push_back(h2_new[i]);
        std::sort(all_hashes.begin(), all_hashes.end());
        all_hashes.erase(std::unique(all_hashes.begin(), all_hashes.end()), all_hashes.end());
        
        for (int i = 1; i <= N; ++i) {
            h1[i] = std::lower_bound(all_hashes.begin(), all_hashes.end(), h1_new[i]) - all_hashes.begin();
            h2[i] = std::lower_bound(all_hashes.begin(), all_hashes.end(), h2_new[i]) - all_hashes.begin();
        }
    }

    // Create permutation based on final hashes and degrees
    std::vector<std::pair<std::pair<long long, int>, int>> v1_tuples, v2_tuples;
    for (int i = 1; i <= N; ++i) {
        v1_tuples.push_back({{h1[i], adj1[i].size()}, i});
        v2_tuples.push_back({{h2[i], adj2[i].size()}, i});
    }

    std::sort(v1_tuples.begin(), v1_tuples.end());
    std::sort(v2_tuples.begin(), v2_tuples.end());
    
    for (int i = 0; i < N; ++i) {
        p[v2_tuples[i].second] = v1_tuples[i].second;
    }
}

// Refine the permutation using simulated annealing
void simulated_annealing() {
    auto start_time = std::chrono::steady_clock::now();
    
    double temp = 10.0;
    double alpha = 0.99997;

    std::uniform_int_distribution<int> dist_v(1, N);
    std::uniform_real_distribution<double> dist_prob(0.0, 1.0);
    
    long long iter_count = 0;
    while (true) {
        iter_count++;
        if ((iter_count & 255) == 0) {
            auto now = std::chrono::steady_clock::now();
            double elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(now - start_time).count();
            if (elapsed > 1950) { 
                break;
            }
        }

        int u = dist_v(rng);
        int v = dist_v(rng);
        if (u == v) continue;

        int delta = 0;
        int pu = p[u], pv = p[v];

        for (int neighbor : adj2[u]) {
            if (neighbor == v) continue;
            int p_neighbor = p[neighbor];
            if (adj1_mat[pv][p_neighbor]) delta++;
            if (adj1_mat[pu][p_neighbor]) delta--;
        }

        for (int neighbor : adj2[v]) {
            if (neighbor == u) continue;
            int p_neighbor = p[neighbor];
            if (adj1_mat[pu][p_neighbor]) delta++;
            if (adj1_mat[pv][p_neighbor]) delta--;
        }

        if (delta > 0 || (temp > 1e-9 && dist_prob(rng) < std::exp(delta / temp))) {
            std::swap(p[u], p[v]);
        }

        temp *= alpha;
    }
}

void solve() {
    std::cin >> N >> M;
    for (int i = 0; i < M; ++i) {
        int u, v;
        std::cin >> u >> v;
        adj1[u].push_back(v);
        adj1[v].push_back(u);
        adj1_mat[u][v] = adj1_mat[v][u] = true;
    }
    for (int i = 0; i < M; ++i) {
        int u, v;
        std::cin >> u >> v;
        adj2[u].push_back(v);
        adj2[v].push_back(u);
    }

    get_initial_permutation();
    simulated_annealing();

    for (int i = 1; i <= N; ++i) {
        std::cout << p[i] << (i == N ? "" : " ");
    }
    std::cout << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    solve();
    return 0;
}