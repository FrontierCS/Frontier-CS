#include <bits/stdc++.h>
using namespace std;

int main() {
  int n;
  scanf("%d", &n);
  vector<vector<int>> x(n + 1, vector<int>(n + 1, 0));
  vector<vector<int>> row_xor(n + 1, vector<int>(n + 1, 0));
  vector<int> suffix_xor(n + 2, 0);
  for (int d = 1; d < n; d++) {
    for (int i = 1; i <= n - d; i++) {
      int q = i + d;
      int temp = row_xor[i][q - 1];
      int s_inner = suffix_xor[q];
      printf("0 %d %d\n", i, q);
      fflush(stdout);
      int S;
      scanf("%d", &S);
      int xx = S ^ s_inner ^ temp;
      x[i][q] = xx;
      row_xor[i][q] = row_xor[i][q - 1] ^ xx;
      suffix_xor[q] ^= row_xor[i][q];
    }
  }
  vector<int> perm(n + 1);
  for (int k = 1; k <= n; k++) {
    int left_larger = 0;
    for (int m = 1; m < k; m++) {
      left_larger += x[m][k];
    }
    int left_small = (k - 1) - left_larger;
    int right_small = 0;
    for (int m = k + 1; m <= n; m++) {
      right_small += x[k][m];
    }
    perm[k] = left_small + right_small + 1;
  }
  printf("1");
  for (int i = 1; i <= n; i++) {
    printf(" %d", perm[i]);
  }
  printf("\n");
  fflush(stdout);
  return 0;
}