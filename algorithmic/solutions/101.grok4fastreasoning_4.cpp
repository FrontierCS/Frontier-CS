#include <bits/stdc++.h>
using namespace std;

void set_subtree(int node, char val, string& s, const vector<vector<int>>& lvs) {
  for (int lf : lvs[node]) {
    s[lf] = val;
  }
}

int main() {
  int N, R;
  cin >> N >> R;
  vector<int> U(N), V(N);
  for (int i = 0; i < N; i++) {
    cin >> U[i] >> V[i];
  }
  int TN = 2 * N + 1;
  vector<int> par(TN, -1);
  for (int i = 0; i < N; i++) {
    par[U[i]] = i;
    par[V[i]] = i;
  }
  vector<vector<int>> leaves(TN);
  for (int j = 2 * N; j >= 0; j--) {
    if (j >= N) {
      leaves[j] = {j};
    } else {
      leaves[j].reserve(leaves[U[j]].size() + leaves[V[j]].size());
      leaves[j].insert(leaves[j].end(), leaves[U[j]].begin(), leaves[U[j]].end());
      leaves[j].insert(leaves[j].end(), leaves[V[j]].begin(), leaves[V[j]].end());
    }
  }
  string typ(N, ' ');
  auto query = [&](const string& ss) -> int {
    cout << "? " << ss << endl;
    cout.flush();
    int res;
    cin >> res;
    return res;
  };
  // determine root 0
  {
    string s(TN, '0');
    set_subtree(U[0], '0', s, leaves);
    set_subtree(V[0], '1', s, leaves);
    int res = query(s);
    typ[0] = (res ? '|' : '&');
  }
  queue<int> qq;
  if (U[0] < N) qq.push(U[0]);
  if (V[0] < N) qq.push(V[0]);
  while (!qq.empty()) {
    int c = qq.front();
    qq.pop();
    string s(TN, '0');
    // set test
    set_subtree(U[c], '0', s, leaves);
    set_subtree(V[c], '1', s, leaves);
    // propagate settings
    int current = c;
    while (par[current] != -1) {
      int k = par[current];
      int sib = (U[k] == current ? V[k] : U[k]);
      char req = (typ[k] == '&' ? '1' : '0');
      set_subtree(sib, req, s, leaves);
      current = k;
    }
    int res = query(s);
    typ[c] = (res ? '|' : '&');
    // add children
    if (U[c] < N) qq.push(U[c]);
    if (V[c] < N) qq.push(V[c]);
  }
  cout << "!";
  for (char t : typ) cout << t;
  cout << endl;
  cout.flush();
  return 0;
}