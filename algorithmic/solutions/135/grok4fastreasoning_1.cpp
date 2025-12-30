#include <bits/stdc++.h>

using namespace std;

int main() {
  int k, n;
  cin >> k >> n;
  vector<int> order = {0, 1, 2};
  // initial query
  cout << "? 0 1 2" << endl;
  cout.flush();
  int r;
  cin >> r;
  set<pair<int, int>> clos;
  for (int j = 0; j < r; j++) {
    int u, v;
    cin >> u >> v;
    if (u > v) swap(u, v);
    clos.insert({u, v});
  }
  // set order arbitrarily {0,1,2}
  for (int i = 3; i < n; i++) {
    int q = i;
    int m = order.size();
    int l = 0, h = m;
    while (l < h) {
      int mid = (l + h) / 2;
      int s = order[mid];
      bool inc;
      if (s == 0) {
        inc = false;  // hack
      } else {
        cout << "? 0 " << s << " " << q << endl;
        cout.flush();
        int rr;
        cin >> rr;
        set<pair<int, int>> cl;
        for (int j = 0; j < rr; j++) {
          int u, v;
          cin >> u >> v;
          if (u > v) swap(u, v);
          cl.insert({u, v});
        }
        inc = cl.count({min(0, s), max(0, s)});
      }
      if (inc) {
        l = mid + 1;
      } else {
        h = mid;
      }
    }
    order.insert(order.begin() + l, q);
  }
  cout << "!";
  for (int x : order) {
    cout << " " << x;
  }
  cout << endl;
  cout.flush();
  return 0;
}