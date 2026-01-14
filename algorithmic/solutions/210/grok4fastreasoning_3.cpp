#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(nullptr);
  int n, m;
  cin >> n >> m;
  vector<string> grid(n);
  for (int i = 0; i < n; i++) cin >> grid[i];
  int N_blue;
  cin >> N_blue;
  set<pair<int, int>> blue_bases;
  vector<vector<long long>> fuel_sup(n, vector<long long>(m, 0LL));
  vector<vector<long long>> miss_sup(n, vector<long long>(m, 0LL));
  for (int i = 0; i < N_blue; i++) {
    int x, y;
    cin >> x >> y;
    blue_bases.insert({x, y});
    long long g, c, d, v;
    cin >> g >> c >> d >> v;
    fuel_sup[x][y] = g;
    miss_sup[x][y] = c;
  }
  int N_red;
  cin >> N_red;
  struct RedBase {
    int x, y;
    long long d, v, hits;
  };
  vector<RedBase> reds(N_red);
  set<pair<int, int>> active_red_pos;
  for (int i = 0; i < N_red; i++) {
    int x, y;
    cin >> x >> y;
    long long g, c, d, v;
    cin >> g >> c >> d >> v;
    reds[i] = {x, y, d, v, 0LL};
    active_red_pos.insert({x, y});
  }
  int k;
  cin >> k;
  struct Fighter {
    int x, y;
    long long G, C;
    long long cur_fuel, cur_miss;
    int target_idx;
  };
  vector<Fighter> fighters(k);
  for (int i = 0; i < k; i++) {
    int x, y;
    long long G, C;
    cin >> x >> y >> G >> C;
    fighters[i] = {x, y, G, C, 0LL, 0LL, -1};
  }
  // Assign targets
  vector<vector<int>> dist_to_adj(k, vector<int>(N_red, INT_MAX / 2));
  int dx[4] = {-1, 1, 0, 0};
  int dy[4] = {0, 0, -1, 1};
  auto valid_pos = [&](int x, int y, const set<pair<int, int>>& act) -> bool {
    if (x < 0 || x >= n || y < 0 || y >= m) return false;
    if (act.count({x, y})) return false;
    return true;
  };
  auto bfs_dist = [&](int sx, int sy, vector<vector<int>>& dist_map, const set<pair<int, int>>& act) {
    dist_map.assign(n, vector<int>(m, -1));
    queue<pair<int, int>> q;
    q.push({sx, sy});
    dist_map[sx][sy] = 0;
    while (!q.empty()) {
      auto [x, y] = q.front();
      q.pop();
      for (int d = 0; d < 4; d++) {
        int nx = x + dx[d], ny = y + dy[d];
        if (valid_pos(nx, ny, act) && dist_map[nx][ny] == -1) {
          dist_map[nx][ny] = dist_map[x][y] + 1;
          q.push({nx, ny});
        }
      }
    }
  };
  set<pair<int, int>> init_active = active_red_pos;
  for (int i = 0; i < k; i++) {
    int sx = fighters[i].x, sy = fighters[i].y;
    vector<vector<int>> dist(n, vector<int>(m, -1));
    bfs_dist(sx, sy, dist, init_active);
    for (int j = 0; j < N_red; j++) {
      int tx = reds[j].x, ty = reds[j].y;
      int mind = INT_MAX / 2;
      for (int d = 0; d < 4; d++) {
        int ax = tx + dx[d], ay = ty + dy[d];
        if (valid_pos(ax, ay, init_active) && dist[ax][ay] != -1) {
          mind = min(mind, dist[ax][ay]);
        }
      }
      dist_to_adj[i][j] = mind;
    }
  }
  // Sort reds by v desc
  vector<int> order(N_red);
  iota(order.begin(), order.end(), 0);
  sort(order.begin(), order.end(), [&](int a, int b) {
    if (reds[a].v != reds[b].v) return reds[a].v > reds[b].v;
    return a < b;
  });
  vector<bool> f_assigned(k, false);
  for (int idx : order) {
    int best_f = -1;
    int min_d = INT_MAX / 2;
    for (int f = 0; f < k; f++) {
      if (!f_assigned[f] && dist_to_adj[f][idx] < min_d) {
        min_d = dist_to_adj[f][idx];
        best_f = f;
      }
    }
    if (best_f != -1) {
      fighters[best_f].target_idx = idx;
      f_assigned[best_f] = true;
    }
  }
  // Remaining fighters to remaining reds
  vector<bool> r_assigned(N_red, false);
  for (int f = 0; f < k; f++) {
    int tid = fighters[f].target_idx;
    if (tid != -1) r_assigned[tid] = true;
  }
  vector<int> remain_r;
  for (int i = 0; i < N_red; i++) if (!r_assigned[i]) remain_r.push_back(i);
  sort(remain_r.begin(), remain_r.end(), [&](int a, int b) {
    if (reds[a].v != reds[b].v) return reds[a].v > reds[b].v;
    return a < b;
  });
  int rptr = 0;
  for (int f = 0; f < k; f++) {
    if (fighters[f].target_idx == -1 && rptr < remain_r.size()) {
      int rid = remain_r[rptr++];
      fighters[f].target_idx = rid;
    }
  }
  // Initial attack positions
  vector<pair<int, int>> attack_pos(k, {-1, -1});
  for (int f = 0; f < k; f++) {
    int tid = fighters[f].target_idx;
    if (tid == -1) continue;
    int tx = reds[tid].x, ty = reds[tid].y;
    vector<vector<int>> dist(n, vector<int>(m, -1));
    bfs_dist(fighters[f].x, fighters[f].y, dist, init_active);
    int mind = INT_MAX / 2;
    pair<int, int> best_a = {-1, -1};
    for (int d = 0; d < 4; d++) {
      int ax = tx + dx[d], ay = ty + dy[d];
      if (valid_pos(ax, ay, init_active) && dist[ax][ay] != -1 && dist[ax][ay] < mind) {
        mind = dist[ax][ay];
        best_a = {ax, ay};
      }
    }
    if (best_a.first != -1) attack_pos[f] = best_a;
  }
  // Simulation
  vector<int> f_posx(k), f_posy(k);
  vector<long long> f_fuel(k, 0LL), f_miss(k, 0LL);
  for (int i = 0; i < k; i++) {
    f_posx[i] = fighters[i].x;
    f_posy[i] = fighters[i].y;
    f_fuel[i] = 0;
    f_miss[i] = 0;
  }
  vector<long long> red_hits(N_red, 0LL);
  set<pair<int, int>> curr_active = active_red_pos;
  vector<vector<long long>> curr_fuel_sup = fuel_sup;
  vector<vector<long long>> curr_miss_sup = miss_sup;
  vector<int> goal_x(k, -1), goal_y(k, -1);
  vector<bool> goal_is_base(k, false);
  vector<deque<int>> current_path(k);
  const int MAX_FRAMES = 15000;
  for (int frame = 0; frame < MAX_FRAMES; frame++) {
    vector<string> frame_commands;
    for (int fid = 0; fid < k; fid++) {
      int fx = f_posx[fid], fy = f_posy[fid];
      long long& ff = f_fuel[fid];
      long long& fm = f_miss[fid];
      int tid = fighters[fid].target_idx;
      if (tid == -1) continue;
      bool is_on_blue = blue_bases.count({fx, fy});
      // Refuel and reload
      long long cap_f = fighters[fid].G;
      long long cap_m = fighters[fid].C;
      if (is_on_blue) {
        long long avail_f = curr_fuel_sup[fx][fy];
        if (ff < cap_f && avail_f > 0) {
          long long take = min(cap_f - ff, avail_f);
          string cmd = "fuel " + to_string(fid) + " " + to_string(take);
          frame_commands.push_back(cmd);
          ff += take;
          curr_fuel_sup[fx][fy] -= take;
        }
        long long avail_m = curr_miss_sup[fx][fy];
        if (fm < cap_m && avail_m > 0) {
          long long take = min(cap_m - fm, avail_m);
          string cmd = "missile " + to_string(fid) + " " + to_string(take);
          frame_commands.push_back(cmd);
          fm += take;
          curr_miss_sup[fx][fy] -= take;
        }
      }
      // Attack if adjacent
      bool target_active = curr_active.count({reds[tid].x, reds[tid].y});
      if (!target_active) {
        // Find new target
        int new_tid = -1;
        long long best_v = -1;
        for (int j = 0; j < N_red; j++) {
          if (curr_active.count({reds[j].x, reds[j].y}) && reds[j].v > best_v) {
            best_v = reds[j].v;
            new_tid = j;
          }
        }
        if (new_tid != -1) {
          fighters[fid].target_idx = new_tid;
          tid = new_tid;
          int tx = reds[tid].x, ty = reds[tid].y;
          vector<vector<int>> dist(n, vector<int>(m, -1));
          bfs_dist(fx, fy, dist, curr_active);
          int mind = INT_MAX / 2;
          pair<int, int> best_a = {-1, -1};
          for (int d = 0; d < 4; d++) {
            int ax = tx + dx[d], ay = ty + dy[d];
            if (valid_pos(ax, ay, curr_active) && dist[ax][ay] != -1 && dist[ax][ay] < mind) {
              mind = dist[ax][ay];
              best_a = {ax, ay};
            }
          }
          if (best_a.first != -1) {
            attack_pos[fid] = best_a;
          } else {
            fighters[fid].target_idx = -1;
            continue;
          }
        } else {
          fighters[fid].target_idx = -1;
          continue;
        }
      }
      pair<int, int> att_p = attack_pos[fid];
      if (att_p.first == -1) continue;
      int ax = att_p.first, ay = att_p.second;
      int tx = reds[tid].x, ty = reds[tid].y;
      target_active = curr_active.count({tx, ty});
      int attack_dir = -1;
      int delx = tx - fx;
      int dely = ty - fy;
      if (abs(delx) + abs(dely) == 1) {
        for (int d = 0; d < 4; d++) {
          if (dx[d] == delx && dy[d] == dely) {
            attack_dir = d;
            break;
          }
        }
      }
      if (attack_dir != -1 && fm > 0 && target_active) {
        long long rem = reds[tid].d - red_hits[tid];
        long long shoot = min(fm, rem);
        if (shoot > 0) {
          string cmd = "attack " + to_string(fid) + " " + to_string(attack_dir) + " " + to_string(shoot);
          frame_commands.push_back(cmd);
          fm -= shoot;
          red_hits[tid] += shoot;
          if (red_hits[tid] >= reds[tid].d) {
            curr_active.erase({tx, ty});
          }
        }
      }
      // Handle goals
      bool reached_goal = (goal_x[fid] != -1 && fx == goal_x[fid] && fy == goal_y[fid]);
      if (reached_goal) {
        current_path[fid].clear();
        if (goal_is_base[fid]) {
          // Set to attack
          vector<vector<int>> dist_to(n, vector<int>(m, -1));
          bfs_dist(fx, fy, dist_to, curr_active);
          int d_to_att = dist_to[ax][ay];
          if (d_to_att != -1 && ff >= d_to_att) {
            goal_x[fid] = ax;
            goal_y[fid] = ay;
            goal_is_base[fid] = false;
          } else {
            goal_x[fid] = -1;
          }
        } else {
          goal_x[fid] = -1;
        }
      }
      // Movement
      bool has_goal = (goal_x[fid] != -1);
      reached_goal = has_goal && (fx == goal_x[fid] && fy == goal_y[fid]);
      if (has_goal && !reached_goal) {
        if (current_path[fid].empty()) {
          // Compute path
          vector<vector<int>> distt(n, vector<int>(m, -1));
          vector<vector<pair<int, int>>> parent(n, vector<pair<int, int>>(m, {-1, -1}));
          queue<pair<int, int>> qq;
          qq.push({fx, fy});
          distt[fx][fy] = 0;
          bool fnd = false;
          while (!qq.empty()) {
            auto [xx, yy] = qq.front();
            qq.pop();
            if (xx == goal_x[fid] && yy == goal_y[fid]) {
              fnd = true;
              break;
            }
            for (int dd = 0; dd < 4; dd++) {
              int nxx = xx + dx[dd], nyy = yy + dy[dd];
              if (valid_pos(nxx, nyy, curr_active) && distt[nxx][nyy] == -1) {
                distt[nxx][nyy] = distt[xx][yy] + 1;
                parent[nxx][nyy] = {xx, yy};
                qq.push({nxx, nyy});
              }
            }
          }
          if (distt[goal_x[fid]][goal_y[fid]] == -1) {
            goal_x[fid] = -1;
            continue;
          }
          // Reconstruct dirs
          deque<int> pdirs;
          pair<int, int> cu = {goal_x[fid], goal_y[fid]};
          pair<int, int> start = {fx, fy};
          while (cu != start) {
            auto pr = parent[cu.first][cu.second];
            int delx = cu.first - pr.first;
            int dely = cu.second - pr.second;
            int pdir = -1;
            for (int dd = 0; dd < 4; dd++) {
              if (dx[dd] == delx && dy[dd] == dely) {
                pdir = dd;
                break;
              }
            }
            if (pdir == -1) assert(false);
            pdirs.push_front(pdir);
            cu = pr;
          }
          current_path[fid] = pdirs;
        }
        if (!current_path[fid].empty() && ff > 0) {
          int ndir = current_path[fid].front();
          int nx = fx + dx[ndir];
          int ny = fy + dy[ndir];
          string cmd = "move " + to_string(fid) + " " + to_string(ndir);
          frame_commands.push_back(cmd);
          f_posx[fid] = nx;
          f_posy[fid] = ny;
          ff--;
          current_path[fid].pop_front();
        }
      }
      // Decide next goal if no goal
      if (goal_x[fid] == -1) {
        bool at_att_pos = (fx == ax && fy == ay);
        target_active = curr_active.count({tx, ty});
        if (!target_active) continue;
        long long rem_d = reds[tid].d - red_hits[tid];
        bool need_base_now = (fm == 0 && rem_d > 0) || (ff < 20);
        if (at_att_pos) {
          if (need_base_now) {
            // Go to nearest base
            vector<vector<int>> dist(n, vector<int>(m, -1));
            bfs_dist(fx, fy, dist, curr_active);
            int min_bd = INT_MAX / 2;
            pair<int, int> best_b = {-1, -1};
            for (auto bp : blue_bases) {
              int dd = dist[bp.first][bp.second];
              if (dd != -1 && dd < min_bd) {
                min_bd = dd;
                best_b = bp;
              }
            }
            if (best_b.first != -1 && min_bd <= ff) {
              goal_x[fid] = best_b.first;
              goal_y[fid] = best_b.second;
              goal_is_base[fid] = true;
              current_path[fid].clear();
            }
          }
        } else {
          // Not at att, check if can go
          vector<vector<int>> dist(n, vector<int>(m, -1));
          bfs_dist(fx, fy, dist, curr_active);
          int d_to_att = dist[ax][ay];
          if (d_to_att == -1 || d_to_att > ff) {
            // Go to nearest base first
            int min_bd = INT_MAX / 2;
            pair<int, int> best_b = {-1, -1};
            for (auto bp : blue_bases) {
              int dd = dist[bp.first][bp.second];
              if (dd != -1 && dd < min_bd) {
                min_bd = dd;
                best_b = bp;
              }
            }
            if (best_b.first != -1 && min_bd <= ff) {
              goal_x[fid] = best_b.first;
              goal_y[fid] = best_b.second;
              goal_is_base[fid] = true;
              current_path[fid].clear();
            }
          } else {
            goal_x[fid] = ax;
            goal_y[fid] = ay;
            goal_is_base[fid] = false;
            current_path[fid].clear();
          }
        }
      }
    }
    // Output
    for (auto& c : frame_commands) {
      cout << c << '\n';
    }
    cout << "OK\n";
    // Check if done
    if (curr_active.empty()) break;
  }
  return 0;
}