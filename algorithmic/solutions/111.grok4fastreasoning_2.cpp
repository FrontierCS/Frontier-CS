#include <bits/stdc++.h>
using namespace std;

int main() {
  int n;
  cin >> n;
  int req = (int) floor(sqrt(n / 2.0));
  vector<int> S;
  int maxv = 2 * n + 10;
  vector<char> forb(maxv, 0);
  for (int x = 1; x <= n && (int) S.size() < req; ++x) {
    bool good = true;
    for (int s : S) {
      int xr = x ^ s;
      if (xr < maxv && forb[xr]) {
        good = false;
        break;
      }
    }
    if (good) {
      for (int s : S) {
        int xr = x ^ s;
        if (xr < maxv) forb[xr] = 1;
      }
      S.push_back(x);
    }
  }
  cout << S.size() << endl;
  for (size_t i = 0; i < S.size(); ++i) {
    cout << S[i];
    if (i + 1 < S.size()) cout << " ";
    else cout << endl;
  }
  return 0;
}