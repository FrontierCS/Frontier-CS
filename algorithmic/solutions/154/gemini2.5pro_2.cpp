#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <deque>
#include <algorithm>
#include <cmath>
#include <map>
#include <set>

using namespace std;

const int GRID_SIZE = 30;
const int TURN_COUNT = 300;

int N, M;

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

int dist_manhattan(Point p1, Point p2) {
    return abs(p1.r - p2.r) + abs(p1.c - p2.c);
}

struct Pet {
    Point pos;
    int type;
};

struct Human {
    Point pos;
};

vector<Pet> pets;
vector<Human> humans;
bool is_impassable[GRID_SIZE + 2][GRID_SIZE + 2];

int dr[] = {-1, 1, 0, 0};
int dc[] = {0, 0, -1, 1};

struct Task {
    Point wall_pos;
    Point station_pos;
};
vector<deque<Task>> human_tasks;
vector<int> stuck_counters;

Point bfs_next_step(Point start, Point end, const vector<vector<bool>>& current_impassable) {
    if (start == end) return start;

    queue<Point> q;
    q.push(start);
    map<Point, Point> parent;
    parent[start] = {-1, -1};

    Point path_end = {-1, -1};

    while (!q.empty()) {
        Point curr = q.front();
        q.pop();

        if (curr == end) {
            path_end = curr;
            break;
        }

        for (int i = 0; i < 4; ++i) {
            Point next = {curr.r + dr[i], curr.c + dc[i]};
            if (next.r >= 1 && next.r <= GRID_SIZE && next.c >= 1 && next.c <= GRID_SIZE && !current_impassable[next.r][next.c] && !parent.count(next)) {
                parent[next] = curr;
                q.push(next);
            }
        }
    }
    
    if (path_end.r == -1) return start;

    Point p = path_end;
    while (parent.count(p) && parent[p] != start && parent[p].r != -1) {
        p = parent[p];
    }
    return p;
}

void plan_enclosure() {
    bool has_pet[GRID_SIZE + 1][GRID_SIZE + 1] = {};
    for (const auto& pet : pets) {
        has_pet[pet.pos.r][pet.pos.c] = true;
    }

    int max_area = 0;
    int best_r1 = -1, best_c1 = -1, best_r2 = -1, best_c2 = -1;

    vector<vector<int>> heights(GRID_SIZE + 1, vector<int>(GRID_SIZE + 1, 0));
    for (int c = 1; c <= GRID_SIZE; ++c) {
        for (int r = 1; r <= GRID_SIZE; ++r) {
            if (!has_pet[r][c]) {
                heights[r][c] = (r > 1 ? heights[r-1][c] : 0) + 1;
            }
        }
    }
    
    for (int r = 1; r <= GRID_SIZE; ++r) {
        vector<int> s;
        vector<int> p_heights(GRID_SIZE + 2, 0);
        for (int c = 1; c <= GRID_SIZE; ++c) p_heights[c] = heights[r][c];
        
        for (int c = 1; c <= GRID_SIZE + 1; ++c) {
            while (!s.empty() && p_heights[s.back()] >= p_heights[c]) {
                int h = p_heights[s.back()];
                s.pop_back();
                int w = s.empty() ? c - 1 : c - s.back() - 1;
                if (h * w > max_area) {
                    max_area = h * w;
                    best_r1 = r - h + 1;
                    best_c1 = s.empty() ? 1 : s.back() + 1;
                    best_r2 = r;
                    best_c2 = c - 1;
                }
            }
            s.push_back(c);
        }
    }
    
    if (max_area == 0) {
        for(int r = 1; r <= GRID_SIZE; ++r) for(int c=1; c<=GRID_SIZE; ++c) {
            bool occupied = false;
            for(const auto& p : pets) if(p.pos.r==r && p.pos.c==c) occupied = true;
            for(const auto& h : humans) if(h.pos.r==r && h.pos.c==c) occupied = true;
            if(!occupied) {
                best_r1=r; best_c1=c; best_r2=r; best_c2=c;
                goto found_empty;
            }
        }
        best_r1 = humans[0].pos.r; best_c1 = humans[0].pos.c; best_r2 = humans[0].pos.r; best_c2 = humans[0].pos.c;
    }
    found_empty:;
    
    vector<Point> perimeter_stations;
    if (best_r1 == best_r2 && best_c1 == best_c2) {
        perimeter_stations.push_back({best_r1, best_c1});
    } else {
        for(int c=best_c1; c<=best_c2; ++c) perimeter_stations.push_back({best_r1, c});
        for(int r=best_r1+1; r<=best_r2; ++r) perimeter_stations.push_back({r, best_c2});
        if (best_r1 != best_r2) for(int c=best_c2-1; c>=best_c1; --c) perimeter_stations.push_back({best_r2, c});
        if (best_c1 != best_c2) for(int r=best_r2-1; r>best_r1; --r) perimeter_stations.push_back({r, best_c1});
    }

    set<Point> wall_set;
    vector<Task> all_tasks;
    for(const auto& p : perimeter_stations) {
        for (int i=0; i<4; ++i) {
            Point wall = {p.r + dr[i], p.c + dc[i]};
            if (wall.r >= 1 && wall.r <= GRID_SIZE && wall.c >= 1 && wall.c <= GRID_SIZE) {
                 if (wall.r < best_r1 || wall.r > best_r2 || wall.c < best_c1 || wall.c > best_c2) {
                     if (wall_set.find(wall) == wall_set.end()) {
                         all_tasks.push_back({wall, p});
                         wall_set.insert(wall);
                     }
                 }
            }
        }
    }
    
    human_tasks.assign(M, deque<Task>());
    if (all_tasks.empty()) return;

    vector<bool> task_assigned(all_tasks.size(), false);
    for(int i=0; i<M; ++i) {
        for(size_t k=0; k<all_tasks.size(); ++k) {
            if (human_tasks[i].size() >= (all_tasks.size() + M -1)/M) break;
            
            int best_task_idx = -1;
            int min_dist = 1e9;
            Point last_pos = humans[i].pos;
            if (!human_tasks[i].empty()) last_pos = human_tasks[i].back().station_pos;

            for(size_t j=0; j<all_tasks.size(); ++j) {
                if (!task_assigned[j]) {
                    int d = dist_manhattan(last_pos, all_tasks[j].station_pos);
                    if (d < min_dist) {
                        min_dist = d;
                        best_task_idx = j;
                    }
                }
            }
            if (best_task_idx != -1) {
                human_tasks[i].push_back(all_tasks[best_task_idx]);
                task_assigned[best_task_idx] = true;
            }
        }
    }
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> N;
    pets.resize(N);
    for (int i = 0; i < N; ++i) {
        cin >> pets[i].pos.r >> pets[i].pos.c >> pets[i].type;
    }

    cin >> M;
    humans.resize(M);
    for (int i = 0; i < M; ++i) {
        cin >> humans[i].pos.r >> humans[i].pos.c;
    }

    plan_enclosure();
    stuck_counters.assign(M, 0);

    for (int t = 0; t < TURN_COUNT; ++t) {
        string actions = "";
        set<Point> future_blocked_set;

        for (int i = 0; i < M; ++i) {
            while (!human_tasks[i].empty() && is_impassable[human_tasks[i].front().wall_pos.r][human_tasks[i].front().wall_pos.c]) {
                human_tasks[i].pop_front();
                stuck_counters[i] = 0;
            }

            if (human_tasks[i].empty()) {
                actions += '.';
                continue;
            }

            Task current_task = human_tasks[i].front();
            Point station = current_task.station_pos;
            Point wall = current_task.wall_pos;

            if (humans[i].pos == station) {
                bool can_build = true;
                for (int pi = 0; pi < N; ++pi) {
                    if (max(abs(pets[pi].pos.r - wall.r), abs(pets[pi].pos.c - wall.c)) <= 1) {
                        can_build = false;
                        break;
                    }
                }
                if (can_build) {
                    for (int hi = 0; hi < M; ++hi) {
                        if (humans[hi].pos.r == wall.r && humans[hi].pos.c == wall.c) {
                            can_build = false;
                            break;
                        }
                    }
                }

                if (can_build) {
                    char action = '.';
                    if (wall.r == station.r - 1) action = 'u';
                    else if (wall.r == station.r + 1) action = 'd';
                    else if (wall.c == station.c - 1) action = 'l';
                    else if (wall.c == station.c + 1) action = 'r';
                    actions += action;
                    future_blocked_set.insert(wall);
                    human_tasks[i].pop_front();
                    stuck_counters[i] = 0;
                } else {
                    stuck_counters[i]++;
                    if (stuck_counters[i] > 5) {
                        human_tasks[i].push_back(human_tasks[i].front());
                        human_tasks[i].pop_front();
                        stuck_counters[i] = 0;
                    }
                    actions += '.';
                }
            } else {
                vector<vector<bool>> current_impassable(GRID_SIZE + 2, vector<bool>(GRID_SIZE + 2, false));
                for(int r=1; r<=GRID_SIZE; ++r) for(int c=1; c<=GRID_SIZE; ++c) current_impassable[r][c] = is_impassable[r][c];

                Point next_pos = bfs_next_step(humans[i].pos, station, current_impassable);
                char action = '.';
                if (next_pos.r < humans[i].pos.r) action = 'U';
                else if (next_pos.r > humans[i].pos.r) action = 'D';
                else if (next_pos.c < humans[i].pos.c) action = 'L';
                else if (next_pos.c > humans[i].pos.c) action = 'R';
                actions += action;
                stuck_counters[i] = 0;
            }
        }
        cout << actions << endl;

        for (const auto& p : future_blocked_set) {
            is_impassable[p.r][p.c] = true;
        }

        for (int i = 0; i < N; ++i) {
            string pet_move;
            cin >> pet_move;
            if (pet_move != ".") {
                for (char move : pet_move) {
                    if (move == 'U') pets[i].pos.r--;
                    else if (move == 'D') pets[i].pos.r++;
                    else if (move == 'L') pets[i].pos.c--;
                    else if (move == 'R') pets[i].pos.c++;
                }
            }
        }
        for (int i=0; i<M; ++i) {
            if(actions[i] == 'U') humans[i].pos.r--;
            else if(actions[i] == 'D') humans[i].pos.r++;
            else if(actions[i] == 'L') humans[i].pos.c--;
            else if(actions[i] == 'R') humans[i].pos.c++;
        }
    }

    return 0;
}