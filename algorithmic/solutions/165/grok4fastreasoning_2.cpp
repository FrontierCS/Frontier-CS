#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int N, M;
  cin >> N >> M;
  int si, sj;
  cin >> si >> sj;
  vector<string> grid(N);
  for (auto& s : grid) cin >> s;
  vector<pair<int, int>> posi[26];
  for (int i = 0; i < N; i++) {
    for (int j = 0; j < N; j++) {
      char ch = grid[i][j];
      posi[ch - 'A'].emplace_back(i, j);
    }
  }
  vector<string> ts(M);
  for (auto& s : ts) cin >> s;
  const int MM = 200;
  int over[MM][MM];
  memset(over, 0, sizeof(over));
  for (int i = 0; i < M; i++) {
    for (int j = 0; j < M; j++) {
      if (i == j) continue;
      for (int o = 4; o >= 1; o--) {
        if (ts[i].substr(5 - o, o) == ts[j].substr(0, o)) {
          over[i][j] = o;
          break;
        }
      }
    }
  }
  int min_len = INT_MAX;
  string best_S;
  for (int start = 0; start < M; start++) {
    vector<bool> used(M, false);
    string curs = ts[start];
    used[start] = true;
    int cur_end = start;
    int num_used = 1;
    while (num_used < M) {
      int max_o = -1;
      int next = -1;
      for (int j = 0; j < M; j++) {
        if (used[j]) continue;
        int o = over[cur_end][j];
        if (o > max_o || (o == max_o && j < next)) {
          max_o = o;
          next = j;
        }
      }
      if (next == -1) break;
      string add = ts[next].substr(max_o);
      curs += add;
      used[next] = true;
      cur_end = next;
      num_used++;
    }
    int this_len = curs.size();
    if (this_len < min_len) {
      min_len = this_len;
      best_S = curs;
    }
  }
  string S = best_S;
  int L = S.size();
  const int INF = 1e9 + 5;
  const int MAXL = 1005;
  const int NN = 15;
  int dp[MAXL][NN][NN];
  memset(dp, 0x3f, sizeof(dp));
  if (L >= 1) {
    char need = S[0];
    auto& cands = posi[need - 'A'];
    for (auto [i, j] : cands) {
      int d = abs(si - i) + abs(sj - j);
      dp[1][i][j] = d + 1;
    }
  }
  for (int kk = 2; kk <= L; kk++) {
    char prev_ch = S[kk - 2];
    char curr_ch = S[kk - 1];
    auto& prevs = posi[prev_ch - 'A'];
    auto& currs = posi[curr_ch - 'A'];
    for (auto [i, j] : currs) {
      dp[kk][i][j] = INF;
    }
    for (auto [pi, pj] : prevs) {
      if (dp[kk - 1][pi][pj] >= INF) continue;
      for (auto [ei, ej] : currs) {
        int d = abs(pi - ei) + abs(pj - ej);
        int newc = dp[kk - 1][pi][pj] + d + 1;
        if (newc < dp[kk][ei][ej]) {
          dp[kk][ei][ej] = newc;
        }
      }
    }
  }
  int min_cost = INF;
  int ei = -1, ej = -1;
  for (int i = 0; i < N; i++) {
    for (int j = 0; j < N; j++) {
      if (dp[L][i][j] < min_cost) {
        min_cost = dp[L][i][j];
        ei = i;
        ej = j;
      }
    }
  }
  vector<pair<int, int>> path;
  if (L == 0) {
    // empty, but shouldn't happen
  } else {
    int ci = ei, cj = ej;
    path.emplace_back(ci, cj);
    for (int kk = L; kk > 1; kk--) {
      char prev_ch = S[kk - 2];
      auto& prevs = posi[prev_ch - 'A'];
      bool found = false;
      for (auto [pi, pj] : prevs) {
        int d = abs(pi - ci) + abs(pj - cj);
        if (dp[kk - 1][pi][pj] < INF && dp[kk - 1][pi][pj] + d + 1 == dp[kk][ci][cj]) {
          path.emplace_back(pi, pj);
          ci = pi;
          cj = pj;
          found = true;
          break;
        }
      }
      assert(found);
    }
    reverse(path.begin(), path.end());
  }
  for (auto [x, y] : path) {
    cout << x << " " << y << '\n';
  }
}