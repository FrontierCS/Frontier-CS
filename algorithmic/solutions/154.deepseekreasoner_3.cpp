#include <iostream>
#include <vector>
#include <queue>
#include <set>
#include <tuple>
#include <algorithm>
#include <cstring>
#include <cmath>

using namespace std;

const int GRID_SIZE = 30;
const int MAX_TURNS = 300;
const int dx[4] = {-1, 1, 0, 0};
const int dy[4] = {0, 0, -1, 1};
const char move_char[4] = {'U', 'D', 'L', 'R'};
const char wall_char[4] = {'u', 'd', 'l', 'r'};
const int GAP_SIZE = 3;

struct Pet {
    int x, y, type;
};

struct Human {
    int x, y;
    int target_wall_id;   // index in walls vector
    int failed_attempts;
};

struct Wall {
    int wx, wy;           // wall square coordinates
    int sx, sy;           // stand position (inside the rectangle)
    bool built;
};

int N, M;
vector<Pet> pets;
vector<Human> humans;
vector<Wall> walls;                     // all walls
vector<int> walls_to_build_now;         // indices of walls to build initially
vector<int> walls_to_build_later;       // indices of entrance gap walls
bool is_wall[GRID_SIZE+2][GRID_SIZE+2]; // 1-indexed, true if impassable
int t_rect, b_rect, l_rect, r_rect;     // rectangle boundaries

// ------------------------------------------------------------
// Helper functions
// ------------------------------------------------------------
inline bool is_inside(int x, int y) {
    return x >= t_rect && x <= b_rect && y >= l_rect && y <= r_rect;
}

inline bool is_passable(int x, int y) {
    if (x < 1 || x > GRID_SIZE || y < 1 || y > GRID_SIZE) return false;
    return !is_wall[x][y];
}

char get_move_char(int x, int y, int nx, int ny) {
    if (nx == x-1) return 'U';
    if (nx == x+1) return 'D';
    if (ny == y-1) return 'L';
    if (ny == y+1) return 'R';
    return '.';
}

char get_wall_char(int hx, int hy, int wx, int wy) {
    if (wx == hx-1 && wy == hy) return 'u';
    if (wx == hx+1 && wy == hy) return 'd';
    if (wx == hx && wy == hy-1) return 'l';
    if (wx == hx && wy == hy+1) return 'r';
    return '.';
}

// BFS to find next step towards any square inside the rectangle
bool bfs_to_inside(int sx, int sy, int& nx, int& ny) {
    vector<vector<pair<int,int>>> parent(GRID_SIZE+2, vector<pair<int,int>>(GRID_SIZE+2, {-1,-1}));
    queue<pair<int,int>> q;
    q.push({sx, sy});
    parent[sx][sy] = {sx, sy};
    while (!q.empty()) {
        auto [x, y] = q.front(); q.pop();
        if (is_inside(x, y)) {
            // backtrack to the first step from (sx,sy)
            while (parent[x][y] != make_pair(sx, sy)) {
                int px = parent[x][y].first;
                int py = parent[x][y].second;
                if (parent[px][py] == make_pair(sx, sy)) {
                    nx = px; ny = py;
                    return true;
                }
                x = px; y = py;
            }
            // should not happen if (sx,sy) is not inside
            return false;
        }
        for (int d = 0; d < 4; ++d) {
            int nx2 = x + dx[d], ny2 = y + dy[d];
            if (nx2 >= 1 && nx2 <= GRID_SIZE && ny2 >= 1 && ny2 <= GRID_SIZE &&
                is_passable(nx2, ny2) && parent[nx2][ny2].first == -1) {
                parent[nx2][ny2] = {x, y};
                q.push({nx2, ny2});
            }
        }
    }
    return false;
}

// BFS to find next step towards a specific target square
bool bfs_to_target(int sx, int sy, int tx, int ty, int& nx, int& ny) {
    if (sx == tx && sy == ty) {
        nx = sx; ny = sy;
        return true;
    }
    vector<vector<pair<int,int>>> parent(GRID_SIZE+2, vector<pair<int,int>>(GRID_SIZE+2, {-1,-1}));
    queue<pair<int,int>> q;
    q.push({sx, sy});
    parent[sx][sy] = {sx, sy};
    while (!q.empty()) {
        auto [x, y] = q.front(); q.pop();
        if (x == tx && y == ty) {
            while (parent[x][y] != make_pair(sx, sy)) {
                int px = parent[x][y].first;
                int py = parent[x][y].second;
                if (parent[px][py] == make_pair(sx, sy)) {
                    nx = px; ny = py;
                    return true;
                }
                x = px; y = py;
            }
            return true;
        }
        for (int d = 0; d < 4; ++d) {
            int nx2 = x + dx[d], ny2 = y + dy[d];
            if (nx2 >= 1 && nx2 <= GRID_SIZE && ny2 >= 1 && ny2 <= GRID_SIZE &&
                is_passable(nx2, ny2) && parent[nx2][ny2].first == -1) {
                parent[nx2][ny2] = {x, y};
                q.push({nx2, ny2});
            }
        }
    }
    return false;
}

// ------------------------------------------------------------
// Initialization: choose rectangle and create wall list
// ------------------------------------------------------------
void choose_rectangle() {
    // Try to find a rectangle with no pets
    vector<tuple<int,int,int,int>> candidates; // (t,b,l,r)
    for (int t = 1; t <= GRID_SIZE; ++t) {
        for (int b = t; b <= GRID_SIZE; ++b) {
            for (int l = 1; l <= GRID_SIZE; ++l) {
                for (int r = l; r <= GRID_SIZE; ++r) {
                    bool ok = true;
                    for (const Pet& pet : pets) {
                        if (pet.x >= t && pet.x <= b && pet.y >= l && pet.y <= r) {
                            ok = false;
                            break;
                        }
                    }
                    if (ok) candidates.emplace_back(t, b, l, r);
                }
            }
        }
    }

    if (candidates.empty()) {
        // If no empty rectangle, choose the one with fewest pets
        int min_pets = 1000, best_area = 0;
        for (int t = 1; t <= GRID_SIZE; ++t) {
            for (int b = t; b <= GRID_SIZE; ++b) {
                for (int l = 1; l <= GRID_SIZE; ++l) {
                    for (int r = l; r <= GRID_SIZE; ++r) {
                        int cnt = 0;
                        for (const Pet& pet : pets) {
                            if (pet.x >= t && pet.x <= b && pet.y >= l && pet.y <= r) ++cnt;
                        }
                        int area = (b-t+1)*(r-l+1);
                        if (cnt < min_pets || (cnt == min_pets && area > best_area)) {
                            min_pets = cnt;
                            best_area = area;
                            t_rect = t; b_rect = b; l_rect = l; r_rect = r;
                        }
                    }
                }
            }
        }
    } else {
        // Choose rectangle with highest score: area * 100 - walls_needed
        int best_score = -1;
        for (auto [t,b,l,r] : candidates) {
            int area = (b-t+1)*(r-l+1);
            int walls_needed = 0;
            if (t > 1) walls_needed += (r-l+1);
            if (b < GRID_SIZE) walls_needed += (r-l+1);
            if (l > 1) walls_needed += (b-t+1);
            if (r < GRID_SIZE) walls_needed += (b-t+1);
            int score = area * 100 - walls_needed;
            if (score > best_score) {
                best_score = score;
                t_rect = t; b_rect = b; l_rect = l; r_rect = r;
            }
        }
    }
}

void create_walls() {
    walls.clear();
    // top side
    if (t_rect > 1) {
        for (int y = l_rect; y <= r_rect; ++y) {
            walls.push_back({t_rect-1, y, t_rect, y, false});
        }
    }
    // bottom side
    if (b_rect < GRID_SIZE) {
        for (int y = l_rect; y <= r_rect; ++y) {
            walls.push_back({b_rect+1, y, b_rect, y, false});
        }
    }
    // left side
    if (l_rect > 1) {
        for (int x = t_rect; x <= b_rect; ++x) {
            walls.push_back({x, l_rect-1, x, l_rect, false});
        }
    }
    // right side
    if (r_rect < GRID_SIZE) {
        for (int x = t_rect; x <= b_rect; ++x) {
            walls.push_back({x, r_rect+1, x, r_rect, false});
        }
    }

    // Choose entrance gap on one side (prefer bottom, then right, top, left)
    int entrance_side = -1;
    if (b_rect < GRID_SIZE) entrance_side = 0;        // bottom
    else if (r_rect < GRID_SIZE) entrance_side = 1;   // right
    else if (t_rect > 1) entrance_side = 2;           // top
    else if (l_rect > 1) entrance_side = 3;           // left

    walls_to_build_now.clear();
    walls_to_build_later.clear();
    for (size_t i = 0; i < walls.size(); ++i) {
        Wall& w = walls[i];
        bool is_gap = false;
        if (entrance_side == 0 && w.wx == b_rect+1) { // bottom
            int idx = w.wy - l_rect; // column index from left
            int len = r_rect - l_rect + 1;
            if (idx >= len - GAP_SIZE && idx < len) is_gap = true;
        } else if (entrance_side == 1 && w.wy == r_rect+1) { // right
            int idx = w.wx - t_rect;
            int len = b_rect - t_rect + 1;
            if (idx >= len - GAP_SIZE && idx < len) is_gap = true;
        } else if (entrance_side == 2 && w.wx == t_rect-1) { // top
            int idx = w.wy - l_rect;
            if (idx < GAP_SIZE) is_gap = true;
        } else if (entrance_side == 3 && w.wy == l_rect-1) { // left
            int idx = w.wx - t_rect;
            if (idx < GAP_SIZE) is_gap = true;
        }
        if (is_gap) {
            walls_to_build_later.push_back(i);
        } else {
            walls_to_build_now.push_back(i);
        }
    }
}

// ------------------------------------------------------------
// Main simulation
// ------------------------------------------------------------
int main() {
    // Read input
    cin >> N;
    pets.resize(N);
    for (int i = 0; i < N; ++i) {
        cin >> pets[i].x >> pets[i].y >> pets[i].type;
    }
    cin >> M;
    humans.resize(M);
    for (int i = 0; i < M; ++i) {
        cin >> humans[i].x >> humans[i].y;
        humans[i].target_wall_id = -1;
        humans[i].failed_attempts = 0;
    }

    // Initialize walls
    memset(is_wall, 0, sizeof(is_wall));
    choose_rectangle();
    create_walls();

    // Main loop
    bool building_entrance = false;
    for (int turn = 1; turn <= MAX_TURNS; ++turn) {
        // Precompute human and pet presence at start of turn
        vector<vector<int>> human_at_start(GRID_SIZE+2, vector<int>(GRID_SIZE+2, -1));
        vector<vector<bool>> pet_present(GRID_SIZE+2, vector<bool>(GRID_SIZE+2, false));
        for (int i = 0; i < M; ++i) {
            human_at_start[humans[i].x][humans[i].y] = i;
        }
        for (const Pet& pet : pets) {
            pet_present[pet.x][pet.y] = true;
        }

        // Determine which humans are inside the rectangle
        vector<bool> inside(M);
        bool all_inside = true;
        for (int i = 0; i < M; ++i) {
            inside[i] = is_inside(humans[i].x, humans[i].y);
            if (!inside[i]) all_inside = false;
        }

        // Update built flags (in case walls were placed by other humans)
        for (Wall& w : walls) {
            w.built = is_wall[w.wx][w.wy];
        }

        // Release target wall if built or too many failed attempts
        for (int i = 0; i < M; ++i) {
            if (humans[i].target_wall_id != -1) {
                Wall& w = walls[humans[i].target_wall_id];
                if (w.built || humans[i].failed_attempts > 10) {
                    humans[i].target_wall_id = -1;
                    humans[i].failed_attempts = 0;
                }
            }
        }

        // Decide available walls for assignment
        vector<int> available_walls;
        if (!building_entrance) {
            for (int idx : walls_to_build_now) {
                if (!walls[idx].built) available_walls.push_back(idx);
            }
            if (all_inside) {
                // Check if all walls_to_build_now are built
                bool all_built = true;
                for (int idx : walls_to_build_now) {
                    if (!walls[idx].built) { all_built = false; break; }
                }
                if (all_built) {
                    building_entrance = true;
                    // Add entrance walls to available list
                    for (int idx : walls_to_build_later) {
                        if (!walls[idx].built) available_walls.push_back(idx);
                    }
                }
            }
        } else {
            for (int idx : walls_to_build_now) {
                if (!walls[idx].built) available_walls.push_back(idx);
            }
            for (int idx : walls_to_build_later) {
                if (!walls[idx].built) available_walls.push_back(idx);
            }
        }

        // Assign target walls to inside humans without a target
        vector<bool> wall_assigned(walls.size(), false);
        for (int i = 0; i < M; ++i) {
            if (inside[i] && humans[i].target_wall_id != -1) {
                wall_assigned[humans[i].target_wall_id] = true;
            }
        }
        for (int i = 0; i < M; ++i) {
            if (inside[i] && humans[i].target_wall_id == -1) {
                // find nearest available wall
                int best_dist = 1e9, best_j = -1;
                for (int j : available_walls) {
                    if (wall_assigned[j]) continue;
                    const Wall& w = walls[j];
                    int dist = abs(humans[i].x - w.sx) + abs(humans[i].y - w.sy);
                    if (dist < best_dist) {
                        best_dist = dist;
                        best_j = j;
                    }
                }
                if (best_j != -1) {
                    humans[i].target_wall_id = best_j;
                    wall_assigned[best_j] = true;
                }
            }
        }

        // For each human, decide desired action
        struct DesiredAction {
            int type;          // 0: stay, 1: move, 2: place
            int arg1, arg2;    // for move: nx,ny; for place: wx,wy
            char dir;          // character to output
        };
        vector<DesiredAction> desired(M, {0,0,0,'.'});

        for (int i = 0; i < M; ++i) {
            if (!inside[i]) {
                // Move towards the inside of the rectangle
                int nx, ny;
                if (bfs_to_inside(humans[i].x, humans[i].y, nx, ny)) {
                    desired[i] = {1, nx, ny, '.'};
                } else {
                    desired[i] = {0,0,0,'.'};
                }
            } else {
                if (humans[i].target_wall_id == -1) {
                    desired[i] = {0,0,0,'.'};
                } else {
                    const Wall& w = walls[humans[i].target_wall_id];
                    if (humans[i].x == w.sx && humans[i].y == w.sy) {
                        // Try to place wall
                        bool can_place = is_passable(w.wx, w.wy);
                        can_place = can_place && (human_at_start[w.wx][w.wy] == -1);
                        // Check no pet adjacent to wall square
                        bool pet_adj = false;
                        for (int d = 0; d < 4; ++d) {
                            int ax = w.wx + dx[d], ay = w.wy + dy[d];
                            if (ax >= 1 && ax <= GRID_SIZE && ay >= 1 && ay <= GRID_SIZE &&
                                pet_present[ax][ay]) {
                                pet_adj = true;
                                break;
                            }
                        }
                        can_place = can_place && !pet_adj;
                        if (can_place) {
                            char d = get_wall_char(humans[i].x, humans[i].y, w.wx, w.wy);
                            desired[i] = {2, w.wx, w.wy, d};
                        } else {
                            desired[i] = {0,0,0,'.'};
                            // failure due to condition, but we only count conflicts later
                        }
                    } else {
                        // Move towards stand position
                        int nx, ny;
                        if (bfs_to_target(humans[i].x, humans[i].y, w.sx, w.sy, nx, ny)) {
                            desired[i] = {1, nx, ny, '.'};
                        } else {
                            desired[i] = {0,0,0,'.'};
                        }
                    }
                }
            }
        }

        // Output actions with conflict resolution
        vector<char> actions(M, '.');
        set<pair<int,int>> planned_walls;
        set<pair<int,int>> planned_move_dests;
        for (int i = 0; i < M; ++i) {
            if (desired[i].type == 1) { // move
                int nx = desired[i].arg1, ny = desired[i].arg2;
                if (is_passable(nx, ny) && planned_walls.count({nx, ny}) == 0) {
                    actions[i] = get_move_char(humans[i].x, humans[i].y, nx, ny);
                    planned_move_dests.insert({nx, ny});
                } else {
                    actions[i] = '.';
                }
            } else if (desired[i].type == 2) { // place wall
                int wx = desired[i].arg1, wy = desired[i].arg2;
                bool can_place = is_passable(wx, wy);
                can_place = can_place && (human_at_start[wx][wy] == -1);
                // pet adjacent check (again)
                bool pet_adj = false;
                for (int d = 0; d < 4; ++d) {
                    int ax = wx + dx[d], ay = wy + dy[d];
                    if (ax >= 1 && ax <= GRID_SIZE && ay >= 1 && ay <= GRID_SIZE &&
                        pet_present[ax][ay]) {
                        pet_adj = true;
                        break;
                    }
                }
                can_place = can_place && !pet_adj;
                can_place = can_place && (planned_move_dests.count({wx, wy}) == 0);
                can_place = can_place && (planned_walls.count({wx, wy}) == 0);
                if (can_place) {
                    actions[i] = desired[i].dir;
                    planned_walls.insert({wx, wy});
                } else {
                    actions[i] = '.';
                    humans[i].failed_attempts++;
                }
            } else {
                actions[i] = '.';
            }
        }

        // Output the actions
        for (int i = 0; i < M; ++i) cout << actions[i];
        cout << endl;
        cout.flush();

        // Update human positions
        for (int i = 0; i < M; ++i) {
            if (actions[i] == 'U') humans[i].x--;
            else if (actions[i] == 'D') humans[i].x++;
            else if (actions[i] == 'L') humans[i].y--;
            else if (actions[i] == 'R') humans[i].y++;
        }

        // Update walls
        for (auto& p : planned_walls) {
            is_wall[p.first][p.second] = true;
        }

        // Read pet movements
        for (int i = 0; i < N; ++i) {
            string move;
            cin >> move;
            for (char c : move) {
                if (c == 'U') pets[i].x--;
                else if (c == 'D') pets[i].x++;
                else if (c == 'L') pets[i].y--;
                else if (c == 'R') pets[i].y++;
            }
        }
    }

    return 0;
}