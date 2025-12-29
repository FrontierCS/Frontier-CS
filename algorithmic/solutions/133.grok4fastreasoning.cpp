#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(NULL);
  int n;
  cin >> n;
  vector<double> X(n), Y(n);
  for(int i = 0; i < n; i++) {
    cin >> X[i] >> Y[i];
  }
  int m;
  cin >> m;
  double sum_len = 0.0;
  for(int i = 0; i < m; i++) {
    int a, b;
    cin >> a >> b;
    a--; b--;
    double dx = X[a] - X[b];
    double dy = Y[a] - Y[b];
    sum_len += sqrt(dx * dx + dy * dy);
  }
  double r;
  cin >> r;
  double pi = acos(-1.0);
  double total = pi * r * r * m + 2.0 * r * sum_len;
  double p1, p2, p3, p4;
  cin >> p1 >> p2 >> p3 >> p4;
  cout << fixed << setprecision(7) << total << '\n';
  return 0;
}