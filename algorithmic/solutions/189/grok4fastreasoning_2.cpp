#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(nullptr);
  string S1, S2;
  cin >> S1 >> S2;
  int N = S1.size();
  int M = S2.size();
  int best_score = -1;
  int best_o = 0;
  const int RANGE = 200;
  auto compute = [&](int oo) -> pair<int, int> {
    int st = max(0, -oo);
    int en = min(N - 1, M - 1 - oo);
    if (st > en) return {0, 0};
    int ll = en - st + 1;
    int cnt = 0;
    for (int i = st; i <= en; ++i) {
      int jj = i + oo;
      if (S1[i] == S2[jj]) ++cnt;
    }
    return {ll, cnt};
  };
  for (int oo = -RANGE; oo <= RANGE; ++oo) {
    auto [ll, cnt] = compute(oo);
    int sc = ll + cnt;
    if (sc > best_score) {
      best_score = sc;
      best_o = oo;
    }
  }
  // right align
  {
    int oo = M - N;
    auto [ll, cnt] = compute(oo);
    int sc = ll + cnt;
    if (sc > best_score) {
      best_score = sc;
      best_o = oo;
    }
  }
  // left align already included
  int o = best_o;
  int st = max(0, -o);
  int en = min(N - 1, M - 1 - o);
  int L = (st <= en ? en - st + 1 : 0);
  int prefix_del = st;
  int first_j = st + o;
  int prefix_ins = max(0, first_j);
  int last_j = (L > 0 ? en + o : -1);
  int suffix_del = N - (en + 1);
  int suffix_ins = max(0, M - last_j - 1);
  string T;
  T.reserve(N + M);
  T.append(prefix_del, 'D');
  T.append(prefix_ins, 'I');
  T.append(L, 'M');
  T.append(suffix_del, 'D');
  T.append(suffix_ins, 'I');
  cout << T << '\n';
}