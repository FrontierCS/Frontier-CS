#include <bits/stdc++.h>
using namespace std;

int main() {
  int n, l1, l2;
  cin >> n >> l1 >> l2;
  if (n == 1) {
    cout << "3 1" << endl;
    cout.flush();
    return 0;
  }
  vector<bool> is_good(n - 1, false);
  int queries = 0;
  for (int i = 0; i < n - 1; ++i) {
    cout << "1 " << (i + 1) << " " << (i + 2) << endl;
    cout.flush();
    int x;
    cin >> x;
    is_good[i] = (x == 1);
    ++queries;
  }
  vector<pair<int, int>> comp;
  int cur_start = 1;
  for (int i = 1; i < n; ++i) {
    if (!is_good[i - 1]) {
      int sz = i - cur_start + 1;
      comp.emplace_back(cur_start, sz);
      cur_start = i + 1;
    }
  }
  int sz_last = n - cur_start + 1;
  comp.emplace_back(cur_start, sz_last);
  int cc = comp.size();
  vector<int> perm(n + 1, 0);
  bool found = false;
  if (cc == 1) {
    int st = comp[0].first;
    int sz = comp[0].second;
    for (int j = 0; j < sz; ++j) {
      perm[st + j] = 1 + j;
    }
    found = true;
  } else if (cc == 2) {
    int m0 = comp[0].second;
    int m1 = comp[1].second;
    int st0 = comp[0].first;
    int st1 = comp[1].first;
    for (int rev = 0; rev < 2; ++rev) {
      int len0 = (rev == 0 ? m0 : m1);
      int len1 = (rev == 0 ? m1 : m0);
      int s0 = 1;
      int s1 = 1 + len0;
      for (int d0 = 0; d0 < 2; ++d0) {
        for (int d1 = 0; d1 < 2; ++d1) {
          int low0 = s0;
          int high0 = s0 + len0 - 1;
          int r0 = (d0 == 0 ? high0 : low0);
          int low1_ = s1;
          int high1_ = s1 + len1 - 1;
          int l1_ = (d1 == 0 ? low1_ : high1_);
          if (abs(r0 - l1_) != 1) {
            // assign comp0 gets block (rev ? 1 : 0), with d = (rev ? d1 : d0), low = (rev ? low1_ : low0), high = (rev ? high1_ : high0)
            int lowa = (rev == 0 ? low0 : low1_);
            int higha = (rev == 0 ? high0 : high1_);
            int da = (rev == 0 ? d0 : d1);
            if (da == 0) {
              for (int j = 0; j < m0; ++j) {
                perm[st0 + j] = lowa + j;
              }
            } else {
              for (int j = 0; j < m0; ++j) {
                perm[st0 + j] = higha - j;
              }
            }
            int lowb = (rev == 0 ? low1_ : low0);
            int highb = (rev == 0 ? high1_ : high0);
            int db = (rev == 0 ? d1 : d0);
            if (db == 0) {
              for (int j = 0; j < m1; ++j) {
                perm[st1 + j] = lowb + j;
              }
            } else {
              for (int j = 0; j < m1; ++j) {
                perm[st1 + j] = highb - j;
              }
            }
            found = true;
            goto done2;
          }
        }
      }
    }
  done2:;
  } else if (cc == 3) {
    int ms[3];
    int sts[3];
    for (int ii = 0; ii < 3; ++ii) {
      ms[ii] = comp[ii].second;
      sts[ii] = comp[ii].first;
    }
    for (int a0 = 0; a0 < 3; ++a0) {
      for (int a1 = 0; a1 < 3; ++a1) {
        if (a1 == a0) continue;
        for (int a2 = 0; a2 < 3; ++a2) {
          if (a2 == a0 || a2 == a1) continue;
          vector<int> blen(3);
          blen[a0] = ms[0];
          blen[a1] = ms[1];
          blen[a2] = ms[2];
          vector<int> bstart(3);
          bstart[0] = 1;
          bstart[1] = 1 + blen[0];
          bstart[2] = bstart[1] + blen[1];
          for (int d0 = 0; d0 < 2; ++d0) {
            for (int d1 = 0; d1 < 2; ++d1) {
              for (int d2 = 0; d2 < 2; ++d2) {
                // comp0 block a0
                int low0 = bstart[a0];
                int high0 = low0 + ms[0] - 1;
                int r0 = (d0 == 0 ? high0 : low0);
                // comp1 block a1
                int low1 = bstart[a1];
                int high1 = low1 + ms[1] - 1;
                int l1 = (d1 == 0 ? low1 : high1);
                bool ok1 = (abs(r0 - l1) != 1);
                int r1 = (d1 == 0 ? high1 : low1);
                // comp2 block a2
                int low2 = bstart[a2];
                int high2 = low2 + ms[2] - 1;
                int l2 = (d2 == 0 ? low2 : high2);
                bool ok2 = (abs(r1 - l2) != 1);
                if (ok1 && ok2) {
                  found = true;
                  // assign comp0
                  if (d0 == 0) {
                    for (int j = 0; j < ms[0]; ++j) perm[sts[0] + j] = low0 + j;
                  } else {
                    for (int j = 0; j < ms[0]; ++j) perm[sts[0] + j] = high0 - j;
                  }
                  // comp1
                  if (d1 == 0) {
                    for (int j = 0; j < ms[1]; ++j) perm[sts[1] + j] = low1 + j;
                  } else {
                    for (int j = 0; j < ms[1]; ++j) perm[sts[1] + j] = high1 - j;
                  }
                  // comp2
                  if (d2 == 0) {
                    for (int j = 0; j < ms[2]; ++j) perm[sts[2] + j] = low2 + j;
                  } else {
                    for (int j = 0; j < ms[2]; ++j) perm[sts[2] + j] = high2 - j;
                  }
                  goto done3;
                }
              }
            }
          }
        }
      }
    }
  done3:;
  } else { // cc >=4
    vector<int> odds, evenss;
    for (int v = 1; v < cc; v += 2) odds.push_back(v);
    for (int v = 0; v < cc; v += 2) evenss.push_back(v);
    vector<int> sigma;
    sigma.insert(sigma.end(), odds.begin(), odds.end());
    sigma.insert(sigma.end(), evenss.begin(), evenss.end());
    vector<int> block_for_pos(cc);
    for (int i = 0; i < cc; ++i) {
      block_for_pos[i] = sigma[i];
    }
    vector<int> blen(cc, 0);
    for (int i = 0; i < cc; ++i) {
      blen[block_for_pos[i]] = comp[i].second;
    }
    vector<int> bstart(cc, 0);
    bstart[0] = 1;
    for (int j = 1; j < cc; ++j) {
      bstart[j] = bstart[j - 1] + blen[j - 1];
    }
    for (int i = 0; i < cc; ++i) {
      int bj = block_for_pos[i];
      int low = bstart[bj];
      int sz = comp[i].second;
      int st = comp[i].first;
      for (int j = 0; j < sz; ++j) {
        perm[st + j] = low + j;
      }
    }
    found = true;
  }
  // now output
  cout << "3";
  for (int i = 1; i <= n; ++i) {
    cout << " " << perm[i];
  }
  cout << endl;
  cout.flush();
  return 0;
}