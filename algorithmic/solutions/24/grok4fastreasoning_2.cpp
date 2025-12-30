#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(NULL);
  int n;
  while (cin >> n) {
    vector<vector<int>> C(n, vector<int>(n));
    for (int i = 0; i < n; i++) {
      for (int j = 0; j < n; j++) {
        cin >> C[i][j];
      }
    }
    vector<int> p(n);
    vector<bool> used(n + 1);
    bool found = false;
    vector<int> perm;
    auto dfs = [&](auto&& self, int pos, int cur_changes, int last_c, int p0_idx, int& count0, int& count1) -> bool {
      if (found) return true;
      if (pos == n) {
        int cn = C[p[n - 1]][p[0]];
        int last_change = (last_c != cn ? 1 : 0);
        if (cur_changes + last_change <= 1) {
          found = true;
          perm.assign(p.begin(), p.end());
          return true;
        }
        return false;
      }
      for (int v = 1; v <= n; v++) {
        if (used[v]) continue;
        int new_c = C[p[pos - 1]][v];
        int new_change = (pos >= 1 && last_c != new_c ? 1 : 0);
        if (cur_changes + new_change > 1) continue;
        bool is_switch = (new_change == 1);
        int remaining_after = n - pos - 1;
        bool can_proceed = true;
        if (is_switch && remaining_after > 0) {
          int delta = (C[p[0]][v] == new_c ? 1 : 0);
          int rem_count = (new_c == 0 ? count0 : count1) - delta;
          if (rem_count <= 0) can_proceed = false;
        } else if (is_switch && remaining_after == 0) {
          if (C[v][p[0]] != new_c) can_proceed = false;
        }
        if (!can_proceed) continue;
        int old_count0 = count0;
        int old_count1 = count1;
        if (C[p[0]][v] == 0) count0--;
        else if (C[p[0]][v] == 1) count1--;
        p[pos] = v;
        used[v] = true;
        if (self(self, pos + 1, cur_changes + new_change, new_c, p0_idx, count0, count1)) return true;
        used[v] = false;
        p[pos] = 0;
        count0 = old_count0;
        count1 = old_count1;
      }
      return false;
    };
    for (int first = 1; first <= n && !found; first++) {
      fill(used.begin(), used.end(), false);
      p[0] = first;
      used[first] = true;
      int cnt0 = 0, cnt1 = 0;
      for (int j = 1; j <= n; j++) {
        if (j != first && C[first][j] == 0) cnt0++;
        if (j != first && C[first][j] == 1) cnt1++;
      }
      bool ok = false;
      for (int second = 1; second <= n && !ok; second++) {
        if (second == first) continue;
        int new_c = C[first][second];
        int new_change = 0;
        int temp_cnt0 = cnt0 - (C[first][second] == 0 ? 1 : 0);
        int temp_cnt1 = cnt1 - (C[first][second] == 1 ? 1 : 0);
        p[1] = second;
        used[second] = true;
        if (dfs(dfs, 2, new_change, new_c, 0, temp_cnt0, temp_cnt1)) {
          ok = true;
          found = true;
        }
        used[second] = false;
      }
      used[first] = false;
    }
    if (found) {
      for (int i = 0; i < n; i++) {
        if (i > 0) cout << " ";
        cout << perm[i];
      }
      cout << "\n";
    } else {
      cout << "-1\n";
    }
  }
  return 0;
}