#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(nullptr);
  int t;
  cin >> t;
  for (int test = 0; test < t; ++test) {
    int n;
    cin >> n;
    cout << n << endl;
    cout.flush();
    vector<int> P(n + 1, 0);
    for (int i = 1; i < n; ++i) {
      // build nextt and indegg
      vector<int> nextt(n + 1, 0);
      vector<int> indegg(n + 1, 0);
      for (int j = 1; j < i; ++j) {
        int im = P[j];
        if (im != i) {
          nextt[j] = im;
          indegg[im]++;
        }
      }
      // build vv
      vector<int> vv;
      vector<bool> vis(n + 1, false);
      // paths
      queue<int> starts;
      for (int j = 1; j < i; ++j) {
        if (nextt[j] != 0 && indegg[j] == 0) {
          starts.push(j);
        }
      }
      while (!starts.empty()) {
        int cur = starts.front();
        starts.pop();
        if (vis[cur]) continue;
        int ccur = cur;
        vector<int> chain;
        while (true) {
          vis[ccur] = true;
          chain.push_back(ccur);
          int nx = nextt[ccur];
          if (nx == 0 || nx == i) break;
          ccur = nx;
          if (vis[ccur]) break; // safety
        }
        for (int u : chain) vv.push_back(u);
      }
      // cycles
      for (int j = 1; j < i; ++j) {
        if (nextt[j] != 0 && !vis[j]) {
          // cycle
          vector<int> cyc;
          int ccur = j;
          set<int> cyc_set;
          do {
            if (cyc_set.count(ccur)) break;
            cyc_set.insert(ccur);
            cyc.push_back(ccur);
            vis[ccur] = true;
            ccur = nextt[ccur];
          } while (ccur != j && nextt[ccur] != 0);
          // place all but one
          for (size_t kk = 0; kk + 1 < cyc.size(); ++kk) {
            vv.push_back(cyc[kk]);
          }
          if (!cyc.empty()) vv.push_back(cyc.back());
        }
      }
      // singletons
      vector<int> singles;
      for (int lab = 1; lab <= n; ++lab) {
        if (lab != i && !vis[lab]) singles.push_back(lab);
      }
      sort(singles.begin(), singles.end());
      for (int ss : singles) vv.push_back(ss);
      // now vv size n-1 , 0-based vv[0..n-2] ? Wait, make 1-based
      vector<int> v(n); // 1 to n-1
      for (int jj = 1; jj <= n - 1; ++jj) v[jj] = vv[jj - 1];
      // now possible
      vector<pair<int, int>> possible;
      for (int p1 = 1; p1 <= n - 1; ++p1) {
        for (int p2 = p1; p2 <= n - 1; ++p2) {
          possible.emplace_back(p1, p2);
        }
      }
      // query fn , r = n
      vector<int> qq(n + 1);
      int idx = 1;
      for (int jj = 1; jj <= n - 1; ++jj) qq[idx++] = v[jj];
      qq[idx++] = i;
      int fn_val = ask(qq); // define ask below
      int search_cnt = 1; // counted the fn
      while (possible.size() > 1 && search_cnt < 10) {
        int best_r = 1;
        int best_max = INT_MAX;
        for (int cand_r = 1; cand_r <= n; ++cand_r) {
          vector<int> cnt(3, 0);
          for (auto [p1, p2] : possible) {
            int su = 0;
            if (p1 >= cand_r) ++su;
            if (p2 >= cand_r) ++su;
            cnt[su]++;
          }
          int mx = 0;
          for (int cc = 0; cc < 3; ++cc) mx = max(mx, cnt[cc]);
          if (mx < best_max) {
            best_max = mx;
            best_r = cand_r;
          }
        }
        // query best_r
        vector<int> qqq(n + 1);
        idx = 1;
        for (int jj = 1; jj < best_r; ++jj) qqq[idx++] = v[jj];
        qqq[idx++] = i;
        for (int jj = best_r; jj <= n - 1; ++jj) qqq[idx++] = v[jj];
        int res = ask(qqq);
        int observed_s = res - fn_val;
        vector<pair<int, int>> newp;
        for (auto pr : possible) {
          int p1 = pr.first, p2 = pr.second;
          int su = (p1 >= best_r ? 1 : 0) + (p2 >= best_r ? 1 : 0);
          if (su == observed_s) newp.push_back(pr);
        }
        possible = std::move(newp);
        ++search_cnt;
      }
      // now possible should be 1
      assert(possible.size() == 1);
      auto [p1, p2] = possible[0];
      int px;
      if (p1 == p2) {
        px = v[p1];
      } else {
        int yy = v[p1];
        // build comm
        vector<int> comm;
        for (int ll = 1; ll <= n; ++ll) {
          if (ll != i && ll != yy) comm.push_back(ll);
        }
        sort(comm.begin(), comm.end());
        // case1 q1
        vector<int> q1(n + 1);
        idx = 1;
        for (int jj = 0; jj < n - 2; ++jj) q1[idx++] = comm[jj];
        q1[idx++] = i;
        q1[idx++] = yy;
        int res1 = ask(q1);
        // case2 q2
        vector<int> q2(n + 1);
        idx = 1;
        for (int jj = 0; jj < n - 2; ++jj) q2[idx++] = comm[jj];
        q2[idx++] = yy;
        q2[idx++] = i;
        int res2 = ask(q2);
        int dif = res1 - res2;
        if (dif == 1) {
          px = yy;
        } else {
          px = v[p2];
        }
      }
      P[i] = px;
    }
    // last
    vector<bool> used(n + 1, false);
    for (int j = 1; j < n; ++j) used[P[j]] = true;
    int miss = -1;
    for (int val = 1; val <= n; ++val) {
      if (!used[val]) {
        miss = val;
        break;
      }
    }
    P[n] = miss;
    // output !
    cout << "!";
    for (int j = 1; j <= n; ++j) cout << " " << P[j];
    cout << endl;
    cout.flush();
  }
  return 0;
}

int ask(const vector<int>& qq, int n) {
  cout << "?";
  for (int j = 1; j <= n; ++j) {
    cout << " " << qq[j];
  }
  cout << endl;
  cout.flush();
  int res;
  cin >> res;
  if (res == -1) {
    exit(0);
  }
  return res;
}