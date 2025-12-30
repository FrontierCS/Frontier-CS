#include <bits/stdc++.h>
using namespace std;

int main() {
  int N;
  cin >> N;
  vector<string> board(N);
  for (int i = 0; i < N; i++) cin >> board[i];
  vector<pair<char, int>> moves;
  bool vert_removed[20][20] = {};
  for (int j = 0; j < N; j++) {
    int min_o = N;
    int max_o = -1;
    for (int i = 0; i < N; i++) {
      if (board[i][j] == 'o') {
        min_o = min(min_o, i);
        max_o = max(max_o, i);
      }
    }
    // top
    bool has_top_x = false;
    for (int i = 0; i < min_o; i++) {
      if (board[i][j] == 'x') has_top_x = true;
    }
    int m = min_o;
    if (has_top_x) {
      for (int t = 0; t < m; t++) moves.emplace_back('U', j);
      for (int t = 0; t < m; t++) moves.emplace_back('D', j);
      for (int i = 0; i < m; i++) {
        if (board[i][j] == 'x') vert_removed[i][j] = true;
      }
    }
    // bottom
    if (min_o < N) {
      int s = max_o + 1;
      int k = N - s;
      bool has_bottom_x = false;
      for (int i = s; i < N; i++) {
        if (board[i][j] == 'x') has_bottom_x = true;
      }
      if (has_bottom_x && k > 0) {
        for (int t = 0; t < k; t++) moves.emplace_back('D', j);
        for (int t = 0; t < k; t++) moves.emplace_back('U', j);
        for (int i = s; i < N; i++) {
          if (board[i][j] == 'x') vert_removed[i][j] = true;
        }
      }
    }
  }
  // horizontal
  for (int i = 0; i < N; i++) {
    int min_c = N;
    int max_c = -1;
    for (int j = 0; j < N; j++) {
      if (board[i][j] == 'o') {
        min_c = min(min_c, j);
        max_c = max(max_c, j);
      }
    }
    // left
    bool has_left_x = false;
    for (int j = 0; j < min_c; j++) {
      if (board[i][j] == 'x' && !vert_removed[i][j]) has_left_x = true;
    }
    int ml = min_c;
    if (has_left_x) {
      for (int t = 0; t < ml; t++) moves.emplace_back('L', i);
      for (int t = 0; t < ml; t++) moves.emplace_back('R', i);
    }
    // right
    if (min_c < N) {
      int sk = max_c + 1;
      int kr = N - sk;
      bool has_right_x = false;
      for (int j = sk; j < N; j++) {
        if (board[i][j] == 'x' && !vert_removed[i][j]) has_right_x = true;
      }
      if (has_right_x && kr > 0) {
        for (int t = 0; t < kr; t++) moves.emplace_back('R', i);
        for (int t = 0; t < kr; t++) moves.emplace_back('L', i);
      }
    }
  }
  for (auto [d, p] : moves) {
    cout << d << " " << p << "\n";
  }
  return 0;
}