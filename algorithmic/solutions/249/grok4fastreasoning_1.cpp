#include <bits/stdc++.h>
using namespace std;

int n;
vector<int> perm;

int query(int i, int j) {
  if (i > j) swap(i, j);
  cout << "? " << i << " " << j << endl;
  cout.flush();
  int res;
  cin >> res;
  if (res == -1) exit(0);
  return res;
}

int find_zero(vector<int> candidates) {
  int m = candidates.size();
  if (m == 1) return candidates[0];

  if (m == 2) {
    int a = candidates[0], b = candidates[1];
    int o = query(a, b);
    // now find l
    vector<int> possible_l;
    for (int i = 1; i <= n; ++i) {
      if (i != a && i != b) possible_l.push_back(i);
    }
    int tries = 0;
    while (tries < 20) {  // safety limit
      int l = possible_l[rand() % possible_l.size()];
      int sa = query(a, l);
      int sb = query(b, l);
      if (sa != sb) {
        return (sa < sb ? a : b);
      }
      ++tries;
    }
    // if not, pick arbitrary
    return a;
  }

  if (m <= 4) {
    // query all pairs
    map<pair<int, int>, int> ors;
    for (int ii = 0; ii < m; ++ii) {
      for (int jj = ii + 1; jj < m; ++jj) {
        int i1 = candidates[ii], i2 = candidates[jj];
        int res = query(i1, i2);
        if (i1 > i2) swap(i1, i2);
        ors[{i1, i2}] = res;
      }
    }
    // try each as zero
    for (int z = 0; z < m; ++z) {
      int zero_pos = candidates[z];
      vector<int> temp(m, -1);
      temp[z] = 0;
      bool good = true;
      set<int> used;
      used.insert(0);
      for (int ii = 0; ii < m; ++ii) {
        if (ii == z) continue;
        int j = candidates[ii];
        int i1 = min(zero_pos, j), i2 = max(zero_pos, j);
        int o_val = ors[{i1, i2}];
        temp[ii] = o_val;
        if (used.count(o_val) || o_val >= n || o_val < 0) {
          good = false;
          break;
        }
        used.insert(o_val);
      }
      if (!good) continue;
      // check pairs
      good = true;
      for (int ii = 0; ii < m; ++ii) {
        if (ii == z) continue;
        for (int jj = ii + 1; jj < m; ++jj) {
          if (jj == z) continue;
          int j1 = candidates[ii], j2 = candidates[jj];
          int i1 = min(j1, j2), i2 = max(j1, j2);
          int queried = ors[{i1, i2}];
          int comp = temp[ii] | temp[jj];
          if (comp != queried) {
            good = false;
            break;
          }
        }
        if (!good) break;
      }
      if (good) {
        return zero_pos;
      }
    }
    // if none, error
    assert(false);
    return -1;
  }

  // random pick
  int idx = rand() % m;
  int f = candidates[idx];
  vector<int> or_vals(m, 0);
  int and_all = (1 << 11) - 1;
  for (int i = 0; i < m; ++i) {
    if (i == idx) continue;
    int j = candidates[i];
    int s = query(f, j);
    or_vals[i] = s;
    and_all &= s;
  }
  int pf = and_all;
  vector<int> new_cand;
  new_cand.push_back(f);
  for (int i = 0; i < m; ++i) {
    if (i == idx) continue;
    int j = candidates[i];
    if (or_vals[i] == pf) {
      new_cand.push_back(j);
    }
  }
  return find_zero(new_cand);
}

int main() {
  srand(time(NULL));
  cin >> n;
  perm.assign(n + 1, 0);
  vector<int> all_cand(n);
  for (int i = 0; i < n; ++i) all_cand[i] = i + 1;
  int zero_pos = find_zero(all_cand);
  perm[zero_pos] = 0;
  for (int j = 1; j <= n; ++j) {
    if (j == zero_pos) continue;
    int s = query(zero_pos, j);
    perm[j] = s;
  }
  cout << "!";
  for (int i = 1; i <= n; ++i) {
    cout << " " << perm[i];
  }
  cout << endl;
  cout.flush();
  return 0;
}