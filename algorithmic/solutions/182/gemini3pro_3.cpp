#include <iostream>
#include <vector>
#include <algorithm>
#include <chrono>

using namespace std;

// Fast random number generator
unsigned int x_rnd = 123456789, y_rnd = 362436069, z_rnd = 521288629;
unsigned int xorshift96() {
    unsigned int t;
    x_rnd ^= x_rnd << 16;
    x_rnd ^= x_rnd >> 5;
    x_rnd ^= x_rnd << 1;
    t = x_rnd;
    x_rnd = y_rnd;
    y_rnd = z_rnd;
    z_rnd = t ^ x_rnd ^ y_rnd;
    return z_rnd;
}

auto start_time = chrono::high_resolution_clock::now();
double get_elapsed() {
    auto current_time = chrono::high_resolution_clock::now();
    chrono::duration<double> diff = current_time - start_time;
    return diff.count();
}

const double TIME_LIMIT = 1.95;

struct Edge {
    int u, v;
    long long weight;
};

int N, M;
vector<Edge> edges;
vector<vector<int>> adj_edge_indices; 
vector<bool> in_set;
vector<long long> dscore;
vector<int> uncov_edge_indices;
vector<int> pos_in_uncov; 

void remove_uncov(int edge_idx) {
    int pos = pos_in_uncov[edge_idx];
    if (pos == -1) return;
    int last_idx = uncov_edge_indices.back();
    if (last_idx != edge_idx) {
        uncov_edge_indices[pos] = last_idx;
        pos_in_uncov[last_idx] = pos;
    }
    uncov_edge_indices.pop_back();
    pos_in_uncov[edge_idx] = -1;
}

void add_uncov(int edge_idx) {
    if (pos_in_uncov[edge_idx] != -1) return;
    pos_in_uncov[edge_idx] = uncov_edge_indices.size();
    uncov_edge_indices.push_back(edge_idx);
}

void flip(int u) {
    in_set[u] = !in_set[u];
    dscore[u] = -dscore[u];
    for (int edge_idx : adj_edge_indices[u]) {
        int v = (edges[edge_idx].u == u) ? edges[edge_idx].v : edges[edge_idx].u;
        if (in_set[u]) {
            // u moved OUT -> IN
            if (!in_set[v]) {
                remove_uncov(edge_idx);
                dscore[v] -= edges[edge_idx].weight;
            } else {
                dscore[v] += edges[edge_idx].weight;
            }
        } else {
            // u moved IN -> OUT
            if (!in_set[v]) {
                add_uncov(edge_idx);
                dscore[v] += edges[edge_idx].weight;
            } else {
                dscore[v] -= edges[edge_idx].weight;
            }
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    if (!(cin >> N >> M)) return 0;

    edges.resize(M);
    adj_edge_indices.resize(N + 1);
    for (int i = 0; i < M; ++i) {
        cin >> edges[i].u >> edges[i].v;
        edges[i].weight = 1;
        adj_edge_indices[edges[i].u].push_back(i);
        adj_edge_indices[edges[i].v].push_back(i);
    }

    in_set.assign(N + 1, false);
    dscore.assign(N + 1, 0);
    pos_in_uncov.assign(M, -1);
    
    // Initialize: all OUT, all edges uncovered
    for (int i = 0; i < M; ++i) {
        add_uncov(i);
        dscore[edges[i].u]++;
        dscore[edges[i].v]++;
    }

    // Construct Initial Cover using simple greedy
    while (!uncov_edge_indices.empty()) {
        int best_u = -1;
        long long best_val = -1e18;
        
        // Sample candidates to be fast
        for (int k = 0; k < 50; ++k) {
             int idx = uncov_edge_indices[xorshift96() % uncov_edge_indices.size()];
             int u = edges[idx].u;
             int v = edges[idx].v;
             if (!in_set[u] && dscore[u] > best_val) { best_val = dscore[u]; best_u = u; }
             if (!in_set[v] && dscore[v] > best_val) { best_val = dscore[v]; best_u = v; }
        }
        if (best_u == -1) best_u = edges[uncov_edge_indices[0]].u;
        flip(best_u);
    }
    
    // Simple Pruning
    for (int u = 1; u <= N; ++u) {
        if (in_set[u] && dscore[u] == 0) flip(u);
    }

    vector<bool> best_sol = in_set;
    vector<int> tabu(N + 1, 0);
    long long iter = 0;
    
    // Local Search Loop
    while (get_elapsed() < TIME_LIMIT) {
        // Step 1: Force remove a vertex to reduce cover size
        int remove_cand = -1;
        long long best_remove_score = -1e18;
        for (int u = 1; u <= N; ++u) {
            if (in_set[u] && dscore[u] > best_remove_score) {
                best_remove_score = dscore[u];
                remove_cand = u;
            }
        }
        if (remove_cand == -1) break;
        flip(remove_cand);
        
        // Step 2: Prepare for optimization at new size
        // Reset edge weights to prevent carry-over bias
        for(int i=0; i<M; ++i) edges[i].weight = 1;
        
        // Recompute dscores cleanly
        fill(dscore.begin(), dscore.end(), 0);
        for (int i=0; i<M; ++i) {
            int u = edges[i].u, v = edges[i].v;
            if (!in_set[u] && !in_set[v]) { dscore[u]++; dscore[v]++; }
            else if (in_set[u] && !in_set[v]) dscore[u]--;
            else if (!in_set[u] && in_set[v]) dscore[v]--;
        }
        fill(tabu.begin(), tabu.end(), 0);

        // Step 3: Try to fix the cover (eliminate uncovered edges)
        int inner_iter = 0;
        const int MAX_INNER = 1000000; 
        
        while (!uncov_edge_indices.empty() && get_elapsed() < TIME_LIMIT) {
            iter++; inner_iter++;
            if (inner_iter > MAX_INNER) break;
            
            // Pick an uncovered edge
            int edge_idx = uncov_edge_indices[xorshift96() % uncov_edge_indices.size()];
            int u = edges[edge_idx].u;
            int v = edges[edge_idx].v;
            
            // Heuristic: Add endpoint with better score
            int u_in = (dscore[u] > dscore[v]) ? u : v;
            
            // Heuristic: Remove a vertex from S
            int w_best = -1;
            long long w_best_val = -1e18;
            
            // Sample candidates for removal
            for (int k = 0; k < 50; ++k) {
                int w = (xorshift96() % N) + 1;
                if (in_set[w] && tabu[w] <= iter) {
                    if (dscore[w] > w_best_val) {
                        w_best_val = dscore[w];
                        w_best = w;
                    }
                }
            }
            if (w_best == -1) {
                // If sampling failed, just pick one linearly
                for (int i=1; i<=N; ++i) if (in_set[i]) { w_best = i; break; }
            }
            
            // Perform Swap
            flip(u_in);
            flip(w_best);
            
            // Update Tabu
            int tenure = 3 + (xorshift96() % 10);
            tabu[u_in] = iter + tenure;
            tabu[w_best] = iter + tenure;
            
            // Weighting
            if (inner_iter % 1000 == 0) {
                for (int idx : uncov_edge_indices) {
                    edges[idx].weight++;
                    dscore[edges[idx].u]++;
                    dscore[edges[idx].v]++;
                }
            }
        }
        
        if (uncov_edge_indices.empty()) {
            best_sol = in_set; // Success, try smaller size in next outer loop iteration
        } else {
            break; // Failed to find cover of this size, terminate
        }
    }

    for (int i = 1; i <= N; ++i) cout << (best_sol[i] ? 1 : 0) << "\n";
    return 0;
}