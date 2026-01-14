#include <bits/stdc++.h>
using namespace std;

int main() {
  int t;
  cin >> t;
  for(int test = 0; test < t; test++) {
    int n;
    cin >> n;
    vector<int> s(n, 0);
    set<int> active;
    for(int i = 0; i < n; i++) active.insert(i);
    while(active.size() > 2) {
      bool same = true;
      auto it = active.begin();
      int mins = s[*it];
      for(auto j : active) {
        if(s[j] != mins) {
          same = false;
          break;
        }
      }
      if(same) {
        vector<int> act(active.begin(), active.end());
        int num = act.size();
        int hh = num / 2;
        for(int jj = 0; jj < hh; jj++) {
          int i = act[jj];
          cout << 0 << " " << i << endl;
          int x;
          cin >> x;
          if(x == 1) {
            s[i]++;
          } else {
            active.erase(i);
          }
        }
      }
      int chosen = -1;
      int minss = INT_MAX;
      for(auto i : active) {
        if(s[i] < minss || (s[i] == minss && i < chosen)) {
          minss = s[i];
          chosen = i;
        }
      }
      while(true) {
        cout << 0 << " " << chosen << endl;
        int x;
        cin >> x;
        if(x == 0) break;
        s[chosen]++;
      }
      active.erase(chosen);
    }
    auto it = active.begin();
    int a = *it; ++it;
    int b = *it;
    if(a > b) swap(a, b);
    cout << 1 << " " << a << " " << b << endl;
  }
  return 0;
}