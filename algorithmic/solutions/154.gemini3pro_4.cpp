#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>
#include <set>
#include <queue>
#include <tuple>

using namespace std;

// Constants
const int H = 30;
const int W = 30;
const int TURN_LIMIT = 300;

// Directions: U, D, L, R
const int dr[4] = {-1, 1, 0, 0};
const int dc[4] = {0, 0, -1, 1};
const char MOVE_CHARS[4] = {'U', 'D', 'L', 'R'};
const char BLOCK_CHARS[4] = {'u', 'd', 'l', 'r'};

struct Pet {
    int r, c, type;
};

struct Human {
    int r, c;
};

int N, M;
vector<Pet> pets;
vector<Human> humans;
int grid_state[H][W]; // 0: empty, 1: wall

// Room definitions
// We divide into 5x5 rooms using specific wall rows and cols
const vector<int> WALL_ROWS = {5, 11, 17, 23};
const vector<int> WALL_COLS = {5, 11, 17, 23};

struct Room {
    int r_min, r_max, c_min, c_max;
    bool dirty;
};
vector<Room> rooms;
int room_grid[H][W]; // map cell to room index, -1 if wall

void init_rooms() {
    int r_start = 0;
    for (int i = 0; i < 5; ++i) {
        int r_end = (i < 4) ? WALL_ROWS[i] - 1 : H - 1;
        int c_start = 0;
        for (int j = 0; j < 5; ++j) {
            int c_end = (j < 4) ? WALL_COLS[j] - 1 : W - 1;
            Room room;
            room.r_min = r_start; room.r_max = r_end;
            room.c_min = c_start; room.c_max = c_end;
            room.dirty = false;
            rooms.push_back(room);
            c_start = c_end + 2;
        }
        r_start = r_end + 2;
    }
    
    for(int r=0; r<H; ++r) {
        for(int c=0; c<W; ++c) {
            room_grid[r][c] = -1;
        }
    }
    for(int i=0; i<rooms.size(); ++i) {
        for(int r=rooms[i].r_min; r<=rooms[i].r_max; ++r) {
            for(int c=rooms[i].c_min; c<=rooms[i].c_max; ++c) {
                room_grid[r][c] = i;
            }
        }
    }
}

bool is_valid(int r, int c) {
    return r >= 0 && r < H && c >= 0 && c < W;
}

bool is_passable(int r, int c) {
    return is_valid(r, c) && grid_state[r][c] == 0;
}

struct Gate {
    int r, c;
    int room1, room2;
};
vector<Gate> gates;

void init_gates() {
    // Horizontal walls gates
    for (int i = 0; i < 4; ++i) { 
        int wr = WALL_ROWS[i];
        for (int j = 0; j < 5; ++j) { 
            int c_start = (j==0) ? 0 : WALL_COLS[j-1]+1;
            int c_end = (j==4) ? W-1 : WALL_COLS[j]-1;
            int c_mid = (c_start + c_end) / 2;
            gates.push_back({wr, c_mid, i * 5 + j, (i + 1) * 5 + j});
        }
    }
    // Vertical walls gates
    for (int j = 0; j < 4; ++j) { 
        int wc = WALL_COLS[j];
        for (int i = 0; i < 5; ++i) { 
            int r_start = (i==0) ? 0 : WALL_ROWS[i-1]+1;
            int r_end = (i==4) ? H-1 : WALL_ROWS[i]-1;
            int r_mid = (r_start + r_end) / 2;
            gates.push_back({r_mid, wc, i * 5 + j, i * 5 + (j + 1)});
        }
    }
}

bool is_gate(int r, int c) {
    for (const auto& g : gates) {
        if (g.r == r && g.c == c) return true;
    }
    return false;
}

void update_room_status() {
    for (auto& room : rooms) room.dirty = false;
    for (const auto& pet : pets) {
        for(int i=0; i<rooms.size(); ++i) {
            if(pet.r >= rooms[i].r_min && pet.r <= rooms[i].r_max &&
               pet.c >= rooms[i].c_min && pet.c <= rooms[i].c_max) {
                rooms[i].dirty = true;
            }
        }
    }
}

bool can_block(int r, int c, const vector<Human>& current_humans) {
    if (!is_valid(r, c) || grid_state[r][c] == 1) return false;
    for (const auto& h : current_humans) {
        if (h.r == r && h.c == c) return false;
    }
    for (const auto& p : pets) {
        if (p.r == r && p.c == c) return false;
        if (abs(p.r - r) + abs(p.c - c) <= 1) return false;
    }
    return true;
}

int dist_map[H][W];
void bfs(int start_r, int start_c) {
    for(int i=0; i<H; ++i) fill(dist_map[i], dist_map[i]+W, 10000);
    queue<pair<int,int>> q;
    
    if (is_passable(start_r, start_c)) {
        dist_map[start_r][start_c] = 0;
        q.push({start_r, start_c});
    }
    
    while(!q.empty()){
        auto [r, c] = q.front(); q.pop();
        int d = dist_map[r][c];
        
        for(int k=0; k<4; ++k){
            int nr = r + dr[k];
            int nc = c + dc[k];
            if(is_passable(nr, nc) && dist_map[nr][nc] > d + 1){
                dist_map[nr][nc] = d + 1;
                q.push({nr, nc});
            }
        }
    }
}

struct Task {
    int r, c;
    int priority;
};

int main() {
    cin.tie(NULL);
    ios_base::sync_with_stdio(false);

    cin >> N;
    pets.resize(N);
    for (int i = 0; i < N; ++i) {
        cin >> pets[i].r >> pets[i].c >> pets[i].type;
        pets[i].r--; pets[i].c--;
    }
    cin >> M;
    humans.resize(M);
    for (int i = 0; i < M; ++i) {
        cin >> humans[i].r >> humans[i].c;
        humans[i].r--; humans[i].c--;
    }

    for (int i = 0; i < H; ++i) fill(grid_state[i], grid_state[i] + W, 0);
    init_rooms();
    init_gates();

    for (int turn = 0; turn < TURN_LIMIT; ++turn) {
        update_room_status();

        vector<Task> tasks;
        for (int r : WALL_ROWS) {
            for (int c = 0; c < W; ++c) {
                if (grid_state[r][c] == 0) {
                    if (!is_gate(r, c)) {
                         int r1 = (r>0) ? room_grid[r-1][c] : -1;
                         int r2 = (r<H-1) ? room_grid[r+1][c] : -1;
                         int prio = 10;
                         if ((r1!=-1 && rooms[r1].dirty) || (r2!=-1 && rooms[r2].dirty)) prio = 50;
                         tasks.push_back({r, c, prio});
                    }
                }
            }
        }
        for (int c : WALL_COLS) {
            for (int r = 0; r < H; ++r) {
                bool in_rows = false;
                for(int wr : WALL_ROWS) if(wr == r) in_rows = true;
                if(in_rows) continue; 

                if (grid_state[r][c] == 0) {
                    if (!is_gate(r, c)) {
                         int r1 = (c>0) ? room_grid[r][c-1] : -1;
                         int r2 = (c<W-1) ? room_grid[r][c+1] : -1;
                         int prio = 10;
                         if ((r1!=-1 && rooms[r1].dirty) || (r2!=-1 && rooms[r2].dirty)) prio = 50;
                         tasks.push_back({r, c, prio});
                    }
                }
            }
        }
        
        for (const auto& g : gates) {
            if (grid_state[g.r][g.c] == 0) {
                bool d1 = rooms[g.room1].dirty;
                bool d2 = rooms[g.room2].dirty;
                if ((d1 && !d2) || (!d1 && d2)) tasks.push_back({g.r, g.c, 200});
                else if (d1 && d2) tasks.push_back({g.r, g.c, 5});
            }
        }
        
        string actions = "";
        vector<bool> task_taken(tasks.size(), false);
        
        for (int i = 0; i < M; ++i) {
            Human& h = humans[i];
            int min_pet_dist = 1000;
            for(const auto& p : pets) {
                int d = abs(h.r - p.r) + abs(h.c - p.c);
                if(d < min_pet_dist) min_pet_dist = d;
            }
            
            bool panic = (min_pet_dist <= 2);
            int current_room_idx = room_grid[h.r][h.c];
            bool in_dirty = (current_room_idx != -1 && rooms[current_room_idx].dirty);
            
            char action = '.';
            
            if (panic) {
                int best_val = -1, best_dir = -1;
                for(int k=0; k<4; ++k){
                    int nr = h.r + dr[k];
                    int nc = h.c + dc[k];
                    if(is_passable(nr, nc)){
                        int min_d = 1000;
                        for(const auto& p : pets) min_d = min(min_d, abs(nr - p.r) + abs(nc - p.c));
                        if(min_d > best_val){
                            best_val = min_d;
                            best_dir = k;
                        }
                    }
                }
                if (min_pet_dist > best_val) best_dir = -1;
                if (best_dir != -1) action = MOVE_CHARS[best_dir];
            } else {
                bfs(h.r, h.c); 
                
                int best_task_idx = -1;
                double best_score = -1e9;
                
                for(int t=0; t<tasks.size(); ++t){
                    if(task_taken[t]) continue;
                    int d = dist_map[tasks[t].r][tasks[t].c];
                    if(d > 200) continue; 
                    double score = tasks[t].priority * 10.0 - d;
                    if(score > best_score){
                        best_score = score;
                        best_task_idx = t;
                    }
                }
                
                int target_clean_r = -1, target_clean_c = -1;
                if(in_dirty) {
                     queue<pair<int,int>> q;
                     vector<vector<int>> dclean(H, vector<int>(W, 1000));
                     dclean[h.r][h.c] = 0;
                     q.push({h.r, h.c});
                     bool found = false;
                     while(!q.empty()){
                         auto [r, c] = q.front(); q.pop();
                         int rid = room_grid[r][c];
                         if(rid != -1 && !rooms[rid].dirty) {
                             target_clean_r = r; target_clean_c = c;
                             found = true;
                             break;
                         }
                         if(dclean[r][c] >= 20) continue;
                         for(int k=0; k<4; ++k){
                             int nr = r + dr[k];
                             int nc = c + dc[k];
                             if(is_passable(nr, nc) && dclean[nr][nc] > dclean[r][c] + 1){
                                 dclean[nr][nc] = dclean[r][c] + 1;
                                 q.push({nr, nc});
                             }
                         }
                     }
                     if (found) {
                         double clean_score = 1500.0 - dclean[target_clean_r][target_clean_c] * 5.0;
                         if(clean_score > best_score) best_task_idx = -2;
                     }
                }
                
                if (best_task_idx == -1) {
                    action = '.';
                } else if (best_task_idx == -2) {
                    bfs(target_clean_r, target_clean_c);
                    int best_dir = -1, min_d = 1000;
                    for(int k=0; k<4; ++k){
                        int nr = h.r + dr[k];
                        int nc = h.c + dc[k];
                        if(is_passable(nr, nc) && dist_map[nr][nc] < min_d){
                            min_d = dist_map[nr][nc];
                            best_dir = k;
                        }
                    }
                    if(best_dir != -1) action = MOVE_CHARS[best_dir];
                } else {
                    Task& t = tasks[best_task_idx];
                    int d = dist_map[t.r][t.c];
                    
                    if (d == 1) {
                        if (can_block(t.r, t.c, humans)) {
                            for(int k=0; k<4; ++k){
                                if(h.r + dr[k] == t.r && h.c + dc[k] == t.c) {
                                    action = BLOCK_CHARS[k];
                                    task_taken[best_task_idx] = true;
                                    break;
                                }
                            }
                        } else action = '.'; 
                    } else if (d == 0) {
                        for(int k=0; k<4; ++k){
                            int nr = h.r + dr[k];
                            int nc = h.c + dc[k];
                            if(is_passable(nr, nc)) {
                                action = MOVE_CHARS[k];
                                break;
                            }
                        }
                    } else {
                        bfs(t.r, t.c);
                        int best_dir = -1, min_d = 1000;
                        for(int k=0; k<4; ++k){
                            int nr = h.r + dr[k];
                            int nc = h.c + dc[k];
                            if(is_passable(nr, nc) && dist_map[nr][nc] < min_d){
                                min_d = dist_map[nr][nc];
                                best_dir = k;
                            }
                        }
                        if(best_dir != -1) action = MOVE_CHARS[best_dir];
                        task_taken[best_task_idx] = true; 
                    }
                }
            }
            actions += action;
        }

        cout << actions << endl;
        
        for (int i = 0; i < N; ++i) {
            string move;
            cin >> move;
            for (char c : move) {
                if (c == 'U') pets[i].r--;
                else if (c == 'D') pets[i].r++;
                else if (c == 'L') pets[i].c--;
                else if (c == 'R') pets[i].c++;
            }
        }
        
        for(int i=0; i<M; ++i){
            char a = actions[i];
            int r = humans[i].r, c = humans[i].c;
            if(a == 'u') { if(can_block(r-1, c, humans)) grid_state[r-1][c] = 1; }
            else if(a == 'd') { if(can_block(r+1, c, humans)) grid_state[r+1][c] = 1; }
            else if(a == 'l') { if(can_block(r, c-1, humans)) grid_state[r][c-1] = 1; }
            else if(a == 'r') { if(can_block(r, c+1, humans)) grid_state[r][c+1] = 1; }
            else if(a == 'U') humans[i].r--;
            else if(a == 'D') humans[i].r++;
            else if(a == 'L') humans[i].c--;
            else if(a == 'R') humans[i].c++;
        }
    }
    return 0;
}