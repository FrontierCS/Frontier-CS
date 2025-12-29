#include <bits/stdc++.h>
using namespace std;

int main() {
  int N;
  cin >> N;
  vector<vector<int>> h(N, vector<int>(N));
  for (int i = 0; i < N; i++) {
    for (int j = 0; j < N; j++) {
      cin >> h[i][j];
    }
  }
  // build path
  vector<pair<int, int>> path;
  for (int i = 0; i < N; i++) {
    if (i % 2 == 0) {
      for (int j = 0; j < N; j++) path.emplace_back(i, j);
    } else {
      for (int j = N - 1; j >= 0; j--) path.emplace_back(i, j);
    }
  }
  // simulate
  vector<string> ops;
  vector<vector<int>> current_h = h;
  long long L = 0;
  int cr = 0, cc = 0;
  // process first cell
  {
    int hh = current_h[0][0];
    if (hh > 0) {
      ops.push_back("+" + to_string(hh));
      L += hh;
      current_h[0][0] = 0;
    } else if (hh < 0) {
      int need = -hh;
      int can = min(need, (int)L);
      if (can > 0) {
        ops.push_back("-" + to_string(can));
        L -= can;
        current_h[0][0] += can;
      }
    }
  }
  for (size_t k = 1; k < path.size(); k++) {
    auto [nr, nc] = path[k];
    // move
    int dr = nr - cr, dc = nc - cc;
    char dir;
    if (dr == 1) dir = 'D';
    else if (dr == -1) dir = 'U';
    else if (dc == 1) dir = 'R';
    else if (dc == -1) dir = 'L';
    else assert(false);
    ops.push_back(string(1, dir));
    cr = nr;
    cc = nc;
    // process
    int hh = current_h[cr][cc];
    if (hh > 0) {
      ops.push_back("+" + to_string(hh));
      L += hh;
      current_h[cr][cc] = 0;
    } else if (hh < 0) {
      int need = -hh;
      int can = min(need, (int)L);
      if (can > 0) {
        ops.push_back("-" + to_string(can));
        L -= can;
        current_h[cr][cc] += can;
      }
    }
  }
  // second phase
  vector<pair<int, int>> remaining;
  for (int i = 0; i < N; i++) {
    for (int j = 0; j < N; j++) {
      if (current_h[i][j] < 0) remaining.emplace_back(i, j);
    }
  }
  if (!remaining.empty()) {
    // nearest neighbor
    set<pair<int, int>> tovisit;
    for (auto p : remaining) tovisit.insert(p);
    vector<pair<int, int>> order;
    pair<int, int> now = {cr, cc};
    while (!tovisit.empty()) {
      int bestd = INT_MAX;
      pair<int, int> bestp = {-1, -1};
      for (auto p : tovisit) {
        int d = abs(p.first - now.first) + abs(p.second - now.second);
        if (d < bestd || (d == bestd && p < bestp)) {
          bestd = d;
          bestp = p;
        }
      }
      assert(bestp.first != -1);
      order.push_back(bestp);
      tovisit.erase(bestp);
      now = bestp;
    }
    // now process order
    for (auto target : order) {
      int tr = target.first, tc = target.second;
      // moves
      int dc = tc - cc;
      int dr = tr - cr;
      // horizontal first
      for (int step = 0; step < abs(dc); step++) {
        char dir = (dc > 0 ? 'R' : 'L');
        ops.push_back(string(1, dir));
      }
      // vertical
      for (int step = 0; step < abs(dr); step++) {
        char dir = (dr > 0 ? 'D' : 'U');
        ops.push_back(string(1, dir));
      }
      // now at target
      cr = tr;
      cc = tc;
      // unload
      int hh = current_h[tr][tc];
      int need = -hh;
      ops.push_back("-" + to_string(need));
      L -= need;
      current_h[tr][tc] = 0;
    }
  }
  // output
  for (auto& s : ops) {
    cout << s << '\n';
  }
  return 0;
}