#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <sstream>
#include <cstring>
#include <cmath>

using namespace std;

typedef pair<int, int> Pos;

enum TaskType { MOVE, PLACE };

struct Task {
    TaskType type;
    int x, y; // for MOVE: target position; for PLACE: wall square coordinates
};

const int GRID_SIZE = 30;
int N, M;
vector<Pos> pet_positions;
vector<int> pet_types;
vector<Pos> human_positions;
bool grid_impassable[GRID_SIZE+2][GRID_SIZE+2] = {false}; // 1-indexed

int r2, c2; // rectangle dimensions (inclusive)
Pos gather_point;

vector<vector<Task>> tasks; // for each human
int phase = 0; // 0: gathering, 1: wall-building

// ------------------------------------------------------------

void compute_rectangle() {
    int best_score = -1e9;
    r2 = c2 = 15; // default
    for (int r = 10; r <= 29; ++r) {
        for (int c = 10; c <= 29; ++c) {
            int area = r * c;
            int pet_count = 0;
            for (auto& pet : pet_positions) {
                if (pet.first <= r && pet.second <= c) pet_count++;
            }
            // score: maximize area, penalize pets
            int score = area - pet_count * 20;
            if (score > best_score) {
                best_score = score;
                r2 = r;
                c2 = c;
            }
        }
    }
}

// ------------------------------------------------------------

char get_move_direction(Pos start, Pos target, const vector<Pos>& blocked) {
    if (start == target) return '.';
    bool blocked_grid[GRID_SIZE+2][GRID_SIZE+2] = {false};
    for (auto& b : blocked) blocked_grid[b.first][b.second] = true;

    int dx[4] = {-1, 1, 0, 0};
    int dy[4] = {0, 0, -1, 1};
    char dir_c[4] = {'U', 'D', 'L', 'R'};

    vector<vector<int>> dist(GRID_SIZE+2, vector<int>(GRID_SIZE+2, -1));
    vector<vector<Pos>> parent(GRID_SIZE+2, vector<Pos>(GRID_SIZE+2, {-1,-1}));
    queue<Pos> q;
    q.push(start);
    dist[start.first][start.second] = 0;

    while (!q.empty()) {
        Pos cur = q.front(); q.pop();
        int x = cur.first, y = cur.second;
        if (cur == target) break;
        for (int d = 0; d < 4; ++d) {
            int nx = x + dx[d], ny = y + dy[d];
            if (nx < 1 || nx > GRID_SIZE || ny < 1 || ny > GRID_SIZE) continue;
            if (grid_impassable[nx][ny]) continue;
            if (blocked_grid[nx][ny]) continue;
            if (dist[nx][ny] != -1) continue;
            dist[nx][ny] = dist[x][y] + 1;
            parent[nx][ny] = cur;
            q.push({nx, ny});
        }
    }

    if (dist[target.first][target.second] == -1) return '.';
    // backtrack to find first step
    Pos cur = target;
    while (parent[cur.first][cur.second] != start) {
        cur = parent[cur.first][cur.second];
    }
    // direction from start to cur
    if (cur.first == start.first-1 && cur.second == start.second) return 'U';
    if (cur.first == start.first+1 && cur.second == start.second) return 'D';
    if (cur.first == start.first && cur.second == start.second-1) return 'L';
    if (cur.first == start.first && cur.second == start.second+1) return 'R';
    return '.';
}

// ------------------------------------------------------------

void assign_tasks() {
    tasks.clear();
    tasks.resize(M);

    if (M == 1) {
        // single human does both walls
        int i = 0;
        // move to start of bottom wall
        if (human_positions[i] != Pos(r2, 1))
            tasks[i].push_back({MOVE, r2, 1});
        // bottom walls
        for (int y = 1; y <= c2; ++y) {
            tasks[i].push_back({PLACE, r2+1, y});
            if (y < c2)
                tasks[i].push_back({MOVE, r2, y+1});
        }
        // move to start of right wall
        if (human_positions[i] != Pos(1, c2))
            tasks[i].push_back({MOVE, 1, c2});
        // right walls
        for (int x = 1; x <= r2; ++x) {
            tasks[i].push_back({PLACE, x, c2+1});
            if (x < r2)
                tasks[i].push_back({MOVE, x+1, c2});
        }
        return;
    }

    // M >= 2
    int total_walls = c2 + r2;
    int M_bottom = max(1, min(M-1, (int)round((double)M * c2 / total_walls)));
    int M_right = M - M_bottom;

    // bottom group (first M_bottom humans)
    int per_bottom = (c2 + M_bottom - 1) / M_bottom; // ceil
    for (int i = 0; i < M_bottom; ++i) {
        int y_start = i * per_bottom + 1;
        int y_end = min(c2, (i+1) * per_bottom);
        if (human_positions[i] != Pos(r2, y_start))
            tasks[i].push_back({MOVE, r2, y_start});
        for (int y = y_start; y <= y_end; ++y) {
            tasks[i].push_back({PLACE, r2+1, y});
            if (y < y_end)
                tasks[i].push_back({MOVE, r2, y+1});
        }
    }

    // right group (remaining humans)
    int per_right = (r2 + M_right - 1) / M_right; // ceil
    for (int i = 0; i < M_right; ++i) {
        int idx = M_bottom + i;
        int x_start = i * per_right + 1;
        int x_end = min(r2, (i+1) * per_right);
        if (human_positions[idx] != Pos(x_start, c2))
            tasks[idx].push_back({MOVE, x_start, c2});
        for (int x = x_start; x <= x_end; ++x) {
            tasks[idx].push_back({PLACE, x, c2+1});
            if (x < x_end)
                tasks[idx].push_back({MOVE, x+1, c2});
        }
    }
}

// ------------------------------------------------------------

int main() {
    // Read initial input
    cin >> N;
    pet_positions.resize(N);
    pet_types.resize(N);
    for (int i = 0; i < N; ++i) {
        cin >> pet_positions[i].first >> pet_positions[i].second >> pet_types[i];
    }
    cin >> M;
    human_positions.resize(M);
    for (int i = 0; i < M; ++i) {
        cin >> human_positions[i].first >> human_positions[i].second;
    }
    string dummy;
    getline(cin, dummy); // consume newline after last number

    // Decide rectangle
    compute_rectangle();
    gather_point = {r2, c2};

    // Initialize tasks for gathering phase
    tasks.resize(M);
    for (int i = 0; i < M; ++i) {
        tasks[i].clear();
        tasks[i].push_back({MOVE, gather_point.first, gather_point.second});
    }
    phase = 0;

    // Main loop
    for (int turn = 1; turn <= 300; ++turn) {
        vector<char> actions(M, '.');
        vector<Pos> new_human_pos = human_positions;
        vector<Pos> planned_walls;

        // Decide actions for each human
        for (int i = 0; i < M; ++i) {
            if (phase == 0) {
                // Gathering phase
                if (human_positions[i] == gather_point) {
                    actions[i] = '.';
                } else {
                    char dir = get_move_direction(human_positions[i], gather_point, planned_walls);
                    actions[i] = dir;
                    if (dir == 'U') new_human_pos[i].first--;
                    else if (dir == 'D') new_human_pos[i].first++;
                    else if (dir == 'L') new_human_pos[i].second--;
                    else if (dir == 'R') new_human_pos[i].second++;
                }
            } else {
                // Wall-building phase
                if (tasks[i].empty()) {
                    actions[i] = '.';
                    continue;
                }
                Task task = tasks[i].front();
                if (task.type == MOVE) {
                    if (human_positions[i] == Pos(task.x, task.y)) {
                        // reached, pop task and do nothing this turn
                        tasks[i].erase(tasks[i].begin());
                        actions[i] = '.';
                    } else {
                        char dir = get_move_direction(human_positions[i], {task.x, task.y}, planned_walls);
                        actions[i] = dir;
                        if (dir == 'U') new_human_pos[i].first--;
                        else if (dir == 'D') new_human_pos[i].first++;
                        else if (dir == 'L') new_human_pos[i].second--;
                        else if (dir == 'R') new_human_pos[i].second++;
                    }
                } else { // PLACE
                    int wx = task.x, wy = task.y;
                    int hx = human_positions[i].first, hy = human_positions[i].second;
                    bool can_place = true;

                    // Check adjacency
                    if (!( (abs(hx-wx)==1 && hy==wy) || (abs(hy-wy)==1 && hx==wx) )) {
                        can_place = false;
                    }
                    // Check no pet/human on wall square
                    if (can_place) {
                        for (auto& pet : pet_positions) {
                            if (pet.first == wx && pet.second == wy) {
                                can_place = false; break;
                            }
                        }
                        for (int j = 0; j < M; ++j) {
                            if (j == i) continue;
                            if (human_positions[j].first == wx && human_positions[j].second == wy) {
                                can_place = false; break;
                            }
                        }
                    }
                    // Check no pet adjacent to wall square
                    if (can_place) {
                        for (auto& pet : pet_positions) {
                            if (abs(pet.first - wx) + abs(pet.second - wy) == 1) {
                                can_place = false; break;
                            }
                        }
                    }
                    // If already impassable, treat as success
                    if (grid_impassable[wx][wy]) {
                        can_place = true;
                    }

                    if (can_place) {
                        // Determine direction
                        char dir;
                        if (hx == wx-1 && hy == wy) dir = 'd';
                        else if (hx == wx+1 && hy == wy) dir = 'u';
                        else if (hy == wy-1 && hx == wx) dir = 'r';
                        else if (hy == wy+1 && hx == wx) dir = 'l';
                        else dir = '.';
                        actions[i] = dir;
                        if (!grid_impassable[wx][wy]) {
                            planned_walls.push_back({wx, wy});
                        }
                        tasks[i].erase(tasks[i].begin());
                    } else {
                        actions[i] = '.';
                    }
                }
            }
        }

        // Output actions
        cout << string(actions.begin(), actions.end()) << endl;

        // Update human positions
        human_positions = new_human_pos;

        // Update grid with newly placed walls
        for (auto& w : planned_walls) {
            grid_impassable[w.first][w.second] = true;
        }

        // Read pet movements
        string line;
        getline(cin, line);
        stringstream ss(line);
        vector<string> pet_moves(N);
        for (int i = 0; i < N; ++i) {
            if (!(ss >> pet_moves[i])) break;
        }
        for (int i = 0; i < N; ++i) {
            int cx = pet_positions[i].first, cy = pet_positions[i].second;
            for (char c : pet_moves[i]) {
                if (c == 'U') cx--;
                else if (c == 'D') cx++;
                else if (c == 'L') cy--;
                else if (c == 'R') cy++;
                // '.' does nothing
            }
            pet_positions[i] = {cx, cy};
        }

        // Check phase transition
        if (phase == 0) {
            bool all_gather = true;
            for (int i = 0; i < M; ++i) {
                if (human_positions[i] != gather_point) {
                    all_gather = false;
                    break;
                }
            }
            if (all_gather) {
                phase = 1;
                assign_tasks();
            }
        }
    }

    return 0;
}