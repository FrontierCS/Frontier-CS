#include <bits/stdc++.h>

using namespace std;

int main() {
  int N;
  cin >> N;
  vector<int> A(N + 1);
  long long sumA = 0;
  for (int i = 1; i <= N; i++) {
    cin >> A[i];
    sumA += A[i];
  }
  vector<int> B(N + 1);
  long long sumB = 0;
  for (int i = 1; i <= N; i++) {
    cin >> B[i];
    sumB += B[i];
  }
  if (sumA != sumB) {
    cout << "No" << endl;
    return 0;
  }
  vector<int> odd_count(2, 0);
  for (int i = 1; i <= N; i++) {
    odd_count[A[i] % 2]++;
  }
  for (int i = 1; i <= N; i++) {
    if ((odd_count[B[i] % 2] % 2) != (odd_count[A[i] % 2] % 2)) {
      cout << "No" << endl;
      return 0;
    }
  }
  vector<int> current = A;
  vector<pair<int, int>> ops;
  const int MAX_ITER = 10000;
  bool reached = false;
  for (int iter = 0; iter < MAX_ITER; iter++) {
    bool match = true;
    int k = -1;
    for (int i = 1; i <= N; i++) {
      if (current[i] != B[i]) {
        match = false;
        k = i;
        break;
      }
    }
    if (match) {
      reached = true;
      break;
    }
    // find best j > k
    int best_j = -1;
    int best_dist = INT_MAX;
    for (int j = k + 1; j <= N; j++) {
      int new_val = current[j] - 1;
      int dist = abs(new_val - B[k]);
      if (dist < best_dist || (dist == best_dist && (current[k] < B[k] ? current[j] > current[best_j] : current[j] < current[best_j]))) {
        best_dist = dist;
        best_j = j;
      }
    }
    if (best_j == -1) break;
    ops.emplace_back(k, best_j);
    int old_ai = current[k];
    int old_aj = current[best_j];
    current[k] = old_aj - 1;
    current[best_j] = old_ai + 1;
  }
  if (reached) {
    cout << "Yes" << endl;
    cout << ops.size() << endl;
    for (auto p : ops) {
      cout << p.first << " " << p.second << endl;
    }
  } else {
    cout << "No" << endl;
  }
  return 0;
}