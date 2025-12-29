#include <bits/stdc++.h>
using namespace std;

int main() {
  int n;
  cin >> n;
  vector<double> X(n), Y(n), Z(n);
  double pi = acos(-1.0);
  if (n == 2) {
    X[0] = 0; Y[0] = 0; Z[0] = 1;
    X[1] = 0; Y[1] = 0; Z[1] = -1;
  } else if (n == 3) {
    double s3 = sqrt(3.0);
    X[0] = 1.0; Y[0] = 0; Z[0] = 0;
    X[1] = -0.5; Y[1] = s3 / 2; Z[1] = 0;
    X[2] = -0.5; Y[2] = -s3 / 2; Z[2] = 0;
  } else if (n == 4) {
    double s3 = sqrt(3.0);
    double a = 1.0 / s3;
    X[0] = a; Y[0] = a; Z[0] = a;
    X[1] = a; Y[1] = -a; Z[1] = -a;
    X[2] = -a; Y[2] = a; Z[2] = -a;
    X[3] = -a; Y[3] = -a; Z[3] = a;
  } else if (n == 5) {
    X[0] = 0; Y[0] = 0; Z[0] = 1;
    X[1] = 0; Y[1] = 0; Z[1] = -1;
    double s3 = sqrt(3.0);
    X[2] = 1.0; Y[2] = 0; Z[2] = 0;
    X[3] = -0.5; Y[3] = s3 / 2; Z[3] = 0;
    X[4] = -0.5; Y[4] = -s3 / 2; Z[4] = 0;
  } else if (n == 6) {
    X[0] = 0; Y[0] = 0; Z[0] = 1;
    X[1] = 0; Y[1] = 0; Z[1] = -1;
    X[2] = 1; Y[2] = 0; Z[2] = 0;
    X[3] = -1; Y[3] = 0; Z[3] = 0;
    X[4] = 0; Y[4] = 1; Z[4] = 0;
    X[5] = 0; Y[5] = -1; Z[5] = 0;
  } else {
    const double golden = (1.0 + sqrt(5.0)) / 2.0;
    for (int i = 0; i < n; i++) {
      double zi = 1.0 - 2.0 * (double)i / (n - 1.0);
      double theta = 2.0 * pi * (double)i / golden;
      double r = sqrt(1.0 - zi * zi);
      X[i] = r * cos(theta);
      Y[i] = r * sin(theta);
      Z[i] = zi;
    }
  }
  double min_dist = 1e100;
  for (int i = 0; i < n; i++) {
    for (int j = i + 1; j < n; j++) {
      double dx = X[i] - X[j];
      double dy = Y[i] - Y[j];
      double dz = Z[i] - Z[j];
      double d = sqrt(dx * dx + dy * dy + dz * dz);
      if (d < min_dist) min_dist = d;
    }
  }
  printf("%.10f\n", min_dist);
  for (int i = 0; i < n; i++) {
    printf("%.10f %.10f %.10f\n", X[i], Y[i], Z[i]);
  }
  return 0;
}