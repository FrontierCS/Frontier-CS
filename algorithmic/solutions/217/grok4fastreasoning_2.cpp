#include <bits/stdc++.h>
using namespace std;

int main() {
  int N, M;
  scanf("%d %d", &N, &M);
  int L = N * M;
  vector<vector<int>> sticks(M);
  bool excluded[10001];
  for (int u = 1; u <= L; u++) {
    vector<pair<int, int>> cand;
    for (int k = 0; k < M; k++) {
      cand.emplace_back(sticks[k].size(), k);
    }
    sort(cand.begin(), cand.end());
    bool assigned = false;
    for (auto &p : cand) {
      int k = p.second;
      vector<int> Q = sticks[k];
      Q.push_back(u);
      memset(excluded, 0, L + 1);
      for (int j : Q) {
        excluded[j] = true;
      }
      int qsize = Q.size();
      int comp = L - qsize;
      printf("? %d", comp);
      for (int i = 1; i <= L; i++) {
        if (!excluded[i]) {
          printf(" %d", i);
        }
      }
      printf("\n");
      fflush(stdout);
      int resp;
      scanf("%d", &resp);
      if (resp == M - 1) {
        sticks[k].push_back(u);
        assigned = true;
        break;
      }
    }
    assert(assigned);
  }
  for (int k = 0; k < M; k++) {
    printf("!");
    for (int j : sticks[k]) {
      printf(" %d", j);
    }
    printf("\n");
    fflush(stdout);
  }
  return 0;
}