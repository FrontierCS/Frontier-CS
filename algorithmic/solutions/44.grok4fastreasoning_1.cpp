#include <bits/stdc++.h>

using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int N;
  cin >> N;
  vector<long long> X(N), Y(N);
  for(int i = 0; i < N; i++) {
    cin >> X[i] >> Y[i];
  }
  auto cmp = [&](int a, int b) -> bool {
    double ya = Y[a] - Y[0];
    double xa = X[a] - X[0];
    double yb = Y[b] - Y[0];
    double xb = X[b] - X[0];
    double anga = atan2(ya, xa);
    double angb = atan2(yb, xb);
    if (anga != angb) return anga < angb;
    long long dxa = X[a] - X[0], dya = Y[a] - Y[0];
    long long dista = dxa * dxa + dya * dya;
    long long dxb = X[b] - X[0], dyb = Y[b] - Y[0];
    long long distb = dxb * dxb + dyb * dyb;
    return dista < distb;
  };
  vector<int> order;
  for(int i = 1; i < N; i++) order.push_back(i);
  sort(order.begin(), order.end(), cmp);
  cout << N + 1 << "\n";
  cout << 0 << "\n";
  for(int i : order) {
    cout << i << "\n";
  }
  cout << 0 << "\n";
  return 0;
}