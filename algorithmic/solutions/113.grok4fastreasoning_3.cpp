#include <bits/stdc++.h>
using namespace std;

void hanoi(int n, int from, int to, int aux) {
  if (n == 0) return;
  hanoi(n - 1, from, aux, to);
  cout << from << " " << to << endl;
  hanoi(n - 1, aux, to, from);
}

int main() {
  int N;
  cin >> N;
  long long M = (1LL << N) - 1;
  cout << M << endl;
  hanoi(N, 1, 3, 2);
  return 0;
}