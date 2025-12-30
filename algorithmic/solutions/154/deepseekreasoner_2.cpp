#include <iostream>
#include <vector>
#include <algorithm>
#include <queue>
#include <cstring>
#include <string>
#include <utility>
#include <cmath>

using namespace std;

const int GRID = 30;
const int MAX_TURNS = 300;

struct Pet {
    int x, y, type;
};
vector<Pet> pets;

struct Human {
    int x, y;
    int state;          // 0: moving to regular builder, 1: at regular builder,
                        // 2: moving to safe spot, 3: at safe spot,
                        // 4: moving to gap builder, 5: at gap builder
    int cur_task_idx;   // index in regular_tasks
    vector<int> tasks;  // regular task indices
    int gap_task_idx;   // index in gap_tasks, -1 if none
    int target_x, target_y;
};
vector<Human> humans;

bool blocked[GRID+2][GRID+2]; // 1-indexed, true if impassable

struct Task {
    int wx, wy; // wall square to block
    int bx, by; // builder position (human stands here)
    char dir;   // block direction (u,d,l,r)
    bool done;
};
vector<Task> regular_tasks;
vector<Task> gap_tasks;
vector<bool> gap_assigned;
vector<bool> gap_done;

int outer_x1, outer_y1, outer_x2, outer_y2;
int gap_start, gap_end;
int safe_x, safe_y;

bool inside(int x, int y) {
    return x >= 1 && x <= GRID && y >= 1 && y <= GRID;
}

int manhattan(int x1, int y1, int x2, int y2) {
    return abs(x1 - x2) + abs(y1 - y2);
}

// BFS to find next move direction from (sx,sy) to (tx,ty)
char get_move(int sx, int sy, int tx, int ty) {
    if (sx == tx && sy == ty) return '.';
    static int dx[4] = {-1, 1, 0, 0};
    static char dir[4] = {'U', 'D', 'L', 'R'};
    queue<pair<int,int>> q;
    bool visited[GRID+2][GRID+2] = {false};
    pair<int,int> prev[GRID+2][GRID+2];
    q.push({sx, sy});
    visited[sx][sy] = true;
    while (!q.empty()) {
        auto [x, y] = q.front(); q.pop();
        for (int d = 0; d < 4; ++d) {
            int nx = x + dx[d], ny = y + dy[d];
            if (inside(nx, ny) && !blocked[nx][ny] && !visited[nx][ny]) {
                visited[nx][ny] = true;
                prev[nx][ny] = {x, y};
                if (nx == tx && ny == ty) {
                    // backtrack to first step
                    while (!(prev[nx][ny].first == sx && prev[nx][ny].second == sy)) {
                        int px = prev[nx][ny].first, py = prev[nx][ny].second;
                        nx = px; ny = py;
                    }
                    for (int d2 = 0; d2 < 4; ++d2)
                        if (sx + dx[d2] == nx && sy + dy[d2] == ny)
                            return dir[d2];
                    return '.';
                }
                q.push({nx, ny});
            }
        }
    }
    return '.'; // no path found, stay
}

// Check if any pet is adjacent to (x,y) at start of turn
bool adjacent_to_pet(int x, int y, const vector<Pet>& pets) {
    for (const auto& pet : pets)
        if (abs(pet.x - x) + abs(pet.y - y) == 1)
            return true;
    return false;
}

// Check if square (x,y) contains any pet or human at start of turn
bool occupied(int x, int y, const vector<Pet>& pets, const vector<Human>& humans, int self_h) {
    for (const auto& pet : pets)
        if (pet.x == x && pet.y == y) return true;
    for (int h = 0; h < (int)humans.size(); ++h)
        if (h != self_h && humans[h].x == x && humans[h].y == y)
            return true;
    return false;
}

int main() {
    // ----- Input -----
    int N;
    cin >> N;
    pets.resize(N);
    for (int i = 0; i < N; ++i)
        cin >> pets[i].x >> pets[i].y >> pets[i].type;
    int M;
    cin >> M;
    humans.resize(M);
    for (int i = 0; i < M; ++i) {
        cin >> humans[i].x >> humans[i].y;
        humans[i].state = 0;
        humans[i].cur_task_idx = 0;
        humans[i].gap_task_idx = -1;
    }

    memset(blocked, 0, sizeof(blocked));

    // ----- Choose outer rectangle -----
    int best_area = -1, best_pet = 100;
    int best_x1, best_y1, best_x2, best_y2;
    for (int x1 = 1; x1 <= GRID - 2; ++x1)
        for (int x2 = x1 + 2; x2 <= GRID; ++x2)
            for (int y1 = 1; y1 <= GRID - 2; ++y1)
                for (int y2 = y1 + 2; y2 <= GRID; ++y2) {
                    int ix1 = x1 + 1, ix2 = x2 - 1;
                    int iy1 = y1 + 1, iy2 = y2 - 1;
                    int pet_cnt = 0;
                    for (const auto& pet : pets)
                        if (pet.x >= ix1 && pet.x <= ix2 && pet.y >= iy1 && pet.y <= iy2)
                            ++pet_cnt;
                    int area = (ix2 - ix1 + 1) * (iy2 - iy1 + 1);
                    if (pet_cnt == 0) {
                        if (area > best_area) {
                            best_area = area;
                            best_x1 = x1; best_y1 = y1; best_x2 = x2; best_y2 = y2;
                        }
                    } else if (best_area == -1) {
                        if (pet_cnt < best_pet || (pet_cnt == best_pet && area > best_area)) {
                            best_pet = pet_cnt;
                            best_area = area;
                            best_x1 = x1; best_y1 = y1; best_x2 = x2; best_y2 = y2;
                        }
                    }
                }
    outer_x1 = best_x1; outer_y1 = best_y1;
    outer_x2 = best_x2; outer_y2 = best_y2;

    int interior_x1 = outer_x1 + 1, interior_x2 = outer_x2 - 1;
    int interior_y1 = outer_y1 + 1, interior_y2 = outer_y2 - 1;
    safe_x = (interior_x1 + interior_x2) / 2;
    safe_y = (interior_y1 + interior_y2) / 2;

    // ----- Define gap on bottom side -----
    int gap_len = 3;
    int mid_y = (outer_y1 + outer_y2) / 2;
    gap_start = mid_y - gap_len / 2;
    gap_end = gap_start + gap_len - 1;
    if (gap_start < outer_y1) gap_start = outer_y1;
    if (gap_end > outer_y2) gap_end = outer_y2;

    // ----- Generate regular tasks (excluding gap) -----
    auto add_task = [&](int wx, int wy, int bx, int by, char dir) {
        regular_tasks.push_back({wx, wy, bx, by, dir, false});
    };
    // top side
    for (int y = outer_y1; y <= outer_y2; ++y)
        add_task(outer_x1, y, outer_x1 + 1, y, 'u');
    // right side
    for (int x = outer_x1 + 1; x <= outer_x2; ++x)
        add_task(x, outer_y2, x, outer_y2 - 1, 'r');
    // bottom side (skip gap)
    for (int y = outer_y2 - 1; y >= outer_y1; --y) {
        if (y >= gap_start && y <= gap_end) {
            // gap task
            gap_tasks.push_back({outer_x2, y, outer_x2 - 1, y, 'd', false});
        } else {
            add_task(outer_x2, y, outer_x2 - 1, y, 'd');
        }
    }
    // left side
    for (int x = outer_x2 - 1; x >= outer_x1 + 1; --x)
        add_task(x, outer_y1, x, outer_y1 + 1, 'l');

    gap_assigned.assign(gap_tasks.size(), false);
    gap_done.assign(gap_tasks.size(), false);

    // ----- Assign regular tasks to humans -----
    int T = regular_tasks.size();
    vector<int> pref(M, 0);
    for (int h = 0; h < M; ++h) {
        int min_d = 1e9, best_i = 0;
        for (int i = 0; i < T; ++i) {
            int d = manhattan(humans[h].x, humans[h].y,
                              regular_tasks[i].bx, regular_tasks[i].by);
            if (d < min_d) { min_d = d; best_i = i; }
        }
        pref[h] = best_i;
    }
    vector<int> order(M);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(),
         [&](int a, int b) { return pref[a] < pref[b]; });

    vector<vector<int>> human_tasks(M);
    int per = T / M, extra = T % M;
    int idx = 0;
    for (int j = 0; j < M; ++j) {
        int h = order[j];
        int start = idx, end = start + per + (j < extra ? 1 : 0);
        idx = end;
        for (int i = start; i < end; ++i)
            human_tasks[h].push_back(i);
    }

    for (int h = 0; h < M; ++h) {
        humans[h].tasks = human_tasks[h];
        if (!humans[h].tasks.empty()) {
            int first = humans[h].tasks[0];
            humans[h].target_x = regular_tasks[first].bx;
            humans[h].target_y = regular_tasks[first].by;
            humans[h].state = 0;
        } else {
            humans[h].target_x = safe_x;
            humans[h].target_y = safe_y;
            humans[h].state = 2;
        }
        humans[h].cur_task_idx = 0;
    }

    // ----- Main game loop -----
    bool gap_started = false;
    for (int turn = 1; turn <= MAX_TURNS; ++turn) {
        // snapshot of pet positions at start of turn
        vector<Pet> pets_start = pets;

        // decide actions for each human
        vector<char> actions(M, '.');

        // if it's time to start closing the gap
        if (!gap_started && (turn > 280 || all_of(regular_tasks.begin(), regular_tasks.end(),
                                                  [](const Task& t) { return t.done; }))) {
            gap_started = true;
        }

        // assign gap tasks to idle humans
        if (gap_started) {
            for (int h = 0; h < M; ++h) {
                if ((humans[h].state == 2 || humans[h].state == 3) && humans[h].gap_task_idx == -1) {
                    for (int g = 0; g < (int)gap_tasks.size(); ++g) {
                        if (!gap_assigned[g] && !gap_done[g]) {
                            gap_assigned[g] = true;
                            humans[h].gap_task_idx = g;
                            humans[h].target_x = gap_tasks[g].bx;
                            humans[h].target_y = gap_tasks[g].by;
                            humans[h].state = 4; // moving to gap builder
                            break;
                        }
                    }
                }
            }
        }

        for (int h = 0; h < M; ++h) {
            Human& hu = humans[h];
            if (hu.state == 0) { // moving to regular builder
                if (hu.x == hu.target_x && hu.y == hu.target_y) {
                    hu.state = 1; // arrived at builder
                } else {
                    actions[h] = get_move(hu.x, hu.y, hu.target_x, hu.target_y);
                }
            }
            if (hu.state == 1) { // at regular builder, try to block
                if (hu.cur_task_idx >= (int)hu.tasks.size()) {
                    // no more regular tasks
                    hu.target_x = safe_x;
                    hu.target_y = safe_y;
                    hu.state = 2;
                    // will move next turn
                    continue;
                }
                int tid = hu.tasks[hu.cur_task_idx];
                Task& t = regular_tasks[tid];
                if (t.done) { // already blocked by someone else
                    hu.cur_task_idx++;
                    if (hu.cur_task_idx < (int)hu.tasks.size()) {
                        int next = hu.tasks[hu.cur_task_idx];
                        hu.target_x = regular_tasks[next].bx;
                        hu.target_y = regular_tasks[next].by;
                        hu.state = 0;
                    } else {
                        hu.target_x = safe_x;
                        hu.target_y = safe_y;
                        hu.state = 2;
                    }
                    actions[h] = '.';
                } else {
                    // check legality
                    if (!adjacent_to_pet(t.wx, t.wy, pets_start) &&
                        !occupied(t.wx, t.wy, pets_start, humans, h)) {
                        actions[h] = t.dir;
                        t.done = true;
                        blocked[t.wx][t.wy] = true;
                        hu.cur_task_idx++;
                        if (hu.cur_task_idx < (int)hu.tasks.size()) {
                            int next = hu.tasks[hu.cur_task_idx];
                            hu.target_x = regular_tasks[next].bx;
                            hu.target_y = regular_tasks[next].by;
                            hu.state = 0;
                        } else {
                            hu.target_x = safe_x;
                            hu.target_y = safe_y;
                            hu.state = 2;
                        }
                    } else {
                        actions[h] = '.'; // cannot block now
                    }
                }
            }
            if (hu.state == 2) { // moving to safe spot
                if (hu.x == hu.target_x && hu.y == hu.target_y) {
                    hu.state = 3;
                    actions[h] = '.';
                } else {
                    actions[h] = get_move(hu.x, hu.y, hu.target_x, hu.target_y);
                }
            }
            if (hu.state == 3) { // at safe spot
                actions[h] = '.';
            }
            if (hu.state == 4) { // moving to gap builder
                if (hu.x == hu.target_x && hu.y == hu.target_y) {
                    hu.state = 5;
                } else {
                    actions[h] = get_move(hu.x, hu.y, hu.target_x, hu.target_y);
                }
            }
            if (hu.state == 5) { // at gap builder, try to block gap
                int gid = hu.gap_task_idx;
                if (gid == -1 || gap_done[gid]) {
                    hu.gap_task_idx = -1;
                    hu.state = 2;
                    hu.target_x = safe_x;
                    hu.target_y = safe_y;
                    actions[h] = '.';
                    continue;
                }
                Task& t = gap_tasks[gid];
                if (!adjacent_to_pet(t.wx, t.wy, pets_start) &&
                    !occupied(t.wx, t.wy, pets_start, humans, h)) {
                    actions[h] = t.dir;
                    gap_done[gid] = true;
                    blocked[t.wx][t.wy] = true;
                    hu.gap_task_idx = -1;
                    hu.state = 2;
                    hu.target_x = safe_x;
                    hu.target_y = safe_y;
                } else {
                    actions[h] = '.';
                }
            }
        }

        // apply human movements
        for (int h = 0; h < M; ++h) {
            char act = actions[h];
            if (act == 'U') humans[h].x--;
            else if (act == 'D') humans[h].x++;
            else if (act == 'L') humans[h].y--;
            else if (act == 'R') humans[h].y++;
        }

        // output actions
        string out(M, '.');
        for (int h = 0; h < M; ++h) out[h] = actions[h];
        cout << out << endl;
        cout.flush();

        // read pet movements for next turn
        if (turn < MAX_TURNS) {
            vector<string> pet_moves(N);
            for (int i = 0; i < N; ++i) cin >> pet_moves[i];
            for (int i = 0; i < N; ++i) {
                int cx = pets[i].x, cy = pets[i].y;
                for (char c : pet_moves[i]) {
                    if (c == 'U') cx--;
                    else if (c == 'D') cx++;
                    else if (c == 'L') cy--;
                    else if (c == 'R') cy++;
                }
                pets[i].x = cx;
                pets[i].y = cy;
            }
        }
    }
    return 0;
}