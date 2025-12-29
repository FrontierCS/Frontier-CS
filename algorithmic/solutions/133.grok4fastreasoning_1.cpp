#include <bits/stdc++.h>
using namespace std;

const double PI = acos(-1.0);

double intersection_area(double d, double r) {
  if (d + 1e-9 >= 2 * r) return 0.0;
  if (d < 1e-9) return PI * r * r;
  double a = acos(d / (2 * r));
  double term1 = 2 * a * r * r;
  double term2 = (d / 2.0) * sqrt(4 * r * r - d * d);
  return term1 - term2;
}

int main() {
  int n;
  scanf("%d", &n);
  vector<double> px(n), py(n);
  for (int i = 0; i < n; i++) {
    scanf("%lf %lf", &px[i], &py[i]);
  }
  int m;
  scanf("%d", &m);
  vector<bool> used(n, false);
  vector<double> edge_lengths;
  edge_lengths.reserve(m);
  for (int i = 0; i < m; i++) {
    int a, b;
    scanf("%d %d", &a, &b);
    a--; b--;
    used[a] = true;
    used[b] = true;
    double dx = px[a] - px[b];
    double dy = py[a] - py[b];
    double L = hypot(dx, dy);
    edge_lengths.push_back(L);
  }
  double r;
  scanf("%lf", &r);
  double p1, p2, p3, p4;
  scanf("%lf %lf %lf %lf", &p1, &p2, &p3, &p4);
  double sum_L = 0.0;
  double sum_inter_e = 0.0;
  int mm = edge_lengths.size();
  for (double L : edge_lengths) {
    sum_L += L;
    sum_inter_e += intersection_area(L, r);
  }
  double total_additional = 2 * r * sum_L - mm * PI * r * r + sum_inter_e;
  vector<pair<double, double>> centers;
  for (int i = 0; i < n; i++) {
    if (used[i]) {
      centers.emplace_back(px[i], py[i]);
    }
  }
  int k = centers.size();
  double union_d = k * PI * r * r;
  for (int i = 0; i < k; i++) {
    for (int j = i + 1; j < k; j++) {
      double dx = centers[i].first - centers[j].first;
      double dy = centers[i].second - centers[j].second;
      double d = hypot(dx, dy);
      if (d <= 2 * r + 1e-9 && d > 1e-9) {
        double inter = intersection_area(d, r);
        union_d -= inter;
      }
    }
  }
  double ans = union_d + total_additional;
  printf("%.7f\n", ans);
  return 0;
}