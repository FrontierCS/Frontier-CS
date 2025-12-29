#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <cmath>
#include <algorithm>
#include <map>
#include <set>
#include <numeric>

using namespace std;

// --- Utilities and Constants ---
const int GRID_SIZE = 30;
const int TURN_LIMIT = 300;
const int dr[] = {-1, 1, 0, 0};
const int dc[] = {0, 0, -1, 1};

struct Point {
    int r, c;
    bool operator==(const Point& other) const {
        return r == other.r && c == other.c;
    }
    bool operator!=(const Point& other) const {
        return !(*this == other);
    }
    bool operator<(const Point& other) const {
        if (r != other.r) return r < other.r;
        return c < other.c;
    }
};

// --- Global State ---
int N, M;
vector<Point> pet_pos;
vector<Point> human_pos;
bool impassable[GRID_SIZE][GRID_SIZE];

// --- Plan ---
enum HumanState { MOVING_TO_BUILD, MOVING_TO_SAFE, DONE };
vector<vector<Point>> human_tasks;
vector<Point> human_safe_spots;
vector<HumanState> human_states;
int enclosure_type; // 0:TL, 1:TR, 2:BL, 3:BR
int R_min, R_max, C_min, C_max;

// --- Functions ---
bool is_valid(int r, int c) {
    return r >= 0 && r < GRID_SIZE && c >= 0 && c < GRID_SIZE;
}

bool can_build(const Point& p) {
    if (!is_valid(p.r, p.c) || impassable[p.r][p.c]) return false;

    for (int i = 0; i < N; ++i) if (pet_pos[i] == p) return false;
    for (int i = 0; i < M; ++i) if (human_pos[i] == p) return false;

    for (int i = 0; i < N; ++i) {
        for (int k = 0; k < 4; ++k) {
            Point adj = {p.r + dr[k], p.c + dc[k]};
            if (is_valid(adj.r, adj.c) && pet_pos[i] == adj) return false;
        }
    }
    return true;
}

Point get_build_pos_for_wall(const Point& wall_cell) {
    if (enclosure_type == 0) { // TL
        if (wall_cell.c == C_max + 1) return {wall_cell.r, C_max};
        return {R_max, wall_cell.c};
    } else if (enclosure_type == 1) { // TR
        if (wall_cell.c == C_min - 1) return {wall_cell.r, C_min};
        return {R_max, wall_cell.c};
    } else if (enclosure_type == 2) { // BL
        if (wall_cell.c == C_max + 1) return {wall_cell.r, C_max};
        return {R_min, wall_cell.c};
    } else { // BR
        if (wall_cell.c == C_min - 1) return {wall_cell.r, C_min};
        return {R_min, wall_cell.c};
    }
}

Point get_next_step(const Point& start, const Point& target) {
    if (start == target) return start;

    queue<Point> q;
    q.push(start);
    Point parent[GRID_SIZE][GRID_SIZE];
    bool visited[GRID_SIZE][GRID_SIZE] = {};

    visited[start.r][start.c] = true;

    bool found = false;
    while (!q.empty()) {
        Point curr = q.front();
        q.pop();

        if (curr == target) {
            found = true;
            break;
        }
        
        int p[] = {0, 1, 2, 3};
        // random_shuffle is deprecated, this is a simple alternative
        for(int i = 0; i < 4; ++i) swap(p[i], p[rand() % 4]);

        for (int i = 0; i < 4; ++i) {
            int k = p[i];
            Point next = {curr.r + dr[k], curr.c + dc[k]};
            if (is_valid(next.r, next.c) && !impassable[next.r][next.c] && !visited[next.r][next.c]) {
                visited[next.r][next.c] = true;
                parent[next.r][next.c] = curr;
                q.push(next);
            }
        }
    }

    if (!found) {
        return {-1, -1};
    }

    Point p = target;
    while (parent[p.r][p.c] != start) {
        p = parent[p.r][p.c];
    }
    return p;
}


char get_move_char(const Point& from, const Point& to) {
    if (to.r == from.r - 1) return 'U';
    if (to.r == from.r + 1) return 'D';
    if (to.c == from.c - 1) return 'L';
    if (to.c == from.c + 1) return 'R';
    return '.';
}

char get_build_char(const Point& from, const Point& to) {
    if (to.r == from.r - 1) return 'u';
    if (to.r == from.r + 1) return 'd';
    if (to.c == from.c - 1) return 'l';
    if (to.c == from.c + 1) return 'r';
    return '.';
}

void plan_enclosure() {
    int pet_counts[4] = {0}; // TL, TR, BL, BR
    for (int i = 0; i < N; ++i) {
        if (pet_pos[i].r < 15 && pet_pos[i].c < 15) pet_counts[0]++;
        else if (pet_pos[i].r < 15 && pet_pos[i].c >= 15) pet_counts[1]++;
        else if (pet_pos[i].r >= 15 && pet_pos[i].c < 15) pet_counts[2]++;
        else pet_counts[3]++;
    }

    enclosure_type = 0;
    for (int i = 1; i < 4; ++i) {
        if (pet_counts[i] < pet_counts[enclosure_type]) {
            enclosure_type = i;
        }
    }

    const int ENC_SIZE = 20;
    if (enclosure_type == 0) { // TL
        R_min = 0; R_max = ENC_SIZE - 1; C_min = 0; C_max = ENC_SIZE - 1;
    } else if (enclosure_type == 1) { // TR
        R_min = 0; R_max = ENC_SIZE - 1; C_min = GRID_SIZE - ENC_SIZE; C_max = GRID_SIZE - 1;
    } else if (enclosure_type == 2) { // BL
        R_min = GRID_SIZE - ENC_SIZE; R_max = GRID_SIZE - 1; C_min = 0; C_max = ENC_SIZE - 1;
    } else { // BR
        R_min = GRID_SIZE - ENC_SIZE; R_max = GRID_SIZE - 1; C_min = GRID_SIZE - ENC_SIZE; C_max = GRID_SIZE - 1;
    }

    vector<Point> all_wall_cells;
    if (enclosure_type == 0) { // TL
        for (int r = R_min; r <= R_max; ++r) all_wall_cells.push_back({r, C_max + 1});
        for (int c = C_min; c <= C_max + 1; ++c) all_wall_cells.push_back({R_max + 1, c});
    } else if (enclosure_type == 1) { // TR
        for (int r = R_min; r <= R_max; ++r) all_wall_cells.push_back({r, C_min - 1});
        for (int c = C_min - 1; c <= C_max; ++c) all_wall_cells.push_back({R_max + 1, c});
    } else if (enclosure_type == 2) { // BL
        for (int r = R_min; r <= R_max + 1; ++r) all_wall_cells.push_back({r, C_max + 1});
        for (int c = C_min; c <= C_max; ++c) all_wall_cells.push_back({R_min - 1, c});
    } else { // BR
        for (int r = R_min; r <= R_max + 1; ++r) all_wall_cells.push_back({r, C_min - 1});
        for (int c = C_min; c <= C_max; ++c) all_wall_cells.push_back({R_min - 1, c});
    }
    
    sort(all_wall_cells.begin(), all_wall_cells.end());
    all_wall_cells.erase(unique(all_wall_cells.begin(), all_wall_cells.end()), all_wall_cells.end());

    int cells_per_human = (all_wall_cells.size() + M - 1) / M;
    for (int i = 0; i < M; ++i) {
        for (int j = 0; j < cells_per_human; ++j) {
            int idx = i * cells_per_human + j;
            if (idx < all_wall_cells.size()) {
                human_tasks[i].push_back(all_wall_cells[idx]);
            }
        }
        human_states[i] = MOVING_TO_BUILD;
        int r_safe = (R_min + R_max) / 2;
        int c_safe = (C_min + C_max) / 2;
        human_safe_spots[i] = {r_safe + (i % 3) - 1, c_safe + (i / 3) - (M/6)};
    }
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n_pets;
    cin >> n_pets;
    N = n_pets;
    pet_pos.resize(N);
    vector<int> pet_type(N);
    for (int i = 0; i < N; ++i) {
        cin >> pet_pos[i].r >> pet_pos[i].c >> pet_type[i];
        pet_pos[i].r--; pet_pos[i].c--;
    }
    cin >> M;
    human_pos.resize(M);
    human_tasks.resize(M);
    human_safe_spots.resize(M);
    human_states.resize(M);
    for (int i = 0; i < M; ++i) {
        cin >> human_pos[i].r >> human_pos[i].c;
        human_pos[i].r--; human_pos[i].c--;
    }

    plan_enclosure();

    for (int t = 0; t < TURN_LIMIT; ++t) {
        vector<pair<char, Point>> intentions(M); // 'b': build, 'm': move, 'w': wait
        
        for (int i = 0; i < M; ++i) {
            // Update tasks
            human_tasks[i].erase(remove_if(human_tasks[i].begin(), human_tasks[i].end(), [&](const Point& p) {
                return impassable[p.r][p.c];
            }), human_tasks[i].end());

            if (human_tasks[i].empty() && human_states[i] != DONE) {
                human_states[i] = MOVING_TO_SAFE;
            }

            if (human_states[i] == DONE) {
                intentions[i] = {'w', {-1, -1}};
                continue;
            }

            if (human_states[i] == MOVING_TO_SAFE) {
                if (human_pos[i] == human_safe_spots[i]) {
                    human_states[i] = DONE;
                    intentions[i] = {'w', {-1, -1}};
                } else {
                    intentions[i] = {'m', human_safe_spots[i]};
                }
                continue;
            }

            Point best_wall_target = {-1, -1};
            Point best_build_pos = {-1, -1};
            int min_dist = 1e9;

            for (const auto& wall_cell : human_tasks[i]) {
                if (can_build(wall_cell)) {
                    Point build_pos = get_build_pos_for_wall(wall_cell);
                    int dist = abs(human_pos[i].r - build_pos.r) + abs(human_pos[i].c - build_pos.c);
                    if (dist < min_dist) {
                        min_dist = dist;
                        best_wall_target = wall_cell;
                        best_build_pos = build_pos;
                    }
                }
            }

            if (best_wall_target.r != -1) {
                if (human_pos[i] == best_build_pos) {
                    intentions[i] = {'b', best_wall_target};
                } else {
                    intentions[i] = {'m', best_build_pos};
                }
            } else {
                intentions[i] = {'w', {-1, -1}};
            }
        }
        
        vector<Point> build_intentions;
        for(int i=0; i<M; ++i) {
            if(intentions[i].first == 'b') {
                build_intentions.push_back(intentions[i].second);
            }
        }

        string final_actions = "";
        for (int i = 0; i < M; ++i) {
            char action_char = '.';
            if (intentions[i].first == 'b') {
                action_char = get_build_char(human_pos[i], intentions[i].second);
            } else if (intentions[i].first == 'm') {
                Point move_target_pos = intentions[i].second;
                Point next_step = get_next_step(human_pos[i], move_target_pos);
                if (next_step.r != -1) {
                     bool conflict = false;
                     for(const auto& p : build_intentions) {
                         if (p == next_step) {
                             conflict = true;
                             break;
                         }
                     }
                     if(!conflict) {
                        action_char = get_move_char(human_pos[i], next_step);
                     }
                }
            }
            final_actions += action_char;
        }

        cout << final_actions << endl;

        for (int i = 0; i < M; ++i) {
            char act = final_actions[i];
            if (islower(act)) {
                Point p = human_pos[i];
                if (act == 'u') p.r--; if (act == 'd') p.r++;
                if (act == 'l') p.c--; if (act == 'r') p.c++;
                if(is_valid(p.r, p.c)) impassable[p.r][p.c] = true;
            }
        }
        for (int i = 0; i < M; ++i) {
            char act = final_actions[i];
            if (isupper(act)) {
                if (act == 'U') human_pos[i].r--; if (act == 'D') human_pos[i].r++;
                if (act == 'L') human_pos[i].c--; if (act == 'R') human_pos[i].c++;
            }
        }

        if (t == TURN_LIMIT - 1) break;

        for (int i = 0; i < N; ++i) {
            string pet_move;
            cin >> pet_move;
            for (char move : pet_move) {
                if (move == '.') continue;
                if (move == 'U') pet_pos[i].r--; if (move == 'D') pet_pos[i].r++;
                if (move == 'L') pet_pos[i].c--; if (move == 'R') pet_pos[i].c++;
            }
        }
    }

    return 0;
}