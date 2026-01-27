#include <bits/stdc++.h>
using namespace std;

int main() {
  double base;
  cin >> base;
  int M;
  cin >> M;
  vector<int> Xs(M);
  vector<vector<int>> points(M);
  for (int i = 0; i < M; i++) {
    int n, x;
    cin >> n >> x;
    Xs[i] = x;
    points[i].resize(n);
    for (int j = 0; j < n; j++) {
      cin >> points[i][j];
    }
  }
  double D_orig, S_orig;
  cin >> D_orig >> S_orig;
  double k = 0.6;
  double wd = (1 - k) / D_orig;
  double ws = k / S_orig;

  // Precompute min cost between cities
  vector<vector<double>> pair_min_cost(M, vector<double>(M, 1e100));
  for (int i = 0; i < M; i++) {
    for (int j = 0; j < M; j++) {
      if (i == j) continue;
      double dx = Xs[j] - Xs[i];
      double hdx = abs(dx);
      double minc = 1e100;
      for (int p = 0; p < (int)points[i].size(); p++) {
        double ya = points[i][p];
        for (int q = 0; q < (int)points[j].size(); q++) {
          double yb = points[j][q];
          double dy = yb - ya;
          double dist = sqrt(dx * dx + dy * dy);
          double slope = (dy > 0 && hdx > 0 ? dy / hdx : (dy > 0 ? 1e18 : 0.0));
          double cc = wd * dist + ws * slope;
          minc = min(minc, cc);
        }
      }
      pair_min_cost[i][j] = minc;
    }
  }

  // Find starting city: smallest x
  int start = 0;
  for (int i = 1; i < M; i++) {
    if (Xs[i] < Xs[start]) start = i;
  }

  // Nearest neighbor
  vector<bool> visited(M, false);
  vector<int> tour;
  tour.push_back(start);
  visited[start] = true;
  int current = start;
  for (int step = 1; step < M; step++) {
    double min_c = 1e100;
    int next = -1;
    for (int cand = 0; cand < M; cand++) {
      if (!visited[cand] && pair_min_cost[current][cand] < min_c) {
        min_c = pair_min_cost[current][cand];
        next = cand;
      }
    }
    assert(next != -1);
    tour.push_back(next);
    visited[next] = true;
    current = next;
  }

  // Now tour is the order
  vector<int> seq = tour;

  // Now compute best for this order
  double min_cost = 1e100;
  int best_fp = -1;
  for (int fp = 0; fp < (int)points[seq[0]].size(); fp++) {
    int first_city = seq[0];
    double ya = points[first_city][fp];

    // init for pos 1
    vector<double> prevv(1e100);
    if (M == 1) continue; // impossible
    int pos1_city = seq[1];
    double dx1 = Xs[pos1_city] - Xs[first_city];
    double hdx1 = abs(dx1);
    int n1 = points[pos1_city].size();
    prevv.assign(n1, 1e100);
    for (int cp = 0; cp < n1; cp++) {
      double yb = points[pos1_city][cp];
      double dy = yb - ya;
      double dist = sqrt(dx1 * dx1 + dy * dy);
      double slope = (dy > 0 && hdx1 > 0 ? dy / hdx1 : (dy > 0 ? 1e18 : 0.0));
      double ec = wd * dist + ws * slope;
      prevv[cp] = ec;
    }

    // DP for ip=2 to M-1
    for (int ip = 2; ip < M; ip++) {
      int this_city = seq[ip];
      int n_this = points[this_city].size();
      vector<double> new_dp(n_this, 1e100);
      int prev_cityy = seq[ip - 1];
      int n_prev = points[prev_cityy].size();
      double dx = Xs[this_city] - Xs[prev_cityy];
      double hdx = abs(dx);
      for (int jp = 0; jp < n_this; jp++) {
        double ythis = points[this_city][jp];
        double minn = 1e100;
        for (int pp = 0; pp < n_prev; pp++) {
          if (prevv[pp] > 1e99) continue;
          double yprev = points[prev_cityy][pp];
          double dy = ythis - yprev;
          double distt = sqrt(dx * dx + dy * dy);
          double slopee = (dy > 0 && hdx > 0 ? dy / hdx : (dy > 0 ? 1e18 : 0.0));
          double ec = wd * distt + ws * slopee;
          minn = min(minn, prevv[pp] + ec);
        }
        new_dp[jp] = minn;
      }
      prevv = new_dp;
    }

    // now closing
    int last_city = seq[M - 1];
    int n_last = points[last_city].size();
    double dx_close = Xs[seq[0]] - Xs[last_city];
    double hdx_close = abs(dx_close);
    double min_this = 1e100;
    vector<double> this_last_dp = prevv;
    for (int lp = 0; lp < n_last; lp++) {
      if (prevv[lp] > 1e99) continue;
      double yl = points[last_city][lp];
      double dy_close = ya - yl;
      double dist_close = sqrt(dx_close * dx_close + dy_close * dy_close);
      double slope_close = (dy_close > 0 && hdx_close > 0 ? dy_close / hdx_close : (dy_close > 0 ? 1e18 : 0.0));
      double ec_close = wd * dist_close + ws * slope_close;
      double total = prevv[lp] + ec_close;
      min_this = min(min_this, total);
    }
    if (min_this < min_cost) {
      min_cost = min_this;
      best_fp = fp;
    }
  }

  // Now reconstruct for best_fp
  int fp = best_fp;
  int first_city = seq[0];
  double ya = points[first_city][fp];

  // init pos1
  vector<double> prevv(1e100);
  int pos1_city = seq[1];
  double dx1 = Xs[pos1_city] - Xs[first_city];
  double hdx1 = abs(dx1);
  int n1 = points[pos1_city].size();
  prevv.assign(n1, 1e100);
  for (int cp = 0; cp < n1; cp++) {
    double yb = points[pos1_city][cp];
    double dy = yb - ya;
    double dist = sqrt(dx1 * dx1 + dy * dy);
    double slope = (dy > 0 && hdx1 > 0 ? dy / hdx1 : (dy > 0 ? 1e18 : 0.0));
    double ec = wd * dist + ws * slope;
    prevv[cp] = ec;
  }

  // prev_point
  vector<vector<int>> prev_point(M);
  prev_point[1] = vector<int>(n1, -1); // dummy

  // DP with tracking
  for (int ip = 2; ip < M; ip++) {
    int this_city = seq[ip];
    int n_this = points[this_city].size();
    vector<double> new_dp(n_this, 1e100);
    vector<int> this_prev(n_this, -1);
    int prev_cityy = seq[ip - 1];
    int n_prev = points[prev_cityy].size();
    double dx = Xs[this_city] - Xs[prev_cityy];
    double hdx = abs(dx);
    for (int jp = 0; jp < n_this; jp++) {
      double ythis = points[this_city][jp];
      double minn = 1e100;
      int bestp = -1;
      for (int pp = 0; pp < n_prev; pp++) {
        if (prevv[pp] > 1e99) continue;
        double yprev = points[prev_cityy][pp];
        double dy = ythis - yprev;
        double distt = sqrt(dx * dx + dy * dy);
        double slopee = (dy > 0 && hdx > 0 ? dy / hdx : (dy > 0 ? 1e18 : 0.0));
        double ec = wd * distt + ws * slopee;
        double total = prevv[pp] + ec;
        if (total < minn) {
          minn = total;
          bestp = pp;
        }
      }
      new_dp[jp] = minn;
      this_prev[jp] = bestp;
    }
    prev_point[ip] = this_prev;
    prevv = new_dp;
  }

  // find best_lp
  int last_city = seq[M - 1];
  int n_last = points[last_city].size();
  double dx_close = Xs[seq[0]] - Xs[last_city];
  double hdx_close = abs(dx_close);
  double best_close_cost = 1e100;
  int best_lp = -1;
  for (int lp = 0; lp < n_last; lp++) {
    if (prevv[lp] > 1e99) continue;
    double yl = points[last_city][lp];
    double dy_close = ya - yl;
    double dist_close = sqrt(dx_close * dx_close + dy_close * dy_close);
    double slope_close = (dy_close > 0 && hdx_close > 0 ? dy_close / hdx_close : (dy_close > 0 ? 1e18 : 0.0));
    double ec_close = wd * dist_close + ws * slope_close;
    double total = prevv[lp] + ec_close;
    if (total < best_close_cost) {
      best_close_cost = total;
      best_lp = lp;
    }
  }

  // reconstruct
  vector<int> chosen_point(M);
  chosen_point[0] = fp;
  chosen_point[M - 1] = best_lp;
  int current_pos = M - 1;
  int current_j = best_lp;
  while (current_pos > 1) {
    int prev_p = prev_point[current_pos][current_j];
    chosen_point[current_pos - 1] = prev_p;
    current_j = prev_p;
    current_pos--;
  }
  // now for M==2, chosen[1] = best_lp already set

  // output
  for (int p = 0; p < M; p++) {
    int c = seq[p];
    int pt = chosen_point[p];
    cout << "(" << (c + 1) << "," << (pt + 1) << ")";
    if (p < M - 1) cout << "@";
  }
  cout << endl;

  return 0;
}