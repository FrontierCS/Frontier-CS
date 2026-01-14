#include <bits/stdc++.h>
using namespace std;

int find_min_yes(int L, int R, int x, const vector<int>& nodes, int nn) {
  if (L > R) return -1;
  if (L == R) {
    cout << "? 2 " << nodes[L] << " " << x << endl;
    cout.flush();
    int res;
    cin >> res;
    if (res == 1) return L;
    return -1;
  }
  int len = R - L + 1;
  if (len <= 32) {
    int minj = -1;
    for (int j = L; j <= R; j++) {
      cout << "? 2 " << nodes[j] << " " << x << endl;
      cout.flush();
      int res;
      cin >> res;
      if (res == 1) {
        minj = j;
        break;
      }
    }
    return minj;
  }
  // batch x + [L..R]
  vector<int> seq;
  seq.push_back(x);
  for (int j = L; j <= R; j++) seq.push_back(nodes[j]);
  cout << "? " << (1 + len);
  for (int v : seq) cout << " " << v;
  cout << endl;
  cout.flush();
  int res;
  cin >> res;
  int gg = res - 1;
  if (gg == len) {
    return -1;
  }
  // batch [L..R]
  vector<int> seqs;
  for (int j = L; j <= R; j++) seqs.push_back(nodes[j]);
  cout << "? " << len;
  for (int v : seqs) cout << " " << v;
  cout << endl;
  cout.flush();
  int res_s;
  cin >> res_s;
  int g2 = res_s;
  int mid = L + (R - L) / 2;
  if (gg < g2) {
    // definite yes
    int left_min = find_min_yes(L, mid, x, nodes, nn);
    if (left_min != -1) return left_min;
    return find_min_yes(mid + 1, R, x, nodes, nn);
  } else {
    // ambiguous
    int left_min = find_min_yes(L, mid, x, nodes, nn);
    if (left_min != -1) return left_min;
    return find_min_yes(mid + 1, R, x, nodes, nn);
  }
}

int main() {
  int n, ty;
  cin >> n >> ty;
  vector<int> G(n + 1);
  for (int f = 1; f <= n; f++) {
    vector<int> seq;
    seq.push_back(f);
    for (int j = 1; j <= n; j++) {
      if (j != f) seq.push_back(j);
    }
    cout << "? " << n;
    for (int v : seq) cout << " " << v;
    cout << endl;
    cout.flush();
    int res;
    cin >> res;
    G[f] = res - 1;
  }
  int root = -1;
  for (int f = 1; f <= n; f++) {
    if (G[f] == 0) {
      root = f;
      break;
    }
  }
  vector<pair<int, int>> sorter;
  for (int i = 1; i <= n; i++) {
    sorter.emplace_back(-G[i], i);
  }
  sort(sorter.begin(), sorter.end());
  vector<int> nodes(n);
  vector<int> pos(n + 1);
  for (int i = 0; i < n; i++) {
    nodes[i] = sorter[i].second;
    pos[nodes[i]] = i;
  }
  vector<int> parent(n + 1, 0);
  parent[root] = 0;
  for (int xx = 1; xx <= n; xx++) {
    if (xx == root) continue;
    int start = pos[xx] + 1;
    int ppos = find_min_yes(start, n - 1, xx, nodes, n);
    int py = (ppos == -1 ? -1 : nodes[ppos]);
    parent[xx] = py;
  }
  cout << "!";
  for (int i = 1; i <= n; i++) {
    cout << " " << parent[i];
  }
  cout << endl;
  cout.flush();
  return 0;
}