#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>
#include <chrono>
#include <random>

using namespace std;

// Global variables for problem data
int N;
int initial_grid[25][25];

// Result structure
struct Result {
    long long cost;
    vector<string> ops;
};

// Timer
auto start_time = chrono::high_resolution_clock::now();
double get_time() {
    auto now = chrono::high_resolution_clock::now();
    return chrono::duration<double>(now - start_time).count();
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N)) return 0;
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            cin >> initial_grid[i][j];
        }
    }

    // Random number generator with fixed seed for reproducibility
    mt19937 rng(12345);
    
    Result best_res;
    best_res.cost = -1; // Indicates invalid

    // Loop until time limit is close (1.85s out of typically 2.0s)
    do {
        // Randomize parameters for greedy scoring
        // P1: Multiplier for positive height (Attraction to soil sources)
        // P2: Multiplier for valid drop amount (Attraction to soil sinks)
        // P3: Multiplier for load (How much current load influences decision)
        
        double p1 = uniform_real_distribution<double>(1.0, 50.0)(rng);
        double p2 = uniform_real_distribution<double>(1.0, 50.0)(rng);
        double p3 = uniform_real_distribution<double>(0.0, 20.0)(rng);
        
        // Simulation state
        int grid[25][25];
        int non_zero_count = 0;
        for(int i=0; i<N; i++) {
            for(int j=0; j<N; j++) {
                grid[i][j] = initial_grid[i][j];
                if (grid[i][j] != 0) non_zero_count++;
            }
        }

        int r = 0, c = 0;
        int load = 0;
        long long current_run_cost = 0;
        vector<string> current_ops;
        current_ops.reserve(5000);
        
        bool possible = true;

        while (non_zero_count > 0) {
            // Safety break for turns limit
            if (current_ops.size() > 95000) {
                possible = false;
                break;
            }

            // 1. Interaction at current cell
            if (grid[r][c] != 0) {
                int h = grid[r][c];
                if (h > 0) {
                    // Pick up all
                    int amount = h;
                    load += amount;
                    current_run_cost += amount;
                    current_ops.push_back("+" + to_string(amount));
                    grid[r][c] = 0;
                    non_zero_count--;
                } else if (h < 0 && load > 0) {
                    // Drop
                    int amount = min(-h, load);
                    load -= amount;
                    current_run_cost += amount;
                    current_ops.push_back("-" + to_string(amount));
                    grid[r][c] += amount;
                    if (grid[r][c] == 0) non_zero_count--;
                }
            }

            if (non_zero_count == 0) break;

            // 2. Select best target among all non-zero cells
            int best_tr = -1, best_tc = -1;
            double best_score = -1e18;

            for (int i = 0; i < N; i++) {
                for (int j = 0; j < N; j++) {
                    if (grid[i][j] == 0) continue;

                    int dist = abs(r - i) + abs(c - j);
                    double move_cost = dist * (100.0 + load);
                    double score = -move_cost;

                    if (grid[i][j] > 0) {
                        // Source: prefer if close or large amount, penalize if already loaded
                        score += p1 * grid[i][j];
                        score -= p3 * load; 
                    } else {
                        // Sink: prefer if we have load
                        if (load > 0) {
                            int can_drop = min(-grid[i][j], load);
                            score += p2 * can_drop;
                            score += p3 * load; // High load makes sinks more attractive
                        } else {
                            score = -1e18; // Cannot use sink if empty
                        }
                    }

                    // Add random noise to explore different paths
                    score += uniform_real_distribution<double>(0.0, 20.0)(rng);

                    if (score > best_score) {
                        best_score = score;
                        best_tr = i;
                        best_tc = j;
                    }
                }
            }

            if (best_tr == -1) {
                // Should not happen given problem constraints
                possible = false;
                break;
            }

            // 3. Move one step towards target
            struct Cand { int nr, nc; string s; };
            vector<Cand> cands;

            if (best_tr > r) cands.push_back({r+1, c, "D"});
            if (best_tr < r) cands.push_back({r-1, c, "U"});
            if (best_tc > c) cands.push_back({r, c+1, "R"});
            if (best_tc < c) cands.push_back({r, c-1, "L"});

            // Heuristic: prefer direction that lands on a non-zero cell
            int chosen_idx = -1;
            vector<int> preferred_indices;
            for(int k=0; k<(int)cands.size(); ++k) {
                if (grid[cands[k].nr][cands[k].nc] != 0) {
                    preferred_indices.push_back(k);
                }
            }

            if (!preferred_indices.empty()) {
                chosen_idx = preferred_indices[rng() % preferred_indices.size()];
            } else {
                chosen_idx = rng() % cands.size();
            }

            // Execute move
            current_run_cost += (100 + load);
            current_ops.push_back(cands[chosen_idx].s);
            r = cands[chosen_idx].nr;
            c = cands[chosen_idx].nc;
        }

        if (possible) {
            if (best_res.cost == -1 || current_run_cost < best_res.cost) {
                best_res.cost = current_run_cost;
                best_res.ops = current_ops;
            }
        }
    } while (get_time() < 1.85);

    // Output best result
    for (const string& s : best_res.ops) {
        cout << s << "\n";
    }

    return 0;
}