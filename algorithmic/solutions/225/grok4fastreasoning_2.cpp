#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int n, q;
  cin >> n >> q;
  vector<int> a(n + 1);
  for (int i = 1; i <= n; i++) cin >> a[i];
  const int MAXC = 2200005;
  vector<int> set_min(MAXC), set_max(MAXC);
  for (int i = 1; i <= n; i++) {
    set_min[i] = a[i];
    set_max[i] = a[i];
  }
  int cnt = n;
  vector<pair<int, int>> operations;
  const int TS = 4 * 4100;
  vector<int> tree(TS, 0);
  auto build = [&](auto self, int v, int tl, int tr) -> void {
    if (tl == tr) {
      tree[v] = tl;
      return;
    }
    int tm = (tl + tr) / 2;
    self(self, 2 * v, tl, tm);
    self(self, 2 * v + 1, tm + 1, tr);
    int left = tree[2 * v];
    int right = tree[2 * v + 1];
    if (left != 0 && right != 0 && set_max[left] < set_min[right]) {
      cnt++;
      operations.push_back({left, right});
      tree[v] = cnt;
      set_min[cnt] = set_min[left];
      set_max[cnt] = set_max[right];
    } else {
      tree[v] = 0;
    }
  };
  build(build, 1, 1, n);
  auto get_ids = [&](auto self, int v, int tl, int tr, int l, int r, vector<int>& covers) -> void {
    if (l > r) return;
    if (tl >= l && tr <= r) {
      if (tree[v] != 0) {
        covers.push_back(tree[v]);
        return;
      } else {
        int tm = (tl + tr) / 2;
        self(self, 2 * v, tl, tm, l, r, covers);
        self(self, 2 * v + 1, tm + 1, tr, l, r, covers);
        return;
      }
    }
    int tm = (tl + tr) / 2;
    self(self, 2 * v, tl, tm, l, min(r, tm), covers);
    self(self, 2 * v + 1, tm + 1, tr, max(l, tm + 1), r, covers);
  };
  vector<int> answers(q);
  for (int iq = 0; iq < q; iq++) {
    int l, r;
    cin >> l >> r;
    vector<int> covers;
    get_ids(get_ids, 1, 1, n, l, r, covers);
    if (!covers.empty()) {
      int current = covers[0];
      for (size_t j = 1; j < covers.size(); j++) {
        int u = current;
        int vv = covers[j];
        cnt++;
        operations.push_back({u, vv});
        current = cnt;
        set_min[current] = set_min[u];
        set_max[current] = set_max[vv];
      }
      answers[iq] = current;
    }
  }
  cout << cnt << "\n";
  for (auto& p : operations) {
    cout << p.first << " " << p.second << "\n";
  }
  for (int i = 0; i < q; i++) {
    if (i > 0) cout << " ";
    cout << answers[i];
  }
  cout << "\n";
}