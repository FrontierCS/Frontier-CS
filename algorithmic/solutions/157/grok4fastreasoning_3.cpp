#include <bits/stdc++.h>
using namespace std;

int main() {
  int N, T;
  cin >> N >> T;
  vector<string> input(N);
  for (int i = 0; i < N; i++) cin >> input[i];
  auto h2i = [](char c) -> int {
    if (c >= '0' && c <= '9') return c - '0';
    return 10 + (c - 'a');
  };
  vector<vector<int>> masks(N, vector<int>(N));
  int ex = -1, ey = -1;
  for (int i = 0; i < N; i++) {
    for (int j = 0; j < N; j++) {
      masks[i][j] = h2i(input[i][j]);
      if (masks[i][j] == 0) {
        ex = i;
        ey = j;
      }
    }
  }
  int empty_init_k = ex * N + ey;
  int NN = N * N;
  int MM = NN - 1;
  vector<int> initial_mask(NN, 0);
  for (int i = 0; i < N; i++) {
    for (int j = 0; j < N; j++) {
      initial_mask[i * N + j] = masks[i][j];
    }
  }
  vector<vector<int>> target_tile(N, vector<int>(N, -1));
  vector<bool> used(NN, false);
  used[empty_init_k] = true;
  vector<pair<int, int>> order;
  for (int i = 0; i < N; i++) {
    for (int j = 0; j < N; j++) {
      if (i == N - 1 && j == N - 1) continue;
      order.emplace_back(i, j);
    }
  }
  function<bool(int)> dfs = [&](int idx) -> bool {
    if (idx == MM) return true;
    auto [r, c] = order[idx];
    for (int pid = 0; pid < NN; pid++) {
      if (used[pid]) continue;
      int msk = initial_mask[pid];
      bool ok = true;
      // left
      if (c > 0) {
        int lpid = target_tile[r][c - 1];
        int lmsk = initial_mask[lpid];
        bool my_left = (msk & 1) != 0;
        bool l_right = (lmsk & 4) != 0;
        if (my_left != l_right) ok = false;
      } else {
        if ((msk & 1) != 0) ok = false;
      }
      // up
      if (r > 0) {
        int upid = target_tile[r - 1][c];
        int upmsk = initial_mask[upid];
        bool my_up = (msk & 2) != 0;
        bool up_down = (upmsk & 8) != 0;
        if (my_up != up_down) ok = false;
      } else {
        if ((msk & 2) != 0) ok = false;
      }
      // right forbidden
      bool no_right = (c == N - 1) || (r == N - 1 && c == N - 2);
      if (no_right && (msk & 4) != 0) ok = false;
      // down forbidden
      bool no_down = (r == N - 1) || (r == N - 2 && c == N - 1);
      if (no_down && (msk & 8) != 0) ok = false;
      if (!ok) continue;
      target_tile[r][c] = pid;
      used[pid] = true;
      if (dfs(idx + 1)) return true;
      used[pid] = false;
      target_tile[r][c] = -1;
    }
    return false;
  };
  dfs(0);
  // now target_tile ready
  // tile nums
  vector<int> k_to_num(NN, 0);
  int tnum = 1;
  for (int k = 0; k < NN; k++) {
    if (k != empty_init_k) k_to_num[k] = tnum++;
  }
  vector<int> target_board(NN, 0);
  for (int i = 0; i < N; i++) {
    for (int j = 0; j < N; j++) {
      int k = i * N + j;
      if (i == N - 1 && j == N - 1) {
        target_board[k] = 0;
        continue;
      }
      int pid = target_tile[i][j];
      target_board[k] = k_to_num[pid];
    }
  }
  vector<int> target_k_of_tnum(NN + 1, -1);
  for (int k = 0; k < NN; k++) {
    int tn = target_board[k];
    if (tn != 0) target_k_of_tnum[tn] = k;
  }
  // target i j for each tnum
  vector<int> target_ii(NN + 1), target_jj(NN + 1);
  for (int t = 1; t <= MM; t++) {
    int tk = target_k_of_tnum[t];
    target_ii[t] = tk / N;
    target_jj[t] = tk % N;
  }
  // init_board
  vector<int> the_board(NN, 0);
  int init_empty_k = ex * N + ey;
  for (int i = 0; i < N; i++) {
    for (int j = 0; j < N; j++) {
      int k = i * N + j;
      int m = masks[i][j];
      if (m == 0) {
        the_board[k] = 0;
      } else {
        the_board[k] = k_to_num[k];
      }
    }
  }
  auto manh = [](int i1, int j1, int i2, int j2) { return abs(i1 - i2) + abs(j1 - j2); };
  auto get_hh = [&](const vector<int>& bd) -> int {
    int hh = 0;
    for (int k = 0; k < NN; k++) {
      int t = bd[k];
      if (t == 0) continue;
      int ii = k / N, jj = k % N;
      hh += manh(ii, jj, target_ii[t], target_jj[t]);
    }
    return hh;
  };
  int initial_hh = get_hh(the_board);
  // directions
  int dirs[4][2] = {{-1, 0}, {1, 0}, {0, -1}, {0, 1}};
  char move_chars[4] = {'U', 'D', 'L', 'R'};
  // IDA*
  string solution = "";
  int bound = initial_hh;
  auto search_ida = [&](auto&& self, int g, int empty_k, string path, int curr_h) -> bool {
    int f = g + curr_h;
    if (f > bound) return false;
    if (curr_h == 0) {
      solution = path;
      return true;
    }
    if (g > T) return false;
    int ei = empty_k / N, ej = empty_k % N;
    for (int d = 0; d < 4; d++) {
      int ni = ei + dirs[d][0], nj = ej + dirs[d][1];
      if (ni < 0 || ni >= N || nj < 0 || nj >= N) continue;
      int tile_k = ni * N + nj;
      int tile_t = the_board[tile_k];
      // old m
      int old_m = manh(ni, nj, target_ii[tile_t], target_jj[tile_t]);
      // new m
      int nni = empty_k / N, nnj = empty_k % N;
      int new_m = manh(nni, nnj, target_ii[tile_t], target_jj[tile_t]);
      int delta = new_m - old_m;
      // swap
      swap(the_board[empty_k], the_board[tile_k]);
      string new_path = path + move_chars[d];
      if (self(self, g + 1, tile_k, new_path, curr_h + delta)) return true;
      // back
      swap(the_board[empty_k], the_board[tile_k]);
    }
    return false;
  };
  bool found_sol = false;
  while (bound <= T + 100) {  // margin
    solution = "";
    the_board = init_board;  // reset? No, since backtrack restores
    if (search_ida(search_ida, 0, init_empty_k, "", initial_hh)) {
      found_sol = true;
      break;
    }
    bound += 1;
  }
  if (found_sol && (int)solution.size() <= T) {
    cout << solution << endl;
  } else {
    cout << "" << endl;
  }
  return 0;
}