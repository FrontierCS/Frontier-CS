#include <bits/stdc++.h>

using namespace std;

int main() {
  int n;
  cin >> n;
  vector<int> curr(n+1);
  for(int i=1; i<=n; i++) {
    cin >> curr[i];
  }
  vector<pair<int,int>> ops;
  for(int k=1; k<=n; k++) {
    int p = 0;
    for(int j=k; j<=n; j++) {
      if(curr[j] == k) {
        p = j;
        break;
      }
    }
    while(p > k) {
      int L, R;
      if(p - k >= 3) {
        L = p - 3;
        R = p;
        reverse(curr.begin() + L, curr.begin() + R + 1);
        ops.emplace_back(L, R);
        p = L;
      } else {
        L = p - 1;
        R = p;
        reverse(curr.begin() + L, curr.begin() + R + 1);
        ops.emplace_back(L, R);
        p = L;
      }
    }
  }
  cout << 3 << endl;
  cout << ops.size() << endl;
  for(auto [l, r] : ops) {
    cout << l << " " << r << endl;
  }
  return 0;
}