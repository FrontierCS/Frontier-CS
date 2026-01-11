#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int n;
  cin >> n;
  int m = n / 2;
  map<int, vector<int>> full_known;
  auto query_full = [&](int a) {
    if (full_known.count(a)) return;
    vector<int> &vec = full_known[a];
    vec.resize(n + 1);
    vec[a] = 0;
    for (int b = 1; b <= n; ++b) {
      if (b == a) continue;
      if (full_known.count(b) && full_known[b][a] != -1) {
        vec[b] = full_known[b][a];
      } else {
        cout << "? " << a << " " << b << '\n';
        cout.flush();
        int res;
        cin >> res;
        vec[b] = res;
      }
    }
  };
  int x = 1;
  query_full(x);
  vector<int> current_dist(n + 1);
  for (int b = 1; b <= n; ++b) current_dist[b] = full_known[x][b];
  while (true) {
    vector<int> neighbors;
    for (int y = 1; y <= n; ++y) {
      if (y != x && current_dist[y] == 1) neighbors.push_back(y);
    }
    int dd = neighbors.size();
    if (dd >= n - m) {
      cout << "! " << x << '\n';
      cout.flush();
      return 0;
    }
    int D = 0;
    int uu = -1;
    for (int y = 1; y <= n; ++y) {
      if (y != x && current_dist[y] > D) {
        D = current_dist[y];
        uu = y;
      }
    }
    query_full(uu);
    int ss = 0;
    for (int y = 1; y <= n; ++y) {
      if (y != x && full_known[uu][y] < current_dist[y] + D) ++ss;
    }
    int root_p = -1;
    for (int cand : neighbors) {
      if (full_known[uu][cand] == D - 1) {
        root_p = cand;
        break;
      }
    }
    int other = n - 1 - ss;
    if (ss <= m) {
      if (other <= m) {
        cout << "! " << x << '\n';
        cout.flush();
        return 0;
      }
      vector<int> other_neigh;
      for (int cand : neighbors) if (cand != root_p) other_neigh.push_back(cand);
      int num_o = other_neigh.size();
      int max_pos = (num_o == 0 ? 0 : other - (num_o - 1));
      if (max_pos <= m) {
        cout << "! " << x << '\n';
        cout.flush();
        return 0;
      }
      int large_ui = -1;
      int max_s = 0;
      for (int ui : other_neigh) {
        query_full(ui);
        int sii = 0;
        for (int y = 1; y <= n; ++y) {
          if (y != x && full_known[ui][y] < current_dist[y] + 1) ++sii;
        }
        if (sii > max_s) {
          max_s = sii;
          large_ui = ui;
        }
      }
      if (max_s > m) {
        int new_x = large_ui;
        vector<bool> in_T(n + 1, false);
        for (int y = 1; y <= n; ++y) {
          if (y != x && full_known[new_x][y] < current_dist[y] + 1) in_T[y] = true;
        }
        in_T[new_x] = true;
        vector<int> new_dist(n + 1);
        for (int y = 1; y <= n; ++y) {
          new_dist[y] = in_T[y] ? current_dist[y] - 1 : current_dist[y] + 1;
        }
        new_dist[x] = 1;
        new_dist[new_x] = 0;
        current_dist = new_dist;
        x = new_x;
        continue;
      } else {
        cout << "! " << x << '\n';
        cout.flush();
        return 0;
      }
    } else {
      int new_x = root_p;
      vector<bool> in_T(n + 1, false);
      for (int y = 1; y <= n; ++y) {
        if (y != x && full_known[uu][y] < current_dist[y] + D) in_T[y] = true;
      }
      in_T[new_x] = true;
      vector<int> new_dist(n + 1);
      for (int y = 1; y <= n; ++y) {
        new_dist[y] = in_T[y] ? current_dist[y] - 1 : current_dist[y] + 1;
      }
      new_dist[x] = 1;
      new_dist[new_x] = 0;
      current_dist = new_dist;
      x = new_x;
      continue;
    }
  }
  return 0;
}