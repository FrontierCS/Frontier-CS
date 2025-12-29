#include <bits/stdc++.h>
using namespace std;

int main() {
  int N;
  cin >> N;
  vector<pair<int, int>> mack(N), sard(N);
  for (auto& p : mack) cin >> p.first >> p.second;
  for (auto& p : sard) cin >> p.first >> p.second;
  const int k = 25;
  vector<pair<int, int>> mack_sorted = mack;
  sort(mack_sorted.begin(), mack_sorted.end());
  vector<pair<int, int>> cents(k);
  for (int i = 0; i < k; i++) {
    int idx = i * N / k;
    if (idx >= N) idx = N - 1;
    cents[i] = mack_sorted[idx];
  }
  vector<vector<int>> clusters(k);
  vector<int> cluster_id(N, -1);
  bool changed = true;
  int maxit = 100;
  while (changed && maxit--) {
    changed = false;
    for (int c = 0; c < k; c++) clusters[c].clear();
    for (int j = 0; j < N; j++) {
      double mind = 1e18;
      int bc = -1;
      for (int c = 0; c < k; c++) {
        double dx = mack[j].first - cents[c].first;
        double dy = mack[j].second - cents[c].second;
        double d = dx * dx + dy * dy;
        if (d < mind || (d == mind && c < bc)) {
          mind = d;
          bc = c;
        }
      }
      if (cluster_id[j] != bc) {
        changed = true;
        cluster_id[j] = bc;
      }
      clusters[bc].push_back(j);
    }
    for (int c = 0; c < k; c++) {
      if (clusters[c].empty()) continue;
      long long sx = 0, sy = 0;
      int cnt = clusters[c].size();
      for (int j : clusters[c]) {
        sx += mack[j].first;
        sy += mack[j].second;
      }
      int nx = round(sx * 1.0 / cnt);
      int ny = round(sy * 1.0 / cnt);
      nx = max(0, min(100000, nx));
      ny = max(0, min(100000, ny));
      cents[c] = {nx, ny};
    }
  }
  vector<int> min_x(k, 100000000), max_x(k, -1), min_y(k, 100000000), max_y(k, -1), szz(k, 0);
  for (int c = 0; c < k; c++) {
    if (clusters[c].empty()) continue;
    szz[c] = clusters[c].size();
    for (int j : clusters[c]) {
      int px = mack[j].first, py = mack[j].second;
      min_x[c] = min(min_x[c], px);
      max_x[c] = max(max_x[c], px);
      min_y[c] = min(min_y[c], py);
      max_y[c] = max(max_y[c], py);
    }
  }
  vector<int> valid;
  for (int c = 0; c < k; c++) if (szz[c] > 0) valid.push_back(c);
  int kk = valid.size();
  vector<int> vminx(kk), vmaxx(kk), vminy(kk), vmaxy(kk), vsz(kk);
  for (int i = 0; i < kk; i++) {
    int c = valid[i];
    vminx[i] = min_x[c];
    vmaxx[i] = max_x[c];
    vminy[i] = min_y[c];
    vmaxy[i] = max_y[c];
    vsz[i] = szz[c];
  }
  int best_sc = -1000000000;
  int best_lx = 0, best_rx = 0, best_ly = 0, best_ry = 0;
  function<void(int, vector<int>)> gen = [&](int start, vector<int> current) {
    if (!current.empty()) {
      int ominx = 100000000, omaxx = -1, ominy = 100000000, omaxy = -1;
      for (int i : current) {
        ominx = min(ominx, vminx[i]);
        omaxx = max(omaxx, vmaxx[i]);
        ominy = min(ominy, vminy[i]);
        omaxy = max(omaxy, vmaxy[i]);
      }
      if (ominx > omaxx || ominy > omaxy) return;
      int aa = 0, bb = 0;
      for (const auto& p : mack) {
        if (p.first >= ominx && p.first <= omaxx && p.second >= ominy && p.second <= omaxy) aa++;
      }
      for (const auto& p : sard) {
        if (p.first >= ominx && p.first <= omaxx && p.second >= ominy && p.second <= omaxy) bb++;
      }
      int sc = aa - bb;
      if (sc > best_sc) {
        best_sc = sc;
        best_lx = ominx;
        best_rx = omaxx;
        best_ly = ominy;
        best_ry = omaxy;
      }
    }
    if (current.size() >= 5) return;
    for (int i = start; i < kk; i++) {
      current.push_back(i);
      gen(i + 1, current);
      current.pop_back();
    }
  };
  vector<int> empty_vec;
  gen(0, empty_vec);
  {
    int ominx = 100000000, omaxx = -1, ominy = 100000000, omaxy = -1;
    for (int i = 0; i < kk; i++) {
      ominx = min(ominx, vminx[i]);
      omaxx = max(omaxx, vmaxx[i]);
      ominy = min(ominy, vminy[i]);
      omaxy = max(omaxy, vmaxy[i]);
    }
    if (ominx <= omaxx && ominy <= omaxy) {
      int aa = 0, bb = 0;
      for (const auto& p : mack) if (p.first >= ominx && p.first <= omaxx && p.second >= ominy && p.second <= omaxy) aa++;
      for (const auto& p : sard) if (p.first >= ominx && p.first <= omaxx && p.second >= ominy && p.second <= omaxy) bb++;
      int sc = aa - bb;
      if (sc > best_sc) {
        best_sc = sc;
        best_lx = ominx;
        best_rx = omaxx;
        best_ly = ominy;
        best_ry = omaxy;
      }
    }
  }
  if (best_sc < 0) {
    auto p = mack[0];
    best_lx = max(0, p.first - 1);
    best_rx = min(100000, p.first + 1);
    best_ly = max(0, p.second - 1);
    best_ry = min(100000, p.second + 1);
    best_sc = 0;
  }
  int lx = best_lx, rx = best_rx, ly = best_ly, ry = best_ry;
  if (lx == rx) {
    if (rx < 100000) {
      rx++;
    } else {
      lx--;
    }
  }
  if (ly == ry) {
    if (ry < 100000) {
      ry++;
    } else {
      ly--;
    }
  }
  cout << 4 << endl;
  cout << lx << " " << ly << endl;
  cout << rx << " " << ly << endl;
  cout << rx << " " << ry << endl;
  cout << lx << " " << ry << endl;
}