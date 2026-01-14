#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <unordered_map>
#include <algorithm>
#include <map>

using namespace std;

// Structure to hold static vehicle information
struct Vehicle {
    int id;
    int len;
    bool is_vert; // true if vertical, false if horizontal
    int fixed;    // col index if vertical, row index if horizontal
};

// Structure to record moves for path reconstruction
struct Move {
    int v_idx; // index in the vehicles vector
    int dir;   // +1 or -1
};

// Global variables
int N = 0;
vector<Vehicle> vehicles;
long long start_state = 0;

// BFS State Management
unordered_map<long long, int> state_to_id;
vector<long long> id_to_state;
vector<int> dist_start;
vector<pair<int, Move>> parent; 
vector<int> dist_target;

// Packing state into a 64-bit integer
// Each vehicle has a variable coordinate (0-5), requires 3 bits.
// Max 10 vehicles => 30 bits.
long long pack(const vector<int>& vars) {
    long long s = 0;
    for (int i = 0; i < N; ++i) {
        s |= ((long long)vars[i] << (3 * i));
    }
    return s;
}

// Unpacking state
vector<int> unpack(long long s) {
    vector<int> vars(N);
    for (int i = 0; i < N; ++i) {
        vars[i] = (s >> (3 * i)) & 7;
    }
    return vars;
}

// Helper to get or create state ID
int get_id(long long s) {
    if (state_to_id.find(s) == state_to_id.end()) {
        int id = state_to_id.size();
        state_to_id[s] = id;
        id_to_state.push_back(s);
        dist_start.push_back(-1);
        parent.push_back({-1, {0, 0}});
        dist_target.push_back(-1);
        return id;
    }
    return state_to_id[s];
}

// Function to fill a board grid based on state variables
// Returns true if valid (no collisions/bounds), false otherwise
void fill_board(const vector<int>& vars, int board[6][6]) {
    for (int r = 0; r < 6; ++r)
        for (int c = 0; c < 6; ++c)
            board[r][c] = 0;

    for (int i = 0; i < N; ++i) {
        int v = vars[i];
        int id = vehicles[i].id;
        if (vehicles[i].is_vert) {
            int c = vehicles[i].fixed;
            for (int k = 0; k < vehicles[i].len; ++k) {
                board[v + k][c] = id;
            }
        } else {
            int r = vehicles[i].fixed;
            for (int k = 0; k < vehicles[i].len; ++k) {
                board[r][v + k] = id;
            }
        }
    }
}

int main() {
    // Optimize I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int grid[6][6];
    map<int, vector<pair<int, int>>> v_cells;

    // Read Input
    for (int r = 0; r < 6; ++r) {
        for (int c = 0; c < 6; ++c) {
            cin >> grid[r][c];
            if (grid[r][c] > 0) {
                v_cells[grid[r][c]].push_back({r, c});
            }
        }
    }

    N = v_cells.size();
    vehicles.resize(N);
    vector<int> initial_vars(N);

    // Parse vehicles. 
    // v_cells map is sorted by ID, so vehicles vector will be sorted by ID.
    // Index 0 is ID 1 (Red Car).
    int idx = 0;
    for (auto const& [id, cells] : v_cells) {
        vehicles[idx].id = id;
        vehicles[idx].len = cells.size();
        
        int min_r = 6, max_r = -1, min_c = 6, max_c = -1;
        for (auto p : cells) {
            min_r = min(min_r, p.first);
            max_r = max(max_r, p.first);
            min_c = min(min_c, p.second);
            max_c = max(max_c, p.second);
        }

        if (max_r > min_r) {
            vehicles[idx].is_vert = true;
            vehicles[idx].fixed = min_c;
            initial_vars[idx] = min_r;
        } else {
            vehicles[idx].is_vert = false;
            vehicles[idx].fixed = min_r;
            initial_vars[idx] = min_c;
        }
        idx++;
    }

    start_state = pack(initial_vars);
    int start_node = get_id(start_state);
    dist_start[start_node] = 0;

    // BFS 1: Find all reachable states
    queue<int> q;
    q.push(start_node);

    int board[6][6]; // Reusable board buffer

    while (!q.empty()) {
        int u = q.front();
        q.pop();

        vector<int> vars = unpack(id_to_state[u]);
        fill_board(vars, board);

        for (int i = 0; i < N; ++i) {
            int cur = vars[i];
            
            // Move Backward (-1)
            if (cur > 0) {
                bool free = false;
                if (vehicles[i].is_vert) {
                    if (board[cur - 1][vehicles[i].fixed] == 0) free = true;
                } else {
                    if (board[vehicles[i].fixed][cur - 1] == 0) free = true;
                }
                
                if (free) {
                    vars[i]--;
                    long long next_s = pack(vars);
                    int v = get_id(next_s);
                    if (dist_start[v] == -1) {
                        dist_start[v] = dist_start[u] + 1;
                        parent[v] = {u, {i, -1}};
                        q.push(v);
                    }
                    vars[i]++; // backtrack
                }
            }

            // Move Forward (+1)
            if (cur + vehicles[i].len < 6) {
                bool free = false;
                if (vehicles[i].is_vert) {
                    if (board[cur + vehicles[i].len][vehicles[i].fixed] == 0) free = true;
                } else {
                    if (board[vehicles[i].fixed][cur + vehicles[i].len] == 0) free = true;
                }
                
                if (free) {
                    vars[i]++;
                    long long next_s = pack(vars);
                    int v = get_id(next_s);
                    if (dist_start[v] == -1) {
                        dist_start[v] = dist_start[u] + 1;
                        parent[v] = {u, {i, 1}};
                        q.push(v);
                    }
                    vars[i]--; // backtrack
                }
            }
        }
    }

    // BFS 2: Calculate distances to "Target"
    // Target: Car 1 (index 0) at col 4 (occupying 4 and 5).
    // From col 4, it takes 2 steps to completely exit: 4->5, 5->6.
    queue<int> q2;
    for (int i = 0; i < id_to_state.size(); ++i) {
        vector<int> vars = unpack(id_to_state[i]);
        if (vars[0] == 4) {
            dist_target[i] = 0;
            q2.push(i);
        }
    }

    // Run BFS on implicit graph (undirected) starting from all target states
    while (!q2.empty()) {
        int u = q2.front();
        q2.pop();

        vector<int> vars = unpack(id_to_state[u]);
        fill_board(vars, board);

        // Generate neighbors again (same as forward BFS)
        for (int i = 0; i < N; ++i) {
            int cur = vars[i];
            
            // Try moves -1
            if (cur > 0) {
                bool free = false;
                if (vehicles[i].is_vert) {
                    if (board[cur - 1][vehicles[i].fixed] == 0) free = true;
                } else {
                    if (board[vehicles[i].fixed][cur - 1] == 0) free = true;
                }
                if (free) {
                    vars[i]--;
                    long long next_s = pack(vars);
                    auto it = state_to_id.find(next_s);
                    if (it != state_to_id.end()) {
                        int v = it->second;
                        if (dist_target[v] == -1) {
                            dist_target[v] = dist_target[u] + 1;
                            q2.push(v);
                        }
                    }
                    vars[i]++;
                }
            }
            
            // Try moves +1
            if (cur + vehicles[i].len < 6) {
                bool free = false;
                if (vehicles[i].is_vert) {
                    if (board[cur + vehicles[i].len][vehicles[i].fixed] == 0) free = true;
                } else {
                    if (board[vehicles[i].fixed][cur + vehicles[i].len] == 0) free = true;
                }
                if (free) {
                    vars[i]++;
                    long long next_s = pack(vars);
                    auto it = state_to_id.find(next_s);
                    if (it != state_to_id.end()) {
                        int v = it->second;
                        if (dist_target[v] == -1) {
                            dist_target[v] = dist_target[u] + 1;
                            q2.push(v);
                        }
                    }
                    vars[i]--;
                }
            }
        }
    }

    // Find best state
    int best_u = -1;
    int max_steps = -1;

    for (int i = 0; i < id_to_state.size(); ++i) {
        if (dist_target[i] != -1) {
            int steps = dist_target[i] + 2; // +2 steps to exit from pos 4
            if (steps > max_steps) {
                max_steps = steps;
                best_u = i;
            }
        }
    }

    // Output
    cout << max_steps << " " << dist_start[best_u] << "\n";

    // Path reconstruction
    vector<string> output_moves;
    int curr = best_u;
    while (curr != start_node) {
        auto p = parent[curr];
        int prev = p.first;
        Move m = p.second;
        
        int v_idx = m.v_idx;
        int dir = m.dir;
        int id = vehicles[v_idx].id;
        
        char c;
        if (vehicles[v_idx].is_vert) {
            c = (dir == 1) ? 'D' : 'U';
        } else {
            c = (dir == 1) ? 'R' : 'L';
        }
        
        output_moves.push_back(to_string(id) + " " + c);
        curr = prev;
    }
    
    reverse(output_moves.begin(), output_moves.end());
    for (const auto& line : output_moves) {
        cout << line << "\n";
    }

    return 0;
}