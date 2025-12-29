#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <ctime>
#include <cstdlib>
#include <climits>
#include <chrono>
#include <random>

using namespace std;

// Structure to represent an Oni piece
struct Oni {
    int id;
    int r, c;
};

// Structure to represent a potential move option for an Oni
struct MoveOption {
    int line_id; // 0-19: Row L, 20-39: Row R, 40-59: Col U, 60-79: Col D
    int dist;    // 1-based depth/distance required to remove the Oni
};

// Structure to represent a line (row or column in a specific direction)
struct Line {
    int id;      // 0-79
    int type;    // 0:L, 1:R, 2:U, 3:D
    int index;   // row or column index
    vector<pair<int, int>> compatible_oni; // List of compatible onis: pair<oni_id, dist>
};

int N;
vector<string> board;
vector<Oni> onis;
vector<Line> lines(80);
vector<vector<MoveOption>> oni_options;

// Parse the board to find all Oni positions
void parse_board() {
    onis.clear();
    int oid = 0;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (board[i][j] == 'x') {
                onis.push_back({oid++, i, j});
            }
        }
    }
}

// Check if a move direction is valid for an Oni at (r, c)
// Valid means no Fukunokami ('o') in the path to the edge
bool check_valid(int r, int c, int type) {
    // 0:L, 1:R, 2:U, 3:D
    if (type == 0) { // Left, check (r, 0..c-1)
        for (int k = 0; k < c; ++k) if (board[r][k] == 'o') return false;
    } else if (type == 1) { // Right, check (r, c+1..N-1)
        for (int k = c + 1; k < N; ++k) if (board[r][k] == 'o') return false;
    } else if (type == 2) { // Up, check (0..r-1, c)
        for (int k = 0; k < r; ++k) if (board[k][c] == 'o') return false;
    } else if (type == 3) { // Down, check (r+1..N-1, c)
        for (int k = r + 1; k < N; ++k) if (board[k][c] == 'o') return false;
    }
    return true;
}

// Calculate the distance (number of shifts) to remove an Oni
int get_dist(int r, int c, int type) {
    if (type == 0) return c + 1;     // Shift left c+1 times
    if (type == 1) return N - c;     // Shift right N-c times
    if (type == 2) return r + 1;     // Shift up r+1 times
    if (type == 3) return N - r;     // Shift down N-r times
    return 0;
}

// Precompute valid moves for all Oni and populate line structures
void precompute() {
    oni_options.assign(onis.size(), {});
    for (int i = 0; i < 80; ++i) {
        lines[i].id = i;
        lines[i].compatible_oni.clear();
        if (i < 20) { lines[i].type = 0; lines[i].index = i; }
        else if (i < 40) { lines[i].type = 1; lines[i].index = i - 20; }
        else if (i < 60) { lines[i].type = 2; lines[i].index = i - 40; }
        else { lines[i].type = 3; lines[i].index = i - 60; }
    }

    for (const auto& oni : onis) {
        // Left
        if (check_valid(oni.r, oni.c, 0)) {
            int dist = get_dist(oni.r, oni.c, 0);
            int lid = oni.r;
            oni_options[oni.id].push_back({lid, dist});
            lines[lid].compatible_oni.push_back({oni.id, dist});
        }
        // Right
        if (check_valid(oni.r, oni.c, 1)) {
            int dist = get_dist(oni.r, oni.c, 1);
            int lid = 20 + oni.r;
            oni_options[oni.id].push_back({lid, dist});
            lines[lid].compatible_oni.push_back({oni.id, dist});
        }
        // Up
        if (check_valid(oni.r, oni.c, 2)) {
            int dist = get_dist(oni.r, oni.c, 2);
            int lid = 40 + oni.c;
            oni_options[oni.id].push_back({lid, dist});
            lines[lid].compatible_oni.push_back({oni.id, dist});
        }
        // Down
        if (check_valid(oni.r, oni.c, 3)) {
            int dist = get_dist(oni.r, oni.c, 3);
            int lid = 60 + oni.c;
            oni_options[oni.id].push_back({lid, dist});
            lines[lid].compatible_oni.push_back({oni.id, dist});
        }
    }

    // Sort compatible onis by distance for easier greedy logic
    for (int i = 0; i < 80; ++i) {
        sort(lines[i].compatible_oni.begin(), lines[i].compatible_oni.end(), 
             [](const pair<int,int>& a, const pair<int,int>& b){
                 return a.second < b.second;
             });
    }
}

struct Solution {
    vector<int> line_depths; // depth for each of 80 lines
    int total_cost;
};

int calculate_cost(const vector<int>& depths) {
    int cost = 0;
    for (int d : depths) cost += 2 * d; // Cost is shift out + shift back
    return cost;
}

mt19937 rng(12345);

// Greedy algorithm to construct a valid solution
// noise_level allows for randomized decision making
Solution solve_greedy(double noise_level) {
    vector<int> current_depths(80, 0);
    vector<bool> covered(onis.size(), false);
    int covered_count = 0;
    int num_onis = onis.size();

    while (covered_count < num_onis) {
        int best_line = -1;
        int best_depth = -1;
        double best_score = 1e18;
        
        // Evaluate all possible moves (extending a line depth)
        for (int i = 0; i < 80; ++i) {
            // Check extensions to cover each compatible oni
            for (auto& p : lines[i].compatible_oni) {
                int dist = p.second;
                if (dist <= current_depths[i]) continue;
                
                // Cost to extend line to this depth
                int cost_increase = 2 * (dist - current_depths[i]);
                int new_cover = 0;
                
                // Calculate how many NEW onis are covered by this extension
                for (auto& q : lines[i].compatible_oni) {
                    if (q.second > dist) break;
                    if (q.second > current_depths[i]) {
                        if (!covered[q.first]) {
                            new_cover++;
                        }
                    }
                }
                
                if (new_cover > 0) {
                    // Score: lower is better. Cost per newly covered item.
                    double score = (double)cost_increase / new_cover;
                    if (noise_level > 0) {
                        uniform_real_distribution<double> dist_noise(1.0 - noise_level, 1.0 + noise_level);
                        score *= dist_noise(rng);
                    }
                    
                    if (score < best_score) {
                        best_score = score;
                        best_line = i;
                        best_depth = dist;
                    }
                }
            }
        }
        
        if (best_line != -1) {
            current_depths[best_line] = best_depth;
            // Mark newly covered onis
            for (auto& q : lines[best_line].compatible_oni) {
                if (q.second <= best_depth) {
                    if (!covered[q.first]) {
                        covered[q.first] = true;
                        covered_count++;
                    }
                }
            }
        } else {
            break; // Should not happen
        }
    }
    
    return {current_depths, calculate_cost(current_depths)};
}

// Optimization phase: try to reduce depths while maintaining validity
void prune(Solution& sol) {
    bool changed = true;
    vector<int> indices(80);
    for(int i=0; i<80; ++i) indices[i] = i;
    
    while(changed) {
        changed = false;
        shuffle(indices.begin(), indices.end(), rng);
        
        for (int lid : indices) {
            if (sol.line_depths[lid] == 0) continue;
            
            int current_d = sol.line_depths[lid];
            
            // Try setting depth to 0 and see what needs coverage
            sol.line_depths[lid] = 0;
            
            int max_needed = 0;
            for (auto& p : lines[lid].compatible_oni) {
                int oid = p.first;
                int odist = p.second;
                if (odist > current_d) break;
                
                // Check if this oni is covered by any OTHER line in the current solution
                bool covered_by_other = false;
                for (auto& opt : oni_options[oid]) {
                    if (opt.line_id == lid) continue;
                    if (sol.line_depths[opt.line_id] >= opt.dist) {
                        covered_by_other = true;
                        break;
                    }
                }
                
                if (!covered_by_other) {
                    max_needed = max(max_needed, odist);
                }
            }
            
            if (max_needed != current_d) {
                sol.line_depths[lid] = max_needed;
                sol.total_cost = calculate_cost(sol.line_depths);
                changed = true;
            } else {
                sol.line_depths[lid] = current_d; // revert
            }
        }
    }
    sol.total_cost = calculate_cost(sol.line_depths);
}

int main() {
    // Optimize I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N)) return 0;
    board.resize(N);
    for (int i = 0; i < N; ++i) cin >> board[i];

    parse_board();
    precompute();
    
    auto start_time = chrono::steady_clock::now();
    
    Solution best_sol;
    best_sol.total_cost = 1e9;
    
    // First pass: deterministic greedy
    {
        Solution sol = solve_greedy(0.0);
        prune(sol);
        if (sol.total_cost < best_sol.total_cost) best_sol = sol;
    }
    
    // Subsequent passes: randomized greedy
    int iters = 0;
    while (true) {
        auto curr_time = chrono::steady_clock::now();
        double elapsed = chrono::duration_cast<chrono::duration<double>>(curr_time - start_time).count();
        if (elapsed > 1.8) break; // Time limit safe margin
        
        iters++;
        // Vary noise level slightly
        double noise = 0.2 + (iters % 10) * 0.05;
        Solution sol = solve_greedy(noise);
        prune(sol);
        if (sol.total_cost < best_sol.total_cost) best_sol = sol;
    }
    
    // Generate output based on best solution
    for (int i = 0; i < 80; ++i) {
        if (best_sol.line_depths[i] > 0) {
            int d = best_sol.line_depths[i];
            char dir;
            int idx = lines[i].index;
            if (lines[i].type == 0) dir = 'L';
            else if (lines[i].type == 1) dir = 'R';
            else if (lines[i].type == 2) dir = 'U';
            else dir = 'D';
            
            // Output operations to shift out
            for (int k = 0; k < d; ++k) cout << dir << " " << idx << "\n";
            
            // Output operations to shift back (restore positions)
            char rev_dir;
            if (dir == 'L') rev_dir = 'R';
            else if (dir == 'R') rev_dir = 'L';
            else if (dir == 'U') rev_dir = 'D';
            else rev_dir = 'U';
            
            for (int k = 0; k < d; ++k) cout << rev_dir << " " << idx << "\n";
        }
    }

    return 0;
}