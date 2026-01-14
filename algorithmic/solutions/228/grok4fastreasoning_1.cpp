#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(NULL);
  string s;
  cin >> s;
  int n = s.size();
  vector<int> pref(n + 1, 0);
  for (int i = 1; i <= n; i++) {
    pref[i] = pref[i - 1] + (s[i - 1] == '1' ? 1 : 0);
  }
  long long ans = 0;
  for (int k = 1;; k++) {
    long long temp = (long long)k * (k + 1);
    if (temp > n) break;
    int L = temp;
    for (int l = 0; l + L <= n; l++) {
      if (pref[l + L] - pref[l] == k) {
        ans++;
      }
    }
  }
  cout << ans << endl;
  return 0;
}