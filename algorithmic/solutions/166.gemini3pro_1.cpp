#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

const int N = 20;

struct Point {
    int r, c;
};

int dist(Point p1, Point p2) {
    return abs(p1.r - p2.r) + abs(p1.c - p2.c);
}

int initial_grid[N][N];

struct Solution {
    vector<string> ops;
    long long cost;
};

char moveChar(int dir) {
    if (dir == 0) return 'U';
    if (dir == 1) return 'D';
    if (dir == 2) return 'L';
    if (dir == 3) return 'R';
    return '?';
}

struct State {
    int grid[N][N];
    Point truck;
    int load;
    long long current_cost;
    vector<string> history;
    
    State() {
        for(int i=0; i<N; ++i)
            for(int j=0; j<N; ++j)
                grid[i][j] = initial_grid[i][j];
        truck = {0, 0};
        load = 0;
        current_cost = 0;
    }
};

void add_moves(State& s, Point target) {
    // Greedy movement (Manhattan)
    while(s.truck.r != target.r) {
        int dir = (target.r > s.truck.r) ? 1 : 0; 
        s.history.push_back(string(1, moveChar(dir)));
        s.current_cost += (100 + s.load);
        s.truck.r += (dir == 1 ? 1 : -1);
    }
    while(s.truck.c != target.c) {
        int dir = (target.c > s.truck.c) ? 3 : 2; 
        s.history.push_back(string(1, moveChar(dir)));
        s.current_cost += (100 + s.load);
        s.truck.c += (dir == 3 ? 1 : -1);
    }
}

mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

Solution solve_greedy(double w1, double w2, double w3, double w4, int top_k) {
    State s;
    int remaining_nonzero = 0;
    for(int i=0; i<N; ++i) 
        for(int j=0; j<N; ++j) 
            if(s.grid[i][j] != 0) remaining_nonzero++;

    int iter = 0;
    while(remaining_nonzero > 0 && iter < 10000) {
        iter++;
        
        struct Cand {
            Point p;
            double score;
            int type; // 1: pick up, -1: drop
            int amount;
        };
        vector<Cand> candidates;
        
        // Find negative nodes for heuristic
        vector<Point> negatives;
        for(int i=0; i<N; ++i) 
            for(int j=0; j<N; ++j) 
                if(s.grid[i][j] < 0) negatives.push_back({i, j});
        
        for(int i=0; i<N; ++i) {
            for(int j=0; j<N; ++j) {
                if(s.grid[i][j] == 0) continue;
                if(s.load == 0 && s.grid[i][j] < 0) continue; // Can't drop if empty

                Point p = {i, j};
                int d = dist(s.truck, p);
                long long move_cost = (long long)d * (100 + s.load);
                
                double heuristic = 0;
                int type = 0;
                int amount = 0;

                if (s.grid[i][j] > 0) {
                    type = 1;
                    amount = s.grid[i][j];
                    int min_sink_dist = 1000;
                    if (negatives.empty()) min_sink_dist = 0; 
                    else {
                        for(auto& neg : negatives) {
                            int d_neg = dist(p, neg);
                            if(d_neg < min_sink_dist) min_sink_dist = d_neg;
                        }
                    }
                    // Penalty for picking up (deferring work and increasing load)
                    heuristic = w1 * amount * min_sink_dist + w4 * amount;
                } else {
                    type = -1;
                    amount = min(s.load, -s.grid[i][j]);
                    if (amount == 0) continue; 
                    
                    // Reward for dropping
                    heuristic = -w2 * amount;
                    // Bonus for clearing the node
                    if (amount == -s.grid[i][j]) heuristic -= w3;
                }
                
                candidates.push_back({p, (double)move_cost + heuristic, type, amount});
            }
        }
        
        if(candidates.empty()) break; 

        // Sort candidates by cost (lower is better)
        sort(candidates.begin(), candidates.end(), [](const Cand& a, const Cand& b){
            return a.score < b.score;
        });

        // Pick one from top K to introduce variety in random runs
        int pick_idx = 0;
        if(top_k > 1 && candidates.size() > 1) {
            int limit = min((int)candidates.size(), top_k);
            uniform_int_distribution<int> dist_idx(0, limit - 1);
            pick_idx = dist_idx(rng);
        }
        
        Cand chosen = candidates[pick_idx];
        
        // Perform move
        add_moves(s, chosen.p);
        
        // Perform operation
        if(chosen.type == 1) {
            // Load
            int amt = s.grid[chosen.p.r][chosen.p.c];
            s.history.push_back("+" + to_string(amt));
            s.load += amt;
            s.grid[chosen.p.r][chosen.p.c] = 0;
            s.current_cost += amt;
            remaining_nonzero--;
        } else {
            // Unload
            int amt = chosen.amount; 
            s.history.push_back("-" + to_string(amt));
            s.load -= amt;
            s.grid[chosen.p.r][chosen.p.c] += amt; // grid is negative
            s.current_cost += amt;
            if(s.grid[chosen.p.r][chosen.p.c] == 0) remaining_nonzero--;
        }
    }
    
    return {s.history, s.current_cost};
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int N_in;
    if (!(cin >> N_in)) return 0;
    
    for(int i=0; i<N; ++i) {
        for(int j=0; j<N; ++j) {
            cin >> initial_grid[i][j];
        }
    }
    
    auto start_time = chrono::steady_clock::now();
    double time_limit = 1.90; // seconds

    Solution best_sol;
    best_sol.cost = -1;
    
    // Heuristic parameter ranges
    uniform_real_distribution<double> dist_w1(0.0, 10.0); // Dist penalty factor
    uniform_real_distribution<double> dist_w2(10.0, 200.0); // Drop reward factor
    uniform_real_distribution<double> dist_w3(0.0, 2000.0); // Completion bonus
    uniform_real_distribution<double> dist_w4(0.0, 50.0);   // Load penalty factor

    int runs = 0;
    while(true) {
        runs++;
        auto curr_time = chrono::steady_clock::now();
        chrono::duration<double> elapsed = curr_time - start_time;
        if(elapsed.count() > time_limit) break;

        double w1, w2, w3, w4;
        int k;
        if(runs == 1) {
            // Baseline sensible parameters
            w1 = 1.0; w2 = 50.0; w3 = 500.0; w4 = 1.0; k = 1;
        } else {
            // Randomized parameters
            w1 = dist_w1(rng);
            w2 = dist_w2(rng);
            w3 = dist_w3(rng);
            w4 = dist_w4(rng);
            k = (runs % 3) + 1;
        }

        Solution sol = solve_greedy(w1, w2, w3, w4, k);
        if(best_sol.cost == -1 || sol.cost < best_sol.cost) {
            best_sol = sol;
        }
    }
    
    for(const string& s : best_sol.ops) {
        cout << s << "\n";
    }

    return 0;
}