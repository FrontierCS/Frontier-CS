#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <set>
#include <algorithm>
#include <cmath>
#include <map>

using namespace std;

const int SIZE = 30;
int N; // Pets
struct Pet {
    int x, y, type;
};
vector<Pet> pets;
int M; // Humans
struct Human {
    int x, y;
};
vector<Human> humans;

// Map representation
// 1-based coordinates
// map[x][y]: 0 = empty, 1 = wall
int grid[35][35];

// Target structure
bool is_structure[35][35];
bool is_door[35][35];

// Directions
int dx[] = {-1, 1, 0, 0};
int dy[] = {0, 0, -1, 1};
char move_chars[] = {'U', 'D', 'L', 'R'};
char build_chars[] = {'u', 'd', 'l', 'r'};

// Helper to check bounds
bool valid(int x, int y) {
    return x >= 1 && x <= SIZE && y >= 1 && y <= SIZE;
}

// Distance
int dist(int r1, int c1, int r2, int c2) {
    return abs(r1 - r2) + abs(c1 - c2);
}

// Room identification
// Grid lines at 5, 10, 15, 20, 25
// Rooms are indexed 0..5 in both dimensions.
int get_room_id(int x, int y) {
    if (!valid(x, y)) return -1;
    int r = (x - 1) / 5;
    int c = (y - 1) / 5;
    if (r > 5) r = 5;
    if (c > 5) c = 5;
    return r * 6 + c;
}

// Check if a square can be blocked
bool can_block(int x, int y, const vector<Pet>& current_pets, const vector<Human>& current_humans) {
    if (!valid(x, y)) return false;
    if (grid[x][y] == 1) return false; // Already blocked
    
    // Check if contains pet or human
    for (const auto& p : current_pets) if (p.x == x && p.y == y) return false;
    for (const auto& h : current_humans) if (h.x == x && h.y == y) return false;
    
    // Check neighbors for pets
    // Rule: "You cannot choose a square whose adjacent square contains a pet."
    for (const auto& p : current_pets) {
        if (dist(x, y, p.x, p.y) <= 1) return false;
    }
    return true;
}

// BFS for pathfinding
// Returns next move direction (0-3) or -1 if no path or already there
int get_move_to_target(int sx, int sy, int tx, int ty, bool avoid_pets_strict) {
    if (sx == tx && sy == ty) return -1;
    
    queue<pair<int, int>> q;
    q.push({sx, sy});
    
    static int d[35][35];
    for(int i=0; i<35; ++i) for(int j=0; j<35; ++j) d[i][j] = -1;
    d[sx][sy] = 0;
    
    static pair<int, int> parent[35][35];
    
    bool found = false;
    
    while(!q.empty()){
        auto [cx, cy] = q.front();
        q.pop();
        
        if (cx == tx && cy == ty) {
            found = true;
            break;
        }
        
        for(int i=0; i<4; ++i){
            int nx = cx + dx[i];
            int ny = cy + dy[i];
            
            if (!valid(nx, ny)) continue;
            if (grid[nx][ny] == 1) continue; // Wall
            if (d[nx][ny] != -1) continue;
            
            // Avoid pets?
            bool unsafe = false;
            // Check current pet positions to avoid walking into them
            for(const auto& p : pets) if(p.x == nx && p.y == ny) unsafe = true;
            
            if (unsafe) continue;
            
            d[nx][ny] = d[cx][cy] + 1;
            parent[nx][ny] = {cx, cy};
            q.push({nx, ny});
        }
    }
    
    if (!found) return -1;
    
    // Backtrack
    int cur_x = tx;
    int cur_y = ty;
    while(true){
        pair<int, int> p = parent[cur_x][cur_y];
        if (p.x == sx && p.y == sy) {
            for(int i=0; i<4; ++i){
                if (sx + dx[i] == cur_x && sy + dy[i] == cur_y) return i;
            }
        }
        cur_x = p.x;
        cur_y = p.y;
    }
    return -1;
}

// Find a standing spot adjacent to target wall (wx, wy)
pair<int, int> get_build_spot(int h_idx, int wx, int wy) {
    int best_dist = 1e9;
    pair<int, int> best_spot = {-1, -1};
    int hx = humans[h_idx].x;
    int hy = humans[h_idx].y;

    for(int i=0; i<4; ++i){
        int nx = wx + dx[i];
        int ny = wy + dy[i];
        if (!valid(nx, ny)) continue;
        if (grid[nx][ny] == 1) continue;
        
        bool occupied = false;
        for(const auto& p : pets) if (p.x == nx && p.y == ny) occupied = true;
        if (occupied) continue;
        
        int d = dist(hx, hy, nx, ny);
        if (d < best_dist) {
            best_dist = d;
            best_spot = {nx, ny};
        }
    }
    return best_spot;
}

// State variables
struct Task {
    int type; // 0: Skeleton, 1: Close Door
    int tx, ty; // Target wall coordinates
};
vector<Task> assignments(20); 

void init() {
    vector<int> lines = {5, 10, 15, 20, 25};
    for(int x : lines) {
        for(int y = 1; y <= SIZE; ++y) is_structure[x][y] = true;
    }
    for(int y : lines) {
        for(int x = 1; x <= SIZE; ++x) is_structure[x][y] = true;
    }
    
    vector<int> door_indices = {3, 8, 13, 18, 23, 28};
    for(int x : lines) {
        for(int y : door_indices) is_door[x][y] = true;
    }
    for(int y : lines) {
        for(int x : door_indices) is_door[x][y] = true;
    }
    
    for(int i=0; i<20; ++i) assignments[i] = { -1, -1, -1 };
}

int main() {
    cin >> N;
    pets.resize(N);
    for(int i=0; i<N; ++i) cin >> pets[i].x >> pets[i].y >> pets[i].type;
    cin >> M;
    humans.resize(M);
    for(int i=0; i<M; ++i) cin >> humans[i].x >> humans[i].y;
    
    init();
    
    for(int turn = 0; turn < 300; ++turn) {
        vector<pair<int, int>> skeleton_tasks;
        for(int i=1; i<=SIZE; ++i){
            for(int j=1; j<=SIZE; ++j){
                if (is_structure[i][j] && !is_door[i][j] && grid[i][j] == 0) {
                    skeleton_tasks.push_back({i, j});
                }
            }
        }
        
        vector<int> room_pets(36, 0);
        vector<int> room_humans(36, 0);
        for(const auto& p : pets) {
            int r = get_room_id(p.x, p.y);
            if(r != -1) room_pets[r]++;
        }
        for(const auto& h : humans) {
            int r = get_room_id(h.x, h.y);
            if(r != -1) room_humans[r]++;
        }
        
        vector<pair<int, int>> door_tasks;
        for(int i=1; i<=SIZE; ++i){
            for(int j=1; j<=SIZE; ++j){
                if (is_structure[i][j] && is_door[i][j] && grid[i][j] == 0) {
                    int r1 = -1, r2 = -1;
                    if (is_structure[i][j] && (i % 5 == 0)) {
                        r1 = get_room_id(i-1, j);
                        r2 = get_room_id(i+1, j);
                    } else {
                        r1 = get_room_id(i, j-1);
                        r2 = get_room_id(i, j+1);
                    }
                    
                    if (r1 != -1 && r2 != -1) {
                        bool safe = true;
                        if (room_pets[r1] > 0 && room_humans[r1] > 0) safe = false;
                        if (room_pets[r2] > 0 && room_humans[r2] > 0) safe = false;
                        
                        if (safe) {
                             if ((room_pets[r1] > 0 && room_pets[r2] == 0) || 
                                 (room_pets[r2] > 0 && room_pets[r1] == 0) ||
                                 (room_pets[r1] > 0 && room_pets[r2] > 0)) {
                                 door_tasks.push_back({i, j});
                             }
                        }
                    }
                }
            }
        }
        
        vector<bool> human_busy(M, false);
        vector<bool> wall_targeted(35*35, false);
        
        for(int i=0; i<M; ++i) {
            if (assignments[i].type != -1) {
                int tx = assignments[i].tx;
                int ty = assignments[i].ty;
                if (grid[tx][ty] == 1) {
                    assignments[i] = {-1, -1, -1};
                } else {
                    wall_targeted[tx * 32 + ty] = true;
                    human_busy[i] = true;
                }
            }
        }
        
        for(int i=0; i<M; ++i) {
            if (human_busy[i]) continue;
            
            int best_dist = 1e9;
            int best_idx = -1;
            int task_type = -1; 
            
            for(int k=0; k<skeleton_tasks.size(); ++k) {
                auto [tx, ty] = skeleton_tasks[k];
                if (wall_targeted[tx * 32 + ty]) continue;
                
                int d = dist(humans[i].x, humans[i].y, tx, ty);
                if (d < best_dist) {
                    best_dist = d;
                    best_idx = k;
                    task_type = 0;
                }
            }
            
            if (best_idx == -1) {
                for(int k=0; k<door_tasks.size(); ++k) {
                    auto [tx, ty] = door_tasks[k];
                    if (wall_targeted[tx * 32 + ty]) continue;
                    
                    int d = dist(humans[i].x, humans[i].y, tx, ty);
                    if (d < best_dist) {
                        best_dist = d;
                        best_idx = k;
                        task_type = 1;
                    }
                }
            }
            
            if (best_idx != -1) {
                pair<int, int> t;
                if (task_type == 0) t = skeleton_tasks[best_idx];
                else t = door_tasks[best_idx];
                
                assignments[i] = {task_type, t.first, t.second};
                wall_targeted[t.first * 32 + t.second] = true;
                human_busy[i] = true;
            }
        }
        
        string action_str = "";
        for(int i=0; i<M; ++i) {
            char action = '.';
            bool panic = false;
            for(const auto& p : pets) {
                if (dist(humans[i].x, humans[i].y, p.x, p.y) <= 1) panic = true;
            }
            
            if (panic) {
                int best_d = -1;
                int best_dir = -1;
                for(int d=0; d<4; ++d) {
                    int nx = humans[i].x + dx[d];
                    int ny = humans[i].y + dy[d];
                    if (!valid(nx, ny) || grid[nx][ny] == 1) continue;
                    
                    int min_p_dist = 100;
                    for(const auto& p : pets) min_p_dist = min(min_p_dist, dist(nx, ny, p.x, p.y));
                    
                    if (min_p_dist > best_d) {
                        best_d = min_p_dist;
                        best_dir = d;
                    }
                }
                if (best_dir != -1) action = move_chars[best_dir];
            } 
            else if (assignments[i].type != -1) {
                int tx = assignments[i].tx;
                int ty = assignments[i].ty;
                
                int d = dist(humans[i].x, humans[i].y, tx, ty);
                if (d == 1) {
                    if (can_block(tx, ty, pets, humans)) {
                        for(int k=0; k<4; ++k) {
                            if (humans[i].x + dx[k] == tx && humans[i].y + dy[k] == ty) {
                                action = build_chars[k];
                            }
                        }
                    } 
                } else {
                    pair<int, int> spot = get_build_spot(i, tx, ty);
                    if (spot.first != -1) {
                        int dir = get_move_to_target(humans[i].x, humans[i].y, spot.first, spot.second, true);
                        if (dir != -1) action = move_chars[dir];
                        else assignments[i] = {-1, -1, -1};
                    } else {
                        assignments[i] = {-1, -1, -1};
                    }
                }
            }
            action_str += action;
        }
        
        cout << action_str << endl;
        
        string dummy_pet_moves; 
        for(int i=0; i<N; ++i) {
            string s;
            cin >> s;
            for(char c : s) {
                int dir = -1;
                if (c == 'U') dir = 0; else if (c == 'D') dir = 1; else if (c == 'L') dir = 2; else if (c == 'R') dir = 3;
                if (dir != -1) {
                    pets[i].x += dx[dir];
                    pets[i].y += dy[dir];
                }
            }
        }
        
        for(int i=0; i<M; ++i) {
            char c = action_str[i];
            if (c == '.') continue;
            if (c >= 'A' && c <= 'Z') {
                int dir = -1;
                if (c == 'U') dir = 0; else if (c == 'D') dir = 1; else if (c == 'L') dir = 2; else if (c == 'R') dir = 3;
                int nx = humans[i].x + dx[dir];
                int ny = humans[i].y + dy[dir];
                bool blocked = false;
                for(int j=0; j<M; ++j) {
                    char c2 = action_str[j];
                    if (c2 >= 'a' && c2 <= 'z') {
                        int d2 = -1;
                        if (c2 == 'u') d2 = 0; else if (c2 == 'd') d2 = 1; else if (c2 == 'l') d2 = 2; else if (c2 == 'r') d2 = 3;
                        int wx = humans[j].x + dx[d2];
                        int wy = humans[j].y + dy[d2];
                        if (wx == nx && wy == ny) blocked = true;
                    }
                }
                if (!blocked) {
                    humans[i].x = nx;
                    humans[i].y = ny;
                }
            }
            else if (c >= 'a' && c <= 'z') {
                int dir = -1;
                if (c == 'u') dir = 0; else if (c == 'd') dir = 1; else if (c == 'l') dir = 2; else if (c == 'r') dir = 3;
                int wx = humans[i].x + dx[dir];
                int wy = humans[i].y + dy[dir];
                grid[wx][wy] = 1;
            }
        }
    }
    
    return 0;
}