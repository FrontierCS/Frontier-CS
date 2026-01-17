#include <bits/stdc++.h>
using namespace std;

int n;
vector<int> p;

bool query(int i, int j, int& r) {
  cout << "? " << i << " " << j << endl;
  cout.flush();
  cin >> r;
  if (r == -1) return false;
  return true;
}

int get_and(const vector<int>& or_list) {
  if (or_list.empty()) return -1;
  int res = or_list[0];
  for (size_t k = 1; k < or_list.size(); ++k) res &= or_list[k];
  return res;
}

void resolve(const vector<int>& G, vector<int> L, int free_mask, int local_zero);

int main() {
  cin >> n;
  p.assign(n + 1, -1);
  int probe = 1;
  vector<int> ors(n + 1, 0);
  for (int j = 1; j <= n; ++j) {
    if (j == probe) continue;
    int r;
    if (!query(probe, j, r)) exit(0);
    ors[j] = r;
  }
  int and_all = -1;
  for (int j = 1; j <= n; ++j) {
    if (j != probe) and_all = (and_all == -1 ? ors[j] : and_all & ors[j]);
  }
  p[probe] = and_all;
  map<int, vector<int>> group_map;
  for (int j = 1; j <= n; ++j) {
    if (j != probe && p[j] == -1) {
      int low = ors[j] & ~p[probe];
      group_map[low].push_back(j);
    }
  }
  int known_zero = -1;
  for (auto& pr : group_map) {
    int low = pr.first;
    vector<int> G = pr.second;
    int mg = G.size();
    vector<int> LL;
    int fixed = low;
    int msk = p[probe];
    set<int> taken;
    for (int jj = 1; jj <= n; ++jj) if (p[jj] != -1) taken.insert(p[jj]);
    for (int z = 0; z < (1 << 11); ++z) {
      if ((z & msk) == z) {
        int x = fixed | z;
        if (x < n && taken.find(x) == taken.end()) LL.push_back(x);
      }
    }
    taken.insert(p[probe]);
    if (mg == 1) {
      p[G[0]] = LL[0];
      if (LL[0] == 0) known_zero = G[0];
      continue;
    }
    if (mg == 2) {
      // special top m=2
      assert(known_zero != -1);
      vector<int> GG = G;
      vector<int> LL_copy = LL;
      int i = GG[0], j = GG[1];
      int r;
      if (!query(i, known_zero, r)) exit(0);
      int z_i = r & msk;
      int px_i = -1;
      for (int x : LL_copy) {
        if ((x & msk) == z_i) {
          px_i = x;
          break;
        }
      }
      assert(px_i != -1);
      p[i] = px_i;
      int px_j = -1;
      for (int x : LL_copy) {
        if (x != px_i) {
          px_j = x;
          break;
        }
      }
      assert(px_j != -1);
      p[j] = px_j;
      if (px_i == 0 || px_j == 0) known_zero = (px_i == 0 ? i : j);
      continue;
    }
    // large
    resolve(G, LL, msk, known_zero);
    for (int pos : G) {
      if (p[pos] == 0) {
        known_zero = pos;
        break;
      }
    }
  }
  // output
  cout << "!";
  for (int i = 1; i <= n; ++i) {
    cout << " " << p[i];
  }
  cout << endl;
  cout.flush();
  return 0;
}

void resolve(const vector<int>& G, vector<int> L, int free_mask, int local_zero) {
  int m = G.size();
  assert(m == (int)L.size());
  if (m <= 1) {
    if (m == 1) p[G[0]] = L[0];
    return;
  }
  if (m == 2) {
    assert(local_zero != -1);
    int i = G[0], j = G[1];
    int r;
    if (!query(i, local_zero, r)) exit(0);
    int z_i = r & free_mask;
    int px_i = -1;
    for (int x : L) {
      if ((x & free_mask) == z_i) {
        px_i = x;
        break;
      }
    }
    assert(px_i != -1);
    p[i] = px_i;
    int px_j = -1;
    for (int x : L) {
      if (x != px_i) {
        px_j = x;
        break;
      }
    }
    assert(px_j != -1);
    p[j] = px_j;
    return;
  }
  if (m <= 4) {
    // enumeration
    vector<vector<int>> obs(m, vector<int>(m, 0));
    for (int ii = 0; ii < m; ++ii) {
      for (int jj = ii + 1; jj < m; ++jj) {
        int r;
        if (!query(G[ii], G[jj], r)) exit(0);
        obs[ii][jj] = obs[jj][ii] = r;
      }
    }
    vector<int> perm = L;
    sort(perm.begin(), perm.end());
    bool found = false;
    vector<int> good_perm;
    do {
      bool good = true;
      for (int ii = 0; ii < m && good; ++ii) {
        for (int jj = ii + 1; jj < m && good; ++jj) {
          int ex = perm[ii] | perm[jj];
          if (ex != obs[ii][jj]) good = false;
        }
      }
      if (good) {
        if (found) assert(false); // multiple
        found = true;
        good_perm = perm;
      }
    } while (next_permutation(perm.begin(), perm.end()));
    assert(found);
    for (int ii = 0; ii < m; ++ii) p[G[ii]] = good_perm[ii];
    return;
  }
  // large m >=5
  int c = G[0];
  vector<int> sub_ors;
  for (size_t kk = 1; kk < G.size(); ++kk) {
    int j = G[kk];
    int r;
    if (!query(c, j, r)) exit(0);
    sub_ors.push_back(r);
  }
  int pc = get_and(sub_ors);
  auto it = find(L.begin(), L.end(), pc);
  assert(it != L.end());
  p[c] = pc;
  vector<int> L_rem;
  for (int x : L) if (x != pc) L_rem.push_back(x);
  map<int, vector<int>> subg;
  for (size_t kk = 1; kk < G.size(); ++kk) {
    int j = G[kk];
    int lnew = sub_ors[kk - 1] & ~pc;
    subg[lnew].push_back(j);
  }
  int zero_lnew = 0;
  int local_zero_pos = local_zero;
  auto zit = subg.find(zero_lnew);
  if (zit != subg.end()) {
    vector<int> zeroG = zit->second;
    vector<int> zeroL;
    int sub_fixed_zero = 0;
    int sub_free = pc & free_mask;
    for (int x : L_rem) {
      if ((x & ~pc) == 0) zeroL.push_back(x);
    }
    resolve(zeroG, zeroL, sub_free, local_zero);
    for (int pos : zeroG) {
      if (p[pos] == 0) {
        local_zero_pos = pos;
        break;
      }
    }
  }
  for (auto& sp : subg) {
    if (sp.first == zero_lnew) continue;
    vector<int> subG = sp.second;
    int sub_m = subG.size();
    if (sub_m == 0) continue;
    vector<int> subL;
    int lnew = sp.first;
    for (int x : L_rem) {
      if ((x & ~pc) == lnew) subL.push_back(x);
    }
    int sub_free = pc & free_mask;
    resolve(subG, subL, sub_free, local_zero_pos);
  }
}