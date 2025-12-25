#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>
#include <ctime>
#include <cstdlib>
#include <chrono>

using namespace std;

// Problem Constants
const int N = 20;
const int MAX_TURNS = 100000;

// Global variables to store input
int initial_grid[N][N];
int g_N;

struct Solution {
    vector<string> ops;
    long long cost;
};

// Parameters for the heuristic
struct Params {
    double dist_pow;
    double amount_pow;
    double pick_base;
    double drop_base;
    double load_penalty_factor;
    double opportunistic_pickup_coeff;
    double noise_mag;
};

// Helper for Manhattan distance
int dist(int r1, int c1, int r2, int c2) {
    return abs(r1 - r2) + abs(c1 - c2);
}

// Random double generator
double rand_double(double min, double max) {
    return min + (double)rand() / RAND_MAX * (max - min);
}

// Main logic to generate a solution given parameters
Solution solve(const Params& p) {
    // Copy initial grid
    int grid[N][N];
    for(int i=0; i<N; ++i) for(int j=0; j<N; ++j) grid[i][j] = initial_grid[i][j];
    
    int r = 0, c = 0;
    int load = 0;
    long long current_cost = 0;
    vector<string> history;
    
    // Manage list of targets (cells with non-zero height)
    vector<pair<int,int>> targets;
    targets.reserve(N*N);
    for(int i=0; i<N; ++i) {
        for(int j=0; j<N; ++j) {
            if (grid[i][j] != 0) targets.push_back({i,j});
        }
    }

    int turns = 0;
    
    // Main loop until all targets cleared or turn limit reached
    while(!targets.empty() && turns < MAX_TURNS) {
        int best_idx = -1;
        double best_score = -1e18;
        
        // 1. Select Best Target
        for (int k = 0; k < targets.size(); ++k) {
            int i = targets[k].first;
            int j = targets[k].second;
            
            // Lazy removal of cleared targets
            if (grid[i][j] == 0) {
                targets[k] = targets.back();
                targets.pop_back();
                k--;
                continue;
            }
            
            int d = dist(r, c, i, j);
            int val = grid[i][j];
            bool is_pick = (val > 0);
            
            // If empty, we must pick
            if (load == 0 && !is_pick) continue;
            
            int amt = is_pick ? val : min(load, -val);
            if (amt == 0) continue;
            
            // Heuristic Scoring
            double term1 = pow(amt, p.amount_pow);
            double term2 = pow(d + 1, p.dist_pow); // +1 to avoid division by zero
            
            double type_mult = 1.0;
            if (is_pick) {
                // Penalize picking if load is high
                type_mult = p.pick_base / (1.0 + load * p.load_penalty_factor);
            } else {
                // Encourage dropping if load is high
                type_mult = p.drop_base * (1.0 + load * p.load_penalty_factor);
            }
            
            double s = (term1 / term2) * type_mult;
            
            // Add noise
            if (p.noise_mag > 1e-6) {
                double noise = ((double)rand() / RAND_MAX - 0.5) * 2.0 * p.noise_mag;
                s *= (1.0 + noise);
            }
            
            if (s > best_score) {
                best_score = s;
                best_idx = k;
            }
        }
        
        // If no valid target found (should typically not happen unless done)
        if (best_idx == -1) break;

        int tr = targets[best_idx].first;
        int tc = targets[best_idx].second;
        
        // 2. Move towards target with opportunistic interactions
        while ((r != tr || c != tc) && turns < MAX_TURNS) {
            char move_char = ' ';
            int nr = r, nc = c;
            
            // Randomly choose dimension to move along to reduce bias
            bool move_row = false;
            if (r != tr && c != tc) {
                move_row = (rand() % 2 == 0);
            } else if (r != tr) {
                move_row = true;
            } else {
                move_row = false;
            }
            
            if (move_row) {
                if (tr > r) { nr++; move_char = 'D'; }
                else { nr--; move_char = 'U'; }
            } else {
                if (tc > c) { nc++; move_char = 'R'; }
                else { nc--; move_char = 'L'; }
            }
            
            // Execute Move
            current_cost += (100 + load);
            r = nr; c = nc;
            history.push_back(string(1, move_char));
            turns++;
            
            // Check for opportunistic interactions at the new cell
            if (grid[r][c] != 0) {
                if (grid[r][c] < 0 && load > 0) {
                    // Always drop if possible and needed
                    int drop = min(load, -grid[r][c]);
                    history.push_back("-" + to_string(drop));
                    current_cost += drop;
                    load -= drop;
                    grid[r][c] += drop;
                    
                    // If we depleted load and our target was a drop-target, we might need to re-think
                    if (load == 0 && grid[tr][tc] < 0) {
                        goto reselect;
                    }
                } else if (grid[r][c] > 0) {
                    // Pick up if the cost of carrying is justified by saving a future visit
                    int dist_rem = dist(r, c, tr, tc);
                    // Approximation: pick if carrying cost < visit cost threshold
                    if (grid[r][c] * dist_rem * p.opportunistic_pickup_coeff < 100.0) {
                        int pick = grid[r][c];
                        history.push_back("+" + to_string(pick));
                        current_cost += pick;
                        load += pick;
                        grid[r][c] -= pick;
                    }
                }
            }
        }
        
        // At target
        if (r == tr && c == tc) {
            if (grid[r][c] > 0) {
                 int pick = grid[r][c];
                 history.push_back("+" + to_string(pick));
                 current_cost += pick;
                 load += pick;
                 grid[r][c] = 0;
            } else if (grid[r][c] < 0 && load > 0) {
                 int drop = min(load, -grid[r][c]);
                 history.push_back("-" + to_string(drop));
                 current_cost += drop;
                 load -= drop;
                 grid[r][c] += drop;
            }
        }
        
        reselect:;
    }
    
    // Check if solution is complete and apply penalty if not
    long long penalty = 0;
    for(int i=0; i<N; ++i) {
        for(int j=0; j<N; ++j) {
            if (grid[i][j] != 0) {
                penalty += 10000 + 100 * abs(grid[i][j]);
            }
        }
    }
    current_cost += penalty;
    
    return {history, current_cost};
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> g_N)) return 0;
    for(int i=0; i<N; ++i) {
        for(int j=0; j<N; ++j) {
            cin >> initial_grid[i][j];
        }
    }

    auto start_time = chrono::high_resolution_clock::now();
    double time_limit = 1.9; // Allow 1.9s for search
    
    Solution best_sol;
    best_sol.cost = -1; 
    
    srand(2023); // Fixed seed for reproducibility
    
    while(true) {
        auto curr_time = chrono::high_resolution_clock::now();
        if (chrono::duration<double>(curr_time - start_time).count() > time_limit) break;
        
        Params p;
        // Randomly sample hyperparameters
        p.dist_pow = rand_double(0.5, 3.0);
        p.amount_pow = rand_double(0.5, 2.0);
        p.pick_base = rand_double(0.5, 2.0);
        p.drop_base = rand_double(1.0, 4.0); // Dropping usually preferred to reduce move cost
        p.load_penalty_factor = rand_double(0.0001, 0.05);
        p.opportunistic_pickup_coeff = rand_double(0.1, 5.0);
        p.noise_mag = rand_double(0.0, 0.5);
        
        Solution sol = solve(p);
        
        if (best_sol.cost == -1 || sol.cost < best_sol.cost) {
            best_sol = sol;
        }
    }
    
    for(const string& s : best_sol.ops) {
        cout << s << "\n";
    }
    
    return 0;
}