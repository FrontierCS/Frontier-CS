#include <bits/stdc++.h>
using namespace std;

int main() {
  int R, H;
  cin >> R >> H;
  const int N = 1000;
  const int RR = 45;
  vector<uint64_t> msk(N + 1, 0);
  for (int i = 1; i <= N; i++) {
    uint64_t h = i;
    h ^= h >> 33;
    h *= 0xff51afd7ed558ccdULL;
    h ^= h >> 33;
    h *= 0xc4ceb9fe1a85ec53ULL;
    h ^= h >> 33;
    msk[i] = h;
  }
  vector<vector<int>> queries(RR);
  for (int i = 1; i <= N; i++) {
    for (int j = 0; j < RR; j++) {
      if (msk[i] & (1ULL << j)) {
        queries[j].push_back(i);
      }
    }
  }
  for (int j = 0; j < RR; j++) {
    cout << "? " << queries[j].size();
    for (int p : queries[j]) {
      cout << " " << p;
    }
    cout << endl;
    cout.flush();
  }
  cout << "@" << endl;
  cout.flush();
  int L;
  cin >> L;
  vector<int> ans(RR);
  for (int &x : ans) cin >> x;
  uint64_t obs = 0;
  for (int j = 0; j < RR; j++) {
    if (ans[j]) obs |= (1ULL << j);
  }
  pair<int, int> res = {-1, -1};
  for (int a = 1; a <= N; a++) {
    for (int b = a; b <= N; b++) {
      uint64_t orr = msk[a] | msk[b];
      if (orr == obs) {
        res = {a, b};
        goto found;
      }
    }
  }
found:
  cout << "! " << res.first << " " << res.second << endl;
  cout.flush();
  return 0;
}