#include <bits/stdc++.h>
using namespace std;

int main() {
  int N = 20;
  vector<string> board(N);
  for (int i = 0; i < N; i++) {
    cin >> board[i];
  }
  vector<pair<char, int>> ops;
  while (true) {
    double best_ratio = -1.0;
    int best_ddist = INT_MAX;
    pair<int, int> target = {-1, -1};
    for (int r = 0; r < N; r++) {
      for (int cc = 0; cc < N; cc++) {
        if (board[r][cc] != 'x') continue;
        bool cu = true;
        for (int k = 0; k < r; k++) if (board[k][cc] == 'o') { cu = false; break; }
        bool cd = true;
        for (int k = r + 1; k < N; k++) if (board[k][cc] == 'o') { cd = false; break; }
        bool cl = true;
        for (int k = 0; k < cc; k++) if (board[r][k] == 'o') { cl = false; break; }
        bool cr = true;
        for (int k = cc + 1; k < N; k++) if (board[r][k] == 'o') { cr = false; break; }
        int numu = 0;
        if (cu) for (int k = 0; k <= r; k++) if (board[k][cc] == 'x') numu++;
        int numd = 0;
        if (cd) for (int k = r; k < N; k++) if (board[k][cc] == 'x') numd++;
        int numl = 0;
        if (cl) for (int k = 0; k <= cc; k++) if (board[r][k] == 'x') numl++;
        int numrr = 0;
        if (cr) for (int k = cc; k < N; k++) if (board[r][k] == 'x') numrr++;
        double this_max_rat = -1.0;
        int this_ddist = INT_MAX;
        char temp_dir;
        if (cu) {
          double rat = (double)numu / (r + 1);
          if (rat > this_max_rat || (rat == this_max_rat && (r + 1) < this_ddist)) {
            this_max_rat = rat;
            this_ddist = r + 1;
            temp_dir = 'U';
          }
        }
        if (cd) {
          double rat = (double)numd / (N - r);
          if (rat > this_max_rat || (rat == this_max_rat && (N - r) < this_ddist)) {
            this_max_rat = rat;
            this_ddist = N - r;
            temp_dir = 'D';
          }
        }
        if (cl) {
          double rat = (double)numl / (cc + 1);
          if (rat > this_max_rat || (rat == this_max_rat && (cc + 1) < this_ddist)) {
            this_max_rat = rat;
            this_ddist = cc + 1;
            temp_dir = 'L';
          }
        }
        if (cr) {
          double rat = (double)numrr / (N - cc);
          if (rat > this_max_rat || (rat == this_max_rat && (N - cc) < this_ddist)) {
            this_max_rat = rat;
            this_ddist = N - cc;
            temp_dir = 'R';
          }
        }
        if (this_max_rat > best_ratio || (this_max_rat == best_ratio && this_ddist < best_ddist)) {
          best_ratio = this_max_rat;
          best_ddist = this_ddist;
          target = {r, cc};
        }
      }
    }
    if (target.first == -1) break;
    int r = target.first;
    int c = target.second;
    bool cu = true;
    for (int k = 0; k < r; k++) if (board[k][c] == 'o') { cu = false; break; }
    bool cd = true;
    for (int k = r + 1; k < N; k++) if (board[k][c] == 'o') { cd = false; break; }
    bool cl = true;
    for (int k = 0; k < c; k++) if (board[r][k] == 'o') { cl = false; break; }
    bool cr = true;
    for (int k = c + 1; k < N; k++) if (board[r][k] == 'o') { cr = false; break; }
    int numu = 0;
    if (cu) for (int k = 0; k <= r; k++) if (board[k][c] == 'x') numu++;
    int numd = 0;
    if (cd) for (int k = r; k < N; k++) if (board[k][c] == 'x') numd++;
    int numl = 0;
    if (cl) for (int k = 0; k <= c; k++) if (board[r][k] == 'x') numl++;
    int numrr = 0;
    if (cr) for (int k = c; k < N; k++) if (board[r][k] == 'x') numrr++;
    double max_rat = -1.0;
    int ddist = 0;
    char ddir = ' ';
    if (cu) {
      double rat = (double)numu / (r + 1);
      if (rat > max_rat || (rat == max_rat && (r + 1) < ddist)) {
        max_rat = rat;
        ddist = r + 1;
        ddir = 'U';
      }
    }
    if (cd) {
      double rat = (double)numd / (N - r);
      if (rat > max_rat || (rat == max_rat && (N - r) < ddist)) {
        max_rat = rat;
        ddist = N - r;
        ddir = 'D';
      }
    }
    if (cl) {
      double rat = (double)numl / (c + 1);
      if (rat > max_rat || (rat == max_rat && (c + 1) < ddist)) {
        max_rat = rat;
        ddist = c + 1;
        ddir = 'L';
      }
    }
    if (cr) {
      double rat = (double)numrr / (N - c);
      if (rat > max_rat || (rat == max_rat && (N - c) < ddist)) {
        max_rat = rat;
        ddist = N - c;
        ddir = 'R';
      }
    }
    char restore_dir;
    int pp;
    if (ddir == 'U' || ddir == 'D') {
      pp = c;
      restore_dir = (ddir == 'U' ? 'D' : 'U');
    } else {
      pp = r;
      restore_dir = (ddir == 'L' ? 'R' : 'L');
    }
    vector<pair<char, int>> seq;
    for (int t = 0; t < ddist; t++) {
      seq.emplace_back(ddir, pp);
    }
    for (int t = 0; t < ddist; t++) {
      seq.emplace_back(restore_dir, pp);
    }
    for (auto& pr : seq) {
      ops.push_back(pr);
    }
    for (auto& pr : seq) {
      char dd = pr.first;
      int pidx = pr.second;
      if (dd == 'L') {
        char rem = board[pidx][0];
        for (int jj = 1; jj < N; jj++) {
          board[pidx][jj - 1] = board[pidx][jj];
        }
        board[pidx][N - 1] = '.';
      } else if (dd == 'R') {
        char rem = board[pidx][N - 1];
        for (int jj = N - 2; jj >= 0; jj--) {
          board[pidx][jj + 1] = board[pidx][jj];
        }
        board[pidx][0] = '.';
      } else if (dd == 'U') {
        char rem = board[0][pidx];
        for (int ii = 1; ii < N; ii++) {
          board[ii - 1][pidx] = board[ii][pidx];
        }
        board[N - 1][pidx] = '.';
      } else if (dd == 'D') {
        char rem = board[N - 1][pidx];
        for (int ii = N - 2; ii >= 0; ii--) {
          board[ii + 1][pidx] = board[ii][pidx];
        }
        board[0][pidx] = '.';
      }
    }
  }
  for (auto& pr : ops) {
    cout << pr.first << " " << pr.second << "\n";
  }
  return 0;
}