#include <bits/stdc++.h>
using namespace std;

int query(int u, int v) {
  if (u == v) return 0;
  cout << "? " << u << " " << v << endl;
  cout.flush();
  int d;
  cin >> d;
  return d;
}

int find_centroid(vector<int> curr_S, int rt, long long ext, int N, int HH) {
  int m = curr_S.size();
  if (m == 1) return rt;

  // query dist from rt to all in curr_S
  vector<int> dist_rt(N + 1, -1);
  dist_rt[rt] = 0;
  for (int x : curr_S) {
    if (x != rt) {
      dist_rt[x] = query(rt, x);
    }
  }

  // find max_d, p
  int max_d = 0;
  int p = -1;
  for (int x : curr_S) {
    int dd = dist_rt[x];
    if (dd > max_d) {
      max_d = dd;
      p = x;
    }
  }

  if (max_d <= 1) {
    return rt;
  }

  // query dist from p to all in curr_S
  vector<int> dist_p(N + 1, -1);
  dist_p[p] = 0;
  for (int x : curr_S) {
    if (x != p) {
      dist_p[x] = query(p, x);
    }
  }

  // use ends uu=rt pos 0, vv=p pos DD=max_d
  int DD = max_d;
  int uu = rt;
  int vv = p;

  // compute for each in curr_S, l and pos
  vector<int> node_pos(m, -1);
  vector<int> node_l(m, -1);
  vector<int> path_n(DD + 1, 0);
  vector<int> hang_s(DD + 1, 0);

  for (int i = 0; i < m; i++) {
    int x = curr_S[i];
    int duu = dist_rt[x];
    int dvv = dist_p[x];
    int summ = duu + dvv;
    int ll = (summ - DD) / 2;
    int ppos = duu - ll;
    node_l[i] = ll;
    node_pos[i] = ppos;
    if (ll == 0) {
      path_n[ppos] = x;
    } else {
      hang_s[ppos]++;
    }
  }

  // cum
  vector<long long> cum(DD + 2, 0);
  for (int j = 0; j <= DD; j++) {
    cum[j + 1] = cum[j] + 1LL + hang_s[j];
  }

  // pos_r = 0
  int pos_r = 0;

  // check for each j
  for (int j = 0; j <= DD; j++) {
    long long lft = cum[j];
    long long rgt = (long long)m - cum[j + 1];
    long long hng = hang_s[j];
    long long l_add = 0;
    long long r_add = 0;
    if (j > pos_r) l_add = ext;
    else if (j < pos_r) r_add = ext;
    if (lft + l_add <= HH && rgt + r_add <= HH && hng <= HH && ext <= HH) {
      return path_n[j];
    }
  }

  // recurse to the one
  for (int j = 0; j <= DD; j++) {
    long long lft = cum[j];
    long long rgt = (long long)m - cum[j + 1];
    long long hng = hang_s[j];
    long long l_add = (j > pos_r ? ext : 0);
    long long r_add = (j < pos_r ? ext : 0);
    if (lft + l_add <= HH && rgt + r_add <= HH && hng > HH) {
      // build new_S
      vector<int> new_S;
      new_S.push_back(path_n[j]);
      for (int i = 0; i < m; i++) {
        if (node_l[i] > 0 && node_pos[i] == j) {
          new_S.push_back(curr_S[i]);
        }
      }
      long long new_ext = (long long)N - new_S.size();
      int new_rt = path_n[j];
      return find_centroid(new_S, new_rt, new_ext, N, HH);
    }
  }

  // should not reach
  assert(false);
  return -1;
}

int main() {
  int n;
  cin >> n;
  int h = n / 2;
  vector<int> S(n);
  for (int i = 0; i < n; i++) S[i] = i + 1;
  int cent = find_centroid(S, 1, 0LL, n, h);
  cout << "! " << cent << endl;
  cout.flush();
  return 0;
}