#include <bits/stdc++.h>

using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int n;
  cin >> n;
  vector<long long> a(n + 1);
  for (int i = 1; i <= n; i++) {
    cout << "? " << i << " " << i << "\n";
    cout.flush();
    long long x;
    int f;
    cin >> x >> f;
    a[i] = x;
  }
  cout << "!";
  for (int i = 1; i <= n; i++) {
    cout << " " << a[i];
  }
  cout << "\n";
  cout.flush();
  return 0;
}