#include <bits/stdc++.h>
using namespace std;

int main() {
  int N, M;
  cin >> N >> M;
  vector<string> subs(M);
  for (int i = 0; i < M; i++) cin >> subs[i];
  sort(subs.begin(), subs.end(), [](const string& a, const string& b) {
    return a.size() > b.size();
  });
  vector<vector<char>> grid(N, vector<char>(N, '.'));
  int placed = 0;
  for (auto& s : subs) {
    int k = s.size();
    vector<int> row_filled(N, 0);
    vector<int> col_filled(N, 0);
    for (int r = 0; r < N; r++) {
      for (int c = 0; c < N; c++) {
        if (grid[r][c] != '.') {
          row_filled[r]++;
          col_filled[c]++;
        }
      }
    }
    int best_score = -1;
    int best_type = -1, best_idx = -1, best_start = -1;
    // horizontal
    for (int r = 0; r < N; r++) {
      int line_filled = row_filled[r];
      int bonus = N - line_filled;
      for (int st = 0; st < N; st++) {
        bool can = true;
        int agree = 0;
        for (int p = 0; p < k; p++) {
          int cc = (st + p) % N;
          char curr = grid[r][cc];
          if (curr != '.' && curr != s[p]) {
            can = false;
            break;
          }
          if (curr != '.') agree++;
        }
        if (can) {
          int fills = k - agree;
          int score = agree * 1000 + fills * 10 + bonus;
          if (score > best_score) {
            best_score = score;
            best_type = 0;
            best_idx = r;
            best_start = st;
          }
        }
      }
    }
    // vertical
    for (int c = 0; c < N; c++) {
      int line_filled = col_filled[c];
      int bonus = N - line_filled;
      for (int st = 0; st < N; st++) {
        bool can = true;
        int agree = 0;
        for (int p = 0; p < k; p++) {
          int rr = (st + p) % N;
          char curr = grid[rr][c];
          if (curr != '.' && curr != s[p]) {
            can = false;
            break;
          }
          if (curr != '.') agree++;
        }
        if (can) {
          int fills = k - agree;
          int score = agree * 1000 + fills * 10 + bonus;
          if (score > best_score) {
            best_score = score;
            best_type = 1;
            best_idx = c;
            best_start = st;
          }
        }
      }
    }
    if (best_score >= 0) {
      placed++;
      if (best_type == 0) {
        int r = best_idx;
        for (int p = 0; p < k; p++) {
          int cc = (best_start + p) % N;
          grid[r][cc] = s[p];
        }
      } else {
        int c = best_idx;
        for (int p = 0; p < k; p++) {
          int rr = (best_start + p) % N;
          grid[rr][c] = s[p];
        }
      }
    }
  }
  // fill dots
  for (int i = 0; i < N; i++) {
    for (int j = 0; j < N; j++) {
      if (grid[i][j] == '.') grid[i][j] = 'A';
    }
  }
  // output
  for (int i = 0; i < N; i++) {
    for (int j = 0; j < N; j++) {
      cout << grid[i][j];
    }
    cout << endl;
  }
  return 0;
}