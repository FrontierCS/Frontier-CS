#include <bits/stdc++.h>

using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int t;
  cin >> t;
  for (int tt = 0; tt < t; tt++) {
    int n;
    cin >> n;
    int k = n;
    cout << k << endl;
    cout.flush();
    vector<int> p(n + 1, 0);
    vector<int> unassigned;
    for (int i = 1; i <= n; i++) unassigned.push_back(i);
    for (int ii = 0; ii < unassigned.size(); ii++) {
      int x = unassigned[ii];
      if (p[x] != 0) continue;
      vector<int> others;
      for (int j = 1; j <= n; j++) if (j != x) others.push_back(j);
      sort(others.begin(), others.end());
      auto get_C = [&](int r) -> int {
        vector<int> q;
        for (int j = 0; j < r; j++) q.push_back(others[j]);
        q.push_back(x);
        for (int j = r; j < (int)others.size(); j++) q.push_back(others[j]);
        cout << "?";
        for (int v : q) cout << " " << v;
        cout << endl;
        cout.flush();
        int ans;
        cin >> ans;
        if (ans == -1) exit(0);
        return ans;
      };
      int C0 = get_C(0);
      int low = 1, high = n - 1;
      int left = -1;
      while (low <= high) {
        int mid = low + (high - low) / 2;
        int cm = get_C(mid);
        if (cm != C0) {
          left = mid;
          high = mid - 1;
        } else {
          low = mid + 1;
        }
      }
      if (left == -1 || get_C(left) == C0) {
        continue;
      }
      low = left + 1;
      high = n - 1;
      int ret = -1;
      while (low <= high) {
        int mid = low + (high - low) / 2;
        int cm = get_C(mid);
        if (cm == C0) {
          ret = mid;
          high = mid - 1;
        } else {
          low = mid + 1;
        }
      }
      int cl = get_C(left);
      int sp;
      if (cl > C0) {
        sp = ret;
      } else {
        sp = left;
      }
      int the_p = others[sp - 1];
      p[x] = the_p;
      int tt;
      if (cl > C0) {
        tt = left;
      } else {
        tt = ret;
      }
      int y0 = others[tt - 1];
      p[y0] = x;
    }
    cout << "!";
    for (int i = 1; i <= n; i++) cout << " " << p[i];
    cout << endl;
    cout.flush();
  }
  return 0;
}