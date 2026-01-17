#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int N;
  cin >> N;
  vector<int> S(N);
  for (int &x : S) cin >> x;
  int M;
  cin >> M;
  vector<pair<int, int>> jerry(M);
  for (auto &p : jerry) cin >> p.first >> p.second;
  vector<int> position(N);
  for (int i = 0; i < N; i++) position[S[i]] = i;
  set<tuple<int, int>> misplaced;
  for (int k = 0; k < N; k++) {
    int d = abs(k - position[k]);
    if (d > 0) misplaced.insert({d, k});
  }
  vector<pair<int, int>> my_swaps;
  vector<long long> costs;
  int R = 0;
  if (!misplaced.empty()) {
    bool done = false;
    for (int r = 0; r < M; r++) {
      int x = jerry[r].first;
      int y = jerry[r].second;
      if (x != y) {
        int numx = S[x];
        int numy = S[y];
        int dx = abs(numx - position[numx]);
        if (dx > 0) misplaced.erase({dx, numx});
        int dy = abs(numy - position[numy]);
        if (dy > 0) misplaced.erase({dy, numy});
        swap(S[x], S[y]);
        position[S[x]] = x;
        position[S[y]] = y;
        int new_d_numx = abs(numx - y);
        if (new_d_numx > 0) misplaced.insert({new_d_numx, numx});
        int new_d_numy = abs(numy - x);
        if (new_d_numy > 0) misplaced.insert({new_d_numy, numy});
      }
      pair<int, int> this_s = {0, 0};
      long long this_c = 0;
      if (!misplaced.empty()) {
        auto [d, k] = *misplaced.begin();
        int p = position[k];
        this_s = {k, p};
        this_c = abs(k - p);
        int u = k, v = p;
        int numu = S[u];
        int numv = S[v];
        int du = abs(numu - position[numu]);
        if (du > 0) misplaced.erase({du, numu});
        int dv = abs(numv - position[numv]);
        if (dv > 0) misplaced.erase({dv, numv});
        swap(S[u], S[v]);
        position[S[u]] = u;
        position[S[v]] = v;
        int new_d_numu = abs(numu - v);
        if (new_d_numu > 0) misplaced.insert({new_d_numu, numu});
      }
      int uu = this_s.first, vv = this_s.second;
      if (uu > vv) swap(uu, vv);
      my_swaps.push_back({uu, vv});
      costs.push_back(this_c);
      if (misplaced.empty()) {
        R = r + 1;
        done = true;
        break;
      }
    }
    if (!done) R = M;
  }
  long long sum_cost = 0;
  for (int i = 0; i < R; i++) sum_cost += costs[i];
  long long VV = (long long)R * sum_cost;
  cout << R << "\n";
  for (int i = 0; i < R; i++) {
    cout << my_swaps[i].first << " " << my_swaps[i].second << "\n";
  }
  cout << VV << "\n";
  return 0;
}