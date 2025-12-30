#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

struct Point {
  ll x, y;
};

bool inside(ll px, ll py, ll minx, ll maxx, ll miny, ll maxy) {
  return px >= minx && px <= maxx && py >= miny && py <= maxy;
}

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int N;
  cin >> N;
  vector<Point> mack(N), sard(N);
  for (int i = 0; i < N; i++) {
    cin >> mack[i].x >> mack[i].y;
  }
  for (int i = 0; i < N; i++) {
    cin >> sard[i].x >> sard[i].y;
  }
  // overall bb
  ll oxmin = 100001, oxmax = -1, oymin = 100001, oymax = -1;
  for (auto p : mack) {
    oxmin = min(oxmin, p.x);
    oxmax = max(oxmax, p.x);
    oymin = min(oymin, p.y);
    oymax = max(oymax, p.y);
  }
  int oa = 0, ob = 0;
  for (auto p : mack) {
    if (inside(p.x, p.y, oxmin, oxmax, oymin, oymax)) oa++;
  }
  for (auto p : sard) {
    if (inside(p.x, p.y, oxmin, oxmax, oymin, oymax)) ob++;
  }
  int osc = max(0, oa - ob + 1);
  ll best_minx = oxmin, best_maxx = oxmax, best_miny = oymin, best_maxy = oymax;
  int best_sc = osc;
  // kmeans
  vector<int> ks = {10, 15, 18, 20, 25};
  for (int kk : ks) {
    int k = kk;
    vector<Point> centers(k);
    for (int i = 0; i < k; i++) {
      centers[i] = mack[i % N];
    }
    int iters = 0;
    bool changed = true;
    while (changed && iters < 30) {
      changed = false;
      iters++;
      vector<vector<int>> groups(k);
      for (int i = 0; i < N; i++) {
        int c = 0;
        ll md = (mack[i].x - centers[0].x) * (mack[i].x - centers[0].x) + (mack[i].y - centers[0].y) * (mack[i].y - centers[0].y);
        for (int j = 1; j < k; j++) {
          ll d = (mack[i].x - centers[j].x) * (mack[i].x - centers[j].x) + (mack[i].y - centers[j].y) * (mack[i].y - centers[j].y);
          if (d < md) {
            md = d;
            c = j;
          }
        }
        groups[c].push_back(i);
      }
      for (int c = 0; c < k; c++) {
        if (groups[c].empty()) continue;
        ll sx = 0, sy = 0;
        int sz = groups[c].size();
        for (int idx : groups[c]) {
          sx += mack[idx].x;
          sy += mack[idx].y;
        }
        ll nx = sx / sz;
        ll ny = sy / sz;
        if (nx != centers[c].x || ny != centers[c].y) changed = true;
        centers[c].x = nx;
        centers[c].y = ny;
      }
    }
    // final assignment
    vector<vector<Point>> cls(k);
    for (int i = 0; i < N; i++) {
      int c = 0;
      ll md = (mack[i].x - centers[0].x) * (mack[i].x - centers[0].x) + (mack[i].y - centers[0].y) * (mack[i].y - centers[0].y);
      for (int j = 1; j < k; j++) {
        ll d = (mack[i].x - centers[j].x) * (mack[i].x - centers[j].x) + (mack[i].y - centers[j].y) * (mack[i].y - centers[j].y);
        if (d < md) {
          md = d;
          c = j;
        }
      }
      cls[c].push_back(mack[i]);
    }
    // process clusters
    for (auto& cl : cls) {
      if (cl.empty()) continue;
      ll minx = 100001, maxx = -1, miny = 100001, maxy = -1;
      for (auto p : cl) {
        minx = min(minx, p.x);
        maxx = max(maxx, p.x);
        miny = min(miny, p.y);
        maxy = max(maxy, p.y);
      }
      if (maxx - minx < 1 || maxy - miny < 1) continue; // skip degenerate
      int a = 0, b = 0;
      for (auto mp : mack) {
        if (inside(mp.x, mp.y, minx, maxx, miny, maxy)) a++;
      }
      for (auto sp : sard) {
        if (inside(sp.x, sp.y, minx, maxx, miny, maxy)) b++;
      }
      int sc = max(0, a - b + 1);
      if (sc > best_sc) {
        best_sc = sc;
        best_minx = minx;
        best_maxx = maxx;
        best_miny = miny;
        best_maxy = maxy;
      }
    }
  }
  // if best_sc <=1, try single
  if (best_sc <= 1) {
    int max_single = 1;
    ll sx = 0, sy = 0, sxx = 1, syy = 1;
    for (auto mp : mack) {
      ll px = mp.x, py = mp.y;
      if (px >= 100000 || py >= 100000) continue;
      ll txmin = px, txmax = px + 1, tymin = py, tymax = py + 1;
      int sa = 0, sb = 0;
      for (auto mpp : mack) {
        if (inside(mpp.x, mpp.y, txmin, txmax, tymin, tymax)) sa++;
      }
      for (auto spp : sard) {
        if (inside(spp.x, spp.y, txmin, txmax, tymin, tymax)) sb++;
      }
      int ssc = max(0, sa - sb + 1);
      if (ssc > max_single) {
        max_single = ssc;
        sx = txmin;
        sy = tymin;
        sxx = txmax;
        syy = tymax;
      }
    }
    if (max_single > best_sc) {
      best_sc = max_single;
      best_minx = sx;
      best_maxx = sxx;
      best_miny = sy;
      best_maxy = syy;
    }
  }
  // output
  cout << 4 << '\n';
  cout << best_minx << " " << best_miny << '\n';
  cout << best_maxx << " " << best_miny << '\n';
  cout << best_maxx << " " << best_maxy << '\n';
  cout << best_minx << " " << best_maxy << '\n';
}