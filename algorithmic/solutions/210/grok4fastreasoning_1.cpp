#include <bits/stdc++.h>
using namespace std;

int main() {
  int n, m;
  cin >> n >> m;
  vector<string> grid(n);
  for (int i = 0; i < n; i++) cin >> grid[i];
  int N_blue;
  cin >> N_blue;
  struct Base {
    int x, y, g, c, d, v;
  };
  vector<Base> blue_bases(N_blue);
  vector<int> blue_remaining_g(N_blue), blue_remaining_c(N_blue);
  for (int i = 0; i < N_blue; i++) {
    cin >> blue_bases[i].x >> blue_bases[i].y;
    cin >> blue_bases[i].g >> blue_bases[i].c >> blue_bases[i].d >> blue_bases[i].v;
    blue_remaining_g[i] = blue_bases[i].g;
    blue_remaining_c[i] = blue_bases[i].c;
  }
  int N_red;
  cin >> N_red;
  vector<Base> red_bases(N_red);
  vector<int> red_remaining_d(N_red);
  vector<int> red_x(N_red), red_y(N_red);
  for (int i = 0; i < N_red; i++) {
    cin >> red_bases[i].x >> red_bases[i].y;
    red_x[i] = red_bases[i].x;
    red_y[i] = red_bases[i].y;
    cin >> red_bases[i].g >> red_bases[i].c >> red_bases[i].d >> red_bases[i].v;
    red_remaining_d[i] = red_bases[i].d;
  }
  int k;
  cin >> k;
  struct FighterInfo {
    int x, y, G, C;
  };
  vector<FighterInfo> fighters(k);
  vector<int> f_x(k), f_y(k), f_fuel(k, 0), f_miss(k, 0);
  for (int i = 0; i < k; i++) {
    cin >> fighters[i].x >> fighters[i].y >> fighters[i].G >> fighters[i].C;
    f_x[i] = fighters[i].x;
    f_y[i] = fighters[i].y;
  }
  vector<vector<int>> blue_base_id(n, vector<int>(m, -1));
  for (int i = 0; i < N_blue; i++) {
    int xx = blue_bases[i].x, yy = blue_bases[i].y;
    if (xx >= 0 && xx < n && yy >= 0 && yy < m) blue_base_id[xx][yy] = i;
  }
  vector<vector<int>> red_base_id(n, vector<int>(m, -1));
  vector<vector<bool>> forbidden(n, vector<bool>(m, false));
  for (int i = 0; i < N_red; i++) {
    int xx = red_x[i], yy = red_y[i];
    if (xx >= 0 && xx < n && yy >= 0 && yy < m) {
      red_base_id[xx][yy] = i;
      forbidden[xx][yy] = true;
    }
  }
  vector<int> current_target(k, -1);
  vector<vector<int>> current_path_dirs(k);
  vector<int> goal_x(k, -1), goal_y(k, -1);
  vector<bool> is_refuel_goal(k, false);
  int DX[4] = {-1, 1, 0, 0};
  int DY[4] = {0, 0, -1, 1};
  auto is_on_blue = [&](int x, int y) -> bool {
    return x >= 0 && x < n && y >= 0 && y < m && blue_base_id[x][y] != -1;
  };
  auto do_bfs = [&](int sx, int sy) -> pair<vector<vector<int>>, vector<vector<pair<int, int>>>> {
    vector<vector<int>> d(n, vector<int>(m, -1));
    vector<vector<pair<int, int>>> p(n, vector<pair<int, int>>(m, {-1, -1}));
    queue<pair<int, int>> q;
    d[sx][sy] = 0;
    q.push({sx, sy});
    while (!q.empty()) {
      auto [cx, cy] = q.front();
      q.pop();
      for (int dd = 0; dd < 4; dd++) {
        int nx = cx + DX[dd], ny = cy + DY[dd];
        if (nx >= 0 && nx < n && ny >= 0 && ny < m && !forbidden[nx][ny] && d[nx][ny] == -1) {
          d[nx][ny] = d[cx][cy] + 1;
          p[nx][ny] = {cx, cy};
          q.push({nx, ny});
        }
      }
    }
    return {d, p};
  };
  auto get_path_dirs = [&](int sx, int sy, int gx, int gy, const vector<vector<int>>& d, const vector<vector<pair<int, int>>>& p) -> vector<int> {
    if (d[gx][gy] == -1) return {};
    vector<pair<int, int>> path_pos;
    int cx = gx, cy = gy;
    while (true) {
      path_pos.push_back({cx, cy});
      if (cx == sx && cy == sy) break;
      auto pr = p[cx][cy];
      cx = pr.first;
      cy = pr.second;
    }
    reverse(path_pos.begin(), path_pos.end());
    vector<int> dirs;
    for (size_t j = 0; j + 1 < path_pos.size(); j++) {
      int px1 = path_pos[j].first, py1 = path_pos[j].second;
      int px2 = path_pos[j + 1].first, py2 = path_pos[j + 1].second;
      int dd = -1;
      for (int t = 0; t < 4; t++) {
        if (px2 == px1 + DX[t] && py2 == py1 + DY[t]) {
          dd = t;
          break;
        }
      }
      if (dd == -1) return {};
      dirs.push_back(dd);
    }
    return dirs;
  };
  int frame = 0;
  bool all_destroyed = (N_red == 0);
  while (frame < 15000 && !all_destroyed) {
    vector<string> commands_this_frame;
    for (int i = 0; i < k; i++) {
      int fx = f_x[i], fy = f_y[i];
      int bid = blue_base_id[fx][fy];
      if (bid != -1) {
        int max_m = fighters[i].C - f_miss[i];
        if (max_m > 0 && blue_remaining_c[bid] > 0) {
          commands_this_frame.push_back("missile " + to_string(i) + " 1000000");
          int take = min({1000000, blue_remaining_c[bid], max_m});
          f_miss[i] += take;
          blue_remaining_c[bid] -= take;
        }
        int max_f = fighters[i].G - f_fuel[i];
        if (max_f > 0 && blue_remaining_g[bid] > 0) {
          commands_this_frame.push_back("fuel " + to_string(i) + " 1000000");
          int take = min({1000000, blue_remaining_g[bid], max_f});
          f_fuel[i] += take;
          blue_remaining_g[bid] -= take;
        }
      }
    }
    for (int i = 0; i < k; i++) {
      if (f_miss[i] == 0) continue;
      int fx = f_x[i], fy = f_y[i];
      bool attacked = false;
      for (int d = 0; d < 4 && !attacked; d++) {
        int tx = fx + DX[d], ty = fy + DY[d];
        if (tx < 0 || tx >= n || ty < 0 || ty >= m) continue;
        int rid = red_base_id[tx][ty];
        if (rid != -1 && red_remaining_d[rid] > 0) {
          int count = min(f_miss[i], red_remaining_d[rid]);
          if (count > 0) {
            commands_this_frame.push_back("attack " + to_string(i) + " " + to_string(d) + " " + to_string(count));
            f_miss[i] -= count;
            red_remaining_d[rid] -= count;
            if (red_remaining_d[rid] <= 0) {
              forbidden[tx][ty] = false;
            }
            attacked = true;
          }
        }
      }
    }
    for (int i = 0; i < k; i++) {
      int fx = f_x[i], fy = f_y[i];
      if (goal_x[i] != -1 && fx == goal_x[i] && fy == goal_y[i]) {
        if (is_refuel_goal[i]) {
          is_refuel_goal[i] = false;
          goal_x[i] = -1;
          goal_y[i] = -1;
        } else if (current_target[i] != -1 && red_remaining_d[current_target[i]] <= 0) {
          current_target[i] = -1;
          goal_x[i] = -1;
          goal_y[i] = -1;
        }
      }
      if (goal_x[i] == -1) {
        bool low_fuel = f_fuel[i] < 200;
        bool no_miss_not_base = (f_miss[i] == 0 && !is_on_blue(fx, fy));
        if (low_fuel || no_miss_not_base) {
          auto [d, p] = do_bfs(fx, fy);
          int best_d = INT_MAX;
          int bx = -1, by = -1;
          for (int b = 0; b < N_blue; b++) {
            int tx = blue_bases[b].x, ty = blue_bases[b].y;
            if (d[tx][ty] != -1 && d[tx][ty] < best_d) {
              best_d = d[tx][ty];
              bx = tx;
              by = ty;
            }
          }
          if (bx != -1) {
            goal_x[i] = bx;
            goal_y[i] = by;
            is_refuel_goal[i] = true;
            current_path_dirs[i] = get_path_dirs(fx, fy, bx, by, d, p);
          }
          continue;
        }
        if (f_miss[i] > 0) {
          int rid = current_target[i];
          if (rid == -1 || red_remaining_d[rid] <= 0) {
            auto [d, p] = do_bfs(fx, fy);
            int best_dist = INT_MAX;
            int best_v = 0;
            int best_r = -1;
            pair<int, int> best_adj = {-1, -1};
            for (int r = 0; r < N_red; r++) {
              if (red_remaining_d[r] <= 0) continue;
              int md = INT_MAX;
              pair<int, int> cadj = {-1, -1};
              for (int dd = 0; dd < 4; dd++) {
                int ax = red_x[r] + DX[dd], ay = red_y[r] + DY[dd];
                if (ax >= 0 && ax < n && ay >= 0 && ay < m && !forbidden[ax][ay] && d[ax][ay] != -1 &&
                    d[ax][ay] < md) {
                  md = d[ax][ay];
                  cadj = {ax, ay};
                }
              }
              if (md < INT_MAX) {
                int vv = red_bases[r].v;
                bool better = (md < best_dist) || (md == best_dist && vv > best_v);
                if (better) {
                  best_dist = md;
                  best_v = vv;
                  best_r = r;
                  best_adj = cadj;
                }
              }
            }
            if (best_r != -1) {
              current_target[i] = best_r;
              goal_x[i] = best_adj.first;
              goal_y[i] = best_adj.second;
              is_refuel_goal[i] = false;
              current_path_dirs[i] = get_path_dirs(fx, fy, goal_x[i], goal_y[i], d, p);
            }
            continue;
          } else {
            auto [d, p] = do_bfs(fx, fy);
            int md = INT_MAX;
            pair<int, int> cadj = {-1, -1};
            for (int dd = 0; dd < 4; dd++) {
              int ax = red_x[rid] + DX[dd], ay = red_y[rid] + DY[dd];
              if (ax >= 0 && ax < n && ay >= 0 && ay < m && !forbidden[ax][ay] && d[ax][ay] != -1 &&
                  d[ax][ay] < md) {
                md = d[ax][ay];
                cadj = {ax, ay};
              }
            }
            if (md < INT_MAX) {
              goal_x[i] = cadj.first;
              goal_y[i] = cadj.second;
              is_refuel_goal[i] = false;
              current_path_dirs[i] = get_path_dirs(fx, fy, goal_x[i], goal_y[i], d, p);
            } else {
              current_target[i] = -1;
            }
            continue;
          }
        }
        continue;
      }
      int gx = goal_x[i], gy = goal_y[i];
      if (current_path_dirs[i].empty() && (fx != gx || fy != gy)) {
        auto [d, p] = do_bfs(fx, fy);
        current_path_dirs[i] = get_path_dirs(fx, fy, gx, gy, d, p);
      }
      if (!current_path_dirs[i].empty()) {
        int dir = current_path_dirs[i][0];
        int nx = fx + DX[dir], ny = fy + DY[dir];
        if (f_fuel[i] >= 1 && !forbidden[nx][ny]) {
          commands_this_frame.push_back("move " + to_string(i) + " " + to_string(dir));
          f_x[i] = nx;
          f_y[i] = ny;
          f_fuel[i]--;
          current_path_dirs[i].erase(current_path_dirs[i].begin());
        }
      }
    }
    for (const string& cmd : commands_this_frame) {
      cout << cmd << endl;
    }
    cout << "OK" << endl;
    frame++;
    all_destroyed = true;
    for (int j = 0; j < N_red; j++) {
      if (red_remaining_d[j] > 0) {
        all_destroyed = false;
        break;
      }
    }
  }
  return 0;
}