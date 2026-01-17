#include <bits/stdc++.h>
using namespace std;

int main() {
  int n, m;
  cin >> n >> m;
  vector<string> grid(n);
  for (int i = 0; i < n; i++) cin >> grid[i];
  int Nb;
  cin >> Nb;
  struct Base {
    int x, y, g, c, d, v;
  };
  vector<Base> blue(Nb);
  for (int i = 0; i < Nb; i++) {
    int x, y;
    cin >> x >> y;
    cin >> blue[i].g >> blue[i].c >> blue[i].d >> blue[i].v;
  }
  int Nr;
  cin >> Nr;
  vector<Base> redd(Nr);
  for (int i = 0; i < Nr; i++) {
    int x, y;
    cin >> x >> y;
    cin >> redd[i].g >> redd[i].c >> redd[i].d >> redd[i].v;
  }
  int k;
  cin >> k;
  vector<int> initx(k), inity(k), GG(k), CC(k);
  for (int i = 0; i < k; i++) {
    cin >> initx[i] >> inity[i] >> GG[i] >> CC[i];
  }
  vector<pair<int, int>> red_pos(Nr);
  vector<int> red_d(Nr), red_v(Nr);
  for (int i = 0; i < Nr; i++) {
    red_pos[i] = {redd[i].x, redd[i].y};
    red_d[i] = redd[i].d;
    red_v[i] = redd[i].v;
  }
  vector<int> order(Nr);
  iota(order.begin(), order.end(), 0);
  sort(order.begin(), order.end(), [&](int a, int b) {
    if (red_v[a] != red_v[b]) return red_v[a] > red_v[b];
    return a < b;
  });
  vector<vector<int>> assignments(k);
  for (int j = 0; j < Nr; j++) {
    int fi = j % k;
    assignments[fi].push_back(order[j]);
  }
  vector<vector<int>> remaining = assignments;
  for (int i = 0; i < k; i++) {
    cout << "missile " << i << " " << CC[i] << endl;
    cout << "fuel " << i << " " << GG[i] << endl;
  }
  cout << "OK" << endl;
  struct State {
    pair<int, int> home;
    vector<pair<int, int>> path;
    int path_idx = 0;
    int target_rb = -1;
    bool is_returning = false;
  };
  vector<State> states(k);
  vector<int> cur_x = initx, cur_y = inity, cur_fuel = GG, cur_miss = CC;
  for (int i = 0; i < k; i++) {
    states[i].home = {initx[i], inity[i]};
  }
  int DX[4] = {-1, 1, 0, 0};
  int DY[4] = {0, 0, -1, 1};
  auto valid = [&](int x, int y) {
    return x >= 0 && x < n && y >= 0 && y < m && grid[x][y] != '#';
  };
  auto bfs_dist = [&](int sx, int sy, int tx, int ty) -> int {
    if (!valid(sx, sy) || !valid(tx, ty)) return -1;
    vector<vector<int>> d(n, vector<int>(m, -1));
    queue<pair<int, int>> q;
    q.push({sx, sy});
    d[sx][sy] = 0;
    while (!q.empty()) {
      auto [x, y] = q.front();
      q.pop();
      if (x == tx && y == ty) return d[x][y];
      for (int dd = 0; dd < 4; dd++) {
        int nx = x + DX[dd], ny = y + DY[dd];
        if (valid(nx, ny) && d[nx][ny] == -1) {
          d[nx][ny] = d[x][y] + 1;
          q.push({nx, ny});
        }
      }
    }
    return -1;
  };
  auto get_path = [&](int sx, int sy, int tx, int ty) -> vector<pair<int, int>> {
    if (sx == tx && sy == ty) return {{sx, sy}};
    vector<vector<pair<int, int>>> prev(n, vector<pair<int, int>>(m, {-1, -1}));
    vector<vector<int>> d(n, vector<int>(m, -1));
    queue<pair<int, int>> q;
    q.push({sx, sy});
    d[sx][sy] = 0;
    bool fnd = false;
    while (!q.empty() && !fnd) {
      auto [x, y] = q.front();
      q.pop();
      for (int dd = 0; dd < 4; dd++) {
        int nx = x + DX[dd], ny = y + DY[dd];
        if (valid(nx, ny) && d[nx][ny] == -1) {
          d[nx][ny] = d[x][y] + 1;
          prev[nx][ny] = {x, y};
          q.push({nx, ny});
          if (nx == tx && ny == ty) {
            fnd = true;
            break;
          }
        }
      }
    }
    if (d[tx][ty] == -1) return {};
    vector<pair<int, int>> pth;
    pair<int, int> cur = {tx, ty};
    while (cur.first != -1) {
      pth.push_back(cur);
      cur = prev[cur.first][cur.second];
    }
    reverse(pth.begin(), pth.end());
    return pth;
  };
  for (int t = 1; t <= 15000; t++) {
    bool done = true;
    for (int i = 0; i < k; i++) {
      if (!remaining[i].empty()) {
        done = false;
        break;
      }
      if (!states[i].path.empty() && states[i].path_idx < (int)states[i].path.size() - 1) {
        done = false;
        break;
      }
    }
    if (done) break;
    vector<string> cmds;
    for (int i = 0; i < k; i++) {
      State& st = states[i];
      bool has_active_path = !st.path.empty() && st.path_idx < (int)st.path.size() - 1;
      if (!has_active_path) {
        bool arrived = !st.path.empty() && st.path_idx == (int)st.path.size() - 1;
        if (arrived) {
          pair<int, int> cpos = {cur_x[i], cur_y[i]};
          if (!st.is_returning) {
            int rb = st.target_rb;
            int rx = red_pos[rb].first, ry = red_pos[rb].second;
            int delx = rx - cpos.first;
            int dely = ry - cpos.second;
            int dir = -1;
            if (delx == -1 && dely == 0) dir = 0;
            else if (delx == 1 && dely == 0) dir = 1;
            else if (delx == 0 && dely == -1) dir = 2;
            else if (delx == 0 && dely == 1) dir = 3;
            if (dir != -1) {
              int cnt = red_d[rb];
              int fire = min(cnt, cur_miss[i]);
              cmds.push_back("attack " + to_string(i) + " " + to_string(dir) + " " + to_string(fire));
              cur_miss[i] -= fire;
            }
            st.is_returning = true;
            st.path.clear();
            st.path_idx = 0;
            st.target_rb = -1;
          } else {
            bool on_home = (cur_x[i] == st.home.first && cur_y[i] == st.home.second);
            if (on_home) {
              int fneed = GG[i] - cur_fuel[i];
              int mneed = CC[i] - cur_miss[i];
              if (fneed > 0) {
                cmds.push_back("fuel " + to_string(i) + " " + to_string(fneed));
                cur_fuel[i] = GG[i];
              }
              if (mneed > 0) {
                cmds.push_back("missile " + to_string(i) + " " + to_string(mneed));
                cur_miss[i] = CC[i];
              }
              st.is_returning = false;
              st.path.clear();
              st.path_idx = 0;
              st.target_rb = -1;
            }
          }
        }
        bool on_home = (cur_x[i] == st.home.first && cur_y[i] == st.home.second);
        if (on_home && !remaining[i].empty() && cur_fuel[i] == GG[i] && cur_miss[i] == CC[i]) {
          int rb = remaining[i][0];
          vector<pair<int, int>> poss_adj;
          for (int dd = 0; dd < 4; dd++) {
            int ax = red_pos[rb].first + DX[dd];
            int ay = red_pos[rb].second + DY[dd];
            if (valid(ax, ay)) poss_adj.emplace_back(ax, ay);
          }
          if (!poss_adj.empty()) {
            pair<int, int> best_a = {-1, -1};
            int min_c = INT_MAX / 2;
            for (auto ad : poss_adj) {
              int d1 = bfs_dist(cur_x[i], cur_y[i], ad.first, ad.second);
              if (d1 == -1) continue;
              int d2 = bfs_dist(ad.first, ad.second, st.home.first, st.home.second);
              if (d2 == -1) continue;
              int tc = d1 + d2;
              if (tc < min_c) {
                min_c = tc;
                best_a = ad;
              }
            }
            if (best_a.first != -1 && min_c <= GG[i]) {
              remaining[i].erase(remaining[i].begin());
              auto pth = get_path(cur_x[i], cur_y[i], best_a.first, best_a.second);
              if (!pth.empty()) {
                st.path = move(pth);
                st.path_idx = 0;
                st.target_rb = rb;
                st.is_returning = false;
              }
            }
          }
        } else if (st.is_returning && !on_home) {
          auto pth = get_path(cur_x[i], cur_y[i], st.home.first, st.home.second);
          if (!pth.empty()) {
            st.path = move(pth);
            st.path_idx = 0;
            st.target_rb = -1;
          }
        } else if (on_home && (cur_fuel[i] < GG[i] || cur_miss[i] < CC[i])) {
          int fneed = GG[i] - cur_fuel[i];
          int mneed = CC[i] - cur_miss[i];
          if (fneed > 0) {
            cmds.push_back("fuel " + to_string(i) + " " + to_string(fneed));
            cur_fuel[i] = GG[i];
          }
          if (mneed > 0) {
            cmds.push_back("missile " + to_string(i) + " " + to_string(mneed));
            cur_miss[i] = CC[i];
          }
          st.is_returning = false;
        }
      }
      if (!st.path.empty() && st.path_idx < (int)st.path.size() - 1) {
        auto [nx, ny] = st.path[st.path_idx + 1];
        int delx = nx - cur_x[i];
        int dely = ny - cur_y[i];
        int dir = -1;
        if (delx == -1 && dely == 0) dir = 0;
        else if (delx == 1 && dely == 0) dir = 1;
        else if (delx == 0 && dely == -1) dir = 2;
        else if (delx == 0 && dely == 1) dir = 3;
        if (dir != -1) {
          cmds.push_back("move " + to_string(i) + " " + to_string(dir));
          cur_x[i] = nx;
          cur_y[i] = ny;
          if (cur_fuel[i] > 0) cur_fuel[i]--;
          st.path_idx++;
        }
      }
    }
    for (auto& s : cmds) {
      cout << s << endl;
    }
    cout << "OK" << endl;
  }
  return 0;
}