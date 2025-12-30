#include <bits/stdc++.h>
using namespace std;

int main() {
  int N, M;
  cin >> N >> M;
  int si, sj;
  cin >> si >> sj;
  vector<string> grid(N);
  for (int i = 0; i < N; i++) cin >> grid[i];
  vector<string> tks(M);
  for (int i = 0; i < M; i++) cin >> tks[i];
  vector<vector<pair<int, int>>> posi(26);
  for (int i = 0; i < N; i++) {
    for (int j = 0; j < N; j++) {
      int c = grid[i][j] - 'A';
      posi[c].emplace_back(i, j);
    }
  }
  const int NN = 225;
  const int INF = 1000000005;
  vector<vector<int>> min_cost(NN, vector<int>(M, INF));
  vector<vector<int>> best_end(NN, vector<int>(M, -1));
  for (int s = 0; s < NN; s++) {
    int ci = s / N;
    int cj = s % N;
    for (int k = 0; k < M; k++) {
      string t = tks[k];
      vector<int> lets(5);
      for (int p = 0; p < 5; p++) lets[p] = t[p] - 'A';
      vector<vector<pair<int, int>>> lpos(5);
      for (int l = 0; l < 5; l++) lpos[l] = posi[lets[l]];
      int sz0 = lpos[0].size();
      vector<int> dists0(sz0);
      for (int j = 0; j < sz0; j++) {
        auto [x, y] = lpos[0][j];
        dists0[j] = abs(x - ci) + abs(y - cj);
      }
      vector<vector<int>> all_dists(5);
      all_dists[0] = dists0;
      for (int l = 1; l < 5; l++) {
        int szp = lpos[l - 1].size();
        int szn = lpos[l].size();
        vector<int> ndist(szn, INF);
        for (int ip = 0; ip < szp; ip++) {
          if (all_dists[l - 1][ip] == INF) continue;
          auto [px, py] = lpos[l - 1][ip];
          for (int in = 0; in < szn; in++) {
            auto [nx, ny] = lpos[l][in];
            int d = abs(nx - px) + abs(ny - py);
            int newd = all_dists[l - 1][ip] + d;
            if (newd < ndist[in]) {
              ndist[in] = newd;
            }
          }
        }
        all_dists[l] = ndist;
      }
      vector<int>& lastd = all_dists[4];
      int minc = INF;
      int bestj = -1;
      for (int j = 0; j < (int)lastd.size(); j++) {
        if (lastd[j] < minc) {
          minc = lastd[j];
          bestj = j;
        }
      }
      if (minc < INF) {
        auto [ei, ej] = lpos[4][bestj];
        int eid = ei * N + ej;
        min_cost[s][k] = minc;
        best_end[s][k] = eid;
      }
    }
  }
  int cur_i = si, cur_j = sj;
  set<int> rem;
  for (int i = 0; i < M; i++) rem.insert(i);
  vector<pair<int, int>> full_path;
  auto get_path = [&](int ci, int cj, int k) -> vector<pair<int, int>> {
    string t = tks[k];
    vector<int> lets(5);
    for (int p = 0; p < 5; p++) lets[p] = t[p] - 'A';
    vector<vector<pair<int, int>>> lpos(5);
    for (int l = 0; l < 5; l++) lpos[l] = posi[lets[l]];
    int sz0 = lpos[0].size();
    vector<int> dists0(sz0);
    for (int j = 0; j < sz0; j++) {
      auto [x, y] = lpos[0][j];
      dists0[j] = abs(x - ci) + abs(y - cj);
    }
    vector<vector<int>> all_dists(5);
    all_dists[0] = dists0;
    vector<vector<int>> preds(5);
    for (int l = 1; l < 5; l++) {
      int szn = lpos[l].size();
      preds[l].assign(szn, -1);
    }
    for (int l = 1; l < 5; l++) {
      int szp = lpos[l - 1].size();
      int szn = lpos[l].size();
      vector<int> ndist(szn, INF);
      for (int ip = 0; ip < szp; ip++) {
        if (all_dists[l - 1][ip] == INF) continue;
        auto [px, py] = lpos[l - 1][ip];
        for (int in = 0; in < szn; in++) {
          auto [nx, ny] = lpos[l][in];
          int d = abs(nx - px) + abs(ny - py);
          int newd = all_dists[l - 1][ip] + d;
          if (newd < ndist[in]) {
            ndist[in] = newd;
            preds[l][in] = ip;
          }
        }
      }
      all_dists[l] = ndist;
    }
    vector<int>& lastd = all_dists[4];
    int minc = INF;
    int bestj = -1;
    for (int j = 0; j < (int)lastd.size(); j++) {
      if (lastd[j] < minc) {
        minc = lastd[j];
        bestj = j;
      }
    }
    vector<int> idxs(5);
    idxs[4] = bestj;
    for (int l = 4; l >= 1; l--) {
      idxs[l - 1] = preds[l][idxs[l]];
    }
    vector<pair<int, int>> res(5);
    for (int l = 0; l < 5; l++) {
      res[l] = lpos[l][idxs[l]];
    }
    return res;
  };
  while (!rem.empty()) {
    int best_k = -1;
    int best_c = INF;
    int curf = cur_i * N + cur_j;
    for (int kk : rem) {
      int cc = min_cost[curf][kk];
      if (cc < best_c) {
        best_c = cc;
        best_k = kk;
      }
    }
    auto typed = get_path(cur_i, cur_j, best_k);
    for (auto p : typed) {
      full_path.push_back(p);
    }
    cur_i = typed[4].first;
    cur_j = typed[4].second;
    rem.erase(best_k);
  }
  for (auto [i, j] : full_path) {
    cout << i << " " << j << "\n";
  }
  return 0;
}