#include <bits/stdc++.h>

using namespace std;

int N, M, L;
bool marked[10001];
bool usedd[10001];

void query_complement(const vector<int>& U, int& response) {
  int u = U.size();
  memset(marked, 0, sizeof(marked));
  for (int p : U) {
    marked[p] = true;
  }
  printf("? %d", L - u);
  for (int i = 1; i <= L; i++) {
    if (!marked[i]) {
      printf(" %d", i);
    }
  }
  printf("\n");
  fflush(stdout);
  scanf("%d", &response);
}

vector<int> find_stick(const vector<int>& available) {
  vector<int> S;
  vector<int> try_order = available;
  sort(try_order.begin(), try_order.end());
  for (int p : try_order) {
    if (S.size() == N) break;
    vector<int> U = S;
    U.push_back(p);
    int r;
    query_complement(U, r);
    if (r == M - 1) {
      S.push_back(p);
    }
  }
  return S;
}

int main() {
  scanf("%d %d", &N, &M);
  L = N * M;
  memset(usedd, 0, sizeof(usedd));
  vector<int> remaining;
  for (int i = 1; i <= L; i++) {
    remaining.push_back(i);
  }
  for (int s = 0; s < M; s++) {
    vector<int> stick = find_stick(remaining);
    printf("!");
    for (int p : stick) {
      printf(" %d", p);
      usedd[p] = true;
    }
    printf("\n");
    fflush(stdout);
    vector<int> new_remaining;
    for (int p : remaining) {
      if (!usedd[p]) new_remaining.push_back(p);
    }
    remaining = new_remaining;
  }
  return 0;
}