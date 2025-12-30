#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int N, LL;
  cin >> N >> LL;
  long long L = LL;
  vector<long long> T(N);
  for(auto &x : T) cin >> x;
  vector<long long> required(N);
  for(int y = 0; y < N; y++) {
    required[y] = (y == 0 ? max(0LL, T[y] - 1) : T[y]);
  }
  int e = 0;
  for(int i = 1; i < N; i++) if(T[i] > T[e]) e = i;
  vector<long long> na(N), nb(N);
  for(int x = 0; x < N; x++) {
    long long s = T[x];
    na[x] = (s + 1LL) / 2;
    nb[x] = s / 2;
  }
  if(nb[e] > 0) {
    nb[e]--;
  } else if(na[e] > 0) {
    na[e]--;
  }
  vector<tuple<long long, int, int>> bundles;
  for(int x = 0; x < N; x++) {
    if(na[x] > 0) bundles.emplace_back(na[x], 1, x);
    if(nb[x] > 0) bundles.emplace_back(nb[x], 0, x);
  }
  long long best_E = LLONG_MAX / 2;
  vector<int> best_A(N), best_B(N);
  mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
  int trials = 32;
  for(int trial = 0; trial < trials; trial++) {
    auto current_bundles = bundles;
    shuffle(current_bundles.begin(), current_bundles.end(), rng);
    vector<long long> ass(N, 0);
    vector<int> AA(N, 0), BB(N, 0);
    for(auto& bund : current_bundles) {
      auto [sz, isa, xx] = bund;
      long long maxd = LLONG_MIN;
      int by = 0;
      for(int y = 0; y < N; y++) {
        long long defi = required[y] - ass[y];
        if(defi > maxd) {
          maxd = defi;
          by = y;
        }
      }
      ass[by] += sz;
      if(isa) AA[xx] = by;
      else BB[xx] = by;
    }
    vector<long long> act(N, 0);
    int cur = 0;
    act[0]++;
    for(long long w = 1; w < L; w++) {
      long long tt = act[cur];
      int nxt = ((tt & 1) ? AA[cur] : BB[cur]);
      cur = nxt;
      act[cur]++;
    }
    long long EE = 0;
    for(int i = 0; i < N; i++) {
      EE += abs(act[i] - T[i]);
    }
    if(EE < best_E) {
      best_E = EE;
      best_A = AA;
      best_B = BB;
    }
  }
  for(int i = 0; i < N; i++) {
    cout << best_A[i] << " " << best_B[i] << "\n";
  }
  return 0;
}