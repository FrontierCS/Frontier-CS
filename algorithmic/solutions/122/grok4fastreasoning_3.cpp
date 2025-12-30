#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int t;
  cin >> t;
  const int MAXW = 100000;
  const int QN = 100000;
  for (int tt = 0; tt < t; tt++) {
    cout << "? " << QN;
    for (int i = 0; i < QN; i++) {
      cout << " 1";
    }
    cout << "\n";
    int res;
    cin >> res;
    if (res == -1) return 0;
    int l = res;
    int W;
    if (l == 1) {
      W = MAXW;
    } else {
      long long nn = QN;
      long long lo = (nn + l - 1LL) / l;
      long long hh = l - 1LL;
      long long hi = (nn - 1LL) / hh;
      hi = min((long long)MAXW, hi);
      long long dd = hi - lo + 1;
      vector<int> art;
      long long DD = dd;
      for (long long i = 0; i < dd; i++) {
        long long C = lo + i;
        long long FF = C - DD + 1;
        art.push_back((int)DD);
        art.push_back((int)FF);
      }
      int nn2 = art.size();
      cout << "? " << nn2;
      for (int x : art) {
        cout << " " << x;
      }
      cout << "\n";
      int res2;
      cin >> res2;
      if (res2 == -1) return 0;
      int extras = res2 - (int)dd;
      W = (int)hi - extras + 1;
    }
    cout << "! " << W << "\n";
  }
  return 0;
}