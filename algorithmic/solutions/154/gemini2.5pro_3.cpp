#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>
#include <queue>
#include <map>

using namespace std;

const int GRID_SIZE = 30;
const int NUM_TURNS = 300;

const int dr[] = {-1, 1, 0, 0};
const int dc[] = {0, 0, -1, 1};
const char MOVE_CH[] = {'U', 'D', 'L', 'R'};
const char BUILD_CH[] = {'u', 'd', 'l', 'r'};

struct Point {
    int r, c;
    bool operator<(const Point& other) const {
        if (r != other.r) return r < other.r;
        return c < other.c;
    }
};

struct Pet {
    int id;
    int r, c, type;
};

struct Human {
    int id;
    int r, c;
};

int N, M;
vector<Pet> pets;
vector<Human> humans;
bool is_wall[GRID_SIZE + 2][GRID_SIZE + 2];

int phase = 1;
int great_wall_coord;
bool great_wall_is_horizontal;
bool safe_zone_is_less;

vector<vector<Point>> p1_human_targets;
vector<Point> p2_targets;
vector<Point> p3_targets;

bool is_valid(int r, int c) {
    return r >= 1 && r <= GRID_SIZE && c >= 1 && c <= GRID_SIZE;
}

void read_initial_input() {
    cin >> N;
    pets.resize(N);
    for (int i = 0; i < N; ++i) {
        pets[i].id = i;
        cin >> pets[i].r >> pets[i].c >> pets[i].type;
    }
    cin >> M;
    humans.resize(M);
    for (int i = 0; i < M; ++i) {
        humans[i].id = i;
        cin >> humans[i].r >> humans[i].c;
    }

    for (int i = 0; i <= GRID_SIZE + 1; ++i) {
        is_wall[i][0] = is_wall[0][i] = is_wall[i][GRID_SIZE + 1] = is_wall[GRID_SIZE + 1][i] = true;
    }
}

void setup_strategy() {
    int best_score = -1e9;
    
    int score1 = 0; for(const auto& p : pets) if (p.r <= 15) score1--;
    if (score1 > best_score) {
        best_score = score1;
        great_wall_is_horizontal = true;
        great_wall_coord = 16;
        safe_zone_is_less = true;
    }
    
    int score2 = 0; for(const auto& p : pets) if (p.r >= 16) score2--;
    if (score2 > best_score) {
        best_score = score2;
        great_wall_is_horizontal = true;
        great_wall_coord = 15;
        safe_zone_is_less = false;
    }
    
    int score3 = 0; for(const auto& p : pets) if (p.c <= 15) score3--;
    if (score3 > best_score) {
        best_score = score3;
        great_wall_is_horizontal = false;
        great_wall_coord = 16;
        safe_zone_is_less = true;
    }
    
    int score4 = 0; for(const auto& p : pets) if (p.c >= 16) score4--;
    if (score4 > best_score) {
        best_score = score4;
        great_wall_is_horizontal = false;
        great_wall_coord = 15;
        safe_zone_is_less = false;
    }

    vector<Point> p1_wall_cells;
    if (great_wall_is_horizontal) {
        for (int c = 1; c <= GRID_SIZE; ++c) p1_wall_cells.push_back({great_wall_coord, c});
    } else {
        for (int r = 1; r <= GRID_SIZE; ++r) p1_wall_cells.push_back({r, great_wall_coord});
    }
    
    p1_human_targets.resize(M);
    vector<pair<int, int>> human_sorted_indices(M);
    for(int i=0; i<M; ++i) human_sorted_indices[i] = {great_wall_is_horizontal ? humans[i].c : humans[i].r, i};
    sort(human_sorted_indices.begin(), human_sorted_indices.end());

    for (int i = 0; i < M; ++i) {
        int human_idx = human_sorted_indices[i].second;
        int start = i * GRID_SIZE / M;
        int end = (i + 1) * GRID_SIZE / M;
        for (int j = start; j < end; ++j) {
            p1_human_targets[human_idx].push_back(p1_wall_cells[j]);
        }
    }

    p3_targets.resize(M);
    if (great_wall_is_horizontal) {
        int safe_r_min = safe_zone_is_less ? 1 : great_wall_coord + 1;
        int safe_r_max = safe_zone_is_less ? great_wall_coord - 1 : GRID_SIZE;
        for (int i = 1; i < M; ++i) {
            int part_c = 1 + i * GRID_SIZE / M;
            for (int r = safe_r_min; r <= safe_r_max; ++r) {
                p2_targets.push_back({r, part_c});
            }
        }
        for (int i = 0; i < M; ++i) {
            int c_min = 1 + i * GRID_SIZE / M;
            int c_max = (i + 1) * GRID_SIZE / M;
            int human_idx = human_sorted_indices[i].second;
            p3_targets[human_idx] = {(safe_r_min + safe_r_max) / 2, (c_min + c_max) / 2};
        }
    } else {
        vector<pair<int, int>> human_sorted_indices_r(M);
        for(int i=0; i<M; ++i) human_sorted_indices_r[i] = {humans[i].r, i};
        sort(human_sorted_indices_r.begin(), human_sorted_indices_r.end());
        
        int safe_c_min = safe_zone_is_less ? 1 : great_wall_coord + 1;
        int safe_c_max = safe_zone_is_less ? great_wall_coord - 1 : GRID_SIZE;
        for (int i = 1; i < M; ++i) {
            int part_r = 1 + i * GRID_SIZE / M;
            for (int c = safe_c_min; c <= safe_c_max; ++c) {
                p2_targets.push_back({part_r, c});
            }
        }
        for (int i = 0; i < M; ++i) {
            int r_min = 1 + i * GRID_SIZE / M;
            int r_max = (i + 1) * GRID_SIZE / M;
            int human_idx = human_sorted_indices_r[i].second;
            p3_targets[human_idx] = {(r_min + r_max) / 2, (safe_c_min + safe_c_max) / 2};
        }
    }
}

bool is_in_safe_zone(int r, int c) {
    if (great_wall_is_horizontal) {
        return safe_zone_is_less ? (r < great_wall_coord) : (r > great_wall_coord);
    } else {
        return safe_zone_is_less ? (c < great_wall_coord) : (c > great_wall_coord);
    }
}

bool can_build(int r, int c) {
    if (!is_valid(r, c) || is_wall[r][c]) return false;
    for (const auto& p : pets) {
        if (abs(p.r - r) <= 1 && abs(p.c - c) <= 1) return false;
    }
    for (const auto& h : humans) {
        if (h.r == r && h.c == c) return false;
    }
    return true;
}

char get_move_char(int r1, int c1, int r2, int c2) {
    if (r2 < r1) return 'U';
    if (r2 > r1) return 'D';
    if (c2 < c1) return 'L';
    if (c2 > c1) return 'R';
    return '.';
}

char get_build_char(int r1, int c1, int r2, int c2) {
    if (r2 < r1) return 'u';
    if (r2 > r1) return 'd';
    if (c2 < c1) return 'l';
    if (c2 > c1) return 'r';
    return '.';
}

void determine_actions(int turn, string& actions) {
    if (turn < 120) phase = 1;
    else if (turn < 260) phase = 2;
    else phase = 3;

    vector<Point> planned_moves;
    vector<Point> planned_walls;

    for (int i = 0; i < M; ++i) {
        int hr = humans[i].r, hc = humans[i].c;
        
        vector<Point> current_targets;
        if (phase == 1) {
            for(const auto& p : p1_human_targets[i]){
                if(!is_wall[p.r][p.c]) current_targets.push_back(p);
            }
        } else if (phase == 2) {
            for(const auto& p : p2_targets){
                if(!is_wall[p.r][p.c]) current_targets.push_back(p);
            }
        }
        
        if (phase != 3 && current_targets.empty()) {
            actions[i] = '.';
            continue;
        }

        queue<Point> q;
        q.push({hr, hc});
        map<Point, Point> parent;
        dist_grid[hr][hc] = 0;

        vector<vector<int>> dist_grid(GRID_SIZE + 2, vector<int>(GRID_SIZE + 2, -1));

        q.push({hr,hc});
        dist_grid[hr][hc] = 0;

        int head = 0;
        vector<Point> q_vec;
        q_vec.push_back({hr,hc});

        while(head < q_vec.size()){
            Point curr = q_vec[head++];
            for(int k=0; k<4; ++k){
                Point next = {curr.r + dr[k], curr.c + dc[k]};
                if(!is_valid(next.r, next.c) || is_wall[next.r][next.c] || dist_grid[next.r][next.c] != -1) continue;
                bool occupied = false;
                for(const auto& pm : planned_moves) if(pm.r == next.r && pm.c == next.c) occupied = true;
                if(occupied) continue;

                if (phase == 1 && is_in_safe_zone(next.r, next.c)) continue;
                if (phase == 2 && !is_in_safe_zone(next.r, next.c)) continue;
                
                dist_grid[next.r][next.c] = dist_grid[curr.r][curr.c] + 1;
                parent[next] = curr;
                q_vec.push_back(next);
            }
        }

        Point best_adj_cell = {-1,-1};
        Point target_wall = {-1,-1};
        int min_dist = 1e9;
        
        if(phase == 3) {
            target_wall = p3_targets[i];
            min_dist = dist_grid[target_wall.r][target_wall.c];
        } else {
             for (const auto& p : current_targets) {
                for (int j = 0; j < 4; ++j) {
                    Point adj = {p.r + dr[j], p.c + dc[j]};
                    if (!is_valid(adj.r, adj.c)) continue;
                    if(dist_grid[adj.r][adj.c] != -1 && dist_grid[adj.r][adj.c] < min_dist){
                        min_dist = dist_grid[adj.r][adj.c];
                        best_adj_cell = adj;
                        target_wall = p;
                    }
                }
            }
        }

        if(min_dist != -1 && min_dist < 1e9){
             Point path_target = (phase == 3) ? target_wall : best_adj_cell;
             if (dist_grid[path_target.r][path_target.c] == 0) { // On target/adj
                if (phase == 3) {
                    actions[i] = '.';
                } else {
                    if (can_build(target_wall.r, target_wall.c)) {
                        actions[i] = get_build_char(hr, hc, target_wall.r, target_wall.c);
                        planned_walls.push_back(target_wall);
                    } else {
                        actions[i] = '.';
                    }
                }
             } else { // Move
                Point curr = path_target;
                while (parent.count(curr) && !(parent[curr].r == hr && parent[curr].c == hc)) {
                    curr = parent[curr];
                }
                actions[i] = get_move_char(hr, hc, curr.r, curr.c);
                planned_moves.push_back(curr);
            }
        } else {
            actions[i] = '.';
        }
    }
}

void update_state(const string& actions) {
    for (int i = 0; i < M; ++i) {
        char action = actions[i];
        if (action >= 'U' && action <= 'R') {
            int move_idx = -1;
            for(int j=0; j<4; ++j) if(MOVE_CH[j] == action) move_idx = j;
            humans[i].r += dr[move_idx];
            humans[i].c += dc[move_idx];
        } else if (action >= 'u' && action <= 'r') {
            int build_idx = -1;
            for(int j=0; j<4; ++j) if(BUILD_CH[j] == action) build_idx = j;
            is_wall[humans[i].r + dr[build_idx]][humans[i].c + dc[build_idx]] = true;
        }
    }

    for (int i = 0; i < N; ++i) {
        string pet_move;
        cin >> pet_move;
        for (char move : pet_move) {
            if (move == 'U') pets[i].r--;
            else if (move == 'D') pets[i].r++;
            else if (move == 'L') pets[i].c--;
            else if (move == 'R') pets[i].c++;
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    read_initial_input();
    setup_strategy();

    for (int t = 0; t < NUM_TURNS; ++t) {
        string actions(M, '.');
        determine_actions(t, actions);
        cout << actions << endl;
        update_state(actions);
    }

    return 0;
}