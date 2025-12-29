#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int n;
  cin >> n;
  int req = (int) floor(sqrt((double)n / 2));
  vector<int> S;
  const int MAXV = 1 << 25;
  vector<char> usd(MAXV, 0);
  for (int c = 1; c <= n; c++) {
    if ((int)S.size() >= req) break;
    bool can = true;
    for (int s : S) {
      int v = c ^ s;
      if (v >= MAXV || usd[v]) {
        can = false;
        break;
      }
    }
    if (can) {
      for (int s : S) {
        int v = c ^ s;
        usd[v] = 1;
      }
      S.push_back(c);
    }
  }
  cout << S.size() << '\n';
  for (size_t i = 0; i < S.size(); i++) {
    if (i > 0) cout << ' ';
    cout << S[i];
  }
  cout << '\n';
  return 0;
}