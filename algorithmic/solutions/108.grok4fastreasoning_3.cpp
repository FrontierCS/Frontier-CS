#include <bits/stdc++.h>
using namespace std;

int main() {
  int n, m;
  cin >> n >> m;
  int S = n * m;
  auto do_query = [](int x, int d) -> int {
    cout << "? " << x << " " << d << endl;
    cout.flush();
    int res;
    cin >> res;
    return res;
  };
  auto probe = [&](int x) -> vector<int> {
    vector<int> aa(S);
    for (int i = 0; i < S; i++) {
      aa[i] = do_query(x, 1);
    }
    long long sum_known = 0;
    for (int i = 0; i < S - 1; i++) {
      int del = aa[i + 1] - aa[i];
      sum_known += del;
    }
    int del0 = -sum_known;
    vector<int> del(S);
    del[0] = del0;
    for (int i = 1; i < S; i++) {
      del[i] = aa[i] - aa[i - 1];
    }
    vector<int> ff(S);
    for (int r = 0; r < m; r++) {
      vector<int> ch_del(n);
      for (int k = 0; k < n; k++) {
        int j = (r + 1LL * k * m) % S;
        ch_del[k] = del[j];
      }
      vector<int> cumm(n, 0);
      for (int k = 0; k < n - 1; k++) {
        cumm[k + 1] = cumm[k] - ch_del[k];
      }
      int minc = INT_MAX;
      for (int v : cumm) minc = min(minc, v);
      for (int k = 0; k < n; k++) {
        int j = (r + 1LL * k * m) % S;
        ff[j] = cumm[k] - minc;
      }
    }
    vector<int> cov(S);
    for (int j = 0; j < S; j++) {
      cov[j] = 1 - ff[j];
    }
    return cov;
  };
  vector<int> covered = probe(0);
  vector<int> pp(n - 1);
  for (int ii = 1; ii <= n - 1; ii++) {
    int i = ii;
    int temp = do_query(i, 1);
    int a_init = do_query(i, -1);
    vector<int> a_pos(m + 1, 0);
    a_pos[0] = a_init;
    for (int k = 1; k <= m; k++) {
      a_pos[k] = do_query(i, 1);
    }
    for (int k = 0; k < m; k++) {
      int dummy;
      do_query(i, -1);
      cin >> dummy;
    }
    vector<int> a_neg(m + 1, 0);
    a_neg[0] = a_init;
    for (int k = 1; k <= m; k++) {
      a_neg[k] = do_query(i, -1);
    }
    for (int k = 0; k < m; k++) {
      int dummy;
      do_query(i, 1);
      cin >> dummy;
    }
    vector<int> local_a(2 * m + 1);
    local_a[m] = a_init;
    for (int k = 1; k <= m; k++) {
      local_a[m + k] = a_pos[k];
      local_a[m - k] = a_neg[k];
    }
    int chosen_q = -1;
    for (int q = 0; q < S; q++) {
      // left -m
      long long stl = ((long long)q - m + 2LL * S) % S;
      int tleft = 0;
      for (int off = 0; off < m; off++) {
        long long sec = (stl + off) % S;
        if (sec < m || covered[sec]) tleft++;
      }
      int al = local_a[0];
      double c1 = al - tleft;
      // right m
      long long str = ((long long)q + m + 2LL * S) % S;
      int tright = 0;
      for (int off = 0; off < m; off++) {
        long long sec = (str + off) % S;
        if (sec < m || covered[sec]) tright++;
      }
      int ar = local_a[2 * m];
      double c2 = ar - tright;
      if (fabs(c1 - c2) > 1e-9) continue;
      double cons = (c1 + c2) / 2.0;
      bool okk = true;
      for (int lp = -m; lp <= m; lp++) {
        int idxx = m + lp;
        int alp = local_a[idxx];
        long long stp = ((long long)q + lp + 2LL * S) % S;
        int tlp = 0;
        for (int off = 0; off < m; off++) {
          long long sec = (stp + off) % S;
          if (sec < m || covered[sec]) tlp++;
        }
        double act_ol = alp - cons;
        if (act_ol > tlp + 1e-9) {
          okk = false;
          break;
        }
      }
      if (okk) {
        chosen_q = q;
        break;
      }
    }
    assert(chosen_q != -1);
    pp[ii - 1] = chosen_q;
  }
  cout << "!";
  for (int val : pp) cout << " " << val;
  cout << endl;
  cout.flush();
  return 0;
}