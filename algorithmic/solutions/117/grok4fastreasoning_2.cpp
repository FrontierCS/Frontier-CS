#include <bits/stdc++.h>
using namespace std;

int main() {
  int n;
  cin >> n;
  double m = 0.5;
  double LOW = -30000.0;
  double HIGH = 30000.0;
  double EPS = 1e-10;
  double TOL = 1e-6;
  auto query = [&](double t) -> double {
    double x = t;
    double y = m * t;
    cout << fixed << setprecision(15) << "? " << x << " " << y << endl;
    cout.flush();
    double res;
    cin >> res;
    return res;
  };
  auto compute_slope = [&](double t0) -> double {
    double s1 = query(t0);
    double s2 = query(t0 + EPS);
    return (s2 - s1) / EPS;
  };
  vector<pair<double, double>> kinks;
  double current = LOW;
  double current_slope = compute_slope(current);
  int found = 0;
  while (found < n) {
    double lo = current;
    double hi = HIGH;
    double left_slope = current_slope;
    double cand_t = -1e100;
    for (int iter = 0; iter < 60; iter++) {
      double mid = (lo + hi) / 2.0;
      double sl = compute_slope(mid);
      if (sl > left_slope + 1e-12) {
        cand_t = mid;
        hi = mid;
      } else {
        lo = mid;
      }
    }
    if (cand_t < current) break;
    double tk = cand_t;
    double sl_left = compute_slope(tk - 1e-6);
    double sl_right = compute_slope(tk + 1e-6);
    double del = sl_right - sl_left;
    if (del > 1e-9) {
      kinks.emplace_back(tk, del);
      current = tk + 1e-6;
      current_slope = sl_right;
      found++;
    } else {
      break;
    }
  }
  vector<int> As, Bs;
  for (auto& p : kinks) {
    double tk = p.first;
    double del = p.second;
    double kk = del * del;
    double qa = 4.0 - kk;
    double qb = -2.0 * kk * m;
    double qc = -kk * (m * m + 1.0);
    double disc = qb * qb - 4 * qa * qc;
    if (disc < 0) continue;
    double sd = sqrt(disc);
    vector<double> us = {(-qb + sd) / (2 * qa), (-qb - sd) / (2 * qa)};
    bool got = false;
    for (double u : us) {
      double ac = round(u + m);
      if (abs(ac) > 10000) continue;
      double dexp = 2.0 * abs(ac - m) / sqrt(ac * ac + 1.0);
      if (abs(dexp - del) > TOL) continue;
      double ue = ac - m;
      double bc = -tk * ue;
      double br = round(bc);
      if (abs(bc - br) < TOL && abs(br) <= 10000) {
        As.push_back((int)ac);
        Bs.push_back((int)br);
        got = true;
        break;
      }
    }
    if (!got) {
      // failed, skip
    }
  }
  cout << "!";
  for (int aa : As) cout << " " << aa;
  for (int bb : Bs) cout << " " << bb;
  cout << endl;
  cout.flush();
  return 0;
}