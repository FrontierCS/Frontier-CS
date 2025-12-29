#include <bits/stdc++.h>
using namespace std;

int main() {
  int n;
  cin >> n;
  vector<pair<int, int>> results(n, make_pair(-1, -1));
  auto query = [&](int i) -> pair<int, int> {
    if (results[i].first != -1) return results[i];
    cout << "? " << i << endl;
    cout.flush();
    int a, b;
    cin >> a >> b;
    results[i] = {a, b};
    return {a, b};
  };
  auto do_search = [&](int l, int r) -> int {
    int lo = l, hi = r;
    while (lo <= hi) {
      int m = lo + (hi - lo) / 2;
      auto [a0m, a1m] = query(m);
      if (a0m == 0) {
        lo = m + 1;
      } else {
        hi = m - 1;
      }
    }
    return hi;
  };
  int c = do_search(0, n - 1);
  auto [a0c, a1c] = query(c);
  if (a0c == 0 && a1c == 0) {
    // done
  } else {
    int next_low = c + 1;
    int d = do_search(next_low, n - 1);
    auto [a0d, a1d] = query(d);
    if (a0d == 0 && a1d == 0) {
      c = d;
    } else {
      // linear from n-1 down to next_low
      int found = -1;
      for (int i = n - 1; i >= next_low; --i) {
        auto [a0, a1] = query(i);
        if (a0 == 0) {
          found = i;
          break;
        }
      }
      if (found != -1 && query(found).second == 0) {
        c = found;
      } else {
        // fallback, should not happen
        c = 0;
      }
    }
  }
  cout << "! " << c << endl;
  cout.flush();
  return 0;
}