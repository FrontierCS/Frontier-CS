#include <bits/stdc++.h>
using namespace std;

int main() {
  int n = 50, m = 50;
  cout << n << " " << m << endl;
  vector<string> g(n, string(m, '.'));
  g[49][0] = 'P';
  g[0][1] = 'B';
  g[0][2] = 'B';
  g[1][1] = 'B';
  g[1][2] = 'B';
  g[0][47] = 'S';
  g[0][48] = 'S';
  g[1][47] = 'S';
  g[1][48] = 'S';
  for(auto &s : g) cout << s << endl;
  return 0;
}