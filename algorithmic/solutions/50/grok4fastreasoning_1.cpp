#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int n, m;
  cin >> n >> m;
  vector<long long> cost(m + 1);
  for (int i = 1; i <= m; i++) {
    cin >> cost[i];
  }
  vector<vector<int>> set_elements(m + 1);
  vector<vector<int>> element_sets(n + 1);
  for (int i = 1; i <= n; i++) {
    int k;
    cin >> k;
    element_sets[i].resize(k);
    for (int j = 0; j < k; j++) {
      cin >> element_sets[i][j];
      int a = element_sets[i][j];
      set_elements[a].push_back(i);
    }
  }
  vector<int> current_cover(m + 1, 0);
  for (int s = 1; s <= m; s++) {
    current_cover[s] = set_elements[s].size();
  }
  vector<bool> is_covered(n + 1, false);
  int num_uncovered = n;
  vector<int> chosen;
  while (num_uncovered > 0) {
    double best_density = -1.0;
    int best_s = -1;
    for (int s = 1; s <= m; s++) {
      if (current_cover[s] <= 0) continue;
      double density;
      if (cost[s] == 0) {
        density = 1e100;
      } else {
        density = (double)current_cover[s] / cost[s];
      }
      if (density > best_density ||
          (density == best_density && cost[s] < cost[best_s])) {
        best_density = density;
        best_s = s;
      }
    }
    if (best_s == -1) {
      break;
    }
    chosen.push_back(best_s);
    for (int e : set_elements[best_s]) {
      if (!is_covered[e]) {
        is_covered[e] = true;
        num_uncovered--;
        for (int t : element_sets[e]) {
          current_cover[t]--;
        }
      }
    }
  }
  sort(chosen.begin(), chosen.end());
  cout << chosen.size() << "\n";
  for (size_t i = 0; i < chosen.size(); i++) {
    if (i > 0) cout << " ";
    cout << chosen[i];
  }
  cout << "\n";
  return 0;
}