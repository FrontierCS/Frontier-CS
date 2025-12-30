#include <bits/stdc++.h>
using namespace std;

int main() {
  int n, m;
  cin >> n >> m;
  vector<vector<int>> stacks(n + 2);
  for (int i = 1; i <= n; i++) {
    stacks[i].resize(m);
    for (int j = 0; j < m; j++) {
      cin >> stacks[i][j];
    }
  }
  vector<vector<int>> pole_color_count(n + 2, vector<int>(n + 1, 0));
  for (int p = 1; p <= n; p++) {
    for (int b : stacks[p]) {
      pole_color_count[p][b]++;
    }
  }
  vector<tuple<int, int, int>> cand;
  for (int c = 1; c <= n; c++) {
    for (int p = 1; p <= n + 1; p++) {
      int cnt = (p <= n ? pole_color_count[p][c] : 0);
      cand.emplace_back(cnt, c, p);
    }
  }
  sort(cand.begin(), cand.end(), [](const tuple<int, int, int>& a, const tuple<int, int, int>& b) {
    return get<0>(a) > get<0>(b);
  });
  vector<int> target(n + 1, 0);
  vector<bool> used(n + 2, false);
  for (auto& t : cand) {
    int cnt, c, p;
    tie(cnt, c, p) = t;
    if (target[c] == 0 && !used[p]) {
      target[c] = p;
      used[p] = true;
    }
  }
  for (int c = 1; c <= n; c++) {
    if (target[c] == 0) {
      for (int p = 1; p <= n + 1; p++) {
        if (!used[p]) {
          target[c] = p;
          used[p] = true;
          break;
        }
      }
    }
  }
  vector<pair<int, int>> moves;
  auto is_pure_correct = [&](int p) -> bool {
    if (stacks[p].empty()) return false;
    int c = stacks[p].back();
    if (target[c] != p) return false;
    if (pole_color_count[p][c] != (int)stacks[p].size()) return false;
    return true;
  };
  auto perform_move = [&](int x, int y) {
    int ball = stacks[x].back();
    stacks[x].pop_back();
    pole_color_count[x][ball]--;
    stacks[y].push_back(ball);
    pole_color_count[y][ball]++;
    moves.emplace_back(x, y);
  };
  const int MAX_MOVES = 2000000;
  while (moves.size() < MAX_MOVES) {
    bool done = true;
    for (int c = 1; c <= n && done; c++) {
      int y = target[c];
      if ((int)stacks[y].size() != m || pole_color_count[y][c] != m) {
        done = false;
      }
    }
    if (done) break;
    bool did_good = false;
    for (int x = 1; x <= n + 1; x++) {
      if (stacks[x].empty()) continue;
      int c = stacks[x].back();
      int y = target[c];
      if (y == x) continue;
      if (stacks[y].size() < (size_t)m && (stacks[y].empty() || stacks[y].back() == c)) {
        perform_move(x, y);
        did_good = true;
        break;
      }
    }
    if (did_good) continue;
    int chosen_x = -1;
    for (int x = 1; x <= n + 1; x++) {
      if (stacks[x].size() == (size_t)m && !is_pure_correct(x)) {
        chosen_x = x;
        break;
      }
    }
    if (chosen_x == -1) {
      for (int x = 1; x <= n + 1; x++) {
        if (!stacks[x].empty() && !is_pure_correct(x)) {
          chosen_x = x;
          break;
        }
      }
    }
    if (chosen_x == -1) break;
    int c = stacks[chosen_x].back();
    int y = target[c];
    if (y != chosen_x && stacks[y].size() < (size_t)m && (stacks[y].empty() || stacks[y].back() == c)) {
      perform_move(chosen_x, y);
      continue;
    }
    int empty_y = -1;
    for (int i = 1; i <= n + 1; i++) {
      if (stacks[i].empty() && i != chosen_x) {
        empty_y = i;
        break;
      }
    }
    if (empty_y != -1) {
      perform_move(chosen_x, empty_y);
      continue;
    }
    int best_y = -1;
    int min_s = m + 1;
    for (int i = 1; i <= n + 1; i++) {
      if (i == chosen_x) continue;
      if (stacks[i].size() >= (size_t)m) continue;
      if (is_pure_correct(i)) continue;
      int s = stacks[i].size();
      if (s < min_s || (s == min_s && i < best_y)) {
        min_s = s;
        best_y = i;
      }
    }
    if (best_y == -1) {
      min_s = m + 1;
      best_y = -1;
      for (int i = 1; i <= n + 1; i++) {
        if (i == chosen_x) continue;
        if (stacks[i].size() >= (size_t)m) continue;
        int s = stacks[i].size();
        if (s < min_s || (s == min_s && i < best_y)) {
          min_s = s;
          best_y = i;
        }
      }
    }
    perform_move(chosen_x, best_y);
  }
  cout << moves.size() << endl;
  for (auto [x, y] : moves) {
    cout << x << " " << y << endl;
  }
  return 0;
}