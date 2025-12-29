#include <bits/stdc++.h>
using namespace std;

int main() {
  int n, ty;
  scanf("%d %d", &n, &ty);
  vector<int> ps(n + 1);
  int root = -1;
  for (int cand = 1; cand <= n; ++cand) {
    vector<int> seq;
    seq.push_back(cand);
    for (int i = 1; i <= n; ++i) {
      if (i != cand) seq.push_back(i);
    }
    printf("? %d", (int)seq.size());
    for (int v : seq) printf(" %d", v);
    printf("\n");
    fflush(stdout);
    int rr;
    scanf("%d", &rr);
    ps[cand] = n - rr;
    if (rr == 1) root = cand;
  }
  vector<int> par(n + 1, 0);
  par[root] = 0;
  vector<pair<int, int>> order;
  for (int i = 1; i <= n; ++i) {
    order.emplace_back(ps[i], i);
  }
  sort(order.rbegin(), order.rend());
  vector<int> z(n + 1);
  for (int i = 1; i <= n; ++i) {
    z[i] = order[i - 1].second;
  }
  for (int x = 1; x <= n; ++x) {
    if (x == root) continue;
    int posx = 1;
    while (posx <= n && ps[z[posx]] > ps[x]) ++posx;
    int mm = posx - 1;
    if (mm < 1) continue;  // error case, skip
    int lo = 1, hi = mm;
    while (lo <= hi) {
      int md = lo + (hi - lo) / 2;
      int llen = mm - md + 1;
      bool has = false;
      if (llen > 0) {
        // V alone
        printf("? %d", llen);
        for (int jj = md; jj <= mm; ++jj) {
          printf(" %d", z[jj]);
        }
        printf("\n");
        fflush(stdout);
        int rr2;
        scanf("%d", &rr2);
        // V + x
        printf("? %d", llen + 1);
        for (int jj = md; jj <= mm; ++jj) {
          printf(" %d", z[jj]);
        }
        printf(" %d\n", x);
        fflush(stdout);
        int rr1;
        scanf("%d", &rr1);
        has = (rr1 == rr2);
      } else {
        has = false;
      }
      if (has) {
        lo = md + 1;
      } else {
        hi = md - 1;
      }
    }
    int ip = hi;
    int pp = z[ip];
    par[x] = pp;
  }
  printf("!");
  for (int i = 1; i <= n; ++i) {
    printf(" %d", par[i]);
  }
  printf("\n");
  fflush(stdout);
  return 0;
}