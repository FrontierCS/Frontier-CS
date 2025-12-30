#include <bits/stdc++.h>

using namespace std;

int main() {
  int n;
  cin >> n;
  vector<int> p(n);
  for(int i = 0; i < n; i++) p[i] = i + 1;
  cout << "!";
  for(int x : p) cout << " " << x;
  cout << endl;
  cout.flush();
  return 0;
}