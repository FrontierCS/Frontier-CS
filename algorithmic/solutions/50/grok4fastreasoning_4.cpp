#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(NULL);
  int n, m;
  cin >> n >> m;
  vector<long long> cost(m + 1);
  for (int i = 1; i <= m; i++) cin >> cost[i];
  vector<bitset<401>> set_bits(m + 1);
  for (int i = 1; i <= n; i++) {
    int k;
    cin >> k;
    for (int j = 0; j < k; j++) {
      int a;
      cin >> a;
      set_bits[a][i] = 1;
    }
  }
  bitset<401> unc;
  for (int i = 1; i <= n; i++) unc[i] = 1;
  vector<bool> available(m + 1, true);
  vector<int> selected;
  while (unc.count() > 0) {
    int best_s = -1;
    long long best_cnt = 0;
    long long best_c = 1;
    for (int s = 1; s <= m; s++) {
      if (!available[s]) continue;
      bitset<401> newcov = set_bits[s] & unc;
      size_t cnt_ = newcov.count();
      if (cnt_ == 0) continue;
      long long cnt = cnt_;
      long long c = cost[s];
      if (best_s == -1 || cnt * best_c > best_cnt * c) {
        best_cnt = cnt;
        best_c = c;
        best_s = s;
      }
    }
    if (best_s == -1) break;
    available[best_s] = false;
    selected.push_back(best_s);
    bitset<401> newcov = set_bits[best_s] & unc;
    unc &= ~newcov;
  }
  sort(selected.begin(), selected.end());
  cout << selected.size() << '\n';
  for (size_t i = 0; i < selected.size(); ++i) {
    if (i > 0) cout << " ";
    cout << selected[i];
  }
  cout << '\n';
  return 0;
}