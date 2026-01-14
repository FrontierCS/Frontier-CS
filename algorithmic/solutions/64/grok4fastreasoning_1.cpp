#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  long long nn, T;
  cin >> nn >> T;
  int n = nn;
  vector<long long> a(n);
  for (int i = 0; i < n; i++) cin >> a[i];
  vector<int> best_choice(n, 0);
  long long min_error = LLONG_MAX / 2;
  auto do_hill = [&](vector<int> start_choice) -> pair<long long, vector<int>> {
    vector<int> choice = start_choice;
    long long cur = 0;
    for (int i = 0; i < n; i++) if (choice[i]) cur += a[i];
    bool changed = true;
    while (changed) {
      changed = false;
      long long cur_error = abs(cur - T);
      long long best_new_error = cur_error;
      int best_j = -1;
      long long best_new_cur = cur;
      for (int j = 0; j < n; j++) {
        long long delta = choice[j] ? -a[j] : +a[j];
        long long new_cur = cur + delta;
        long long new_err = abs(new_cur - T);
        if (new_err < best_new_error) {
          best_new_error = new_err;
          best_j = j;
          best_new_cur = new_cur;
        }
      }
      if (best_j != -1 && best_new_error < cur_error) {
        choice[best_j] = 1 - choice[best_j];
        cur = best_new_cur;
        changed = true;
      }
    }
    return {cur, choice};
  };
  int num_starts = 100;
  srand(time(NULL));
  for (int s = 0; s < num_starts; s++) {
    vector<int> start(n);
    for (int i = 0; i < n; i++) {
      start[i] = (rand() & 1);
    }
    auto [new_sum, new_choice] = do_hill(start);
    long long err = abs(new_sum - T);
    if (err < min_error) {
      min_error = err;
      best_choice = new_choice;
    }
  }
  // greedy start
  vector<pair<long long, int>> items(n);
  for (int i = 0; i < n; i++) items[i] = {a[i], i};
  sort(items.rbegin(), items.rend());
  vector<int> gchoice(n, 0);
  long long gcur = 0;
  for (auto &p : items) {
    if (gcur + p.first <= T) {
      gcur += p.first;
      gchoice[p.second] = 1;
    }
  }
  auto [gnew_sum, gnew_choice] = do_hill(gchoice);
  long long gerr = abs(gnew_sum - T);
  if (gerr < min_error) {
    min_error = gerr;
    best_choice = gnew_choice;
  }
  for (int i = 0; i < n; i++) {
    cout << best_choice[i];
  }
  cout << "\n";
}