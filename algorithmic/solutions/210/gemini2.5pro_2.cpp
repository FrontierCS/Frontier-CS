#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <cmath>
#include <algorithm>
#include <map>

using namespace std;

const int MAX_FRAMES = 15000;
const int DIRS[4][2] = {{-1, 0}, {1, 0}, {0, -1}, {0, 1}}; // 0:U, 1:D, 2:L, 3:R
const int INF = 1e9;

struct Point {
    int x, y;
    bool operator==(const Point& other) const { return x == other.x && y == other.y; }
    bool operator!=(const Point& other) const { return !(*this == other); }
    bool operator<(const Point& other) const {
        if (x != other.x) return x < other.x;
        return y < other.y;
    }
};

int n, m;

bool is_valid(int r, int c) {
    return r >= 0 && r < n && c >= 0 && c < m;
}

struct BlueBase {
    int id;
    Point pos;
    long long g, c;
};

struct RedBase {
    int id;
    Point pos;
    int initial_d, d, v;
    bool destroyed;
};

struct Fighter {
    int id;
    Point pos;
    int G, C;
    long long fuel, missiles;
    enum Status { IDLE, MOVING_TO_SUPPLY, RESUPPLYING, MOVING_TO_TARGET, ATTACKING, RETURNING_TO_BASE } status;
    int target_red_base_id;
    int supply_blue_base_id;
    vector<Point> path;
    int idle_frames;
};

vector<string> initial_grid;
vector<string> current_grid;
vector<BlueBase> blue_bases;
vector<RedBase> red_bases;
vector<Fighter> fighters;
vector<vector<int>> blue_base_map;
vector<vector<int>> red_base_map;

// For planning
vector<vector<vector<int>>> planning_dists;

void bfs(Point start, vector<vector<int>>& dist, vector<vector<Point>>& parent, const vector<string>& grid_to_use) {
    dist.assign(n, vector<int>(m, INF));
    parent.assign(n, vector<Point>(m, {-1, -1}));
    
    queue<Point> q;
    q.push(start);
    dist[start.x][start.y] = 0;
    
    while (!q.empty()) {
        Point curr = q.front();
        q.pop();
        
        for (int i = 0; i < 4; ++i) {
            Point next = {curr.x + DIRS[i][0], curr.y + DIRS[i][1]};
            if (is_valid(next.x, next.y) && grid_to_use[next.x][next.y] != '#' && dist[next.x][next.y] == INF) {
                dist[next.x][next.y] = dist[curr.x][curr.y] + 1;
                parent[next.x][next.y] = curr;
                q.push(next);
            }
        }
    }
}

vector<Point> get_path(Point start, Point end, const vector<vector<Point>>& parent) {
    vector<Point> path;
    if (parent[end.x][end.y].x == -1 && start != end) return path;
    Point curr = end;
    while (curr != start) {
        path.push_back(curr);
        curr = parent[curr.x][curr.y];
    }
    reverse(path.begin(), path.end());
    return path;
}

int get_dir(Point from, Point to) {
    if (to.x < from.x) return 0; // Up
    if (to.x > from.x) return 1; // Down
    if (to.y < from.y) return 2; // Left
    if (to.y > from.y) return 3; // Right
    return -1;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n >> m;
    initial_grid.resize(n);
    for (int i = 0; i < n; ++i) cin >> initial_grid[i];
    current_grid = initial_grid;

    blue_base_map.assign(n, vector<int>(m, -1));
    red_base_map.assign(n, vector<int>(m, -1));

    int num_blue_bases;
    cin >> num_blue_bases;
    for (int i = 0; i < num_blue_bases; ++i) {
        BlueBase b;
        b.id = i;
        cin >> b.pos.x >> b.pos.y;
        cin >> b.g >> b.c;
        blue_bases.push_back(b);
        blue_base_map[b.pos.x][b.pos.y] = i;
    }

    int num_red_bases;
    cin >> num_red_bases;
    for (int i = 0; i < num_red_bases; ++i) {
        RedBase r;
        r.id = i;
        cin >> r.pos.x >> r.pos.y;
        cin >> r.initial_d >> r.v;
        r.d = r.initial_d;
        r.destroyed = false;
        red_bases.push_back(r);
        red_base_map[r.pos.x][r.pos.y] = i;
    }

    int k;
    cin >> k;
    for (int i = 0; i < k; ++i) {
        Fighter f;
        f.id = i;
        cin >> f.pos.x >> f.pos.y;
        cin >> f.G >> f.C;
        f.fuel = 0;
        f.missiles = 0;
        f.status = Fighter::IDLE;
        f.target_red_base_id = -1;
        f.supply_blue_base_id = -1;
        f.idle_frames = 0;
        fighters.push_back(f);
    }
    
    planning_dists.resize(blue_bases.size());
    for (size_t i = 0; i < blue_bases.size(); ++i) {
        vector<vector<Point>> parents;
        bfs(blue_bases[i].pos, planning_dists[i], parents, initial_grid);
    }
    
    int total_red_bases = red_bases.size();
    int destroyed_count = 0;

    for (int frame = 0; frame < MAX_FRAMES; ++frame) {
        if (destroyed_count == total_red_bases) break;

        for (auto& f : fighters) {
            if (f.status == Fighter::IDLE) {
                f.idle_frames++;
                int current_base_id = blue_base_map[f.pos.x][f.pos.y];
                if (current_base_id == -1) continue; 

                double best_score = -1.0;
                int best_target_id = -1;

                for (const auto& r : red_bases) {
                    if (r.destroyed) continue;

                    int min_dist_to_adj = INF;
                    for (int i = 0; i < 4; ++i) {
                        Point adj = {r.pos.x + DIRS[i][0], r.pos.y + DIRS[i][1]};
                        if (is_valid(adj.x, adj.y) && initial_grid[adj.x][adj.y] != '#') {
                            min_dist_to_adj = min(min_dist_to_adj, planning_dists[current_base_id][adj.x][adj.y]);
                        }
                    }

                    if (min_dist_to_adj == INF) continue;
                    
                    long long fuel_needed = 2LL * min_dist_to_adj;
                    if (f.G < fuel_needed) continue;

                    if (f.C == 0) continue;

                    long long missiles_to_deliver = min((long long)f.C, (long long)r.d);
                    if (missiles_to_deliver == 0) missiles_to_deliver = f.C;
                    
                    double value_of_sortie = (double)missiles_to_deliver * ((double)r.v / r.initial_d);
                    double time_cost = fuel_needed + 2; 
                    
                    double score = value_of_sortie / time_cost;
                    if (score > best_score) {
                        best_score = score;
                        best_target_id = r.id;
                    }
                }
                
                if (best_target_id != -1) {
                    f.target_red_base_id = best_target_id;
                    f.supply_blue_base_id = current_base_id;
                    f.status = Fighter::RESUPPLYING;
                    f.idle_frames = 0;
                } else if (f.idle_frames > 200) {
                    int best_base_id = -1;
                    int min_dist = INF;
                    for(const auto& b : blue_bases) {
                        if (b.id == current_base_id) continue;
                        int dist = planning_dists[current_base_id][b.pos.x][b.pos.y];
                        if (dist < min_dist && dist != INF) {
                            min_dist = dist;
                            best_base_id = b.id;
                        }
                    }
                    if (best_base_id != -1) {
                        f.supply_blue_base_id = best_base_id;
                        f.status = Fighter::MOVING_TO_SUPPLY;
                        f.idle_frames = 0;
                    }
                }
            }
        }
        
        vector<string> commands;
        for (auto& f : fighters) {
            switch (f.status) {
                case Fighter::IDLE:
                    break;

                case Fighter::MOVING_TO_SUPPLY: {
                    Point dest = blue_bases[f.supply_blue_base_id].pos;
                    if (f.pos == dest) {
                        f.status = Fighter::IDLE;
                        f.path.clear();
                        break;
                    }
                    if (f.path.empty()) {
                        vector<vector<int>> dists;
                        vector<vector<Point>> parents;
                        bfs(dest, dists, parents, current_grid);
                        f.path = get_path(f.pos, dest, parents);
                    }
                    if (!f.path.empty()) {
                        Point next_pos = f.path.front();
                        int dir = get_dir(f.pos, next_pos);
                        if (f.fuel > 0) {
                            commands.push_back("move " + to_string(f.id) + " " + to_string(dir));
                            f.fuel--;
                            f.pos = next_pos;
                            f.path.erase(f.path.begin());
                        }
                    }
                    break;
                }

                case Fighter::RESUPPLYING: {
                    if (red_bases[f.target_red_base_id].destroyed) {
                        f.status = Fighter::IDLE;
                        break;
                    }
                    
                    auto& base = blue_bases[f.supply_blue_base_id];
                    long long fuel_to_load = f.G - f.fuel;
                    if (fuel_to_load > 0 && base.g > 0) {
                        long long amount = min(fuel_to_load, base.g);
                        commands.push_back("fuel " + to_string(f.id) + " " + to_string(amount));
                        f.fuel += amount;
                        base.g -= amount;
                    }
                    
                    long long missiles_to_load = min((long long)f.C, (long long)red_bases[f.target_red_base_id].d) - f.missiles;
                    if(missiles_to_load <= 0 && f.missiles > 0) missiles_to_load = f.C - f.missiles;

                    if (missiles_to_load > 0 && base.c > 0) {
                        long long amount = min(missiles_to_load, base.c);
                        commands.push_back("missile " + to_string(f.id) + " " + to_string(amount));
                        f.missiles += amount;
                        base.c -= amount;
                    }
                    f.status = Fighter::MOVING_TO_TARGET;
                    break;
                }
                
                case Fighter::MOVING_TO_TARGET: {
                    if (red_bases[f.target_red_base_id].destroyed) {
                        f.status = Fighter::RETURNING_TO_BASE;
                        f.path.clear();
                        break;
                    }
                    if (f.path.empty()) {
                        vector<vector<int>> dists;
                        vector<vector<Point>> parents;
                        bfs(blue_bases[f.supply_blue_base_id].pos, dists, parents, current_grid);
                        
                        Point target_pos = red_bases[f.target_red_base_id].pos;
                        Point best_adj = {-1, -1};
                        int min_dist = INF;
                        
                        for (int i = 0; i < 4; ++i) {
                            Point adj = {target_pos.x + DIRS[i][0], target_pos.y + DIRS[i][1]};
                            if (is_valid(adj.x, adj.y) && current_grid[adj.x][adj.y] != '#' && dists[adj.x][adj.y] < min_dist) {
                                min_dist = dists[adj.x][adj.y];
                                best_adj = adj;
                            }
                        }
                        if (best_adj.x != -1) {
                            f.path = get_path(f.pos, best_adj, parents);
                        } else {
                             f.status = Fighter::RETURNING_TO_BASE;
                             f.path.clear();
                             break;
                        }
                    }
                    
                    bool is_adj = false;
                    for (int i = 0; i < 4; ++i) {
                        Point adj = {f.pos.x + DIRS[i][0], f.pos.y + DIRS[i][1]};
                        if (is_valid(adj.x, adj.y) && adj == red_bases[f.target_red_base_id].pos) {
                           is_adj = true; break;
                        }
                    }

                    if (is_adj) {
                        f.status = Fighter::ATTACKING;
                        f.path.clear();
                    } else if (!f.path.empty()) {
                        Point next_pos = f.path.front();
                        int dir = get_dir(f.pos, next_pos);
                        if (f.fuel > 0) {
                            commands.push_back("move " + to_string(f.id) + " " + to_string(dir));
                            f.fuel--;
                            f.pos = next_pos;
                            f.path.erase(f.path.begin());
                        }
                    } else {
                         f.status = Fighter::RETURNING_TO_BASE;
                         f.path.clear();
                    }
                    break;
                }

                case Fighter::ATTACKING: {
                    auto& rbase = red_bases[f.target_red_base_id];
                    if (rbase.destroyed) {
                        f.status = Fighter::RETURNING_TO_BASE;
                        break;
                    }
                    int dir = get_dir(f.pos, rbase.pos);
                    if (dir != -1 && f.missiles > 0) {
                        long long attack_count = min(f.missiles, (long long)rbase.d);
                        if(attack_count <= 0) attack_count = f.missiles;
                        
                        commands.push_back("attack " + to_string(f.id) + " " + to_string(dir) + " " + to_string(attack_count));
                        f.missiles -= attack_count;
                        rbase.d -= attack_count;

                        if (rbase.d <= 0) {
                            rbase.destroyed = true;
                            current_grid[rbase.pos.x][rbase.pos.y] = '.';
                            destroyed_count++;
                        }
                    }
                    f.status = Fighter::RETURNING_TO_BASE;
                    break;
                }
                
                case Fighter::RETURNING_TO_BASE: {
                    Point dest = blue_bases[f.supply_blue_base_id].pos;
                    if (f.pos == dest) {
                        f.status = Fighter::IDLE;
                        f.path.clear();
                        break;
                    }
                    if (f.path.empty()) {
                        vector<vector<int>> dists;
                        vector<vector<Point>> parents;
                        bfs(dest, dists, parents, current_grid);
                        f.path = get_path(f.pos, dest, parents);
                    }
                    
                    if (!f.path.empty()) {
                        Point next_pos = f.path.front();
                        int dir = get_dir(f.pos, next_pos);
                        if (f.fuel > 0) {
                            commands.push_back("move " + to_string(f.id) + " " + to_string(dir));
                            f.fuel--;
                            f.pos = next_pos;
                            f.path.erase(f.path.begin());
                        }
                    } else if (f.pos != dest) {
                         f.status = Fighter::IDLE;
                    }
                    break;
                }
            }
        }
        
        for (const auto& cmd : commands) {
            cout << cmd << "\n";
        }
        cout << "OK\n";
    }

    return 0;
}