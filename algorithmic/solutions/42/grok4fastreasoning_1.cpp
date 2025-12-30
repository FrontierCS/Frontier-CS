#include <bits/stdc++.h>

using namespace std;

int main() {
  int n;
  cin >> n;
  int k = 0;
  while (k * 1LL * k < n) k++;
  double L = k;
  cout << fixed << setprecision(6) << L << endl;
  int placed = 0;
  for (int y = 0; y < k && placed < n; y++) {
    for (int x = 0; x < k && placed < n; x++) {
      double cx = 0.5 + x;
      double cy = 0.5 + y;
      double a = 0.0;
      cout << fixed << setprecision(6) << cx << " " << cy << " " << a << endl;
      placed++;
    }
  }
  return 0;
}