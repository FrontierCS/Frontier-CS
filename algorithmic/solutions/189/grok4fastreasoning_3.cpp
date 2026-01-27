#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(NULL);
  string s1, s2;
  cin >> s1 >> s2;
  int n = s1.size();
  int m = s2.size();
  vector<vector<int>> pos(128);
  for (int j = 0; j < m; j++) {
    pos[(unsigned char)s2[j]].push_back(j);
  }
  vector<pair<int, int>> matches;
  int cur_j = 0;
  for (int i = 0; i < n; i++) {
    char c = s1[i];
    auto& lst = pos[(unsigned char)c];
    auto it = lower_bound(lst.begin(), lst.end(), cur_j);
    if (it != lst.end()) {
      int k = *it;
      matches.emplace_back(i, k);
      cur_j = k + 1;
    }
  }
  vector<pair<int, int>> all_points;
  all_points.emplace_back(-1, -1);
  for (auto p : matches) all_points.push_back(p);
  all_points.emplace_back(n, m);
  string t = "";
  for (size_t r = 0; r + 1 < all_points.size(); ++r) {
    int pi = all_points[r].first;
    int pj = all_points[r].second;
    int ni = all_points[r + 1].first;
    int nj = all_points[r + 1].second;
    int g1 = ni - pi - 1;
    int g2 = nj - pj - 1;
    int mn = min(g1, g2);
    t += string(mn, 'M');
    int df = g1 - g2;
    if (df > 0) {
      t += string(df, 'D');
    } else if (df < 0) {
      t += string(-df, 'I');
    }
    if (r + 1 < all_points.size() - 1) {
      t += 'M';
    }
  }
  cout << t << '\n';
  return 0;
}