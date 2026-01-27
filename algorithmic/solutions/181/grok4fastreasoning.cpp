#include <bits/stdc++.h>
using namespace std;

long long compute_delta(int a, int b, const vector<int>& p, const vector<vector<int>>& D, const vector<vector<int>>& F, int n) {
  int la = p[a], lb = p[b];
  long long delta = 0;
  // self terms
  delta += 1LL * F[a][a] * (D[lb][lb] - D[la][la]);
  delta += 1LL * F[b][b] * (D[la][la] - D[lb][lb]);
  // cross terms
  delta += 1LL * (F[a][b] - F[b][a]) * (D[lb][la] - D[la][lb]);
  // other j
  for (int j = 0; j < n; j++) {
    if (j == a || j == b) continue;
    int lj = p[j];
    delta += 1LL * F[a][j] * (D[lb][lj] - D[la][lj]);
    delta += 1LL * F[j][a] * (D[lj][lb] - D[lj][la]);
    delta += 1LL * F[b][j] * (D[la][lj] - D[lb][lj]);
    delta += 1LL * F[j][b] * (D[lj][la] - D[lj][lb]);
  }
  return delta;
}

int main() {
  int n;
  scanf("%d", &n);
  vector<vector<int>> D(n, vector<int>(n, 0));
  for (int i = 0; i < n; i++) {
    for (int j = 0; j < n; j++) {
      scanf("%d", &D[i][j]);
    }
  }
  vector<vector<int>> F(n, vector<int>(n, 0));
  for (int i = 0; i < n; i++) {
    for (int j = 0; j < n; j++) {
      scanf("%d", &F[i][j]);
    }
  }
  vector<int> p(n);
  for (int i = 0; i < n; i++) p[i] = i;
  srand(time(NULL));
  const int NUM_TRIALS = 50000;
  for (int trial = 0; trial < NUM_TRIALS; trial++) {
    int a = rand() % n;
    int b = rand() % n;
    if (a == b) continue;
    long long del = compute_delta(a, b, p, D, F, n);
    if (del < 0) {
      swap(p[a], p[b]);
    }
  }
  for (int i = 0; i < n; i++) {
    if (i > 0) printf(" ");
    printf("%d", p[i] + 1);
  }
  printf("\n");
  return 0;
}