#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int t;
  cin >> t;
  for (int test = 0; test < t; test++) {
    int n;
    cin >> n;
    if (n == -1) return 0;
    int m = 2 * n - 1;
    bool found = false;
    for (int x = 1; x <= n && !found; x++) {
      int lo = 1, hi = m;
      while (lo < hi) {
        int md = (lo + hi) / 2;
        cout << "? " << x << " " << (md - lo + 1);
        for (int i = lo; i <= md; i++) cout << " " << i;
        cout << "\n";
        cout.flush();
        int res;
        cin >> res;
        if (res == -1) return 0;
        if (res == 1) {
          hi = md;
        } else {
          lo = md + 1;
        }
      }
      int pos1 = lo;
      cout << "? " << x << " " << (m - 1);
      for (int i = 1; i <= m; i++) {
        if (i != pos1) cout << " " << i;
      }
      cout << "\n";
      cout.flush();
      int res;
      cin >> res;
      if (res == -1) return 0;
      if (res == 0) {
        cout << "! " << x << "\n";
        cout.flush();
        found = true;
      }
    }
  }
  return 0;
}