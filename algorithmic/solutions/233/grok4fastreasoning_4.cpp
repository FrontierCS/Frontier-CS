#include <bits/stdc++.h>
using namespace std;

double logfact[1005];

double logbinom(int n, int k) {
  if (k < 0 || k > n) return -1e300;
  return logfact[n] - logfact[k] - logfact[n - k];
}

int main() {
  logfact[0] = 0.0;
  for (int i = 1; i <= 1000; ++i) {
    logfact[i] = logfact[i - 1] + log(i);
  }
  int t;
  cin >> t;
  for (int test = 0; test < t; ++test) {
    int n, m;
    cin >> n >> m;
    vector<vector<int>> G(n + 1, vector<int>(n + 1));
    for (int i = 1; i <= n; ++i) {
      for (int j = 1; j <= n; ++j) {
        cin >> G[i][j];
      }
    }
    vector<int> all_f;
    for (int l = 1; l <= n; ++l) {
      vector<int> fs(2 * n);
      deque<pair<int, int>> snake;
      for (int j = 1; j <= l; ++j) {
        snake.push_back({1, j});
      }
      int cur_max = INT_MIN;
      for (auto [x, y] : snake) {
        cur_max = max(cur_max, G[x][y]);
      }
      fs[1] = cur_max;
      pair<int, int> nh = {2, 1};
      snake.pop_back();
      snake.push_front(nh);
      cur_max = INT_MIN;
      for (auto [x, y] : snake) {
        cur_max = max(cur_max, G[x][y]);
      }
      fs[2] = cur_max;
      int curr_t = 2;
      vector<deque<pair<int, int>>> states;
      states.push_back(snake);
      while (curr_t < 2 * n - 1) {
        map<int, vector<pair<int, pair<int, int>>>> group;
        set<int> poss_v;
        for (size_t s = 0; s < states.size(); ++s) {
          auto sn = states[s];
          auto hd = sn.front();
          int x = hd.first, y = hd.second;
          vector<pair<int, int>> poss_nh;
          if (x < n) poss_nh.emplace_back(x + 1, y);
          if (y < n) poss_nh.emplace_back(x, y + 1);
          int mw = INT_MIN;
          size_t lenm1 = sn.size() - 1;
          for (size_t k = 0; k < lenm1; ++k) {
            auto p = sn[k];
            mw = max(mw, G[p.first][p.second]);
          }
          for (auto pnh : poss_nh) {
            int gnh = G[pnh.first][pnh.second];
            int nm = (lenm1 == 0 ? gnh : max(mw, gnh));
            poss_v.insert(nm);
            group[nm].emplace_back(s, pnh);
          }
        }
        int V;
        vector<deque<pair<int, int>>> new_states;
        if (poss_v.size() > 1) {
          cout << "? " << l << " " << (curr_t + 1) << endl;
          cout.flush();
          cin >> V;
          auto it = group.find(V);
          if (it != group.end()) {
            for (auto [sidx, pnh] : it->second) {
              auto newsn = states[sidx];
              newsn.pop_back();
              newsn.push_front(pnh);
              new_states.push_back(newsn);
            }
          }
        } else if (!poss_v.empty()) {
          V = *poss_v.begin();
          auto it = group.find(V);
          if (it != group.end()) {
            for (auto [sidx, pnh] : it->second) {
              auto newsn = states[sidx];
              newsn.pop_back();
              newsn.push_front(pnh);
              new_states.push_back(newsn);
            }
          }
        }
        fs[curr_t + 1] = V;
        states = std::move(new_states);
        ++curr_t;
      }
      for (int tt = 1; tt <= 2 * n - 1; ++tt) {
        all_f.push_back(fs[tt]);
      }
    }
    sort(all_f.begin(), all_f.end());
    cout << "!";
    for (int i = 0; i < m; ++i) {
      cout << " " << all_f[i];
    }
    cout << endl;
    cout.flush();
  }
  return 0;
}