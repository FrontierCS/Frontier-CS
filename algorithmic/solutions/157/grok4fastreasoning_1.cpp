#include <bits/stdc++.h>
using namespace std;

int hex_val(char c) {
  if (isdigit(c)) return c - '0';
  return 10 + tolower(c) - 'a';
}

bool place(int r, int c, array<int, 16>& cnt, vector<vector<int>>& targ, int NN) {
  if (r == NN) return true;
  int maxc = (r == NN - 1 ? NN - 2 : NN - 1);
  if (c > maxc) {
    return place(r + 1, 0, cnt, targ, NN);
  }
  if (r == NN - 1 && c == NN - 1) {
    return place(r + 1, 0, cnt, targ, NN);
  }
  // place at r,c
  int req_left = 0;
  if (c > 0) {
    int pm = targ[r][c - 1];
    req_left = (pm & 4) ? 1 : 0;
  }
  int req_up = 0;
  if (r > 0) {
    int am = targ[r - 1][c];
    req_up = (am & 8) ? 1 : 0;
  }
  bool is_adj_empty = false;
  int towards = 0;
  if (r == NN - 2 && c == NN - 1) {
    is_adj_empty = true;
    towards = 8; // down
  } else if (r == NN - 1 && c == NN - 2) {
    is_adj_empty = true;
    towards = 4; // right
  }
  for (int k = 1; k < 16; k++) {
    if (cnt[k] == 0) continue;
    int has_left = (k & 1) ? 1 : 0;
    if (has_left != req_left) continue;
    int has_up = (k & 2) ? 1 : 0;
    if (has_up != req_up) continue;
    if (is_adj_empty && (k & towards) != 0) continue;
    targ[r][c] = k;
    cnt[k]--;
    if (place(r, c + 1, cnt, targ, NN)) return true;
    cnt[k]++;
    targ[r][c] = 0;
  }
  return false;
}

int main() {
  int N, T;
  cin >> N >> T;
  vector<vector<int>> initial(N, vector<int>(N));
  array<int, 16> cnt{};
  int ex = -1, ey = -1;
  for (int i = 0; i < N; i++) {
    for (int j = 0; j < N; j++) {
      string s;
      cin >> s;
      char ch = s[0];
      int val = hex_val(ch);
      initial[i][j] = val;
      if (val == 0) {
        ex = i;
        ey = j;
      } else {
        cnt[val]++;
      }
    }
  }
  // reconstruct target
  vector<vector<int>> targ(N, vector<int>(N, 0));
  array<int, 16> work_cnt = cnt;
  bool success = place(0, 0, work_cnt, targ, N);
  // now generate moves to move empty to bottom right
  int tx = N - 1, ty = N - 1;
  if (ex == tx && ey == ty) {
    cout << "" << endl;
    return 0;
  }
  int dr[4] = {-1, 1, 0, 0};
  int dc[4] = {0, 0, -1, 1};
  char chs[4] = {'U', 'D', 'L', 'R'};
  vector<vector<int>> dist(N, vector<int>(N, -1));
  vector<vector<pair<int, int>>> par(N, vector<pair<int, int>>(N, {-1, -1}));
  queue<pair<int, int>> q;
  q.push({ex, ey});
  dist[ex][ey] = 0;
  while (!q.empty()) {
    auto [r, c] = q.front();
    q.pop();
    for (int d = 0; d < 4; d++) {
      int nr = r + dr[d];
      int nc = c + dc[d];
      if (nr >= 0 && nr < N && nc >= 0 && nc < N && dist[nr][nc] == -1) {
        dist[nr][nc] = dist[r][c] + 1;
        par[nr][nc] = {r, c};
        q.push({nr, nc});
      }
    }
  }
  // reconstruct
  vector<char> path;
  pair<int, int> cur = {tx, ty};
  while (cur.first != ex || cur.second != ey) {
    auto p = par[cur.first][cur.second];
    int ddr = cur.first - p.first;
    int ddc = cur.second - p.second;
    char ch;
    if (ddr == -1 && ddc == 0) ch = 'U';
    else if (ddr == 1 && ddc == 0) ch = 'D';
    else if (ddr == 0 && ddc == -1) ch = 'L';
    else ch = 'R';
    path.push_back(ch);
    cur = p;
  }
  reverse(path.begin(), path.end());
  string seq(path.begin(), path.end());
  cout << seq << endl;
  return 0;
}