#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int N;
  cin >> N;
  vector<int> S(N);
  for (int i = 0; i < N; i++) cin >> S[i];
  int M;
  cin >> M;
  vector<int> XX(M), YY(M);
  for (int k = 0; k < M; k++) {
    cin >> XX[k] >> YY[k];
  }
  vector<int> pos(N);
  for (int i = 0; i < N; i++) pos[S[i]] = i;
  set<int> incorrect;
  for (int i = 0; i < N; i++) {
    if (S[i] != i) incorrect.insert(i);
  }
  vector<pair<int, int>> my_swaps;
  long long sum_cost = 0;
  int R = 0;
  bool issorted = incorrect.empty();
  while (!issorted && R < M) {
    // Jerry's move
    int x = XX[R], y = YY[R];
    if (x != y) {
      int a = S[x], b = S[y];
      S[x] = b;
      S[y] = a;
      pos[a] = y;
      pos[b] = x;
      incorrect.erase(x);
      incorrect.erase(y);
      if (S[x] != x) incorrect.insert(x);
      if (S[y] != y) incorrect.insert(y);
    }
    R++;
    // my move
    pair<int, int> this_swap;
    if (incorrect.empty()) {
      this_swap = {0, 0};
    } else {
      int i = *incorrect.begin();
      int val = i;
      int j = pos[val];
      this_swap = {i, j};
      // apply swap
      int a = S[i], b = S[j];
      S[i] = b;
      S[j] = a;
      pos[a] = j;
      pos[b] = i;
      incorrect.erase(i);
      incorrect.erase(j);
      if (S[i] != i) incorrect.insert(i);
      if (S[j] != j) incorrect.insert(j);
    }
    my_swaps.push_back(this_swap);
    int u = this_swap.first, v = this_swap.second;
    sum_cost += abs(u - v);
    issorted = incorrect.empty();
  }
  cout << R << '\n';
  for (auto pr : my_swaps) {
    cout << pr.first << " " << pr.second << '\n';
  }
  long long V = (long long)R * sum_cost;
  cout << V << '\n';
  return 0;
}