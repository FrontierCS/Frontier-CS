#include <bits/stdc++.h>
using namespace std;

int main() {
  int n;
  cin >> n;
  vector<int> a(n + 1);
  for (int i = 1; i <= n; i++) cin >> a[i];
  vector<tuple<int, int, int>> ops;
  for (int i = 1; i < n; i++) {
    int p = i;
    while (a[p] != i) p++;
    for (int j = p; j > i; j--) {
      ops.emplace_back(j - 1, j, 1);
      swap(a[j - 1], a[j]);
    }
  }
  int x = 2;
  int m = ops.size();
  cout << x << " " << m << endl;
  for (auto [l, r, d] : ops) {
    cout << l << " " << r << " " << d << endl;
  }
  return 0;
}