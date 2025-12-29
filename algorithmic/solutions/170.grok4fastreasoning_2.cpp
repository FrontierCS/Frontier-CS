#include <bits/stdc++.h>
using namespace std;

long long compute_error(const vector<int>& A, const vector<int>& B, const vector<long long>& T, int L, int N) {
  vector<int> visits(N, 0);
  int current = 0;
  visits[0] = 1;
  for (int w = 1; w < L; ++w) {
    int t = visits[current];
    int nextt = (t & 1 ? A[current] : B[current]);
    current = nextt;
    visits[current]++;
  }
  long long err = 0;
  for (int i = 0; i < N; i++) {
    err += abs((long long)visits[i] - T[i]);
  }
  return err;
}

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int N, L;
  cin >> N >> L;
  vector<long long> T(N);
  for (auto& x : T) cin >> x;
  srand(time(0));
  vector<int> A(N), B(N);
  for (int i = 0; i < N; i++) {
    int nxt = (i + 1) % N;
    A[i] = nxt;
    B[i] = nxt;
  }
  long long best_e = compute_error(A, B, T, L, N);
  vector<int> best_A = A, best_B = B;
  const int NUM_ITER = 4000;
  for (int iter = 0; iter < NUM_ITER; iter++) {
    int i = rand() % N;
    bool change_a = (rand() % 2 == 0);
    int old_val = change_a ? A[i] : B[i];
    int new_val = rand() % N;
    if (new_val == old_val) continue;
    if (change_a) A[i] = new_val;
    else B[i] = new_val;
    long long new_e = compute_error(A, B, T, L, N);
    if (new_e < best_e) {
      best_e = new_e;
      best_A = A;
      best_B = B;
    } else {
      if (change_a) A[i] = old_val;
      else B[i] = old_val;
    }
  }
  for (int i = 0; i < N; i++) {
    cout << best_A[i] << " " << best_B[i] << "\n";
  }
  return 0;
}