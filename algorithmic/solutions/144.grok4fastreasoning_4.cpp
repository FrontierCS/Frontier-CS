#include <bits/stdc++.h>
using namespace std;

int main() {
  int n;
  cin >> n;
  int med1 = n / 2;
  int med2 = n / 2 + 1;
  auto query = [&](int ex1, int ex2) -> pair<int, int> {
    vector<int> s;
    for (int i = 1; i <= n; i++) {
      if (i != ex1 && i != ex2) s.push_back(i);
    }
    cout << "0 " << (n - 2) << " ";
    for (int x : s) cout << x << " ";
    cout << endl;
    cout.flush();
    int m1, m2;
    cin >> m1 >> m2;
    return {m1, m2};
  };
  vector<pair<int, int>> resp(n + 1, {-1, -1});
  for (int j = 2; j <= n; j++) {
    resp[j] = query(1, j);
  }
  pair<int, int> ans_pos = {-1, -1};
  for (int j = 2; j <= n; j++) {
    int a = resp[j].first, b = resp[j].second;
    if (a < med1 && b > med2) {
      ans_pos = {1, j};
      break;
    }
  }
  if (ans_pos.first != -1) {
    int i1 = min(ans_pos.first, ans_pos.second);
    int i2 = max(ans_pos.first, ans_pos.second);
    cout << "1 " << i1 << " " << i2 << endl;
    cout.flush();
    return 0;
  }
  vector<int> unamb;
  for (int j = 2; j <= n; j++) {
    int a = resp[j].first, b = resp[j].second;
    if ((a < med1 && b == med2) || (a == med1 && b > med2)) {
      unamb.push_back(j);
    }
  }
  int j0 = unamb[0];
  int aa = resp[j0].first, bb = resp[j0].second;
  int pos_known;
  bool is_med1_known;
  vector<int> cands;
  if (aa < med1 && bb == med2) {
    pos_known = j0;
    is_med1_known = true;
    for (int k = 2; k <= n; k++)
      if (k != j0) {
        int aaa = resp[k].first, bbb = resp[k].second;
        if (aaa < med1 && bbb == med1) {
          cands.push_back(k);
        }
      }
  } else {
    pos_known = j0;
    is_med1_known = false;
    for (int k = 2; k <= n; k++)
      if (k != j0) {
        int aaa = resp[k].first, bbb = resp[k].second;
        if (aaa == med2 && bbb > med2) {
          cands.push_back(k);
        }
      }
  }
  int pos_other = -1;
  for (int c : cands) {
    auto [m1, m2] = query(pos_known, c);
    if (m1 < med1 && m2 > med2) {
      pos_other = c;
      break;
    }
  }
  int i1 = is_med1_known ? pos_known : pos_other;
  int i2 = is_med1_known ? pos_other : pos_known;
  int mi = min(i1, i2);
  int ma = max(i1, i2);
  cout << "1 " << mi << " " << ma << endl;
  cout.flush();
  return 0;
}