#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(NULL);
  int N, M;
  cin >> N >> M;
  int L = N * M;
  vector<vector<int>> color_groups(N + 1);
  vector<int> active_colors;
  vector<int> reps;
  int next_color = 1;
  for (int x = 1; x <= L; ++x) {
    int comp = -1;
    int K = active_colors.size();
    if (K == 0) {
      comp = next_color++;
      color_groups[comp].push_back(x);
      active_colors.push_back(comp);
      reps.push_back(x);
    } else {
      // Binary search for the component index 0 to K-1 or K for none
      int low = 0, high = K;
      while (low < high) {
        int mid = (low + high) / 2;
        vector<int> P;
        for (int i = low; i <= mid; ++i) {
          P.push_back(reps[i]);
        }
        vector<char> is_excluded(L + 1, 0);
        is_excluded[x] = 1;
        for (int p : P) {
          is_excluded[p] = 1;
        }
        int num_s = L - (int)P.size() - 1;
        cout << "? " << num_s;
        for (int i = 1; i <= L; ++i) {
          if (!is_excluded[i]) {
            cout << " " << i;
          }
        }
        cout << "\n";
        fflush(stdout);
        int response;
        cin >> response;
        bool matches = (response == M - 2);
        if (matches) {
          high = mid;
        } else {
          low = mid + 1;
        }
      }
      if (low < K) {
        // Verify single
        vector<int> P_single = {reps[low]};
        vector<char> is_excluded(L + 1, 0);
        is_excluded[x] = 1;
        for (int p : P_single) {
          is_excluded[p] = 1;
        }
        int num_s = L - 1 - 1;
        cout << "? " << num_s;
        for (int i = 1; i <= L; ++i) {
          if (!is_excluded[i]) {
            cout << " " << i;
          }
        }
        cout << "\n";
        fflush(stdout);
        int resp_verify;
        cin >> resp_verify;
        if (resp_verify == M - 2) {
          comp = active_colors[low];
        }
      }
      if (comp == -1) {
        comp = next_color++;
        active_colors.push_back(comp);
        reps.push_back(x);
      }
      color_groups[comp].push_back(x);
    }
    // Check if full
    if ((int)color_groups[comp].size() == M) {
      auto it = find(active_colors.begin(), active_colors.end(), comp);
      int idx = it - active_colors.begin();
      active_colors.erase(it);
      reps.erase(reps.begin() + idx);
    }
  }
  // Form sticks
  vector<vector<int>> sticks(M);
  for (int c = 1; c <= N; ++c) {
    for (int j = 0; j < M; ++j) {
      sticks[j].push_back(color_groups[c][j]);
    }
  }
  // Output
  for (int k = 0; k < M; ++k) {
    cout << "!";
    for (int d : sticks[k]) {
      cout << " " << d;
    }
    cout << "\n";
    fflush(stdout);
  }
  return 0;
}