#include <bits/stdc++.h>
using namespace std;

int main() {
  int N, L;
  cin >> N >> L;
  vector<int> T(N);
  for (int &x : T) cin >> x;
  vector<int> choices;
  for (int i = 0; i < N; i++) {
    for (int j = 0; j < T[i]; j++) {
      choices.push_back(i);
    }
  }
  mt19937 rng(42);
  uniform_int_distribution<int> dist(0, L - 1);
  uniform_int_distribution<int> distn(0, N - 1);
  uniform_int_distribution<int> dist01(0, 1);
  const int TRIALS = 500;
  vector<int> best_a(N), best_b(N);
  int min_e = INT_MAX;
  auto simulate = [&](const vector<int> &a, const vector<int> &b) -> int {
    vector<int> cnt(N, 0);
    int cur = 0;
    cnt[0]++;
    for (int w = 1; w < L; w++) {
      int t = cnt[cur];
      int nxt = (t & 1) ? a[cur] : b[cur];
      cur = nxt;
      cnt[nxt]++;
    }
    int e = 0;
    for (int i = 0; i < N; i++) {
      e += abs(cnt[i] - T[i]);
    }
    return e;
  };
  for (int trial = 0; trial < TRIALS; trial++) {
    vector<int> a(N), bb(N);
    for (int i = 0; i < N; i++) {
      int idx = dist(rng);
      a[i] = choices[idx];
      idx = dist(rng);
      bb[i] = choices[idx];
    }
    int e = simulate(a, bb);
    if (e < min_e) {
      min_e = e;
      best_a = a;
      best_b = bb;
    }
  }
  // local search
  const int LOCAL = 100;
  for (int loc = 0; loc < LOCAL; loc++) {
    vector<int> ca = best_a;
    vector<int> cb = best_b;
    int i = distn(rng);
    bool isa = dist01(rng) == 0;
    int idx = dist(rng);
    if (isa) {
      ca[i] = choices[idx];
    } else {
      cb[i] = choices[idx];
    }
    int e = simulate(ca, cb);
    if (e < min_e) {
      min_e = e;
      best_a = ca;
      best_b = cb;
    }
  }
  for (int i = 0; i < N; i++) {
    cout << best_a[i] << " " << best_b[i] << "\n";
  }
}