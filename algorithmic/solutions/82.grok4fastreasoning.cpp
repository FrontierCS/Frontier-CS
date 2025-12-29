#include <bits/stdc++.h>
using namespace std;

int n;
vector<int> perm;

int ask(int i, int j) {
  if (i > j) swap(i, j);
  cout << "? " << i << " " << j << endl;
  cout.flush();
  int r;
  cin >> r;
  if (r == -1) {
    exit(0);
  }
  return r;
}

void output() {
  cout << "!";
  for (int i = 1; i <= n; ++i) {
    cout << " " << perm[i];
  }
  cout << endl;
  cout.flush();
}

int resolve(vector<int> positions, int base, int mask) {
  int sz = positions.size();
  if (sz == 0) return 0;
  if (sz == 1) {
    perm[positions[0]] = base;
    return 0;
  }
  int ref = positions[0];
  int andv = (1 << 12) - 1;
  map<int, int> o_for;
  for (size_t idx = 1; idx < positions.size(); ++idx) {
    int j = positions[idx];
    int o = ask(ref, j);
    o_for[j] = o;
    andv &= o;
  }
  int v_ref = andv & mask;
  int p_ref = base | v_ref;
  perm[ref] = p_ref;
  map<int, vector<int>> subg;
  for (auto& pr : o_for) {
    int j = pr.first;
    int o = pr.second;
    int vo = o & mask;
    int knownv = vo & ~v_ref;
    subg[knownv].push_back(j);
  }
  int q = positions.size() - 1;
  for (auto& prr : subg) {
    int subb = base | prr.first;
    int subm = v_ref;
    q += resolve(prr.second, subb, subm);
  }
  return q;
}

int main() {
  cin >> n;
  perm.resize(n + 1);
  vector<int> allpos(n);
  iota(allpos.begin(), allpos.end(), 1);
  resolve(allpos, 0, (1 << 11) - 1);
  output();
  return 0;
}