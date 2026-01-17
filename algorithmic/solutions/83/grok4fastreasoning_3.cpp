#include <bits/stdc++.h>
using namespace std;

int main() {
  ios_base::sync_with_stdio(false);
  cin.tie(NULL);
  int n;
  cin >> n;
  vector<int> spf(n + 1);
  for (int i = 0; i <= n; i++) spf[i] = i;
  for (long long i = 2; i <= n; i++) {
    if (spf[i] == i) {
      for (long long j = i * i; j <= n; j += i) {
        if (spf[j] == j) spf[j] = i;
      }
    }
  }
  for (int i = 1; i <= n; i++) {
    int x = i;
    int om = 0;
    while (x > 1) {
      int p = spf[x];
      while (x % p == 0) {
        x /= p;
        om++;
      }
    }
    int sign = (om % 2 == 0 ? 1 : -1);
    cout << sign;
    if (i < n) cout << " ";
    else cout << "\n";
  }
  return 0;
}