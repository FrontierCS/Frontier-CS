#include <bits/stdc++.h>
using namespace std;

uint64_t get_hash(const vector<int>& v) {
  uint64_t h = 0;
  for (int val : v) {
    h = h * 1009ULL + (uint64_t)val;
  }
  return h;
}

vector<int> get_greedy_r(const vector<int>& current, const vector<int>& TT, int si) {
  vector<pair<int, int>> typelist;
  for (int c = 0; c < 128; c++) {
    if (current[c] > 0) typelist.emplace_back(current[c] - TT[c], c);
  }
  sort(typelist.rbegin(), typelist.rend());
  vector<int> rr(128, 0);
  int rem = si;
  for (auto [exx, c] : typelist) {
    if (rem == 0) break;
    int tk = min(rem, current[c]);
    rr[c] = tk;
    rem -= tk;
  }
  return rr;
}

vector<tuple<int, int, int>> get_rearrange_ops(vector<vector<char>> start_grid, const vector<vector<char>>& goal, int n, int m) {
  vector<vector<char>> local = start_grid;
  vector<tuple<int, int, int>> ops;
  int N = n * m;
  vector<pair<int, int>> dirs = {{-1, 0}, {1, 0}, {0, -1}, {0, 1}};
  for (int pid = 0; pid < N; pid++) {
    int row = pid / m;
    int col = pid % m;
    if (local[row][col] == goal[row][col]) continue;
    char needed = goal[row][col];
    // BFS to find closest source
    vector<vector<int>> dist(n, vector<int>(m, INT_MAX / 2));
    vector<vector<pair<int, int>>> parent(n, vector<pair<int, int>>(m, {-1, -1}));
    vector<vector<bool>> vis(n, vector<bool>(m, false));
    queue<pair<int, int>> qq;
    qq.push({row, col});
    vis[row][col] = true;
    dist[row][col] = 0;
    pair<int, int> best_source = {-1, -1};
    int min_d = INT_MAX / 2;
    while (!qq.empty()) {
      auto [cr, cc] = qq.front();
      qq.pop();
      int cid = cr * m + cc;
      if (cid < pid) continue; // should not happen
      if (local[cr][cc] == needed && dist[cr][cc] < min_d && cid >= pid) {
        min_d = dist[cr][cc];
        best_source = {cr, cc};
      }
      for (auto [dr, dc] : dirs) {
        int nr = cr + dr, nc = cc + dc;
        if (nr >= 0 && nr < n && nc >= 0 && nc < m && !vis[nr][nc]) {
          int nid = nr * m + nc;
          if (nid >= pid) {
            vis[nr][nc] = true;
            dist[nr][nc] = dist[cr][cc] + 1;
            parent[nr][nc] = {cr, cc};
            qq.push({nr, nc});
          }
        }
      }
    }
    if (best_source.first == -1) {
      // impossible, but should not
      continue;
    }
    // reconstruct path from best_source to {row,col}
    vector<pair<int, int>> path;
    pair<int, int> at = best_source;
    while (at != make_pair(row, col)) {
      path.push_back(at);
      at = parent[at.first][at.second];
    }
    path.push_back({row, col});
    reverse(path.begin(), path.end()); // path[0] = {row,col}, last = source
    // now apply swaps
    for (size_t ii = path.size() - 1; ii > 0; ii--) {
      auto [r1, c1] = path[ii - 1];
      auto [r2, c2] = path[ii];
      int opr, x, y;
      if (r1 == r2) {
        // horizontal
        int left_c = min(c1, c2);
        x = r1 + 1;
        y = left_c + 1;
        opr = -1;
      } else {
        // vertical
        int upper_r = min(r1, r2);
        x = upper_r + 1;
        y = c1 + 1;
        opr = -4;
      }
      ops.emplace_back(opr, x, y);
      // swap local
      swap(local[r1][c1], local[r2][c2]);
    }
  }
  return ops;
}

int main() {
  ios::sync_with_stdio(false);
  cin.tie(nullptr);
  int n, m, k;
  cin >> n >> m >> k;
  string dummy;
  getline(cin, dummy);
  vector<vector<char>> initial(n, vector<char>(m));
  for (int i = 0; i < n; i++) {
    string s;
    getline(cin, s);
    for (int j = 0; j < m; j++) initial[i][j] = s[j];
  }
  string empt;
  getline(cin, empt);
  vector<vector<char>> targ(n, vector<char>(m));
  for (int i = 0; i < n; i++) {
    string s;
    getline(cin, s);
    for (int j = 0; j < m; j++) targ[i][j] = s[j];
  }
  getline(cin, empt);
  vector<int> f_np(k), f_mp(k), f_size(k);
  vector<vector<vector<char>>> formulas(k);
  vector<vector<int>> fcount(k, vector<int>(128, 0));
  for (int ki = 0; ki < k; ki++) {
    getline(cin, empt);
    string ln;
    getline(cin, ln);
    stringstream ss(ln);
    ss >> f_np[ki] >> f_mp[ki];
    f_size[ki] = f_np[ki] * f_mp[ki];
    formulas[ki].resize(f_np[ki], vector<char>(f_mp[ki]));
    for (int i = 0; i < f_np[ki]; i++) {
      string s;
      getline(cin, s);
      for (int j = 0; j < f_mp[ki]; j++) {
        formulas[ki][i][j] = s[j];
        fcount[ki][(int)s[j]]++;
      }
    }
  }
  vector<int> count_S(128, 0), count_T(128, 0);
  for (auto& row : initial)
    for (char ch : row) count_S[(int)ch]++;
  for (auto& row : targ)
    for (char ch : row) count_T[(int)ch]++;
  bool same = (count_S == count_T);
  vector<int> the_seq;
  if (!same) {
    auto get_h = get_hash;
    uint64_t h0 = get_h(count_S);
    uint64_t th = get_h(count_T);
    queue<uint64_t> q;
    unordered_set<uint64_t> visited;
    unordered_map<uint64_t, pair<uint64_t, int>> came_from;
    unordered_map<uint64_t, vector<int>> state_to_count;
    q.push(h0);
    visited.insert(h0);
    came_from[h0] = {0ULL, -1};
    state_to_count[h0] = count_S;
    bool foundd = false;
    while (!q.empty() && !foundd) {
      uint64_t curh = q.front();
      q.pop();
      vector<int> current = state_to_count[curh];
      for (int i = 0; i < k; i++) {
        vector<int> rr = get_greedy_r(current, count_T, f_size[i]);
        vector<int> newc(128);
        bool okk = true;
        for (int c = 0; c < 128; c++) {
          int temp = current[c] - rr[c];
          if (temp < 0) okk = false;
          newc[c] = temp + fcount[i][c];
        }
        if (!okk) continue;
        uint64_t nh = get_h(newc);
        bool is_target = (nh == th) && (newc == count_T);
        if (is_target) {
          foundd = true;
          uint64_t temp = curh;
          the_seq.clear();
          while (temp != h0) {
            auto [prv, prs] = came_from[temp];
            the_seq.push_back(prs);
            temp = prv;
          }
          reverse(the_seq.begin(), the_seq.end());
          the_seq.push_back(i);
          break;
        }
        if (state_to_count.find(nh) == state_to_count.end()) {
          state_to_count[nh] = newc;
          visited.insert(nh);
          q.push(nh);
          came_from[nh] = {curh, i};
        } else if (state_to_count[nh] != newc) {
          // collision, skip
          continue;
        }
      }
    }
    same = foundd;
  }
  vector<tuple<int, int, int>> all_ops;
  if (same) {
    vector<int> seqq = the_seq;
    vector<vector<int>> the_rs(seqq.size());
    vector<vector<int>> before_c(seqq.size() + 1);
    before_c[0] = count_S;
    vector<int> simm = count_S;
    for (size_t st = 0; st < seqq.size(); st++) {
      int ii = seqq[st];
      vector<int> rrr = get_greedy_r(simm, count_T, f_size[ii]);
      the_rs[st] = rrr;
      for (int c = 0; c < 128; c++) {
        simm[c] -= rrr[c];
        simm[c] += fcount[ii][c];
      }
      before_c[st + 1] = simm;
    }
    vector<vector<char>> curr_sim = initial;
    if (seqq.empty()) {
      auto opss = get_rearrange_ops(initial, targ, n, m);
      all_ops = opss;
    } else {
      for (size_t st = 0; st < seqq.size(); st++) {
        int ii = seqq[st];
        vector<int> temp_cc = before_c[st];
        vector<char> sacrifice_list;
        for (int ccc = 0; ccc < 128; ccc++) {
          for (int tt = 0; tt < the_rs[st][ccc]; tt++) {
            sacrifice_list.push_back((char)ccc);
          }
        }
        int px = 0, py = 0;
        int rnp = f_np[ii], rmp = f_mp[ii];
        vector<pair<int, int>> rectt;
        for (int a = 0; a < rnp; a++)
          for (int b = 0; b < rmp; b++) rectt.emplace_back(px + a, py + b);
        vector<pair<int, int>> nonr;
        set<pair<int, int>> rect_set(rectt.begin(), rectt.end());
        for (int ii2 = 0; ii2 < n; ii2++)
          for (int jj2 = 0; jj2 < m; jj2++)
            if (rect_set.count({ii2, jj2}) == 0) nonr.emplace_back(ii2, jj2);
        vector<vector<char>> temp_targ(n, vector<char>(m));
        for (size_t idx = 0; idx < rectt.size(); idx++) {
          auto [ii2, jj2] = rectt[idx];
          temp_targ[ii2][jj2] = sacrifice_list[idx];
        }
        vector<int> remain_c = temp_cc;
        for (char chh : sacrifice_list) remain_c[(int)chh]--;
        vector<char> remain_l;
        for (int ccc = 0; ccc < 128; ccc++)
          for (int tt = 0; tt < remain_c[ccc]; tt++) remain_l.push_back((char)ccc);
        for (size_t idx = 0; idx < nonr.size(); idx++) {
          auto [ii2, jj2] = nonr[idx];
          temp_targ[ii2][jj2] = remain_l[idx];
        }
        auto ops_temp = get_rearrange_ops(curr_sim, temp_targ, n, m);
        for (auto& ttt : ops_temp) all_ops.push_back(ttt);
        curr_sim = temp_targ;
        int x1b = px + 1, y1b = py + 1;
        all_ops.emplace_back(ii + 1, x1b, y1b);
        for (int a = 0; a < rnp; a++)
          for (int b = 0; b < rmp; b++) {
            curr_sim[px + a][py + b] = formulas[ii][a][b];
          }
      }
      auto ops_final = get_rearrange_ops(curr_sim, targ, n, m);
      for (auto& ttt : ops_final) all_ops.push_back(ttt);
    }
    cout << all_ops.size() << '\n';
    for (auto [op, xx, yy] : all_ops) {
      cout << op << " " << xx << " " << yy << '\n';
    }
  } else {
    cout << -1 << '\n';
  }
  return 0;
}