#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(NULL);
  int sub, n;
  cin >> sub >> n;
  // set S = {1}
  cout << 1 << " " << 1 << endl;
  cout.flush();
  int r0;
  cin >> r0;
  // find neighbors of 1
  vector<int> ops;
  for (int i = 1; i <= n; ++i) {
    if (i != 1) {
      ops.push_back(i);
      ops.push_back(i);
    }
  }
  int L = ops.size();
  cout << L;
  for (int u : ops) cout << " " << u;
  cout << endl;
  cout.flush();
  vector<int> res(L);
  for (int i = 0; i < L; ++i) cin >> res[i];
  vector<int> neigh;
  for (int i = 0; i < L; i += 2) {
    if (res[i] == 1) neigh.push_back(ops[i]);
  }
  assert(neigh.size() == 2);
  int a = neigh[0];
  int b = neigh[1];
  // set S = {a}
  cout << 2 << " " << 1 << " " << a << endl;
  cout.flush();
  vector<int> res_set(2);
  for (int &x : res_set) cin >> x;
  // now S = {a}
  vector<int> perm;
  perm.push_back(1);
  perm.push_back(a);
  vector<int> rem;
  for (int i = 1; i <= n; ++i) {
    if (i != 1 && i != a) rem.push_back(i);
  }
  int current = a;
  while (!rem.empty()) {
    vector<int> ops_big;
    for (int c : rem) {
      ops_big.push_back(c);
      ops_big.push_back(c);
    }
    int Lb = ops_big.size();
    cout << Lb;
    for (int u : ops_big) cout << " " << u;
    cout << endl;
    cout.flush();
    vector<int> resb(Lb);
    for (int i = 0; i < Lb; ++i) cin >> resb[i];
    int next_c = -1;
    for (int i = 0; i < Lb; i += 2) {
      if (resb[i] == 1) {
        next_c = ops_big[i];
        break;
      }
    }
    assert(next_c != -1);
    auto it = find(rem.begin(), rem.end(), next_c);
    assert(it != rem.end());
    rem.erase(it);
    perm.push_back(next_c);
    // set S = {next_c}
    cout << 2 << " " << current << " " << next_c << endl;
    cout.flush();
    vector<int> res_next(2);
    for (int &x : res_next) cin >> x;
    current = next_c;
  }
  assert(perm.size() == (size_t)n);
  // output
  cout << -1;
  for (int p : perm) cout << " " << p;
  cout << endl;
  cout.flush();
  return 0;
}