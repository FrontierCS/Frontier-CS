#include <bits/stdc++.h>
using namespace std;

int main() {
  int n;
  cin >> n;
  vector<int> arr(n+1);
  for(int i=1; i<=n; i++) {
    cin >> arr[i];
  }
  vector<pair<int,int>> ops;
  int x = 3;
  for(int k=1; k<=n; k++) {
    int pos = -1;
    for(int i=k; i<=n; i++) {
      if(arr[i] == k) {
        pos = i;
        break;
      }
    }
    int rel_r = pos - k + 1;
    while(rel_r > 4) {
      int left = pos - 3;
      ops.emplace_back(left, pos);
      reverse(arr.begin() + left, arr.begin() + pos + 1);
      pos = left;
      rel_r = pos - k + 1;
    }
    if(rel_r == 1) continue;
    if(rel_r == 2 || rel_r == 4) {
      ops.emplace_back(k, pos);
      reverse(arr.begin() + k, arr.begin() + pos + 1);
    } else {
      int p1 = k, p2 = k+1;
      ops.emplace_back(p1, p2);
      reverse(arr.begin() + p1, arr.begin() + p2 + 1);
      int p3 = k+1, p4 = k+2;
      ops.emplace_back(p3, p4);
      reverse(arr.begin() + p3, arr.begin() + p4 + 1);
      ops.emplace_back(p1, p2);
      reverse(arr.begin() + p1, arr.begin() + p2 + 1);
    }
  }
  cout << x << endl;
  int m = ops.size();
  cout << m << endl;
  for(auto [l,r] : ops) {
    cout << l << " " << r << endl;
  }
  return 0;
}