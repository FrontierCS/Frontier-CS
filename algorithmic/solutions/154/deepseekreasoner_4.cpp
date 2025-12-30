#include <iostream>
#include <vector>
#include <set>
#include <string>
#include <cstdlib>
#include <algorithm>
#include <cctype>

using namespace std;

struct Task {
    int wx, wy; // wall square coordinates
    int bx, by; // base square coordinates (human stands here to block)
};

// directions for movement
const int dx[4] = {-1, 1, 0, 0};
const int dy[4] = {0, 0, -1, 1};
const char dir_char[4] = {'U', 'D', 'L', 'R'};

// check if a square is inside the target rectangle
inline bool inside_rectangle(int x, int y, int r, int c) {
    return x >= 1 && x <= r && y >= 1 && y <= c;
}

// check if a square contains any pet from the given list
bool no_pet_at(int x, int y, const vector<pair<int,int>>& pets) {
    for (const auto& p : pets)
        if (p.first == x && p.second == y)
            return false;
    return true;
}

// check if any pet is adjacent to (x,y)
bool no_pet_adjacent(int x, int y, const vector<pair<int,int>>& pets) {
    for (const auto& p : pets)
        if (abs(p.first - x) + abs(p.second - y) == 1)
            return false;
    return true;
}

// check if any human other than 'exclude' is at (x,y)
bool no_human_at(int x, int y, const vector<pair<int,int>>& humans, int exclude) {
    for (int i = 0; i < (int)humans.size(); ++i)
        if (i != exclude && humans[i].first == x && humans[i].second == y)
            return false;
    return true;
}

// determine if it is safe to block square (wx,wy) at this turn
bool safe_to_block(int wx, int wy,
                   const vector<pair<int,int>>& pets,
                   const vector<pair<int,int>>& humans,
                   int exclude_human) {
    if (!no_pet_at(wx, wy, pets)) return false;
    if (!no_human_at(wx, wy, humans, exclude_human)) return false;
    if (!no_pet_adjacent(wx, wy, pets)) return false;
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // read input
    int N;
    cin >> N;
    vector<pair<int,int>> pets(N);
    vector<int> pet_type(N);
    for (int i = 0; i < N; ++i) {
        cin >> pets[i].first >> pets[i].second >> pet_type[i];
    }
    int M;
    cin >> M;
    vector<pair<int,int>> humans(M);
    for (int i = 0; i < M; ++i) {
        cin >> humans[i].first >> humans[i].second;
    }

    // ------------------------------------------------------------------
    // Step 1: choose target rectangle anchored at (1,1)
    int r = 1, c = 1;
    bool found = false;
    int best_area = 0;
    // try all rectangles with r<=29, c<=29 (because walls are at r+1 and c+1)
    for (int rr = 29; rr >= 1; --rr) {
        for (int cc = 29; cc >= 1; --cc) {
            bool ok = true;
            for (const auto& pet : pets) {
                int x = pet.first, y = pet.second;
                if (x <= rr && y <= cc) { ok = false; break; }
                if (x == rr+1 && y <= cc) { ok = false; break; }
                if (x <= rr && y == cc+1) { ok = false; break; }
            }
            if (ok) {
                int area = rr * cc;
                if (area > best_area) {
                    best_area = area;
                    r = rr;
                    c = cc;
                    found = true;
                }
            }
        }
    }
    if (!found) {
        // fallback: if no perfect rectangle, choose a reasonable size
        r = 15;
        c = 15;
    }
    // ------------------------------------------------------------------
    // Step 2: create list of wall-building tasks (except the entrance)
    vector<Task> tasks;
    bool unbuilt_wall[31][31] = {false};   // squares that are planned to become walls
    bool grid_wall[31][31] = {false};      // squares already impassable

    // horizontal walls: (r+1, y) for y = 1..c-1  (skip y=c as entrance)
    for (int y = 1; y <= c; ++y) {
        if (y == c) continue; // entrance will be handled later
        tasks.push_back({r+1, y, r, y});
        unbuilt_wall[r+1][y] = true;
    }
    // vertical walls: (x, c+1) for x = 1..r
    for (int x = 1; x <= r; ++x) {
        tasks.push_back({x, c+1, x, c});
        unbuilt_wall[x][c+1] = true;
    }

    // entrance task (will be added after all humans are inside)
    Task entrance_task = {r+1, c, r, c};
    bool entrance_assigned = false;

    // ------------------------------------------------------------------
    // Step 3: assign tasks to humans
    vector<int> human_tasks[10]; // each human has a list of task indices
    int total_tasks = tasks.size();
    int tasks_per_human = total_tasks / M;
    int extra = total_tasks % M;
    int idx = 0;
    for (int i = 0; i < M; ++i) {
        int cnt = tasks_per_human + (i < extra ? 1 : 0);
        for (int j = 0; j < cnt; ++j) {
            human_tasks[i].push_back(idx);
            ++idx;
        }
    }

    // task completion status
    vector<bool> task_done(total_tasks, false);
    // current task index for each human (points to first undone task)
    int human_task_idx[10] = {0};

    // ------------------------------------------------------------------
    // Main loop (300 turns)
    for (int turn = 0; turn < 300; ++turn) {
        // check if all humans are inside the rectangle
        bool all_inside = true;
        for (int i = 0; i < M; ++i) {
            if (!inside_rectangle(humans[i].first, humans[i].second, r, c)) {
                all_inside = false;
                break;
            }
        }
        // if all inside and entrance not yet assigned, add the entrance task
        if (all_inside && !entrance_assigned) {
            tasks.push_back(entrance_task);
            int tid = tasks.size() - 1;
            task_done.push_back(false);
            unbuilt_wall[entrance_task.wx][entrance_task.wy] = true;
            // assign to human 0 (could be any)
            human_tasks[0].push_back(tid);
            entrance_assigned = true;
            total_tasks++;
        }

        // copy current positions for safety checks
        vector<pair<int,int>> pet_start = pets;
        vector<pair<int,int>> human_start = humans;

        // decide actions for this turn
        vector<char> actions(M, '.');
        set<pair<int,int>> blocked_this_turn; // squares that will become walls this turn

        // First pass: assign blocking actions to humans that are ready
        for (int i = 0; i < M; ++i) {
            bool inside = inside_rectangle(humans[i].first, humans[i].second, r, c);
            if (!inside) continue; // only working humans can block

            // find current undone task for this human
            int tid = -1;
            while (human_task_idx[i] < (int)human_tasks[i].size()) {
                int t = human_tasks[i][human_task_idx[i]];
                if (!task_done[t]) {
                    tid = t;
                    break;
                }
                ++human_task_idx[i];
            }
            if (tid == -1) continue; // no pending task

            Task& task = tasks[tid];
            // check if human is standing on the base square
            if (humans[i].first == task.bx && humans[i].second == task.by) {
                // check if the wall square is already a wall
                if (grid_wall[task.wx][task.wy]) {
                    task_done[tid] = true;
                    continue;
                }
                // check safety conditions
                if (safe_to_block(task.wx, task.wy, pet_start, human_start, i)) {
                    char dir = '.';
                    if (task.wx == task.bx + 1) dir = 'd';
                    else if (task.wx == task.bx - 1) dir = 'u';
                    else if (task.wy == task.by + 1) dir = 'r';
                    else if (task.wy == task.by - 1) dir = 'l';
                    if (dir != '.') {
                        actions[i] = dir;
                        blocked_this_turn.insert({task.wx, task.wy});
                    }
                }
            }
        }

        // Second pass: assign movement actions to remaining humans
        for (int i = 0; i < M; ++i) {
            if (actions[i] != '.') continue; // already assigned

            bool inside = inside_rectangle(humans[i].first, humans[i].second, r, c);
            pair<int,int> target;

            if (!inside) {
                // entering human: target is inside the rectangle (e.g., bottom-right interior)
                target = {r, c};
            } else {
                // working human: target is the base of its current task
                int tid = -1;
                int temp_idx = human_task_idx[i];
                while (temp_idx < (int)human_tasks[i].size()) {
                    int t = human_tasks[i][temp_idx];
                    if (!task_done[t]) {
                        tid = t;
                        break;
                    }
                    ++temp_idx;
                }
                if (tid == -1) {
                    // no task, stay idle
                    continue;
                }
                Task& task = tasks[tid];
                target = {task.bx, task.by};
            }

            // greedy move towards target, avoiding obstacles and squares that will be blocked
            int cx = humans[i].first, cy = humans[i].second;
            int best_dir = -1;
            int best_score = 1e9;
            for (int d = 0; d < 4; ++d) {
                int nx = cx + dx[d];
                int ny = cy + dy[d];
                if (nx < 1 || nx > 30 || ny < 1 || ny > 30) continue;
                if (grid_wall[nx][ny]) continue;
                if (blocked_this_turn.count({nx, ny})) continue;

                int dist = abs(nx - target.first) + abs(ny - target.second);
                // penalty for stepping on an unbuilt wall square (we want to avoid that)
                if (unbuilt_wall[nx][ny]) dist += 1000;

                if (dist < best_score) {
                    best_score = dist;
                    best_dir = d;
                }
            }
            if (best_dir != -1) {
                actions[i] = toupper(dir_char[best_dir]); // movement actions are uppercase
            }
        }

        // output actions for this turn
        cout << string(actions.begin(), actions.end()) << endl;

        // ------------------------------------------------------------------
        // Update human positions and wall state based on actions
        for (int i = 0; i < M; ++i) {
            char a = actions[i];
            int& hx = humans[i].first;
            int& hy = humans[i].second;
            if (a == 'U') hx--;
            else if (a == 'D') hx++;
            else if (a == 'L') hy--;
            else if (a == 'R') hy++;
            else if (islower(a)) { // blocking action
                int wx, wy;
                if (a == 'u') { wx = hx - 1; wy = hy; }
                else if (a == 'd') { wx = hx + 1; wy = hy; }
                else if (a == 'l') { wx = hx; wy = hy - 1; }
                else if (a == 'r') { wx = hx; wy = hy + 1; }
                else continue;

                // mark the square as impassable
                grid_wall[wx][wy] = true;
                unbuilt_wall[wx][wy] = false;

                // mark the corresponding task as done
                for (int tid : human_tasks[i]) {
                    if (tid < (int)tasks.size() && tasks[tid].wx == wx && tasks[tid].wy == wy) {
                        task_done[tid] = true;
                        break;
                    }
                }
            }
        }

        // ------------------------------------------------------------------
        // Read pet movements for this turn
        vector<string> pet_moves(N);
        for (int i = 0; i < N; ++i) {
            cin >> pet_moves[i];
        }
        // update pet positions according to the received moves
        for (int i = 0; i < N; ++i) {
            for (char ch : pet_moves[i]) {
                if (ch == 'U') pets[i].first--;
                else if (ch == 'D') pets[i].first++;
                else if (ch == 'L') pets[i].second--;
                else if (ch == 'R') pets[i].second++;
                // '.' does nothing
            }
        }
    }

    return 0;
}