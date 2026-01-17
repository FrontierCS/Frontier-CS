#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int n;
  cin >> n;
  vector<int> p(n);
  for (int i = 0; i < n; i++) cin >> p[i];
  vector<vector<int>> subs(4);
  vector<int> lastv(4);
  vector<bool> is_inc(4, false);
  lastv[0] = 0; is_inc[0] = true;
  lastv[1] = n + 1; is_inc[1] = false;
  lastv[2] = 0; is_inc[2] = true;
  lastv[3] = n + 1; is_inc[3] = false;
  for (int i = 0; i < n; i++) {
    int val = p[i];
    bool assigned = false;
    for (int g = 0; g < 4 && !assigned; g++) {
      bool can = is_inc[g] ? (val > lastv[g]) : (val < lastv[g]);
      if (can) {
        subs[g].push_back(val);
        lastv[g] = val;
        assigned = true;
      }
    }
    if (!assigned) {
      int minsz = INT_MAX;
      int bestg = -1;
      for (int g = 0; g < 4; g++) {
        int sz = subs[g].size();
        if (sz < minsz || (sz == minsz && g < bestg)) {
          minsz = sz;
          bestg = g;
        }
      }
      subs[bestg].push_back(val);
      lastv[bestg] = val;
    }
  }
  cout << subs[0].size() << " " << subs[1].size() << " " << subs[2].size() << " " << subs[3].size() << "\n";
  for (int g = 0; g < 4; g++) {
    for (size_t j = 0; j < subs[g].size(); j++) {
      if (j > 0) cout << " ";
      cout << subs[g][j];
    }
    cout << "\n";
  }
  return 0;
}