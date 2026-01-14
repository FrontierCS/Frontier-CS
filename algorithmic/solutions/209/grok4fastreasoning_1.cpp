#include <bits/stdc++.h>
using namespace std;

int main() {
  int h;
  scanf("%d", &h);
  long long n = (1LL << h) - 1;
  int D = 2 * (h - 1);
  long long total = 0;
  for (long long u = 1; u <= n; u++) {
    long long localsum = 0;
    for (int d = 1; d <= D; d++) {
      printf("? %lld %d\n", u, d);
      fflush(stdout);
      long long res;
      scanf("%lld", &res);
      localsum += res;
    }
    total += localsum;
  }
  long long S = total / (n - 1);
  printf("! %lld\n", S);
  fflush(stdout);
  return 0;
}