#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(NULL);
  int n, ty;
  cin >> n >> ty;
  int root = -1;
  for (int cand = 1; cand <= n; ++cand) {
    cout << "? " << n << " " << cand;
    for (int i = 1; i <= n; ++i) {
      if (i != cand) cout << " " << i;
    }
    cout << '\n';
    cout.flush();
    int res;
    cin >> res;
    if (res == 1) {
      root = cand;
      break;
    }
  }
  assert(root != -1);
  const int NUM_COL = 12;
  vector<vector<int>> colors(NUM_COL);
  vector<int> col_of(n + 1, -1);
  for (int x = 1; x <= n; ++x) {
    bool added = false;
    for (int c = 0; c < NUM_COL; ++c) {
      vector<int> lis = colors[c];
      int sz = lis.size();
      if (sz == 0) {
        colors[c].push_back(x);
        col_of[x] = c;
        added = true;
        break;
      }
      cout << "? " << 1 + sz << " " << x;
      for (int y : lis) cout << " " << y;
      cout << '\n';
      cout.flush();
      int r;
      cin >> r;
      if (r == 1 + sz) {
        colors[c].push_back(x);
        col_of[x] = c;
        added = true;
        break;
      }
    }
    assert(added);
  }
  // ordering the colors
  vector<vector<int>> conn(NUM_COL);
  for (int c1 = 0; c1 < NUM_COL; ++c1) {
    for (int c2 = c1 + 1; c2 < NUM_COL; ++c2) {
      vector<int> l1 = colors[c1];
      vector<int> l2 = colors[c2];
      if (l1.empty() || l2.empty()) continue;
      cout << "? " << l1.size() + l2.size();
      for (int y : l1) cout << " " << y;
      for (int y : l2) cout << " " << y;
      cout << '\n';
      cout.flush();
      int r;
      cin >> r;
      if (r < (int)l1.size() + (int)l2.size()) {
        conn[c1].push_back(c2);
        conn[c2].push_back(c1);
      }
    }
  }
  vector<pair<int, int>> class_dir;
  for (int c1 = 0; c1 < NUM_COL; ++c1) {
    for (int c2 : conn[c1]) {
      if (c2 <= c1) continue;
      vector<int> B = colors[c1];
      vector<int> E = colors[c2];
      int oc1 = c1, oc2 = c2;
      if (B.size() > E.size()) {
        swap(B, E);
        swap(oc1, oc2);
      }
      // find one e in E connected to some in B
      int found_e = -1;
      for (size_t mm = 0; mm < E.size(); ++mm) {
        int ee = E[mm];
        cout << "? " << (int)B.size() + 1;
        for (int b : B) cout << " " << b;
        cout << " " << ee << '\n';
        cout.flush();
        int rr;
        cin >> rr;
        if (rr < (int)B.size() + 1) {
          found_e = mm;
          break;
        }
      }
      assert(found_e != -1);
      int e = E[found_e];
      // find one b in B connected to e
      int found_b = -1;
      for (size_t mm = 0; mm < B.size(); ++mm) {
        int bb = B[mm];
        cout << "? 2 " << bb << " " << e << '\n';
        cout.flush();
        int rr;
        cin >> rr;
        if (rr == 1) {
          found_b = mm;
          break;
        }
      }
      assert(found_b != -1);
      int b = B[found_b];
      // now b and e comparable, b in original c1 or swapped, but use oc1 oc2
      int u = (oc1 == c1 ? b : e);
      int v = (oc1 == c1 ? e : b);
      // L all except u v
      vector<int> L;
      for (int ii = 1; ii <= n; ++ii) {
        if (ii != u && ii != v) L.push_back(ii);
      }
      // u first L v
      cout << "? " << n << " " << u;
      for (int yy : L) cout << " " << yy;
      cout << " " << v << '\n';
      cout.flush();
      int su;
      cin >> su;
      // v first L u
      cout << "? " << n << " " << v;
      for (int yy : L) cout << " " << yy;
      cout << " " << u << '\n';
      cout.flush();
      int sv;
      cin >> sv;
      bool u_anc_vv = (su < sv);
      int higher = u_anc_vv ? oc1 : oc2;
      int lower = u_anc_vv ? oc2 : oc1;
      class_dir.emplace_back(higher, lower);
    }
  }
  // now topo sort
  vector<vector<int>> dag(NUM_COL);
  vector<int> indeg(NUM_COL, 0);
  for (auto [hi, lo] : class_dir) {
    dag[hi].push_back(lo);
    indeg[lo]++;
  }
  vector<int> topo_order;
  queue<int> q;
  for (int c = 0; c < NUM_COL; ++c) {
    if (indeg[c] == 0) q.push(c);
  }
  while (!q.empty()) {
    int c = q.front();
    q.pop();
    topo_order.push_back(c);
    for (int nx : dag[c]) {
      if (--indeg[nx] == 0) q.push(nx);
    }
  }
  assert((int)topo_order.size() == NUM_COL);
  vector<int> color_level(NUM_COL);
  for (int i = 0; i < NUM_COL; ++i) {
    color_level[ topo_order[i] ] = i;  // 0 highest, NUM_COL-1 lowest
  }
  // now find parents
  vector<int> par(n + 1, 0);
  par[root] = 0;
  for (int x = 1; x <= n; ++x) {
    if (x == root) continue;
    int ck = col_of[x];
    int lk = color_level[ck];
    int found_j = -1;
    for (int jj = lk - 1; jj >= 0; --jj) {
      int cj = topo_order[jj];
      vector<int> lis = colors[cj];
      int szz = lis.size();
      cout << "? " << 1 + szz << " " << x;
      for (int y : lis) cout << " " << y;
      cout << '\n';
      cout.flush();
      int rr;
      cin >> rr;
      int numcc = szz + 1 - rr;
      if (numcc == 1) {
        found_j = cj;
        break;
      }
    }
    assert(found_j != -1);
    // now identify y in colors[found_j]
    vector<int> lis2 = colors[found_j];
    int sz2 = lis2.size();
    // binary search for the unique comparable
    int ll = 0, rr = sz2 - 1;
    while (ll < rr) {
      int mm = (ll + rr) / 2;
      int subsz = mm - ll + 1;
      cout << "? " << 1 + subsz << " " << x;
      for (int ii = ll; ii <= mm; ++ii) cout << " " << lis2[ii];
      cout << '\n';
      cout.flush();
      int rrr;
      cin >> rrr;
      int numccc = subsz + 1 - rrr;
      if (numccc > 0) {
        rr = mm;
      } else {
        ll = mm + 1;
      }
    }
    int yy = lis2[ll];
    // verify
    cout << "? 2 " << x << " " << yy << '\n';
    cout.flush();
    int rver;
    cin >> rver;
    assert(rver == 1);
    par[x] = yy;
  }
  // output
  cout << "!";
  for (int i = 1; i <= n; ++i) {
    cout << " " << par[i];
  }
  cout << '\n';
  cout.flush();
  return 0;
}