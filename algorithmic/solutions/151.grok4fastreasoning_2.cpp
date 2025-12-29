#include <bits/stdc++.h>
using namespace std;
using ll = long long;
const ll INF = 1LL << 60;

int main() {
  int N, si, sj;
  cin >> N >> si >> sj;
  vector<string> grid(N);
  for (auto& s : grid) cin >> s;
  int dx[4] = {-1, 1, 0, 0};
  int dy[4] = {0, 0, -1, 1};
  vector<tuple<int, int, int>> h_list;
  for (int i = 0; i < N; i += 2) {
    int jj = 0;
    while (jj < N) {
      if (grid[i][jj] == '#') {
        jj++;
        continue;
      }
      int j1 = jj;
      while (jj < N && grid[i][jj] != '#') jj++;
      int j2 = jj - 1;
      if (j1 <= j2) h_list.emplace_back(i, j1, j2);
    }
  }
  int num_h = h_list.size();
  vector<tuple<int, int, int>> v_list;
  for (int j = 0; j < N; j += 2) {
    int ii = 0;
    while (ii < N) {
      if (grid[ii][j] == '#') {
        ii++;
        continue;
      }
      int i1 = ii;
      while (ii < N && grid[ii][j] != '#') ii++;
      int i2 = ii - 1;
      if (i1 <= i2) v_list.emplace_back(j, i1, i2);
    }
  }
  int num_v = v_list.size();
  vector<vector<int>> bip_left(num_h), bip_right(num_v);
  for (int hi = 0; hi < num_h; hi++) {
    auto [row, j1, j2] = h_list[hi];
    for (int jj = j1; jj <= j2; jj++) {
      if (jj % 2 != 0) continue;
      if (grid[row][jj] == '#') continue;
      int col = jj;
      bool found = false;
      for (int vi = 0; vi < num_v; vi++) {
        auto [c, i11, i22] = v_list[vi];
        if (c == col && i11 <= row && row <= i22) {
          bip_left[hi].push_back(vi);
          bip_right[vi].push_back(hi);
          found = true;
          break;
        }
      }
    }
  }
  vector<int> pairU(num_h, -1), pairV(num_v, -1);
  vector<bool> visv;
  auto dfs_match = [&](auto&& self, int u) -> bool {
    for (int v : bip_left[u]) {
      if (visv[v]) continue;
      visv[v] = true;
      if (pairV[v] == -1 || self(self, pairV[v])) {
        pairU[u] = v;
        pairV[v] = u;
        return true;
      }
    }
    return false;
  };
  int matching = 0;
  for (int u = 0; u < num_h; u++) {
    if (pairU[u] == -1) {
      visv.assign(num_v, false);
      if (dfs_match(dfs_match, u)) matching++;
    }
  }
  set<pair<int, int>> key_pos;
  for (int u = 0; u < num_h; u++) {
    int v = pairU[u];
    if (v != -1) {
      auto [row, _, __] = h_list[u];
      auto [col, ___, ____] = v_list[v];
      key_pos.emplace(row, col);
    }
  }
  for (int u = 0; u < num_h; u++) {
    if (pairU[u] != -1) continue;
    auto [row, j1, j2] = h_list[u];
    pair<int, int> pt;
    if (!bip_left[u].empty()) {
      int v = bip_left[u][0];
      auto [col, ___, ____] = v_list[v];
      pt = {row, col};
    } else {
      int jj = j1 + (j2 - j1) / 2;
      pt = {row, jj};
    }
    key_pos.emplace(pt.first, pt.second);
  }
  for (int vv = 0; vv < num_v; vv++) {
    if (pairV[vv] != -1) continue;
    auto [col, i1, i2] = v_list[vv];
    pair<int, int> pt;
    if (!bip_right[vv].empty()) {
      int u = bip_right[vv][0];
      auto [roww, ___, ____] = h_list[u];
      pt = {roww, col};
    } else {
      int ii = i1 + (i2 - i1) / 2;
      pt = {ii, col};
    }
    key_pos.emplace(pt.first, pt.second);
  }
  if (key_pos.find({si, sj}) == key_pos.end()) {
    key_pos.emplace(si, sj);
  }
  vector<pair<int, int>> keys(key_pos.begin(), key_pos.end());
  int KK = keys.size();
  int start_idx = -1;
  for (int k = 0; k < KK; k++) {
    if (keys[k].first == si && keys[k].second == sj) {
      start_idx = k;
      break;
    }
  }
  vector<vector<ll>> tdist(KK, vector<ll>(KK, INF));
  for (int s = 0; s < KK; s++) {
    int fi = keys[s].first, fj = keys[s].second;
    vector<vector<ll>> dd(N, vector<ll>(N, INF));
    dd[fi][fj] = 0;
    auto comp = greater<tuple<ll, int, int>>();
    priority_queue<tuple<ll, int, int>, vector<tuple<ll, int, int>>, decltype(comp)> pqq(comp);
    pqq.emplace(0LL, fi, fj);
    while (!pqq.empty()) {
      auto [cc, ii, jj] = pqq.top();
      pqq.pop();
      if (cc > dd[ii][jj]) continue;
      for (int d = 0; d < 4; d++) {
        int ni = ii + dx[d], nj = jj + dy[d];
        if (ni < 0 || ni >= N || nj < 0 || nj >= N || grid[ni][nj] == '#') continue;
        ll nc = cc + (grid[ni][nj] - '0');
        if (nc < dd[ni][nj]) {
          dd[ni][nj] = nc;
          pqq.emplace(nc, ni, nj);
        }
      }
    }
    for (int t = 0; t < KK; t++) {
      int ti = keys[t].first, tj = keys[t].second;
      tdist[s][t] = dd[ti][tj];
    }
  }
  vector<int> order;
  vector<bool> usedd(KK, false);
  int currr = start_idx;
  order.push_back(currr);
  usedd[currr] = true;
  while (order.size() < KK) {
    ll bestt = INF;
    int nxt = -1;
    for (int cand = 0; cand < KK; cand++) {
      if (usedd[cand]) continue;
      ll dd = tdist[currr][cand];
      if (dd < bestt) {
        bestt = dd;
        nxt = cand;
      }
    }
    assert(nxt != -1);
    currr = nxt;
    order.push_back(currr);
    usedd[currr] = true;
  }
  string ans = "";
  for (size_t ii = 0; ii < order.size(); ii++) {
    int fromm = order[ii];
    size_t nextii = (ii + 1) % order.size();
    int too = order[nextii];
    int fi = keys[fromm].first, fjj = keys[fromm].second;
    int ti = keys[too].first, tjj = keys[too].second;
    if (fi == ti && fjj == tjj) continue;
    vector<vector<ll>> dd(N, vector<ll>(N, INF));
    vector<vector<pair<int, int>>> pre(N, vector<pair<int, int>>(N, {-1, -1}));
    dd[fi][fjj] = 0;
    auto compp = greater<tuple<ll, int, int>>();
    priority_queue<tuple<ll, int, int>, vector<tuple<ll, int, int>>, decltype(compp)> pqqq(compp);
    pqqq.emplace(0LL, fi, fjj);
    while (!pqqq.empty()) {
      auto [ccc, iii, jjj] = pqqq.top();
      pqqq.pop();
      if (ccc > dd[iii][jjj]) continue;
      for (int d = 0; d < 4; d++) {
        int nni = iii + dx[d], nnj = jjj + dy[d];
        if (nni < 0 || nni >= N || nnj < 0 || nnj >= N || grid[nni][nnj] == '#') continue;
        ll nnc = ccc + (grid[nni][nnj] - '0');
        if (nnc < dd[nni][nnj]) {
          dd[nni][nnj] = nnc;
          pre[nni][nnj] = {iii, jjj};
          pqqq.emplace(nnc, nni, nnj);
        }
      }
    }
    vector<pair<int, int>> pathh;
    int cii = ti, cjj = tjj;
    while (true) {
      pathh.emplace_back(cii, cjj);
      pair<int, int> pr = pre[cii][cjj];
      if (pr.first == -1) break;
      cii = pr.first;
      cjj = pr.second;
    }
    reverse(pathh.begin(), pathh.end());
    for (size_t pp = 0; pp + 1 < pathh.size(); pp++) {
      int i11 = pathh[pp].first, j11 = pathh[pp].second;
      int i22 = pathh[pp + 1].first, j22 = pathh[pp + 1].second;
      int ddi = i22 - i11;
      int ddjj = j22 - j11;
      char ch;
      if (ddi == -1 && ddjj == 0) ch = 'U';
      else if (ddi == 1 && ddjj == 0) ch = 'D';
      else if (ddi == 0 && ddjj == -1) ch = 'L';
      else if (ddi == 0 && ddjj == 1) ch = 'R';
      else assert(false);
      ans += ch;
    }
  }
  cout << ans << endl;
}