#include <bits/stdc++.h>

using namespace std;

void hanoi(int n, int from, int to, int usingg) {
  if (n == 0) return;
  hanoi(n - 1, from, usingg, to);
  cout << from << " " << to << endl;
  hanoi(n - 1, usingg, to, from);
}

int main() {
  int n;
  cin >> n;
  long long m = (1LL << n) - 1;
  cout << m << endl;
  hanoi(n, 1, 3, 2);
  return 0;
}