#include <bits/stdc++.h>
using namespace std;

int can_place(double r, int n) {
  if (r <= 0) return 1000000000;
  double scale = r * sqrt(2.0);
  double sh = 0.0;
  int cmin = -200;
  int cmax = 200;
  int count = 0;
  for (int ix = cmin; ix <= cmax; ++ix) {
    double x = scale * ix + sh;
    if (x < r || x > 1 - r) continue;
    for (int jy = cmin; jy <= cmax; ++jy) {
      double y = scale * jy + sh;
      if (y < r || y > 1 - r) continue;
      for (int kz = cmin; kz <= cmax; ++kz) {
        double z = scale * kz + sh;
        if (z < r || z > 1 - r) continue;
        if (((ix & 1) ^ (jy & 1) ^ (kz & 1)) == 0) {
          ++count;
          if (count >= n) return n;
        }
      }
    }
  }
  return count;
}

int main() {
  int n;
  cin >> n;
  double lo = 0, hi = 0.5;
  for (int it = 0; it < 100; it++) {
    double mid = (lo + hi) / 2;
    if (can_place(mid, n) >= n) lo = mid;
    else hi = mid;
  }
  double radius = lo;
  double scale = radius * sqrt(2.0);
  double sh = 0.0;
  int cmin = -200, cmax = 200;
  vector<array<double, 3>> centers;
  bool done = false;
  for (int ix = cmin; ix <= cmax && !done; ix++) {
    double x = scale * ix + sh;
    if (x < radius || x > 1 - radius) continue;
    for (int jy = cmin; jy <= cmax && !done; jy++) {
      double y = scale * jy + sh;
      if (y < radius || y > 1 - radius) continue;
      for (int kz = cmin; kz <= cmax && !done; kz++) {
        double z = scale * kz + sh;
        if (z < radius || z > 1 - radius) continue;
        if (((ix & 1) ^ (jy & 1) ^ (kz & 1)) == 0) {
          centers.push_back({x, y, z});
          if ((int)centers.size() == n) {
            done = true;
          }
        }
      }
    }
  }
  for (auto& p : centers) {
    printf("%.10f %.10f %.10f\n", p[0], p[1], p[2]);
  }
  return 0;
}