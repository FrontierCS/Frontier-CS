#include <bits/stdc++.h>
using namespace std;

struct Base {
    int x, y, g, c, d, v;
};

struct Fighter {
    int x, y, G, C;
    int fuel, miss;
    pair<int, int> current_goal;
    vector<pair<int, int>> current_path;
};

int main() {
    int n, m;
    cin >> n >> m;
    vector<string> grid(n);
    for (int i = 0; i < n; i++) cin >> grid[i];

    int Nb;
    cin >> Nb;
    vector<Base> blue(Nb);
    for (int i = 0; i < Nb; i++) {
        cin >> blue[i].x >> blue[i].y;
        cin >> blue[i].g >> blue[i].c >> blue[i].d >> blue[i].v;
    }

    int Nr;
    cin >> Nr;
    vector<Base> red(Nr);
    for (int i = 0; i < Nr; i++) {
        cin >> red[i].x >> red[i].y;
        cin >> red[i].g >> red[i].c >> red[i].d >> red[i].v;
    }

    int k;
    cin >> k;
    vector<Fighter> fighters(k);
    for (int i = 0; i < k; i++) {
        int x, y, G, C;
        cin >> x >> y >> G >> C;
        fighters[i] = {x, y, G, C, 0, 0, {-1, -1}, {}};
    }

    vector<long long> blue_fuel(Nb), blue_miss(Nb);
    for (int i = 0; i < Nb; i++) {
        blue_fuel[i] = blue[i].g;
        blue_miss[i] = blue[i].c;
    }

    vector<long long> red_hits(Nr, 0);
    vector<bool> red_destroyed(Nr, false);

    set<pair<int, int>> blocked;
    for (int i = 0; i < Nr; i++) {
        blocked.insert({red[i].x, red[i].y});
    }

    set<pair<int, int>> blue_cells;
    map<pair<int, int>, int> pos_to_bi;
    for (int i = 0; i < Nb; i++) {
        blue_cells.insert({blue[i].x, blue[i].y});
        pos_to_bi[{blue[i].x, blue[i].y}] = i;
    }

    int delx[4] = {-1, 1, 0, 0};
    int dely[4] = {0, 0, -1, 1};

    auto get_path = [&](int sx, int sy, int gx, int gy) -> vector<pair<int, int>> {
        if (sx == gx && sy == gy) return {{sx, sy}};
        vector<vector<bool>> vis(n, vector<bool>(m, false));
        vector<vector<pair<int, int>>> par(n, vector<pair<int, int>>(m, {-1, -1}));
        queue<pair<int, int>> q;
        q.push({sx, sy});
        vis[sx][sy] = true;
        par[sx][sy] = {-2, -2};
        bool found = false;
        while (!q.empty() && !found) {
            auto [cx, cy] = q.front();
            q.pop();
            for (int d = 0; d < 4; d++) {
                int nx = cx + delx[d], ny = cy + dely[d];
                if (nx >= 0 && nx < n && ny >= 0 && ny < m && !vis[nx][ny] &&
                    blocked.find({nx, ny}) == blocked.end()) {
                    vis[nx][ny] = true;
                    par[nx][ny] = {cx, cy};
                    q.push({nx, ny});
                    if (nx == gx && ny == gy) {
                        found = true;
                        break;
                    }
                }
            }
        }
        if (!vis[gx][gy]) return {};
        vector<pair<int, int>> path;
        pair<int, int> cur = {gx, gy};
        while (cur != make_pair(-2, -2)) {
            path.push_back(cur);
            cur = par[cur.first][cur.second];
        }
        reverse(path.begin(), path.end());
        return path;
    };

    for (int frame = 0; frame < 15000; frame++) {
        // refuel
        for (int id = 0; id < k; id++) {
            int x = fighters[id].x, y = fighters[id].y;
            auto it = pos_to_bi.find({x, y});
            if (it != pos_to_bi.end()) {
                int bi = it->second;
                // fuel
                long long need_f = (long long)fighters[id].G - fighters[id].fuel;
                long long take_f = min(need_f, blue_fuel[bi]);
                if (take_f > 0) {
                    cout << "fuel " << id << " " << take_f << endl;
                    fighters[id].fuel += take_f;
                    blue_fuel[bi] -= take_f;
                }
                // missile
                long long need_m = (long long)fighters[id].C - fighters[id].miss;
                long long take_m = min(need_m, blue_miss[bi]);
                if (take_m > 0) {
                    cout << "missile " << id << " " << take_m << endl;
                    fighters[id].miss += take_m;
                    blue_miss[bi] -= take_m;
                }
            }
        }

        // actions
        for (int id = 0; id < k; id++) {
            int x = fighters[id].x, y = fighters[id].y;
            int& fx = fighters[id].x;
            int& fy = fighters[id].y;
            int& ffu = fighters[id].fuel;
            int& fmi = fighters[id].miss;
            auto& cgoal = fighters[id].current_goal;
            auto& cpath = fighters[id].current_path;

            // check attack
            bool did_attack = false;
            for (int d = 0; d < 4; d++) {
                int tx = x + delx[d], ty = y + dely[d];
                if (tx < 0 || tx >= n || ty < 0 || ty >= m) continue;
                int target_r = -1;
                for (int r = 0; r < Nr; r++) {
                    if (!red_destroyed[r] && red[r].x == tx && red[r].y == ty) {
                        target_r = r;
                        break;
                    }
                }
                if (target_r != -1 && fmi > 0) {
                    long long rem = (long long)red[target_r].d - red_hits[target_r];
                    long long shoot = min((long long)fmi, rem);
                    if (shoot > 0) {
                        cout << "attack " << id << " " << d << " " << shoot << endl;
                        fmi -= shoot;
                        red_hits[target_r] += shoot;
                        if (red_hits[target_r] >= red[target_r].d) {
                            red_destroyed[target_r] = true;
                            blocked.erase({red[target_r].x, red[target_r].y});
                        }
                        did_attack = true;
                        break;
                    }
                }
            }
            if (did_attack) continue;

            // check arrived
            if (cgoal.first != -1 && x == cgoal.first && y == cgoal.second) {
                cgoal = {-1, -1};
                cpath.clear();
            }

            // follow path
            if (cgoal.first != -1) {
                if (cpath.size() > 1 && ffu > 0) {
                    pair<int, int> nextp = cpath[1];
                    int nx = nextp.first, ny = nextp.second;
                    if (blocked.find({nx, ny}) == blocked.end()) {
                        int del_x = nx - x, del_y = ny - y;
                        int dirr = -1;
                        if (del_x == -1 && del_y == 0) dirr = 0;
                        else if (del_x == 1 && del_y == 0) dirr = 1;
                        else if (del_x == 0 && del_y == -1) dirr = 2;
                        else if (del_x == 0 && del_y == 1) dirr = 3;
                        cout << "move " << id << " " << dirr << endl;
                        fx = nx;
                        fy = ny;
                        ffu--;
                        cpath.erase(cpath.begin());
                    } else {
                        cpath.clear();
                    }
                }
                continue;
            }

            // choose new goal
            pair<int, int> goal_pos = {-1, -1};
            bool need_base = (fmi == 0);
            if (need_base) {
                // go to base
                int min_d = INT_MAX;
                long long best_supply = -1;
                for (int b = 0; b < Nb; b++) {
                    int bx = blue[b].x, by = blue[b].y;
                    int dist = abs(bx - x) + abs(by - y);
                    long long this_supply = blue_miss[b];
                    if (dist < min_d || (dist == min_d && this_supply > best_supply)) {
                        min_d = dist;
                        best_supply = this_supply;
                        goal_pos = {bx, by};
                    }
                }
            } else {
                // choose red
                int chosen_r = -1;
                int min_d = INT_MAX;
                int max_v = -1;
                for (int r = 0; r < Nr; r++) {
                    if (red_destroyed[r]) continue;
                    long long rem = red[r].d - red_hits[r];
                    if (rem <= 0) continue;
                    int dist = abs(red[r].x - x) + abs(red[r].y - y);
                    if (dist < min_d || (dist == min_d && red[r].v > max_v)) {
                        min_d = dist;
                        max_v = red[r].v;
                        chosen_r = r;
                    }
                }
                if (chosen_r != -1) {
                    int rx = red[chosen_r].x, ry = red[chosen_r].y;
                    pair<int, int> best_adj = {-1, -1};
                    int min_approx = INT_MAX;
                    for (int d = 0; d < 4; d++) {
                        int ax = rx + delx[d], ay = ry + dely[d];
                        if (ax >= 0 && ax < n && ay >= 0 && ay < m && blocked.count({ax, ay}) == 0) {
                            int approx = abs(ax - x) + abs(ay - y);
                            if (approx < min_approx) {
                                min_approx = approx;
                                best_adj = {ax, ay};
                            }
                        }
                    }
                    if (best_adj.first != -1) {
                        goal_pos = best_adj;
                    }
                }
                if (goal_pos.first == -1) {
                    // go to base
                    int min_d2 = INT_MAX;
                    long long best_supply = -1;
                    for (int b = 0; b < Nb; b++) {
                        int bx = blue[b].x, by = blue[b].y;
                        int dist = abs(bx - x) + abs(by - y);
                        long long this_supply = blue_miss[b];
                        if (dist < min_d2 || (dist == min_d2 && this_supply > best_supply)) {
                            min_d2 = dist;
                            best_supply = this_supply;
                            goal_pos = {bx, by};
                        }
                    }
                }
            }
            if (goal_pos.first == -1) continue;
            auto newpath = get_path(x, y, goal_pos.first, goal_pos.second);
            if (newpath.empty()) continue;
            cgoal = goal_pos;
            cpath = newpath;
        }

        cout << "OK" << endl;

        // check if done
        bool all_done = true;
        for (bool b : red_destroyed) {
            if (!b) all_done = false;
        }
        if (all_done) break;
    }
    return 0;
}