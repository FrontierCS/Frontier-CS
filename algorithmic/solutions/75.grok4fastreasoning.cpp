#include <bits/stdc++.h>
using namespace std;

int main() {
  int b, w, x, y;
  cin >> b >> w >> x >> y;
  long long best_cost = LLONG_MAX / 2;
  int best_r = -1, best_c = -1;
  bool best_stack_black = true;
  int best_num = 0;
  int best_k = 0;
  bool best_wide = false;
  auto compute = [&](bool stack_black) -> tuple<long long, int, int, bool, int, int> {
    int num_main = stack_black ? b : w;
    int num_other = stack_black ? w : b;
    if ((stack_black ? w : b) < (num_main - 1)) return {LLONG_MAX / 2, 0, 0, false, 0, 0};
    int k_extra = num_other - (num_main - 1);
    vector<tuple<long long, int, int, bool>> options;
    if (k_extra == 0) {
      int cc = 1;
      int rr = 2 * num_main - 1;
      long long tt = (long long)rr * cc;
      int num_sep = num_main - 1;
      long long BB = stack_black ? num_main : num_sep;
      long long WW = stack_black ? num_sep : num_main;
      long long ccost = (long long)x * BB + (long long)y * WW;
      options.emplace_back(ccost, rr, cc, false, 0, 0);
    } else {
      int cc_w = 2 * k_extra - 1;
      int rr_w = 2 * num_main;
      long long tt_w = (long long)rr_w * cc_w;
      if (tt_w <= 100000LL) {
        int num_sep = num_main - 1;
        long long other_tiles = (long long)num_sep * cc_w + k_extra;
        long long main_tiles = tt_w - other_tiles;
        long long BB = stack_black ? main_tiles : other_tiles;
        long long WW = stack_black ? other_tiles : main_tiles;
        long long ccost = (long long)x * BB + (long long)y * WW;
        options.emplace_back(ccost, rr_w, cc_w, true, k_extra, 0);
      }
      int cc_t = 2;
      int mm_t = 2 * k_extra - 1;
      int hh_t = (num_main == 1 ? mm_t : mm_t + 1);
      int rr_t = (num_main == 1 ? hh_t : hh_t + 2 * (num_main - 1));
      long long tt_t = (long long)rr_t * cc_t;
      if (tt_t <= 100000LL) {
        int num_sep = num_main - 1;
        long long other_tiles = (long long)num_sep * cc_t + k_extra;
        long long main_tiles = tt_t - other_tiles;
        long long BB = stack_black ? main_tiles : other_tiles;
        long long WW = stack_black ? other_tiles : main_tiles;
        long long ccost = (long long)x * BB + (long long)y * WW;
        options.emplace_back(ccost, rr_t, cc_t, false, k_extra, 0);
      }
    }
    long long min_c = LLONG_MAX / 2;
    int best_rr = 0, best_cc = 0;
    bool best_wd = false;
    int best_ek = 0;
    for (auto& op : options) {
      long long ccst;
      int rrr, ccc;
      bool wd;
      int ek;
      tie(ccst, rrr, ccc, wd, ek, ignore) = op;
      if (ccst < min_c) {
        min_c = ccst;
        best_rr = rrr;
        best_cc = ccc;
        best_wd = wd;
        best_ek = ek;
      }
    }
    return {min_c, best_rr, best_cc, best_wd, best_ek, num_main};
  };
  auto [costA, rA, cA, wideA, kA, numA] = compute(true);
  bool a_possible = (costA < LLONG_MAX / 2);
  auto [costB, rB, cB, wideB, kB, numB] = compute(false);
  bool b_possible = (costB < LLONG_MAX / 2);
  bool use_A = false;
  long long chosen_cost;
  int chosen_r, chosen_c, chosen_k, chosen_num;
  bool chosen_wide;
  if (!a_possible) {
    use_A = false;
    chosen_cost = costB;
    chosen_r = rB;
    chosen_c = cB;
    chosen_wide = wideB;
    chosen_k = kB;
    chosen_num = numB;
  } else if (!b_possible) {
    use_A = true;
    chosen_cost = costA;
    chosen_r = rA;
    chosen_c = cA;
    chosen_wide = wideA;
    chosen_k = kA;
    chosen_num = numA;
  } else {
    if (costA <= costB) {
      use_A = true;
      chosen_cost = costA;
      chosen_r = rA;
      chosen_c = cA;
      chosen_wide = wideA;
      chosen_k = kA;
      chosen_num = numA;
    } else {
      use_A = false;
      chosen_cost = costB;
      chosen_r = rB;
      chosen_c = cB;
      chosen_wide = wideB;
      chosen_k = kB;
      chosen_num = numB;
    }
  }
  vector<string> grid(chosen_r, string(chosen_c, ' '));
  char main_char = use_A ? '@' : '.';
  char other_char = use_A ? '.' : '@';
  char extra_char = use_A ? '.' : '@';
  int cur_row = 0;
  int kk = chosen_k;
  bool is_wide = chosen_wide;
  int cc = chosen_c;
  int num_main_layers = chosen_num;
  int h;
  if (kk == 0) {
    h = 1;
  } else if (is_wide) {
    h = 2;
  } else {
    int m = 2 * kk - 1;
    h = (num_main_layers == 1 ? m : m + 1);
  }
  for (int i = 0; i < h; ++i) {
    fill(grid[cur_row + i].begin(), grid[cur_row + i].end(), main_char);
  }
  if (kk > 0) {
    if (is_wide) {
      int row_place = cur_row + 0;
      for (int j = 0; j < kk; ++j) {
        int col = 2 * j;
        grid[row_place][col] = extra_char;
      }
    } else {
      int buffer = (num_main_layers > 1 ? 1 : 0);
      int m_safe = h - buffer;
      for (int j = 0; j < kk; ++j) {
        int local = 2 * j;
        int global_r = cur_row + local;
        grid[global_r][0] = extra_char;
      }
    }
  }
  cur_row += h;
  for (int lay = 1; lay < num_main_layers; ++lay) {
    fill(grid[cur_row].begin(), grid[cur_row].end(), other_char);
    ++cur_row;
    fill(grid[cur_row].begin(), grid[cur_row].end(), main_char);
    ++cur_row;
  }
  cout << chosen_r << " " << chosen_c << endl;
  for (auto& s : grid) {
    cout << s << endl;
  }
  return 0;
}