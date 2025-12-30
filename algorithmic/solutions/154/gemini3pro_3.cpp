#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <queue>
#include <set>
#include <algorithm>

using namespace std;

// Structure to represent coordinates
struct Point {
    int x, y;
    bool operator<(const Point& other) const {
        if (x != other.x) return x < other.x;
        return y < other.y;
    }
    bool operator==(const Point& other) const {
        return x == other.x && y == other.y;
    }
};

int N_pets;
struct Pet {
    int x, y, type;
};
vector<Pet> pets;

int M_humans;
struct Human {
    int x, y;
    int id;
};
vector<Human> humans;

// 1-based 30x30 grid state. 0: passable, 1: impassable
int grid_state[32][32];

// Check if coordinates are within bounds
bool is_valid(int x, int y) {
    return x >= 1 && x <= 30 && y >= 1 && y <= 30;
}

// Define target wall positions for partitioning (6x6 grid of cells)
bool is_wall_pos(int r, int c) {
    if (!is_valid(r, c)) return false;
    // Walls at multiples of 6 divide the 30x30 grid into 5x5 blocks of rooms
    if (r % 6 == 0) return true;
    if (c % 6 == 0) return true;
    return false;
}

// Identify which "room" a coordinate belongs to. Returns {-1, -1} if on a wall.
pair<int, int> get_room(int r, int c) {
    if (is_wall_pos(r, c)) return {-1, -1};
    return {(r - 1) / 6, (c - 1) / 6};
}

int dx[] = {-1, 1, 0, 0};
int dy[] = {0, 0, -1, 1};
char dir_chars[] = {'U', 'D', 'L', 'R'}; 
char block_chars[] = {'u', 'd', 'l', 'r'};

struct BFSResult {
    int dist;
    int first_move_dir; 
    Point target;
};

// BFS to find closest target
BFSResult bfs(Point start, const set<Point>& targets, const set<Point>& extra_obstacles) {
    if (targets.count(start)) return {0, -1, start};
    
    queue<pair<Point, int>> q;
    q.push({start, -1});
    
    // Using static array to avoid repeated allocation
    static int dist[32][32];
    for(int i=0;i<=30;++i) for(int j=0;j<=30;++j) dist[i][j] = 1e9;
    
    dist[start.x][start.y] = 0;
    
    while (!q.empty()) {
        auto [u, fdir] = q.front();
        q.pop();
        
        if (targets.count(u)) {
            return {dist[u.x][u.y], fdir, u};
        }
        
        for (int i = 0; i < 4; ++i) {
            int nx = u.x + dx[i];
            int ny = u.y + dy[i];
            
            if (is_valid(nx, ny) && grid_state[nx][ny] == 0 && !extra_obstacles.count({nx, ny})) {
                if (dist[nx][ny] > dist[u.x][u.y] + 1) {
                    dist[nx][ny] = dist[u.x][u.y] + 1;
                    int new_fdir = (fdir == -1) ? i : fdir;
                    q.push({{nx, ny}, new_fdir});
                }
            }
        }
    }
    return {-1, -1, {-1, -1}};
}

// Check safety rules for blocking a square
bool can_block(int r, int c, const vector<Pet>& current_pets, const vector<Human>& current_humans) {
    if (!is_valid(r, c)) return false;
    if (grid_state[r][c] != 0) return false;
    
    // Cannot choose square containing pets or humans
    for (const auto& p : current_pets) if (p.x == r && p.y == c) return false;
    for (const auto& h : current_humans) if (h.x == r && h.y == c) return false;
    
    // Cannot choose square adjacent to a pet
    for (const auto& p : current_pets) {
        if (abs(p.x - r) + abs(p.y - c) <= 1) return false;
    }
    return true;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> N_pets;
    pets.resize(N_pets);
    for (int i = 0; i < N_pets; ++i) cin >> pets[i].x >> pets[i].y >> pets[i].type;
    
    cin >> M_humans;
    humans.resize(M_humans);
    for (int i = 0; i < M_humans; ++i) {
        cin >> humans[i].x >> humans[i].y;
        humans[i].id = i;
    }
    
    // Init grid
    for(int i=1; i<=30; ++i)
        for(int j=1; j<=30; ++j)
            grid_state[i][j] = 0;

    for (int turn = 0; turn < 300; ++turn) {
        string actions(M_humans, '.');
        
        // Count pets in each 5x5 room
        int room_pets[5][5] = {0};
        for (const auto& p : pets) {
            pair<int, int> pr = get_room(p.x, p.y);
            if (pr.first != -1) {
                room_pets[pr.first][pr.second]++;
            }
        }
        
        set<Point> reserved_cells; 
        set<Point> blocked_this_turn; 
        
        vector<int> human_mode(M_humans); // 0: build, 1: flee
        vector<int> human_target_dir(M_humans, -1); 
        vector<Point> human_move_dest(M_humans, {-1, -1});

        // Determine mode for each human
        for (int i = 0; i < M_humans; ++i) {
            pair<int, int> pr = get_room(humans[i].x, humans[i].y);
            bool in_danger = false;
            // If inside a room with pets, flee
            if (pr.first != -1) {
                if (room_pets[pr.first][pr.second] > 0) in_danger = true;
            } else {
                // If on wall, check proximity
                for(const auto& p : pets) {
                     if(abs(p.x - humans[i].x) + abs(p.y - humans[i].y) <= 1) in_danger = true;
                }
            }
            human_mode[i] = in_danger ? 1 : 0;
        }

        // Logic for FLEE humans: move to safe area
        for (int i = 0; i < M_humans; ++i) {
            if (human_mode[i] == 1) {
                set<Point> safe_targets;
                for (int r=1; r<=30; ++r) {
                    for (int c=1; c<=30; ++c) {
                        if (grid_state[r][c]) continue;
                        pair<int, int> pr = get_room(r, c);
                        // Safe if on wall or in empty room
                        if (pr.first == -1 || room_pets[pr.first][pr.second] == 0) {
                            safe_targets.insert({r, c});
                        }
                    }
                }
                
                BFSResult res = bfs({humans[i].x, humans[i].y}, safe_targets, {});
                if (res.first_move_dir != -1) {
                    int nx = humans[i].x + dx[res.first_move_dir];
                    int ny = humans[i].y + dy[res.first_move_dir];
                    bool conflict = false;
                    for(int j=0; j<i; ++j) {
                        if (human_move_dest[j].x == nx && human_move_dest[j].y == ny) conflict = true;
                    }
                    if (!conflict) {
                        human_target_dir[i] = res.first_move_dir; 
                        human_move_dest[i] = {nx, ny};
                        reserved_cells.insert({nx, ny});
                    }
                }
            }
        }

        // Identify buildable walls
        vector<Point> wall_targets;
        for (int r=1; r<=30; ++r) {
            for (int c=1; c<=30; ++c) {
                if (is_wall_pos(r, c) && grid_state[r][c] == 0) {
                    if (can_block(r, c, pets, humans)) {
                        bool occupied = false;
                        for(const auto& h : humans) if(h.x == r && h.y == c) occupied = true;
                        if(occupied) continue;
                        if (reserved_cells.count({r, c})) continue;
                        wall_targets.push_back({r, c});
                    }
                }
            }
        }

        set<Point> taken_walls;
        
        // Logic for BUILD humans
        for (int i = 0; i < M_humans; ++i) {
            if (human_mode[i] == 0 && human_target_dir[i] == -1) {
                int best_dist = 1e9;
                Point best_wall = {-1, -1};
                
                // Check if can block adjacent wall immediately
                for (int d = 0; d < 4; ++d) {
                    int nx = humans[i].x + dx[d];
                    int ny = humans[i].y + dy[d];
                    bool is_target = false;
                    for (const auto& w : wall_targets) {
                        if (w.x == nx && w.y == ny && !taken_walls.count(w)) {
                            is_target = true;
                            break;
                        }
                    }
                    // Don't block a cell someone is moving to
                    if (is_target && reserved_cells.count({nx, ny})) is_target = false;

                    if (is_target) {
                        best_dist = 0;
                        best_wall = {nx, ny};
                        break;
                    }
                }

                if (best_dist == 0) {
                    for(int d=0; d<4; ++d) {
                        if(humans[i].x + dx[d] == best_wall.x && humans[i].y + dy[d] == best_wall.y) {
                            actions[i] = block_chars[d];
                            taken_walls.insert(best_wall);
                            blocked_this_turn.insert(best_wall);
                            break;
                        }
                    }
                } else {
                    // Move towards nearest wall target
                    set<Point> current_targets;
                    for(const auto& w : wall_targets) if(!taken_walls.count(w)) current_targets.insert(w);
                    
                    if (!current_targets.empty()) {
                         set<Point> obstacles;
                         for(auto p : reserved_cells) obstacles.insert(p);
                         for(auto p : blocked_this_turn) obstacles.insert(p);
                        
                        BFSResult res = bfs({humans[i].x, humans[i].y}, current_targets, obstacles);
                        if (res.first_move_dir != -1) {
                            Point target_wall = res.target;
                            taken_walls.insert(target_wall);
                            
                            int nx = humans[i].x + dx[res.first_move_dir];
                            int ny = humans[i].y + dy[res.first_move_dir];
                            
                            if (!blocked_this_turn.count({nx, ny})) {
                                actions[i] = dir_chars[res.first_move_dir];
                                reserved_cells.insert({nx, ny});
                            }
                        }
                    }
                }
            } else if (human_mode[i] == 1 && human_target_dir[i] != -1) {
                actions[i] = dir_chars[human_target_dir[i]];
            }
        }
        
        cout << actions << endl;
        
        // Read pet moves
        for(int k=0; k<N_pets; ++k) {
            string s;
            cin >> s;
            for(char c : s) {
                int d = -1;
                if(c == 'U') d = 0;
                else if(c == 'D') d = 1;
                else if(c == 'L') d = 2;
                else if(c == 'R') d = 3;
                
                if(d != -1) {
                    pets[k].x += dx[d];
                    pets[k].y += dy[d];
                }
            }
        }
        
        // Update local state based on our actions
        for(int i=0; i<M_humans; ++i) {
            char a = actions[i];
            if(a == 'U') humans[i].x--;
            else if(a == 'D') humans[i].x++;
            else if(a == 'L') humans[i].y--;
            else if(a == 'R') humans[i].y++;
            else if(a == 'u') grid_state[humans[i].x-1][humans[i].y] = 1;
            else if(a == 'd') grid_state[humans[i].x+1][humans[i].y] = 1;
            else if(a == 'l') grid_state[humans[i].x][humans[i].y-1] = 1;
            else if(a == 'r') grid_state[humans[i].x][humans[i].y+1] = 1;
        }
    }
    return 0;
}