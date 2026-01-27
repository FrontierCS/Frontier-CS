#include <bits/stdc++.h>

using namespace std;

int main() {
  int n;
  cin >> n;
  if (n <= 4) {
    cout << 0 << endl;
    return 0;
  }
  int t = n - 3;
  vector<tuple<int, int, int>> adds;
  int start = max(0, n - 5);
  for (int i = start; i >= 0; i--) {
    int c = i + 1;
    adds.emplace_back(i, c, t);
  }
  cout << adds.size() << endl;
  for (auto [u, c, v] : adds) {
    cout << u << " " << c << " " << v << endl;
  }
  return 0;
}