#include <bits/stdc++.h>
using namespace std;

int main() {
  int N = 20;
  vector<string> board(N);
  for (int i = 0; i < N; i++) cin >> board[i];
  vector<int> maxr_up(N, -1);
  vector<int> minr_down(N, N);
  vector<int> maxc_left(N, -1);
  vector<int> minc_right(N, N);
  for (int r = 0; r < N; r++) {
    for (int c = 0; c < N; c++) {
      if (board[r][c] != 'x') continue;
      bool can_up = true;
      for (int ii = 0; ii < r; ii++) if (board[ii][c] == 'o') { can_up = false; break; }
      bool can_down = true;
      for (int ii = r + 1; ii < N; ii++) if (board[ii][c] == 'o') { can_down = false; break; }
      bool can_left = true;
      for (int jj = 0; jj < c; jj++) if (board[r][jj] == 'o') { can_left = false; break; }
      bool can_right = true;
      for (int jj = c + 1; jj < N; jj++) if (board[r][jj] == 'o') { can_right = false; break; }
      int best_d = INT_MAX;
      char ch_dir = ' ';
      int ch_line = -1;
      bool ch_is_col = false;
      if (can_up) {
        int d = r + 1;
        best_d = d;
        ch_dir = 'U';
        ch_line = c;
        ch_is_col = true;
      }
      if (can_down) {
        int d = N - r;
        if (d < best_d) {
          best_d = d;
          ch_dir = 'D';
          ch_line = c;
          ch_is_col = true;
        }
      }
      if (can_left) {
        int d = c + 1;
        if (d < best_d) {
          best_d = d;
          ch_dir = 'L';
          ch_line = r;
          ch_is_col = false;
        }
      }
      if (can_right) {
        int d = N - c;
        if (d < best_d) {
          best_d = d;
          ch_dir = 'R';
          ch_line = r;
          ch_is_col = false;
        }
      }
      if (ch_dir == 'U') {
        maxr_up[ch_line] = max(maxr_up[ch_line], r);
      } else if (ch_dir == 'D') {
        minr_down[ch_line] = min(minr_down[ch_line], r);
      } else if (ch_dir == 'L') {
        maxc_left[ch_line] = max(maxc_left[ch_line], c);
      } else if (ch_dir == 'R') {
        minc_right[ch_line] = min(minc_right[ch_line], c);
      }
    }
  }
  for (int j = 0; j < N; j++) {
    if (maxr_up[j] != -1) {
      int k = maxr_up[j] + 1;
      for (int t = 0; t < k; t++) cout << "U " << j << '\n';
      for (int t = 0; t < k; t++) cout << "D " << j << '\n';
    }
    if (minr_down[j] != N) {
      int k = N - minr_down[j];
      for (int t = 0; t < k; t++) cout << "D " << j << '\n';
      for (int t = 0; t < k; t++) cout << "U " << j << '\n';
    }
  }
  for (int i = 0; i < N; i++) {
    if (maxc_left[i] != -1) {
      int k = maxc_left[i] + 1;
      for (int t = 0; t < k; t++) cout << "L " << i << '\n';
      for (int t = 0; t < k; t++) cout << "R " << i << '\n';
    }
    if (minc_right[i] != N) {
      int k = N - minc_right[i];
      for (int t = 0; t < k; t++) cout << "R " << i << '\n';
      for (int t = 0; t < k; t++) cout << "L " << i << '\n';
    }
  }
  return 0;
}