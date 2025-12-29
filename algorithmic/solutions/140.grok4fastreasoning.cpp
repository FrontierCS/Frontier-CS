#include <bits/stdc++.h>
using namespace std;
using ll = long long;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(nullptr);
  ll B, K, W;
  cin >> B >> K >> W;
  cout << "? 1 " << -B << " " << -B << endl;
  cout.flush();
  vector<ll> D_SW(K);
  for (int i = 0; i < K; ++i) cin >> D_SW[i];
  cout << "? 1 " << -B << " " << B << endl;
  cout.flush();
  vector<ll> D_NW(K);
  for (int i = 0; i < K; ++i) cin >> D_NW[i];
  cout << "? 1 0 0" << endl;
  cout.flush();
  vector<ll> D_C(K);
  for (int i = 0; i < K; ++i) cin >> D_C[i];
  map<ll, int> freq_c;
  for (ll d : D_C) ++freq_c[d];
  vector<vector<int>> possible(K);
  for (int i = 0; i < K; ++i) {
    ll pp = D_SW[i];
    vector<pair<ll, int>> candidates;
    for (int j = 0; j < K; ++j) {
      ll qq = D_NW[j];
      ll diff = pp - qq;
      if (diff % 2 != 0) continue;
      ll sumv = pp + qq;
      if (sumv % 2 != 0) continue;
      ll yy = diff / 2;
      ll xx = (sumv - 4LL * B) / 2;
      if (xx < -B || xx > B || yy < -B || yy > B) continue;
      ll comp_c = abs(xx) + abs(yy);
      if (freq_c.count(comp_c) && freq_c[comp_c] > 0) {
        candidates.emplace_back(abs(pp - qq), j);
      }
    }
    sort(candidates.begin(), candidates.end());
    for (auto [_, j] : candidates) {
      possible[i].push_back(j);
    }
  }
  vector<int> assignment(K, -1);
  vector<pair<ll, ll>> answer(K);
  bool found = false;
  function<void(int, vector<bool>&)> dfs = [&](int pos, vector<bool>& used) {
    if (found) return;
    if (pos == K) {
      vector<ll> comp_list(K);
      for (int i = 0; i < K; ++i) {
        int j = assignment[i];
        ll pp = D_SW[i], qq = D_NW[j];
        ll diff = pp - qq;
        ll sumv = pp + qq;
        ll yy = diff / 2;
        ll xx = (sumv - 4LL * B) / 2;
        answer[i] = {xx, yy};
        comp_list[i] = abs(xx) + abs(yy);
      }
      sort(comp_list.begin(), comp_list.end());
      if (comp_list == D_C) {
        found = true;
      }
      return;
    }
    for (int j : possible[pos]) {
      if (used[j]) continue;
      assignment[pos] = j;
      used[j] = true;
      dfs(pos + 1, used);
      if (found) return;
      used[j] = false;
      assignment[pos] = -1;
    }
  };
  vector<bool> used(K, false);
  dfs(0, used);
  cout << "!";
  for (auto [x, y] : answer) {
    cout << " " << x << " " << y;
  }
  cout << endl;
  cout.flush();
}