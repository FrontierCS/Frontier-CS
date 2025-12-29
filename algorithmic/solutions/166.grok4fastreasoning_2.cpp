#include <bits/stdc++.h>
using namespace std;

int main() {
  int N;
  cin >> N;
  vector<vector<int>> h(20, vector<int>(20));
  for (int i = 0; i < 20; i++) {
    for (int j = 0; j < 20; j++) {
      cin >> h[i][j];
    }
  }
  int row = 0, col = 0;
  int curload = 0;
  vector<string> operations;
  auto is_done = [&]() -> bool {
    for (int i = 0; i < 20; i++) {
      for (int j = 0; j < 20; j++) {
        if (h[i][j] != 0) return false;
      }
    }
    return true;
  };
  while (operations.size() < 100000 && !is_done()) {
    bool changed = true;
    while (changed && operations.size() < 100000) {
      changed = false;
      if (h[row][col] > 0) {
        int d = min(1000000, h[row][col]);
        operations.push_back("+" + to_string(d));
        h[row][col] -= d;
        curload += d;
        changed = true;
      } else if (h[row][col] < 0 && curload > 0) {
        int d = min({1000000, curload, -h[row][col]});
        operations.push_back("-" + to_string(d));
        h[row][col] += d;
        curload -= d;
        changed = true;
      }
    }
    if (is_done()) break;
    int tr = -1, tc = -1;
    int min_d = INT_MAX;
    int max_pr = -1;
    for (int i = 0; i < 20; i++) {
      for (int j = 0; j < 20; j++) {
        if (h[i][j] == 0) continue;
        if ((curload > 0 && h[i][j] >= 0) || (curload == 0 && h[i][j] <= 0)) continue;
        int dist = abs(i - row) + abs(j - col);
        int pr = abs(h[i][j]);
        bool update = false;
        if (dist < min_d) {
          update = true;
        } else if (dist == min_d) {
          if (pr > max_pr) {
            update = true;
          } else if (pr == max_pr) {
            if (i < tr || (i == tr && j < tc)) {
              update = true;
            }
          }
        }
        if (update) {
          tr = i;
          tc = j;
          min_d = dist;
          max_pr = pr;
        }
      }
    }
    if (tr == -1) break;
    while (col < tc && operations.size() < 100000) {
      operations.push_back("R");
      col++;
    }
    while (col > tc && operations.size() < 100000) {
      operations.push_back("L");
      col--;
    }
    while (row < tr && operations.size() < 100000) {
      operations.push_back("D");
      row++;
    }
    while (row > tr && operations.size() < 100000) {
      operations.push_back("U");
      row--;
    }
    if (operations.size() >= 100000) break;
  }
  for (const auto& op : operations) {
    cout << op << '\n';
  }
  return 0;
}