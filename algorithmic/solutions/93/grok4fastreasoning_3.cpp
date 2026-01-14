#include <bits/stdc++.h>
using namespace std;

int n;
vector<int> par;

void reconstruct(int u, vector<int> Sub) {
  sort(Sub.begin(), Sub.end());
  vector<int> S;
  for (int x : Sub) if (x != u) S.push_back(x);
  vector<int> local_children;
  for (size_t j = 0; j < S.size(); ++j) {
    int v = S[j];
    vector<int> group;
    for (size_t k = 0; k < j; ++k) group.push_back(S[k]);
    for (size_t k = j + 1; k < (size_t)S.size(); ++k) group.push_back(S[k]);
    int R_group = 0;
    if (!group.empty()) {
      cout << "? " << group.size();
      for (int x : group) cout << " " << x;
      cout << endl;
      cout.flush();
      cin >> R_group;
    }
    vector<int> seq2;
    seq2.push_back(v);
    seq2.insert(seq2.end(), group.begin(), group.end());
    cout << "? " << seq2.size();
    for (int x : seq2) cout << " " << x;
    cout << endl;
    cout.flush();
    int R2;
    cin >> R2;
    if (R2 == R_group + 1) {
      local_children.push_back(v);
      par[v] = u;
    }
  }
  if (local_children.empty()) return;
  vector<int> local_C = local_children;
  sort(local_C.begin(), local_C.end());
  int kk = local_C.size();
  vector<vector<int>> local_sub(kk);
  for (int i = 0; i < kk; ++i) {
    local_sub[i].push_back(local_C[i]);
  }
  for (size_t jj = 0; jj < S.size(); ++jj) {
    int v = S[jj];
    bool is_local_child = false;
    for (int c : local_children) {
      if (c == v) {
        is_local_child = true;
        break;
      }
    }
    if (is_local_child) continue;
    int lo = 0, hi = kk - 1;
    while (lo < hi) {
      int mid = (lo + hi) / 2;
      vector<int> F(local_C.begin(), local_C.begin() + mid + 1);
      cout << "? " << F.size() + 1;
      for (int x : F) cout << " " << x;
      cout << " " << v;
      cout << endl;
      cout.flush();
      int RR;
      cin >> RR;
      if (RR == (int)F.size()) {
        hi = mid;
      } else {
        lo = mid + 1;
      }
    }
    local_sub[lo].push_back(v);
  }
  for (int i = 0; i < kk; ++i) {
    if (local_sub[i].size() > 1) {
      reconstruct(local_C[i], local_sub[i]);
    }
  }
}

int main() {
  ios::sync_with_stdio(false);
  cin.tie(NULL);
  int ty;
  cin >> n >> ty;
  par.assign(n + 1, 0);
  int root = -1;
  for (int r = 1; r <= n; ++r) {
    vector<int> seq;
    seq.push_back(r);
    for (int i = 1; i <= n; ++i) {
      if (i != r) seq.push_back(i);
    }
    cout << "? " << seq.size();
    for (int x : seq) cout << " " << x;
    cout << endl;
    cout.flush();
    int R;
    cin >> R;
    if (R == 1) {
      root = r;
      break;
    }
  }
  par[root] = 0;
  vector<int> all_nodes;
  for (int i = 1; i <= n; ++i) all_nodes.push_back(i);
  reconstruct(root, all_nodes);
  cout << "!";
  for (int i = 1; i <= n; ++i) cout << " " << par[i];
  cout << endl;
  cout.flush();
  return 0;
}