#include <vector>
#include <cmath>
#include <algorithm>
#include <random>
#include <chrono>
#include <map>
#include <iostream>

using namespace std;

static int N_val;
static int M_val;
static vector<vector<bool>> adj;
static vector<pair<int, int>> edges_list;
static chrono::high_resolution_clock::time_point start_time;

static double get_time() {
    return chrono::duration<double>(chrono::high_resolution_clock::now() - start_time).count();
}

struct MapSolver {
    int K;
    vector<vector<int>> grid;
    vector<int> color_counts;
    vector<vector<int>> edge_counts;
    int present_edges_count;
    int present_colors_count;
    mt19937 rng;
    vector<int> candidates;

    MapSolver(int k, int seed) : K(k), rng(seed) {
        grid.resize(K, vector<int>(K));
        color_counts.resize(N_val + 1, 0);
        edge_counts.resize(N_val + 1, vector<int>(N_val + 1, 0));
        candidates.reserve(N_val);
    }

    void initialize() {
        for(int r=0; r<K; ++r) {
            for(int c=0; c<K; ++c) {
                // Initialize with 1s. This is a valid configuration with respect to the hard constraints
                // (no invalid adjacencies), assuming self-loops (1-1) are allowed or ignored.
                // The problem forbids adjacent cells with DIFFERENT colors if not in adj list.
                // Same colors are fine.
                grid[r][c] = 1; 
            }
        }
        recalc_stats();
    }

    void recalc_stats() {
        fill(color_counts.begin(), color_counts.end(), 0);
        for(int i=1; i<=N_val; ++i) fill(edge_counts[i].begin(), edge_counts[i].end(), 0);
        present_edges_count = 0;
        present_colors_count = 0;

        for (int r = 0; r < K; ++r) {
            for (int c = 0; c < K; ++c) {
                int u = grid[r][c];
                color_counts[u]++;
                if (c + 1 < K) {
                    int v = grid[r][c+1];
                    if (u != v) {
                        int a = min(u, v), b = max(u, v);
                        edge_counts[a][b]++;
                    }
                }
                if (r + 1 < K) {
                    int v = grid[r+1][c];
                    if (u != v) {
                        int a = min(u, v), b = max(u, v);
                        edge_counts[a][b]++;
                    }
                }
            }
        }
        for (int i = 1; i <= N_val; ++i) if (color_counts[i] > 0) present_colors_count++;
        for (auto &p : edges_list) {
            if (edge_counts[p.first][p.second] > 0) present_edges_count++;
        }
    }
    
    int get_cost() {
        return (N_val - present_colors_count) * 500 + (M_val - present_edges_count);
    }

    bool solve(double timeout) {
        int cost = get_cost();
        if (cost == 0) return true;
        
        double T = 2.0;
        double decay = 0.99995; 
        
        uniform_int_distribution<int> dist_coord(0, K-1);
        uniform_real_distribution<double> dist_real(0.0, 1.0);
        
        int iter = 0;
        while (true) {
            iter++;
            if ((iter & 1023) == 0) {
                if (get_time() > timeout) break;
            }
            
            int r = dist_coord(rng);
            int c = dist_coord(rng);
            int current_color = grid[r][c];
            
            int n_up = (r > 0) ? grid[r-1][c] : 0;
            int n_down = (r + 1 < K) ? grid[r+1][c] : 0;
            int n_left = (c > 0) ? grid[r][c-1] : 0;
            int n_right = (c + 1 < K) ? grid[r][c+1] : 0;
            
            candidates.clear();
            for (int cand = 1; cand <= N_val; ++cand) {
                if (cand == current_color) continue;
                // Hard constraint check: candidates must be compatible with all neighbors
                if (n_up && cand != n_up && !adj[cand][n_up]) continue;
                if (n_down && cand != n_down && !adj[cand][n_down]) continue;
                if (n_left && cand != n_left && !adj[cand][n_left]) continue;
                if (n_right && cand != n_right && !adj[cand][n_right]) continue;
                candidates.push_back(cand);
            }
            
            if (candidates.empty()) continue;
            
            int new_color = candidates[uniform_int_distribution<int>(0, candidates.size()-1)(rng)];
            
            // Calculate Delta Cost
            int delta = 0;
            
            // Delta for Colors
            if (color_counts[current_color] == 1) delta += 500;
            if (color_counts[new_color] == 0) delta -= 500;
            
            // Delta for Edges
            auto calc_edge_change = [&](int u, int neighbor, int diff) {
                if (neighbor == 0 || u == neighbor) return 0;
                int a = min(u, neighbor), b = max(u, neighbor);
                int old_c = edge_counts[a][b];
                int new_c = old_c + diff;
                if (adj[a][b]) {
                    if (old_c == 0 && new_c > 0) return -1;
                    if (old_c > 0 && new_c == 0) return 1;
                }
                return 0;
            };
            
            if (n_up) { delta += calc_edge_change(current_color, n_up, -1); delta += calc_edge_change(new_color, n_up, 1); }
            if (n_down) { delta += calc_edge_change(current_color, n_down, -1); delta += calc_edge_change(new_color, n_down, 1); }
            if (n_left) { delta += calc_edge_change(current_color, n_left, -1); delta += calc_edge_change(new_color, n_left, 1); }
            if (n_right) { delta += calc_edge_change(current_color, n_right, -1); delta += calc_edge_change(new_color, n_right, 1); }
            
            bool accept = (delta <= 0);
            if (!accept) {
                accept = (dist_real(rng) < exp(-delta / T));
            }
            
            if (accept) {
                grid[r][c] = new_color;
                
                color_counts[current_color]--;
                if (color_counts[current_color] == 0) present_colors_count--;
                if (color_counts[new_color] == 0) present_colors_count++;
                color_counts[new_color]++;
                
                auto update_edge = [&](int u, int neighbor, int diff) {
                    if (neighbor == 0 || u == neighbor) return;
                    int a = min(u, neighbor), b = max(u, neighbor);
                    int old_c = edge_counts[a][b];
                    edge_counts[a][b] += diff;
                    if (adj[a][b]) {
                        if (old_c == 0 && edge_counts[a][b] > 0) present_edges_count++;
                        if (old_c > 0 && edge_counts[a][b] == 0) present_edges_count--;
                    }
                };
                
                if (n_up) { update_edge(current_color, n_up, -1); update_edge(new_color, n_up, 1); }
                if (n_down) { update_edge(current_color, n_down, -1); update_edge(new_color, n_down, 1); }
                if (n_left) { update_edge(current_color, n_left, -1); update_edge(new_color, n_left, 1); }
                if (n_right) { update_edge(current_color, n_right, -1); update_edge(new_color, n_right, 1); }
                
                cost += delta;
                if (cost == 0) return true;
            }
            T *= decay;
            if (T < 0.05) T = 0.05; 
        }
        return false;
    }
};

vector<vector<int>> create_map(int N, int M, vector<int> A, vector<int> B) {
    start_time = chrono::high_resolution_clock::now();
    N_val = N;
    M_val = M;
    adj.assign(N + 1, vector<bool>(N + 1, false));
    edges_list.clear();
    for (int i = 0; i < M; ++i) {
        adj[A[i]][B[i]] = adj[B[i]][A[i]] = true;
        edges_list.push_back({A[i], B[i]});
    }
    
    if (N == 1) return {{1}};
    
    int start_K = sqrt(N);
    if (start_K < 2) start_K = 2;
    
    for (int k = start_K; k <= 240; ++k) {
        double current_time = get_time();
        if (current_time > 1.95) break; 
        
        double time_slice = 0.15;
        if (N > 15) time_slice = 0.25;
        
        MapSolver solver(k, k * 12345 + 7);
        solver.initialize();
        if (solver.solve(current_time + time_slice)) {
            return solver.grid;
        }
    }
    
    return {{1}};
}