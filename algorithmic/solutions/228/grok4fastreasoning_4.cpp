#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  string t;
  cin >> t;
  int N = t.size();
  vector<int> pref(N + 1, 0);
  for (int i = 1; i <= N; ++i) {
    pref[i] = pref[i - 1] + (t[i - 1] == '1' ? 1 : 0);
  }
  long long ans = 0;
  for (int k = 1;; ++k) {
    long long L = (long long)k * (k + 1);
    if (L > N) break;
    int LL = (int)L;
    for (int i = 0; i + LL <= N; ++i) {
      int ones = pref[i + LL] - pref[i];
      if (ones == k) ++ans;
    }
  }
  cout << ans << '\n';
}