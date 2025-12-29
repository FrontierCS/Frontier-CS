#include <iostream>
#include <vector>
#include <queue>
#include <map>
#include <algorithm>
#include <string>

using namespace std;

// Vehicle structure
struct Vehicle {
    int id; // Original ID
    int type; // 0: Horizontal, 1: Vertical
    int length;
    int fixed; // Row for Horz, Col for Vert
};

int N;
vector<Vehicle> vehicles;
const int DIM = 6;

// Helper to reconstruct board from state
void fill_board(int state, vector<vector<int>>& board) {
    for(int i=0; i<DIM; ++i) fill(board[i].begin(), board[i].end(), 0);
    
    for(int i=0; i<N; ++i) {
        int pos = (state >> (3*i)) & 7;
        int len = vehicles[i].length;
        int r, c;
        if(vehicles[i].type == 0) { // Horz
            r = vehicles[i].fixed;
            c = pos;
            for(int k=0; k<len; ++k) {
                if(c+k < DIM) board[r][c+k] = vehicles[i].id;
            }
        } else { // Vert
            c = vehicles[i].fixed;
            r = pos;
            for(int k=0; k<len; ++k) {
                if(r+k < DIM) board[r+k][c] = vehicles[i].id;
            }
        }
    }
}

// Apply move: returns new state or -1 if invalid
int apply_move(int state, int v_idx, int dir, const vector<vector<int>>& current_board) {
    int pos = (state >> (3*v_idx)) & 7;
    int new_pos = (dir == 1) ? pos + 1 : pos - 1;
    
    if(new_pos < 0) return -1;
    int len = vehicles[v_idx].length;
    if(new_pos + len > DIM) return -1;
    
    int target_r, target_c;
    if(vehicles[v_idx].type == 0) { // Horz
        int r = vehicles[v_idx].fixed;
        if(dir == 1) { // Right: check cell at new_pos + len - 1
            target_r = r;
            target_c = new_pos + len - 1;
        } else { // Left: check cell at new_pos
            target_r = r;
            target_c = new_pos;
        }
    } else { // Vert
        int c = vehicles[v_idx].fixed;
        if(dir == 1) { // Down: check cell at new_pos + len - 1
            target_c = c;
            target_r = new_pos + len - 1;
        } else { // Up: check cell at new_pos
            target_c = c;
            target_r = new_pos;
        }
    }
    
    if(target_r < 0 || target_r >= DIM || target_c < 0 || target_c >= DIM) return -1;
    if(current_board[target_r][target_c] != 0) return -1;
    
    int mask = ~(7 << (3*v_idx));
    return (state & mask) | (new_pos << (3*v_idx));
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    vector<vector<int>> input_board(DIM, vector<int>(DIM));
    for(int i=0; i<DIM; ++i) {
        for(int j=0; j<DIM; ++j) {
            cin >> input_board[i][j];
        }
    }
    
    map<int, Vehicle> temp_vehicles;
    vector<bool> visited_ids(11, false);
    int max_id = 0;
    
    for(int i=0; i<DIM; ++i) {
        for(int j=0; j<DIM; ++j) {
            int id = input_board[i][j];
            if(id > 0 && !visited_ids[id]) {
                visited_ids[id] = true;
                max_id = max(max_id, id);
                Vehicle v;
                v.id = id;
                bool horz = false;
                if(j+1 < DIM && input_board[i][j+1] == id) horz = true;
                
                if(horz) {
                    v.type = 0;
                    v.fixed = i;
                    int k = 0;
                    while(j+k < DIM && input_board[i][j+k] == id) k++;
                    v.length = k;
                } else {
                    v.type = 1; 
                    v.fixed = j;
                    int k = 0;
                    while(i+k < DIM && input_board[i+k][j] == id) k++;
                    v.length = k;
                }
                temp_vehicles[id] = v;
            }
        }
    }
    
    N = max_id;
    vehicles.resize(N);
    int initial_state = 0;
    
    for(int id=1; id<=N; ++id) {
        vehicles[id-1] = temp_vehicles[id];
        int pos = -1;
        if(vehicles[id-1].type == 0) {
            int r = vehicles[id-1].fixed;
            for(int c=0; c<DIM; ++c) if(input_board[r][c] == id) { pos = c; break; }
        } else {
             int c = vehicles[id-1].fixed;
             for(int r=0; r<DIM; ++r) if(input_board[r][c] == id) { pos = r; break; }
        }
        initial_state |= (pos << (3*(id-1)));
    }
    
    // BFS 1: Explore State Space
    queue<int> q;
    q.push(initial_state);
    
    map<int, int> dist_start;
    map<int, pair<int, int>> parent;
    dist_start[initial_state] = 0;
    parent[initial_state] = {-1, -1};
    
    vector<int> all_reachable;
    vector<vector<int>> board(DIM, vector<int>(DIM));
    
    while(!q.empty()) {
        int u = q.front();
        q.pop();
        all_reachable.push_back(u);
        
        fill_board(u, board);
        
        for(int i=0; i<N; ++i) {
            // Try neg (Left/Up)
            int next_u = apply_move(u, i, 0, board);
            if(next_u != -1 && dist_start.find(next_u) == dist_start.end()) {
                dist_start[next_u] = dist_start[u] + 1;
                parent[next_u] = {u, (i << 1) | 0};
                q.push(next_u);
            }
            // Try pos (Right/Down)
            next_u = apply_move(u, i, 1, board);
            if(next_u != -1 && dist_start.find(next_u) == dist_start.end()) {
                dist_start[next_u] = dist_start[u] + 1;
                parent[next_u] = {u, (i << 1) | 1};
                q.push(next_u);
            }
        }
    }
    
    // BFS 2: Distance to Solved
    queue<int> bq;
    map<int, int> dist_goal;
    
    for(int s : all_reachable) {
        int car1_pos = (s & 7); 
        // Car 1 at col 4 (occupying 4,5) needs 2 steps to exit (5, 6)
        if(car1_pos == 4) {
            dist_goal[s] = 2; 
            bq.push(s);
        }
    }
    
    while(!bq.empty()) {
        int u = bq.front();
        bq.pop();
        int d = dist_goal[u];
        fill_board(u, board);
        
        for(int i=0; i<N; ++i) {
            for(int dir=0; dir<=1; ++dir) {
                int v = apply_move(u, i, dir, board);
                if(v != -1 && dist_start.count(v)) {
                    if(dist_goal.find(v) == dist_goal.end()) {
                        dist_goal[v] = d + 1;
                        bq.push(v);
                    }
                }
            }
        }
    }
    
    int max_steps = -1;
    int best_state = initial_state;
    
    for(int s : all_reachable) {
        if(dist_goal.find(s) != dist_goal.end()) {
            int d = dist_goal[s];
            if(d > max_steps) {
                max_steps = d;
                best_state = s;
            }
        }
    }
    
    vector<string> moves;
    int curr = best_state;
    while(curr != initial_state) {
        pair<int, int> p = parent[curr];
        int prev = p.first;
        int move_enc = p.second;
        int v_idx = move_enc >> 1;
        int dir = move_enc & 1;
        
        int vid = vehicles[v_idx].id;
        char d_char;
        if(vehicles[v_idx].type == 0) d_char = (dir == 1) ? 'R' : 'L';
        else d_char = (dir == 1) ? 'D' : 'U';
        
        moves.push_back(to_string(vid) + " " + d_char);
        curr = prev;
    }
    reverse(moves.begin(), moves.end());
    
    cout << max_steps << " " << moves.size() << "\n";
    for(const string& m : moves) {
        cout << m << "\n";
    }
    
    return 0;
}