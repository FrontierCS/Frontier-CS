#include <bits/stdc++.h>
using namespace std;

int main() {
  int N, T;
  cin >> N >> T;
  vector<string> input(N);
  for (auto& s : input) cin >> s;
  int mask_board[10][10];
  int ex, ey;
  multiset<int> avail;
  for (int i = 0; i < N; i++) {
    for (int j = 0; j < N; j++) {
      char ch = input[i][j];
      int val = (ch >= '0' && ch <= '9') ? ch - '0' : 10 + (ch - 'a');
      mask_board[i][j] = val;
      if (val == 0) {
        ex = i;
        ey = j;
      } else {
        avail.insert(val);
      }
    }
  }
  vector<pair<int, int>> positions;
  for (int i = 0; i < N; i++) {
    for (int j = 0; j < N; j++) {
      if (i == N - 1 && j == N - 1) continue;
      positions.emplace_back(i, j);
    }
  }
  int num_pos = positions.size();
  int grid_mask[100];
  int target_mask[10][10];
  auto compute_connected = [&](const int gmask[100]) -> bool {
    int par[100];
    for (int ii = 0; ii < N * N; ii++) par[ii] = ii;
    function<int(int)> find = [&](int x) -> int {
      return par[x] == x ? x : par[x] = find(par[x]);
    };
    int empty_f = (N - 1) * N + (N - 1);
    for (int i = 0; i < N - 1; i++) {
      for (int j = 0; j < N; j++) {
        int f1 = i * N + j;
        int f2 = (i + 1) * N + j;
        if (f1 == empty_f || f2 == empty_f) continue;
        int m1 = gmask[f1];
        int m2 = gmask[f2];
        if ((m1 & 8) && (m2 & 2)) {
          int p1 = find(f1);
          int p2 = find(f2);
          if (p1 != p2) par[p1] = p2;
        }
      }
    }
    for (int i = 0; i < N; i++) {
      for (int j = 0; j < N - 1; j++) {
        int f1 = i * N + j;
        int f2 = i * N + j + 1;
        if (f1 == empty_f || f2 == empty_f) continue;
        int m1 = gmask[f1];
        int m2 = gmask[f2];
        if ((m1 & 4) && (m2 & 1)) {
          int p1 = find(f1);
          int p2 = find(f2);
          if (p1 != p2) par[p1] = p2;
        }
      }
    }
    int root = find(0);
    for (int f = 0; f < N * N; f++) {
      if (f == empty_f) continue;
      if (find(f) != root) return false;
    }
    return true;
  };
  function<bool(int, multiset<int>&)> dfs = [&](int k, multiset<int>& av) -> bool {
    if (k == num_pos) {
      if (!compute_connected(grid_mask)) return false;
      for (int p = 0; p < num_pos; p++) {
        auto [i, j] = positions[p];
        target_mask[i][j] = grid_mask[i * N + j];
      }
      target_mask[N - 1][N - 1] = 0;
      return true;
    }
    auto [ci, cj] = positions[k];
    int flat = ci * N + cj;
    int req_l = 0;
    if (cj > 0) {
      int left_f = ci * N + (cj - 1);
      req_l = (grid_mask[left_f] & 4) ? 1 : 0;
    }
    int req_u = 0;
    if (ci > 0) {
      int above_f = (ci - 1) * N + cj;
      req_u = (grid_mask[above_f] & 8) ? 1 : 0;
    }
    for (int m = 1; m <= 15; m++) {
      if (av.find(m) == av.end()) continue;
      int this_l = (m & 1) ? 1 : 0;
      int this_u = (m & 2) ? 1 : 0;
      if (this_l != req_l || this_u != req_u) continue;
      int this_r = (m & 4) ? 1 : 0;
      int this_d = (m & 8) ? 1 : 0;
      bool ok = true;
      if (cj == N - 1 && this_r != 0) ok = false;
      if (ci == N - 1 && this_d != 0) ok = false;
      if (ci == N - 2 && cj == N - 1 && this_d != 0) ok = false;
      if (ci == N - 1 && cj == N - 2 && this_r != 0) ok = false;
      if (!ok) continue;
      av.erase(av.find(m));
      grid_mask[flat] = m;
      if (dfs(k + 1, av)) return true;
      av.insert(m);
    }
    return false;
  };
  multiset<int> available = avail;
  bool found = dfs(0, available);
  // proceed assuming found
  string sequence = "";
  double temp = 5.0;
  double cooling = 0.999;
  int full_size = N * N;
  int cur_h = 0;
  for (int i = 0; i < N; i++)
    for (int j = 0; j < N; j++)
      if (mask_board[i][j] == target_mask[i][j]) cur_h++;
  srand(42);
  int cur_k = 0;
  while (cur_k < T) {
    if (cur_h == full_size) break;
    vector<char> poss_dirs;
    vector<pair<int, int>> poss_new_e;
    if (ex > 0) {
      poss_dirs.push_back('U');
      poss_new_e.emplace_back(ex - 1, ey);
    }
    if (ex < N - 1) {
      poss_dirs.push_back('D');
      poss_new_e.emplace_back(ex + 1, ey);
    }
    if (ey > 0) {
      poss_dirs.push_back('L');
      poss_new_e.emplace_back(ex, ey - 1);
    }
    if (ey < N - 1) {
      poss_dirs.push_back('R');
      poss_new_e.emplace_back(ex, ey + 1);
    }
    if (poss_dirs.empty()) break;
    int idx = rand() % poss_dirs.size();
    char dir = poss_dirs[idx];
    auto [nx, ny] = poss_new_e[idx];
    int ax = ex, ay = ey;
    int bx = nx, by = ny;
    int M = mask_board[bx][by];
    int old_contrib = (0 == target_mask[ax][ay] ? 1 : 0) + (M == target_mask[bx][by] ? 1 : 0);
    int new_contrib = (M == target_mask[ax][ay] ? 1 : 0) + (0 == target_mask[bx][by] ? 1 : 0);
    int delta = new_contrib - old_contrib;
    bool accept = false;
    if (delta >= 0) {
      accept = true;
    } else {
      double p = exp(static_cast<double>(delta) / temp);
      if (static_cast<double>(rand()) / RAND_MAX < p) accept = true;
    }
    if (accept) {
      mask_board[ax][ay] = M;
      mask_board[bx][by] = 0;
      ex = nx;
      ey = ny;
      cur_h += delta;
      sequence += dir;
      cur_k++;
    }
    temp *= cooling;
    if (temp < 0.01) break;
  }
  cout << sequence << endl;
  return 0;
}