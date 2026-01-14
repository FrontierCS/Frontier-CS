#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <map>
#include <unordered_map>
#include <algorithm>
#include <cstring>

using namespace std;

// --- Data Structures ---

struct Vehicle {
    int id;
    int len;
    bool horizontal; // true: Horizontal (Row fixed), false: Vertical (Col fixed)
    int fixed;       // Row index if H, Col index if V
};

struct Move {
    int vehicle_idx;
    int dir; // 0:L, 1:R, 2:U, 3:D
};

// --- Globals ---

int N_VEHICLES = 0;
vector<Vehicle> vehicles;
vector<int> initial_pos;

// State encoding:
// Pack variable coordinates of up to 10 vehicles into uint64_t (4 bits each).
typedef uint64_t State;

// BFS / Graph Data
unordered_map<State, int> state_to_id;
vector<State> id_to_state;
vector<vector<int>> adj;
vector<vector<Move>> adj_moves;

// Board for collision checks (6x6)
int board[6][6];

const char DIR_CHARS[] = {'L', 'R', 'U', 'D'};

// --- Helpers ---

State encode(const vector<int>& pos) {
    State s = 0;
    for(int i = 0; i < N_VEHICLES; ++i) {
        s |= ((uint64_t)pos[i] << (4 * i));
    }
    return s;
}

vector<int> decode(State s) {
    vector<int> pos(N_VEHICLES);
    for(int i = 0; i < N_VEHICLES; ++i) {
        pos[i] = (s >> (4 * i)) & 0xF;
    }
    return pos;
}

void fill_board(const vector<int>& pos) {
    for(int i=0; i<6; ++i) memset(board[i], 0, sizeof(board[i]));
    
    for(int i=0; i<N_VEHICLES; ++i) {
        int r, c;
        if(vehicles[i].horizontal) {
            r = vehicles[i].fixed;
            c = pos[i];
            for(int k=0; k<vehicles[i].len; ++k) board[r][c+k] = vehicles[i].id;
        } else {
            c = vehicles[i].fixed;
            r = pos[i];
            for(int k=0; k<vehicles[i].len; ++k) board[r+k][c] = vehicles[i].id;
        }
    }
}

// --- Main ---

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    // 1. Parse Input
    int grid[6][6];
    map<int, vector<pair<int,int>>> v_cells;
    
    for(int i=0; i<6; ++i) {
        for(int j=0; j<6; ++j) {
            cin >> grid[i][j];
            if(grid[i][j] > 0) {
                v_cells[grid[i][j]].push_back({i, j});
            }
        }
    }
    
    N_VEHICLES = v_cells.size();
    vehicles.resize(N_VEHICLES);
    initial_pos.resize(N_VEHICLES);
    
    // Map is sorted by ID. 
    // IDs are 1..N. Vehicle at index i has ID i+1.
    for(auto const& [id, cells] : v_cells) {
        int idx = id - 1;
        vehicles[idx].id = id;
        vehicles[idx].len = cells.size();
        
        // Determine orientation and coords
        bool horiz = true;
        if(cells.size() > 1) {
            if(cells[0].first != cells[1].first) horiz = false;
        }
        
        vehicles[idx].horizontal = horiz;
        if(horiz) {
            vehicles[idx].fixed = cells[0].first; // Row
            int min_c = 6;
            for(auto p : cells) min_c = min(min_c, p.second);
            initial_pos[idx] = min_c;
        } else {
            vehicles[idx].fixed = cells[0].second; // Col
            int min_r = 6;
            for(auto p : cells) min_r = min(min_r, p.first);
            initial_pos[idx] = min_r;
        }
    }
    
    // 2. BFS from Start to find all reachable states
    State start_s = encode(initial_pos);
    state_to_id[start_s] = 0;
    id_to_state.push_back(start_s);
    
    // Graph init
    adj.push_back({});
    adj_moves.push_back({});
    
    vector<int> parent;
    parent.push_back(-1);
    
    vector<Move> parent_move;
    parent_move.push_back({-1, -1});
    
    queue<int> q;
    q.push(0);
    
    while(!q.empty()) {
        int u = q.front();
        q.pop();
        
        vector<int> u_pos = decode(id_to_state[u]);
        fill_board(u_pos);
        
        for(int i=0; i<N_VEHICLES; ++i) {
            // Backward move (Left or Up) -> Decrease coord
            int curr = u_pos[i];
            if(curr > 0) {
                bool blocked = false;
                if(vehicles[i].horizontal) {
                    if(board[vehicles[i].fixed][curr - 1] != 0) blocked = true;
                } else {
                    if(board[curr - 1][vehicles[i].fixed] != 0) blocked = true;
                }
                
                if(!blocked) {
                    vector<int> next_pos = u_pos;
                    next_pos[i]--;
                    State next_s = encode(next_pos);
                    
                    int v;
                    if(state_to_id.find(next_s) == state_to_id.end()) {
                        v = state_to_id.size();
                        state_to_id[next_s] = v;
                        id_to_state.push_back(next_s);
                        adj.push_back({});
                        adj_moves.push_back({});
                        parent.push_back(u);
                        Move m = {i, vehicles[i].horizontal ? 0 : 2};
                        parent_move.push_back(m);
                        q.push(v);
                    } else {
                        v = state_to_id[next_s];
                    }
                    adj[u].push_back(v);
                    Move m = {i, vehicles[i].horizontal ? 0 : 2};
                    adj_moves[u].push_back(m);
                }
            }
            
            // Forward move (Right or Down) -> Increase coord
            int tail = curr + vehicles[i].len;
            if(tail < 6) {
                bool blocked = false;
                if(vehicles[i].horizontal) {
                    if(board[vehicles[i].fixed][tail] != 0) blocked = true;
                } else {
                    if(board[tail][vehicles[i].fixed] != 0) blocked = true;
                }
                
                if(!blocked) {
                    vector<int> next_pos = u_pos;
                    next_pos[i]++;
                    State next_s = encode(next_pos);
                    
                    int v;
                    if(state_to_id.find(next_s) == state_to_id.end()) {
                        v = state_to_id.size();
                        state_to_id[next_s] = v;
                        id_to_state.push_back(next_s);
                        adj.push_back({});
                        adj_moves.push_back({});
                        parent.push_back(u);
                        Move m = {i, vehicles[i].horizontal ? 1 : 3};
                        parent_move.push_back(m);
                        q.push(v);
                    } else {
                        v = state_to_id[next_s];
                    }
                    adj[u].push_back(v);
                    Move m = {i, vehicles[i].horizontal ? 1 : 3};
                    adj_moves[u].push_back(m);
                }
            }
        }
    }
    
    // 3. BFS Backward from Goal
    // Goal: Red Car (ID 1, index 0) exits.
    // Red car len=2. Rightmost valid board position is 4 (occupies 4,5).
    // From Pos 4, move Right -> Pos 5 (partly out), move Right -> Pos 6 (fully out).
    // Total 2 steps from Pos 4.
    
    int num_states = id_to_state.size();
    vector<int> dist_goal(num_states, -1);
    queue<int> q_goal;
    
    for(int i=0; i<num_states; ++i) {
        vector<int> pos = decode(id_to_state[i]);
        if(pos[0] == 4) {
            dist_goal[i] = 2; 
            q_goal.push(i);
        }
    }
    
    while(!q_goal.empty()) {
        int u = q_goal.front();
        q_goal.pop();
        
        // Graph is symmetric
        for(int v : adj[u]) {
            if(dist_goal[v] == -1) {
                dist_goal[v] = dist_goal[u] + 1;
                q_goal.push(v);
            }
        }
    }
    
    // 4. Find state with Max Distance
    int max_d = -1;
    int target = 0;
    
    for(int i=0; i<num_states; ++i) {
        if(dist_goal[i] != -1) {
            if(dist_goal[i] > max_d) {
                max_d = dist_goal[i];
                target = i;
            }
        }
    }
    
    // 5. Output
    vector<Move> path;
    int curr = target;
    while(curr != 0) {
        path.push_back(parent_move[curr]);
        curr = parent[curr];
    }
    reverse(path.begin(), path.end());
    
    cout << max_d << " " << path.size() << "\n";
    for(const auto& m : path) {
        cout << vehicles[m.vehicle_idx].id << " " << DIR_CHARS[m.dir] << "\n";
    }

    return 0;
}