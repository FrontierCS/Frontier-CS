#include <bits/stdc++.h>

using namespace std;

int main() {
  long long n;
  cin >> n;
  vector<long long> s;
  long long x = 1;
  while (x <= n) {
    s.push_back(x);
    if (x > (n >> 1)) break;
    x <<= 1;
  }
  cout << s.size() << endl;
  for (auto y : s) cout << y << " ";
  cout << endl;
  return 0;
}