#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <cmath>
#include <algorithm>
#include <tuple>
#include <sstream>

using namespace std;

// --- Data Structures ---

struct Point {
    int x, y;
    bool operator==(const Point& other) const { return x == other.x && y == other.y; }
    bool operator!=(const Point& other) const { return !(*this == other); }
};

enum FighterStatus {
    IDLE,
    MOVING_TO_MISSION_BASE,
    RESUPPLYING,
    MOVING_TO_ATTACK_POS,
    ATTACKING,
    RETURNING_TO_BASE
};

struct BlueBase {
    int id;
    Point pos;
    long long g, c;
};

struct RedBase {
    int id;
    Point pos;
    long long d, v;
    long long current_d;
    bool is_destroyed;
    int assigned_to_fighter_id;
    vector<Point> attack_positions;
};

struct Fighter {
    int id;
    Point pos;
    long long G, C;
    long long fuel, missiles;

    FighterStatus status;
    vector<Point> path;
    int mission_rid;
    int mission_bid;
    Point mission_attack_pos;
};

// --- Global State ---
int n, m, k;
vector<string> initial_grid;
vector<BlueBase> blue_bases;
vector<RedBase> red_bases;
vector<Fighter> fighters;

vector<vector<vector<int>>> dists;
vector<vector<vector<Point>>> parents;

int dx[] = {-1, 1, 0, 0};
int dy[] = {0, 0, -1, 1};

// --- Pathfinding ---
bool is_valid(int r, int c, const vector<string>& grid) {
    return r >= 0 && r < n && c >= 0 && c < m && grid[r][c] != '#';
}

void bfs_from(Point start, vector<vector<int>>& dist_map, vector<vector<Point>>& parent_map, const vector<string>& grid) {
    dist_map.assign(n, vector<int>(m, -1));
    parent_map.assign(n, vector<Point>(m, {-1, -1}));
    queue<Point> q;

    if (!is_valid(start.x, start.y, grid)) return;

    dist_map[start.x][start.y] = 0;
    q.push(start);

    while (!q.empty()) {
        Point curr = q.front();
        q.pop();

        for (int i = 0; i < 4; ++i) {
            Point next = {curr.x + dx[i], curr.y + dy[i]};
            if (is_valid(next.x, next.y, grid) && dist_map[next.x][next.y] == -1) {
                dist_map[next.x][next.y] = dist_map[curr.x][curr.y] + 1;
                parent_map[next.x][next.y] = curr;
                q.push(next);
            }
        }
    }
}

void recalculate_all_paths() {
    vector<string> current_grid = initial_grid;
    for (const auto& rb : red_bases) {
        if (!rb.is_destroyed) {
            current_grid[rb.pos.x][rb.pos.y] = '#';
        } else {
            current_grid[rb.pos.x][rb.pos.y] = '.';
        }
    }

    int num_blue_bases = blue_bases.size();
    dists.assign(num_blue_bases, vector<vector<int>>(n, vector<int>(m)));
    parents.assign(num_blue_bases, vector<vector<Point>>(n, vector<Point>(m)));

    for (int i = 0; i < num_blue_bases; ++i) {
        bfs_from(blue_bases[i].pos, dists[i], parents[i], current_grid);
    }
}

vector<Point> get_path(int base_idx, Point dest) {
    vector<Point> path;
    Point curr = dest;
    while (curr.x != -1) {
        path.push_back(curr);
        if (curr == blue_bases[base_idx].pos) break;
        curr = parents[base_idx][curr.x][curr.y];
    }
    reverse(path.begin(), path.end());
    if(!path.empty() && path[0] == blue_bases[base_idx].pos) {
        path.erase(path.begin());
    }
    return path;
}

int get_move_dir(Point from, Point to) {
    if (to.x < from.x) return 0; // up
    if (to.x > from.x) return 1; // down
    if (to.y < from.y) return 2; // left
    if (to.y > from.y) return 3; // right
    return -1;
}

// --- Mission Assignment ---
void assign_missions() {
    vector<int> idle_fighters_indices;
    for (int i = 0; i < k; ++i) {
        if (fighters[i].status == IDLE) {
            idle_fighters_indices.push_back(i);
        }
    }
    if (idle_fighters_indices.empty()) return;
    
    using MissionInfo = tuple<double, int, int, int, Point>;
    vector<MissionInfo> potential_missions;

    for (int fid : idle_fighters_indices) {
        Fighter& f = fighters[fid];
        int f_base_idx = -1;
        for (size_t i = 0; i < blue_bases.size(); ++i) if (blue_bases[i].pos == f.pos) {f_base_idx = i; break;}
        if (f_base_idx == -1) continue; 

        for (int rid = 0; rid < red_bases.size(); ++rid) {
            if (red_bases[rid].is_destroyed || red_bases[rid].assigned_to_fighter_id != -1) continue;

            RedBase& r = red_bases[rid];
            if (r.current_d <= 0) continue;
            long long missiles_needed = r.current_d;
            long long num_sorties = (missiles_needed + f.C - 1) / f.C;

            for (int bid = 0; bid < blue_bases.size(); ++bid) {
                Point best_attack_pos = {-1, -1};
                int min_dist_to_attack = 1e9;
                for(const auto& p : r.attack_positions) {
                    int d = dists[bid][p.x][p.y];
                    if(d != -1 && d < min_dist_to_attack) { min_dist_to_attack = d; best_attack_pos = p; }
                }
                if(best_attack_pos.x == -1) continue;

                int time_to_b = (f_base_idx == bid) ? 0 : dists[f_base_idx][blue_bases[bid].pos.x][blue_bases[bid].pos.y];
                if (time_to_b == -1 && f_base_idx != bid) continue;
                
                long long time_for_sorties = num_sorties * (min_dist_to_attack * 2LL + 2LL);
                long long total_time = time_to_b + time_for_sorties;
                if(f.fuel < time_to_b) total_time++; 

                if (total_time <= 0) continue;

                double score = (double)r.v / total_time;
                potential_missions.emplace_back(score, fid, rid, bid, best_attack_pos);
            }
        }
    }
    
    sort(potential_missions.rbegin(), potential_missions.rend());

    for (const auto& mission : potential_missions) {
        int fid, rid, bid;
        Point attack_pos;
        tie(ignore, fid, rid, bid, attack_pos) = mission;

        if (fighters[fid].status != IDLE || red_bases[rid].assigned_to_fighter_id != -1) continue;
        
        Fighter& f = fighters[fid];
        
        f.mission_rid = rid;
        f.mission_bid = bid;
        f.mission_attack_pos = attack_pos;
        red_bases[rid].assigned_to_fighter_id = fid;
        
        int f_base_idx = -1;
        for (size_t i = 0; i < blue_bases.size(); ++i) if (blue_bases[i].pos == f.pos) f_base_idx = i;

        if (f_base_idx == bid) {
            f.status = RESUPPLYING;
        } else {
            f.status = MOVING_TO_MISSION_BASE;
            f.path = get_path(f_base_idx, blue_bases[bid].pos);
        }
    }
}


// --- Main Simulation Loop ---
void solve() {
    cin >> n >> m;
    initial_grid.resize(n);
    for (int i = 0; i < n; ++i) cin >> initial_grid[i];
    int num_blue_bases, num_red_bases;
    cin >> num_blue_bases;
    for (int i = 0; i < num_blue_bases; ++i) {
        BlueBase b; b.id = i;
        cin >> b.pos.x >> b.pos.y >> b.g >> b.c;
        long long d_dummy, v_dummy; cin >> d_dummy >> v_dummy;
        blue_bases.push_back(b);
    }
    cin >> num_red_bases;
    for (int i = 0; i < num_red_bases; ++i) {
        RedBase r; r.id = i;
        cin >> r.pos.x >> r.pos.y;
        long long g_dummy, c_dummy; cin >> g_dummy >> c_dummy >> r.d >> r.v;
        r.current_d = r.d; r.is_destroyed = false; r.assigned_to_fighter_id = -1;
        red_bases.push_back(r);
    }
    cin >> k;
    for (int i = 0; i < k; ++i) {
        Fighter f; f.id = i;
        cin >> f.pos.x >> f.pos.y >> f.G >> f.C;
        f.fuel = 0; f.missiles = 0; f.status = IDLE; f.mission_rid = -1; f.mission_bid = -1;
        fighters.push_back(f);
    }

    for(auto& r : red_bases) {
        for(int i=0; i<4; ++i) {
            Point p = {r.pos.x + dx[i], r.pos.y + dy[i]};
            if(p.x >= 0 && p.x < n && p.y >= 0 && p.y < m && initial_grid[p.x][p.y] != '#') {
                r.attack_positions.push_back(p);
            }
        }
    }
    recalculate_all_paths();

    int destroyed_count = 0;
    for (int frame = 0; frame < 15000; ++frame) {
        if (destroyed_count == red_bases.size()) break;
        assign_missions();
        vector<string> commands;
        
        for (auto& f : fighters) {
            switch (f.status) {
                case IDLE: {
                    int base_idx = -1;
                    for(size_t i=0; i < blue_bases.size(); ++i) if(blue_bases[i].pos == f.pos) base_idx = i;
                    if(base_idx != -1 && f.fuel < f.G && blue_bases[base_idx].g > 0) {
                        long long can_get = min(f.G - f.fuel, blue_bases[base_idx].g);
                        if(can_get > 0) commands.push_back("fuel " + to_string(f.id) + " " + to_string(can_get));
                    }
                    break;
                }
                case MOVING_TO_MISSION_BASE:
                case MOVING_TO_ATTACK_POS:
                case RETURNING_TO_BASE: {
                    if (f.path.empty()) {
                         if (f.status == MOVING_TO_MISSION_BASE) f.status = RESUPPLYING;
                         else if (f.status == MOVING_TO_ATTACK_POS) f.status = ATTACKING;
                         else if (f.status == RETURNING_TO_BASE) {
                             if (f.mission_rid != -1 && red_bases[f.mission_rid].is_destroyed) {
                                 red_bases[f.mission_rid].assigned_to_fighter_id = -1;
                                 f.status = IDLE; f.mission_rid = -1;
                             } else f.status = RESUPPLYING;
                         }
                    } else if (f.fuel > 0) {
                        commands.push_back("move " + to_string(f.id) + " " + to_string(get_move_dir(f.pos, f.path.front())));
                    }
                    break;
                }
                case RESUPPLYING: {
                    long long dist_to_target = dists[f.mission_bid][f.mission_attack_pos.x][f.mission_attack_pos.y];
                    long long fuel_for_sortie = dist_to_target > 0 ? 2 * dist_to_target : 0;
                    long long missiles_for_sortie = min((long long)f.C, red_bases[f.mission_rid].current_d);
                    
                    if (f.fuel >= fuel_for_sortie && f.missiles >= missiles_for_sortie) {
                        f.status = MOVING_TO_ATTACK_POS;
                        f.path = get_path(f.mission_bid, f.mission_attack_pos);
                    } else {
                        if (f.fuel < fuel_for_sortie && blue_bases[f.mission_bid].g > 0) {
                            long long needed = min(fuel_for_sortie - f.fuel, f.G - f.fuel);
                            long long can_get = min(needed, blue_bases[f.mission_bid].g);
                            if(can_get > 0) commands.push_back("fuel " + to_string(f.id) + " " + to_string(can_get));
                        }
                        if (f.missiles < missiles_for_sortie && blue_bases[f.mission_bid].c > 0) {
                            long long needed = missiles_for_sortie - f.missiles;
                            long long can_get = min(needed, blue_bases[f.mission_bid].c);
                            if(can_get > 0) commands.push_back("missile " + to_string(f.id) + " " + to_string(can_get));
                        }
                    }
                    break;
                }
                case ATTACKING: {
                    long long to_fire = min(f.missiles, red_bases[f.mission_rid].current_d);
                    if (to_fire > 0) {
                        commands.push_back("attack " + to_string(f.id) + " " + to_string(get_move_dir(f.pos, red_bases[f.mission_rid].pos)) + " " + to_string(to_fire));
                    } else {
                       f.status = RETURNING_TO_BASE;
                       f.path = get_path(f.mission_bid, blue_bases[f.mission_bid].pos);
                    }
                    break;
                }
            }
        }

        for (const auto& cmd : commands) cout << cmd << endl;
        cout << "OK" << endl;

        bool recalculate_paths_needed = false;
        for (const auto& cmd_str : commands) {
            stringstream ss(cmd_str); string type; ss >> type; int id; ss >> id;
            if (type == "move") {
                int dir; ss >> dir;
                fighters[id].fuel--; fighters[id].pos = {fighters[id].pos.x + dx[dir], fighters[id].pos.y + dy[dir]};
                if (!fighters[id].path.empty() && fighters[id].pos == fighters[id].path.front()) fighters[id].path.erase(fighters[id].path.begin());
            } else if (type == "fuel") {
                long long count; ss >> count; fighters[id].fuel += count;
                int b_idx = -1; for(size_t i=0; i<blue_bases.size(); ++i) if(blue_bases[i].pos == fighters[id].pos) b_idx=i;
                if(b_idx!=-1) blue_bases[b_idx].g -= count;
            } else if (type == "missile") {
                long long count; ss >> count; fighters[id].missiles += count;
                int b_idx = -1; for(size_t i=0; i<blue_bases.size(); ++i) if(blue_bases[i].pos == fighters[id].pos) b_idx=i;
                if(b_idx!=-1) blue_bases[b_idx].c -= count;
            } else if (type == "attack") {
                int dir; long long count; ss >> dir >> count;
                fighters[id].missiles -= count;
                int rid = fighters[id].mission_rid;
                if(rid != -1) {
                    red_bases[rid].current_d -= count;
                    if (red_bases[rid].current_d <= 0 && !red_bases[rid].is_destroyed) {
                        red_bases[rid].is_destroyed = true; recalculate_paths_needed = true; destroyed_count++;
                    }
                    fighters[id].status = RETURNING_TO_BASE;
                    fighters[id].path = get_path(fighters[id].mission_bid, blue_bases[fighters[id].mission_bid].pos);
                }
            }
        }
        if (recalculate_paths_needed) recalculate_all_paths();
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    solve();
    return 0;
}