#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int n, m;
  cin >> n >> m;
  vector<string> s(m);
  for (int i = 0; i < m; i++) {
    cin >> s[i];
  }
  double ans = 0.0;
  int M = 1 << m;
  for (int mask = 1; mask < M; mask++) {
    int pop = __builtin_popcount(mask);
    double signn = (pop & 1) ? 1.0 : -1.0;
    bool poss = true;
    int freee = 0;
    for (int j = 0; j < n && poss; j++) {
      char forced = '\0';
      bool has = false;
      for (int i = 0; i < m; i++) {
        if ((mask & (1 << i)) == 0) continue;
        char c = s[i][j];
        if (c == '?') continue;
        if (!has) {
          has = true;
          forced = c;
        } else if (forced != c) {
          poss = false;
          break;
        }
      }
      if (poss && !has) freee++;
    }
    if (poss) {
      double p = pow(4.0, freee - n);
      ans += signn * p;
    }
  }
  cout << fixed << setprecision(15) << ans << endl;
}