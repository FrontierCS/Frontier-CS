#include <bits/stdc++.h>

using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int n, m;
  cin >> n >> m;
  vector<int> errors(n, 0);
  for (int wager = 0; wager < m; ++wager) {
    string s;
    cin >> s;
    int min_err = *min_element(errors.begin(), errors.end());
    vector<int> leaders;
    for (int i = 0; i < n; i++) {
      if (errors[i] == min_err) leaders.push_back(i);
    }
    int count0 = 0, count1 = 0;
    for (int idx : leaders) {
      int pred = s[idx] - '0';
      if (pred == 0) count0++;
      else count1++;
    }
    int my_pred;
    if (count0 > count1) my_pred = 0;
    else if (count1 > count0) my_pred = 1;
    else {
      int all0 = 0, all1 = 0;
      for (char c : s) {
        int p = c - '0';
        if (p == 0) all0++;
        else all1++;
      }
      my_pred = (all0 >= all1 ? 0 : 1);
    }
    cout << my_pred << endl;
    int y;
    cin >> y;
    for (int i = 0; i < n; i++) {
      int pred_i = s[i] - '0';
      if (pred_i != y) errors[i]++;
    }
  }
  return 0;
}