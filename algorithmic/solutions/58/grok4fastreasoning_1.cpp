#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

int main() {
  ll x;
  cin >> x;
  const int M = 5;
  const int TS = M * M;
  int configg[71];
  memset(configg, -1, sizeof configg);
  for (int mask = 0; mask < (1 << TS); mask++) {
    int g[6][6] = {0};
    int id = 0;
    for (int i = 1; i <= M; i++) {
      for (int j = 1; j <= M; j++) {
        g[i][j] = (mask & (1 << id)) ? 1 : 0;
        id++;
      }
    }
    ll dpp[6][6] = {0};
    if (g[1][1]) dpp[1][1] = 1;
    for (int i = 1; i <= M; i++) {
      for (int j = 1; j <= M; j++) {
        if (i == 1 && j == 1) continue;
        if (g[i][j] == 0) continue;
        ll ways = 0;
        if (i > 1) ways += dpp[i - 1][j];
        if (j > 1) ways += dpp[i][j - 1];
        dpp[i][j] = ways;
      }
    }
    int p = dpp[M][M];
    if (p >= 0 && p <= 70 && configg[p] == -1) {
      configg[p] = mask;
    }
  }
  vector<int> digits;
  ll temp = x;
  while (temp > 0) {
    digits.push_back(temp % 70);
    temp /= 70;
  }
  int nd = digits.size();
  vector<pair<int, int>> terms;
  for (int j = 0; j < nd; j++) {
    if (digits[j] > 0) {
      terms.emplace_back(j, digits[j]);
    }
  }
  int num_terms = terms.size();
  int current_col = 1;
  vector<int> start_cols(num_terms), sizes(num_terms), input_masks(num_terms);
  int max_used_c = 0;
  int max_used_r = 0;
  for (int ti = 0; ti < num_terms; ti++) {
    int j = terms[ti].first;
    int dd = terms[ti].second;
    int num_bl = j + 1;
    int szz = 5 * num_bl;
    start_cols[ti] = current_col;
    sizes[ti] = szz;
    input_masks[ti] = configg[dd];
    current_col += szz;
    max_used_c = max(max_used_c, current_col - 1);
    max_used_r = max(max_used_r, 5 * num_bl);
  }
  int exit_col = max_used_c + 1;
  int n_row = max_used_r;
  int n_col = exit_col;
  int nn = max(n_row, n_col);
  bool bigg[301][301];
  memset(bigg, 0, sizeof bigg);
  for (int j = 1; j <= max_used_c; j++) {
    bigg[1][j] = true;
  }
  vector<int> end_rs(num_terms), end_cs(num_terms);
  for (int ti = 0; ti < num_terms; ti++) {
    int sr = 1;
    int sc = start_cols[ti];
    int sz = sizes[ti];
    int in_m = input_masks[ti];
    int jj = terms[ti].first;
    int flat = 0;
    for (int di = 0; di < 5; di++) {
      for (int dj = 0; dj < 5; dj++) {
        bool op = (in_m & (1 << flat)) != 0;
        bigg[sr + di][sc + dj] = op;
        flat++;
      }
    }
    int curr_er = sr + 4;
    int curr_ec = sc + 4;
    for (int pb = 0; pb < jj; pb++) {
      bigg[curr_er + 1][curr_ec] = true;
      bigg[curr_er + 1][curr_ec + 1] = true;
      int bsr = curr_er + 1;
      int bsc = curr_ec + 1;
      for (int di = 0; di < 5; di++) {
        for (int dj = 0; dj < 5; dj++) {
          bigg[bsr + di][bsc + dj] = true;
        }
      }
      curr_er = bsr + 4;
      curr_ec = bsc + 4;
    }
    end_rs[ti] = curr_er;
    end_cs[ti] = curr_ec;
  }
  int min_er = 301;
  for (int ti = 0; ti < num_terms; ti++) {
    min_er = min(min_er, end_rs[ti]);
  }
  for (int ii = min_er; ii <= nn; ii++) {
    bigg[ii][exit_col] = true;
  }
  for (int ti = 0; ti < num_terms; ti++) {
    int er = end_rs[ti];
    int ec = end_cs[ti];
    for (int jj = ec + 1; jj <= exit_col; jj++) {
      bigg[er][jj] = true;
    }
  }
  if (n_row > exit_col) {
    for (int jj = exit_col + 1; jj <= nn; jj++) {
      bigg[n_row][jj] = true;
    }
  }
  cout << nn << endl;
  for (int i = 1; i <= nn; i++) {
    for (int j = 1; j <= nn; j++) {
      cout << (bigg[i][j] ? 1 : 0);
      if (j < nn) cout << " ";
      else cout << endl;
    }
  }
  return 0;
}