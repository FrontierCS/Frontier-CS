#include <bits/stdc++.h>

using namespace std;

int main() {
  int N;
  cin >> N;
  vector<int> A(N), B(N);
  long long sumA = 0, sumB = 0;
  for (int &x : A) {
    cin >> x;
    sumA += x;
  }
  for (int &x : B) {
    cin >> x;
    sumB += x;
  }
  if (sumA != sumB) {
    cout << "No" << endl;
    return 0;
  }
  vector<int> current = A;
  vector<pair<int, int>> ops;
  int max_steps = 10000;
  int steps = 0;
  while (steps < max_steps) {
    int curr_mismatch = 0;
    for (int k = 0; k < N; k++) curr_mismatch += abs(current[k] - B[k]);
    if (curr_mismatch == 0) break;
    int best_improve = 0;
    int best_i = -1, best_j = -1;
    for (int i = 0; i < N; i++) {
      for (int j = i + 1; j < N; j++) {
        int x = current[i];
        int y = current[j];
        int newx = y - 1;
        int newy = x + 1;
        int old_m = abs(x - B[i]) + abs(y - B[j]);
        int new_m = abs(newx - B[i]) + abs(newy - B[j]);
        int improve = old_m - new_m;
        if (improve > best_improve) {
          best_improve = improve;
          best_i = i + 1;
          best_j = j + 1;
        }
      }
    }
    if (best_improve > 0) {
      int i = best_i - 1, j = best_j - 1;
      int x = current[i];
      int y = current[j];
      current[i] = y - 1;
      current[j] = x + 1;
      ops.emplace_back(best_i, best_j);
      steps++;
    } else {
      break;
    }
  }
  bool success = true;
  for (int k = 0; k < N; k++) if (current[k] != B[k]) success = false;
  if (success) {
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