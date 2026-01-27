#include <bits/stdc++.h>
using namespace std;

int main() {
  int N;
  cin >> N;
  vector<int> A(N), B(N);
  long long sa = 0, sb = 0;
  for (int &x : A) {
    cin >> x;
    sa += x;
  }
  for (int &x : B) {
    cin >> x;
    sb += x;
  }
  if (sa != sb) {
    cout << "No" << endl;
    return 0;
  }
  int init_dist = 0;
  for (int k = 0; k < N; k++) init_dist += abs(A[k] - B[k]);
  if (init_dist == 0) {
    cout << "Yes" << endl << 0 << endl;
    return 0;
  }
  struct State {
    vector<int> pos;
    vector<pair<int, int>> path;
    int d;
  };
  vector<State> beam{{A, {}, init_dist}};
  set<vector<int>> visited;
  visited.insert(A);
  int width = 20;
  int allow_increase = 10;
  int max_steps = 5000;
  bool found = false;
  vector<pair<int, int>> ans_path;
  int step = 0;
  while (!found && step < max_steps && !beam.empty()) {
    vector<tuple<int, int, int, int>> cands;
    int cur_min = INT_MAX;
    for (auto &bs : beam) cur_min = min(cur_min, bs.d);
    int max_all = cur_min + allow_increase;
    for (size_t b = 0; b < beam.size(); ++b) {
      const vector<int> &st = beam[b].pos;
      int cd = beam[b].d;
      for (int ii = 1; ii < N; ++ii) {
        for (int jj = ii + 1; jj <= N; ++jj) {
          int x = st[ii - 1];
          int y = st[jj - 1];
          int nx = y - 1;
          int ny = x + 1;
          int oldc = abs(x - B[ii - 1]) + abs(y - B[jj - 1]);
          int newc = abs(nx - B[ii - 1]) + abs(ny - B[jj - 1]);
          int nd = cd + newc - oldc;
          cands.emplace_back(nd, ii, jj, (int)b);
        }
      }
    }
    sort(cands.begin(), cands.end());
    vector<State> new_beam;
    size_t num_cand = 0;
    for (; num_cand < cands.size(); ++num_cand) {
      auto [nd, ii, jj, b] = cands[num_cand];
      if (nd > max_all) break;
      const State &parent = beam[b];
      vector<int> ns = parent.pos;
      ns[ii - 1] = parent.pos[jj - 1] - 1;
      ns[jj - 1] = parent.pos[ii - 1] + 1;
      if (visited.count(ns)) continue;
      int real_d = 0;
      bool zero = true;
      for (int p = 0; p < N; p++) {
        int dif = abs(ns[p] - B[p]);
        real_d += dif;
        if (dif != 0) zero = false;
      }
      if (zero) {
        found = true;
        ans_path = parent.path;
        ans_path.emplace_back(ii, jj);
        break;
      }
      vector<pair<int, int>> np = parent.path;
      np.emplace_back(ii, jj);
      new_beam.push_back({move(ns), move(np), real_d});
      visited.insert(new_beam.back().pos);
      if (new_beam.size() >= (size_t)width) break;
    }
    beam = move(new_beam);
    step++;
  }
  if (found) {
    cout << "Yes" << endl;
    cout << ans_path.size() << endl;
    for (auto p : ans_path) {
      cout << p.first << " " << p.second << endl;
    }
  } else {
    cout << "No" << endl;
  }
  return 0;
}