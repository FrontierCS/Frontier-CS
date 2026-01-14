#include <bits/stdc++.h>

using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int t;
  cin >> t;
  for (int test = 0; test < t; ++test) {
    int n;
    cin >> n;
    vector<int> active(n);
    for (int i = 0; i < n; ++i) active[i] = i;
    int target = (n + 3) / 2;
    while ((int)active.size() > target) {
      vector<int> new_active;
      for (int i : active) {
        cout << "0 " << i << endl;
        int x;
        cin >> x;
        if (x == 1) {
          new_active.push_back(i);
        }
      }
      active = new_active;
    }
    int a = active[0];
    int b = active[1];
    cout << "1 " << a << " " << b << endl;
  }
  return 0;
}