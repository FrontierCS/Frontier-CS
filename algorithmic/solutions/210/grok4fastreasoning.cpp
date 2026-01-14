#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

struct Dir {
    int dx, dy;
};

Dir directions[4] = {{-1, 0}, {1, 0}, {0, -1}, {0, 1}};

struct BlueBase {
    int x, y;
    ll fuel_supply, missile_supply;
};

struct RedBase {
    int x, y;
    ll d, v;
    ll damage = 0;
    bool destroyed() const { return damage >= d; }
};

struct FighterState {
    int x, y;
    ll fuel, missiles;
    int max_fuel, max_miss;
};

class Simulator {
public:
    int n, m;
    vector<string> grid;
    vector<BlueBase> blue_bases;
    vector<RedBase> red_bases;
    vector<FighterState> fighters;
    set<pair<int, int>> undestroyed_red_pos;

    Simulator(int _n, int _m) : n(_n), m(_m), grid(_n) {}

    void add_blue(int x, int y, ll g, ll c) {
        blue_bases.push_back({x, y, g, c});
    }

    void add_red(int x, int y, ll d, ll v) {
        red_bases.push_back({x, y, d, v});
        undestroyed_red_pos.insert({x, y});
    }

    void add_fighter(int x, int y, int G, int C) {
        fighters.push_back({x, y, 0LL, 0LL, G, C});
    }

    FighterState get_fighter(int id) const {
        return fighters[id];
    }

    void apply_commands(const vector<string>& cmds) {
        for (const string& cmd : cmds) {
            istringstream iss(cmd);
            string type;
            iss >> type;
            if (type == "move") {
                int id, dir;
                iss >> id >> dir;
                if (id < 0 || id >= (int)fighters.size() || dir < 0 || dir > 3) continue;
                FighterState& f = fighters[id];
                int nx = f.x + directions[dir].dx;
                int ny = f.y + directions[dir].dy;
                if (nx < 0 || nx >= n || ny < 0 || ny >= m) continue;
                if (f.fuel < 1) continue;
                pair<int, int> tp = {nx, ny};
                if (undestroyed_red_pos.count(tp)) continue;
                f.x = nx;
                f.y = ny;
                f.fuel--;
            } else if (type == "attack") {
                int id, dir;
                ll count;
                iss >> id >> dir >> count;
                if (id < 0 || id >= (int)fighters.size() || dir < 0 || dir > 3 || count <= 0) continue;
                FighterState& f = fighters[id];
                if (f.missiles < count) continue;
                int tx = f.x + directions[dir].dx;
                int ty = f.y + directions[dir].dy;
                if (tx < 0 || tx >= n || ty < 0 || ty >= m) continue;
                pair<int, int> tp = {tx, ty};
                auto it = undestroyed_red_pos.find(tp);
                if (it == undestroyed_red_pos.end()) continue;
                bool found = false;
                for (size_t r = 0; r < red_bases.size(); ++r) {
                    auto& rb = red_bases[r];
                    if (rb.x == tx && rb.y == ty && !rb.destroyed()) {
                        rb.damage += count;
                        if (rb.destroyed()) {
                            undestroyed_red_pos.erase(tp);
                        }
                        found = true;
                        break;
                    }
                }
                if (!found) continue;
                f.missiles -= count;
            } else if (type == "fuel") {
                int id;
                ll count;
                iss >> id >> count;
                if (id < 0 || id >= (int)fighters.size() || count <= 0) continue;
                FighterState& f = fighters[id];
                int base_id = -1;
                for (size_t b = 0; b < blue_bases.size(); ++b) {
                    if (blue_bases[b].x == f.x && blue_bases[b].y == f.y) {
                        base_id = b;
                        break;
                    }
                }
                if (base_id == -1) continue;
                ll take = min(count, blue_bases[base_id].fuel_supply);
                take = min(take, (ll)f.max_fuel - f.fuel);
                if (take <= 0) continue;
                f.fuel += take;
                blue_bases[base_id].fuel_supply -= take;
            } else if (type == "missile") {
                int id;
                ll count;
                iss >> id >> count;
                if (id < 0 || id >= (int)fighters.size() || count <= 0) continue;
                FighterState& f = fighters[id];
                int base_id = -1;
                for (size_t b = 0; b < blue_bases.size(); ++b) {
                    if (blue_bases[b].x == f.x && blue_bases[b].y == f.y) {
                        base_id = b;
                        break;
                    }
                }
                if (base_id == -1) continue;
                ll take = min(count, blue_bases[base_id].missile_supply);
                take = min(take, (ll)f.max_miss - f.missiles);
                if (take <= 0) continue;
                f.missiles += take;
                blue_bases[base_id].missile_supply -= take;
            }
        }
    }

    pair<pair<int, int>, int> get_nearest_blue(int sx, int sy) {
        vector<vector<int>> dist(n, vector<int>(m, -1));
        queue<pair<int, int>> q;
        q.push({sx, sy});
        dist[sx][sy] = 0;
        int min_d = INT_MAX;
        pair<int, int> best = {-1, -1};
        while (!q.empty()) {
            auto [x, y] = q.front();
            q.pop();
            if (dist[x][y] >= min_d) continue;
            bool is_blue = false;
            for (const auto& b : blue_bases) {
                if (b.x == x && b.y == y) {
                    is_blue = true;
                    break;
                }
            }
            if (is_blue && dist[x][y] < min_d) {
                min_d = dist[x][y];
                best = {x, y};
            }
            for (int d = 0; d < 4; ++d) {
                int nx = x + directions[d].dx;
                int ny = y + directions[d].dy;
                if (nx >= 0 && nx < n && ny >= 0 && ny < m && dist[nx][ny] == -1 && grid[nx][ny] != '#') {
                    dist[nx][ny] = dist[x][y] + 1;
                    q.push({nx, ny});
                }
            }
        }
        if (min_d == INT_MAX) return {{-1, -1}, -1};
        return {best, min_d};
    }

    vector<int> get_path(int sx, int sy, int tx, int ty) {
        if (sx == tx && sy == ty) return {};
        vector<vector<int>> dist(n, vector<int>(m, -1));
        vector<vector<pair<int, int>>> parent(n, vector<pair<int, int>>(m, {-1, -1}));
        queue<pair<int, int>> q;
        q.push({sx, sy});
        dist[sx][sy] = 0;
        bool found = false;
        while (!q.empty() && !found) {
            auto [x, y] = q.front();
            q.pop();
            for (int d = 0; d < 4; ++d) {
                int nx = x + directions[d].dx;
                int ny = y + directions[d].dy;
                if (nx >= 0 && nx < n && ny >= 0 && ny < m && dist[nx][ny] == -1 && grid[nx][ny] != '#') {
                    dist[nx][ny] = dist[x][y] + 1;
                    parent[nx][ny] = {x, y};
                    q.push({nx, ny});
                    if (nx == tx && ny == ty) {
                        found = true;
                        break;
                    }
                }
            }
        }
        if (dist[tx][ty] == -1) return {};
        vector<int> path_dirs;
        pair<int, int> cur = {tx, ty};
        while (cur != make_pair(sx, sy)) {
            pair<int, int> prev = parent[cur.first][cur.second];
            int pdx = cur.first - prev.first;
            int pdy = cur.second - prev.second;
            int pdir = -1;
            for (int d = 0; d < 4; ++d) {
                if (directions[d].dx == pdx && directions[d].dy == pdy) {
                    pdir = d;
                    break;
                }
            }
            path_dirs.push_back(pdir);
            cur = prev;
        }
        reverse(path_dirs.begin(), path_dirs.end());
        return path_dirs;
    }

    pair<pair<int, int>, vector<int>> get_best_attack_pos_and_path(int sx, int sy, int rid) {
        int rx = red_bases[rid].x;
        int ry = red_bases[rid].y;
        pair<int, int> best_pos = {-1, -1};
        int min_dist = INT_MAX;
        vector<int> best_path;
        for (int d = 0; d < 4; ++d) {
            int ax = rx - directions[d].dx;
            int ay = ry - directions[d].dy;
            if (ax < 0 || ax >= n || ay < 0 || ay >= m || grid[ax][ay] == '#') continue;
            auto path = get_path(sx, sy, ax, ay);
            if (!path.empty()) {
                int this_dist = path.size();
                if (this_dist < min_dist) {
                    min_dist = this_dist;
                    best_pos = {ax, ay};
                    best_path = path;
                }
            }
        }
        return {best_pos, best_path};
    }
};

int main() {
    int n, m;
    cin >> n >> m;
    Simulator sim(n, m);
    for (int i = 0; i < n; ++i) {
        cin >> sim.grid[i];
    }
    int nb;
    cin >> nb;
    for (int i = 0; i < nb; ++i) {
        int x, y;
        cin >> x >> y;
        ll g, c, d, v;
        cin >> g >> c >> d >> v;
        sim.add_blue(x, y, g, c);
    }
    int nr;
    cin >> nr;
    for (int i = 0; i < nr; ++i) {
        int x, y;
        cin >> x >> y;
        ll g, c, d, v;
        cin >> g >> c >> d >> v;
        sim.add_red(x, y, d, v);
    }
    int k;
    cin >> k;
    for (int i = 0; i < k; ++i) {
        int x, y, G, C;
        cin >> x >> y >> G >> C;
        sim.add_fighter(x, y, G, C);
    }
    vector<string> output;
    int max_frames = 15000;
    struct FighterPlan {
        pair<int, int> goal;
        vector<int> path;
        int path_idx = 0;
    };
    vector<FighterPlan> plans(k);
    for (int frame = 0; frame < max_frames; ++frame) {
        int current_target = -1;
        ll max_v = -1;
        for (int r = 0; r < nr; ++r) {
            if (!sim.red_bases[r].destroyed() && sim.red_bases[r].v > max_v) {
                max_v = sim.red_bases[r].v;
                current_target = r;
            }
        }
        if (current_target == -1) break;
        vector<string> cmds;
        for (int id = 0; id < k; ++id) {
            auto fstate = sim.get_fighter(id);
            int cx = fstate.x, cy = fstate.y;
            ll cf = fstate.fuel, cm = fstate.missiles;
            int G = fstate.max_fuel, C = fstate.max_miss;
            int base_id = -1;
            for (int b = 0; b < nb; ++b) {
                if (sim.blue_bases[b].x == cx && sim.blue_bases[b].y == cy) {
                    base_id = b;
                    break;
                }
            }
            ll take_f = 0, take_m = 0;
            if (base_id != -1) {
                take_f = min((ll)G - cf, sim.blue_bases[base_id].fuel_supply);
                take_m = min((ll)C - cm, sim.blue_bases[base_id].missile_supply);
            }
            ll future_fuel = cf + take_f;
            ll future_missiles = cm + take_m;
            bool do_attack = false;
            int attack_dir = -1;
            int rx = sim.red_bases[current_target].x;
            int ry = sim.red_bases[current_target].y;
            for (int d = 0; d < 4; ++d) {
                int tx = cx + directions[d].dx;
                int ty = cy + directions[d].dy;
                if (tx == rx && ty == ry) {
                    do_attack = true;
                    attack_dir = d;
                    break;
                }
            }
            if (do_attack && future_missiles > 0 && !sim.red_bases[current_target].destroyed()) {
                if (take_f > 0) {
                    cmds.push_back("fuel " + to_string(id) + " " + to_string(take_f));
                }
                if (take_m > 0) {
                    cmds.push_back("missile " + to_string(id) + " " + to_string(take_m));
                }
                ll acount = future_missiles;
                cmds.push_back("attack " + to_string(id) + " " + to_string(attack_dir) + " " + to_string(acount));
                continue;
            }
            if (take_f > 0) {
                cmds.push_back("fuel " + to_string(id) + " " + to_string(take_f));
            }
            if (take_m > 0) {
                cmds.push_back("missile " + to_string(id) + " " + to_string(take_m));
            }
            auto& plan = plans[id];
            bool need_replan = (plan.path_idx >= (int)plan.path.size());
            if (!need_replan) {
                if (future_fuel < 1) need_replan = true;
            }
            if (need_replan) {
                auto nearest_b = sim.get_nearest_blue(cx, cy);
                int dist_b = nearest_b.second;
                bool go_refuel = (future_missiles == 0);
                if (!go_refuel) {
                    if (dist_b != -1 && future_fuel < (ll)dist_b) go_refuel = true;
                }
                if (go_refuel) {
                    if (dist_b != -1 && future_fuel >= (ll)dist_b) {
                        plan.goal = nearest_b.first;
                        plan.path = sim.get_path(cx, cy, plan.goal.first, plan.goal.second);
                        plan.path_idx = 0;
                    } else {
                        plan.path.clear();
                        plan.path_idx = 0;
                    }
                } else {
                    auto [apos, apath] = sim.get_best_attack_pos_and_path(cx, cy, current_target);
                    if (apos.first != -1 && !apath.empty()) {
                        int d1 = apath.size();
                        auto nb_a = sim.get_nearest_blue(apos.first, apos.second);
                        int d2 = nb_a.second;
                        if (d2 != -1 && future_fuel >= (ll)(d1 + d2)) {
                            plan.goal = apos;
                            plan.path = apath;
                            plan.path_idx = 0;
                        } else {
                            if (dist_b != -1 && future_fuel >= (ll)dist_b) {
                                plan.goal = nearest_b.first;
                                plan.path = sim.get_path(cx, cy, plan.goal.first, plan.goal.second);
                                plan.path_idx = 0;
                            } else {
                                plan.path.clear();
                                plan.path_idx = 0;
                            }
                        }
                    } else {
                        if (dist_b != -1 && future_fuel >= (ll)dist_b) {
                            plan.goal = nearest_b.first;
                            plan.path = sim.get_path(cx, cy, plan.goal.first, plan.goal.second);
                            plan.path_idx = 0;
                        } else {
                            plan.path.clear();
                            plan.path_idx = 0;
                        }
                    }
                }
            }
            if (plan.path_idx < (int)plan.path.size() && future_fuel >= 1) {
                int next_dir = plan.path[plan.path_idx];
                cmds.push_back("move " + to_string(id) + " " + to_string(next_dir));
                plan.path_idx++;
            }
        }
        for (const auto& c : cmds) {
            output.push_back(c);
        }
        output.push_back("OK");
        sim.apply_commands(cmds);
    }
    for (const auto& line : output) {
        cout << line << endl;
    }
    return 0;
}