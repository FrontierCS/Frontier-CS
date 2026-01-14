#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int n, q;
  cin >> n >> q;
  vector<int> a(n + 1);
  for (int i = 1; i <= n; i++) {
    cin >> a[i];
  }
  vector<pair<int, int>> queries(q);
  for (int i = 0; i < q; i++) {
    int l, r;
    cin >> l >> r;
    queries[i] = {l, r};
  }
  int cnt = n;
  vector<pair<int, int>> merges;
  vector<int> ks(q);
  for (int iq = 0; iq < q; iq++) {
    int l = queries[iq].first;
    int r = queries[iq].second;
    vector<int> pos;
    for (int i = l; i <= r; i++) {
      pos.push_back(i);
    }
    sort(pos.begin(), pos.end(), [&](int x, int y) {
      return a[x] < a[y];
    });
    if (pos.empty()) continue;
    int current = pos[0];
    for (size_t j = 1; j < pos.size(); j++) {
      int nexts = pos[j];
      int newid = ++cnt;
      merges.emplace_back(current, nexts);
      current = newid;
    }
    ks[iq] = current;
  }
  cout << cnt << '\n';
  for (auto p : merges) {
    cout << p.first << " " << p.second << '\n';
  }
  for (int i = 0; i < q; i++) {
    if (i > 0) cout << " ";
    cout << ks[i];
  }
  cout << '\n';
  return 0;
}