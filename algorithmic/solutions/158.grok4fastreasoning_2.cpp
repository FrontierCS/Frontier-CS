#include <bits/stdc++.h>
using namespace std;
using ll = long long;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(nullptr);
  int N, K;
  cin >> N >> K;
  vector<int> a(11, 0);
  for (int d = 1; d <= 10; ++d) cin >> a[d];
  vector<pair<ll, ll>> pos(N);
  for (int i = 0; i < N; ++i) {
    ll x, y;
    cin >> x >> y;
    pos[i] = {x, y};
  }
  vector<vector<int>> current_groups(1, vector<int>(N));
  iota(current_groups[0].begin(), current_groups[0].end(), 0);
  auto compute_score = [&](const vector<vector<int>>& grps) -> int {
    vector<int> freq(11, 0);
    for (const auto& g : grps) {
      int s = g.size();
      if (s >= 1 && s <= 10) ++freq[s];
    }
    int sc = 0;
    for (int d = 1; d <= 10; ++d) sc += min(a[d], freq[d]);
    return sc;
  };
  int current_score = compute_score(current_groups);
  vector<tuple<ll, ll, ll, ll>> chosen_lines;
  mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
  const ll RR = 1000000000LL;
  const ll MOD = 2 * RR + 1;
  auto gen_line = [&]() -> tuple<ll, ll, ll, ll> {
    ll px, py, qx, qy;
    do {
      px = ((ll)rng() % MOD) - RR;
      py = ((ll)rng() % MOD) - RR;
      qx = ((ll)rng() % MOD) - RR;
      qy = ((ll)rng() % MOD) - RR;
    } while (px == qx && py == qy);
    return {px, py, qx, qy};
  };
  auto compute_cross = [&](int i, ll px, ll py, ll qx, ll qy) -> ll {
    ll dx = qx - px;
    ll dy = qy - py;
    ll dx1 = pos[i].first - px;
    ll dy1 = pos[i].second - py;
    return dx1 * dy - dy1 * dx;
  };
  for (int step = 0; step < K; ++step) {
    int best_score = current_score;
    tuple<ll, ll, ll, ll> best_line{};
    int num_cand = 500;
    for (int c = 0; c < num_cand; ++c) {
      auto [px, py, qx, qy] = gen_line();
      bool hits = false;
      vector<int> new_gs;
      for (const auto& g : current_groups) {
        int l = 0, r = 0, o = 0;
        for (int idx : g) {
          ll cross = compute_cross(idx, px, py, qx, qy);
          if (cross == 0) {
            ++o;
            hits = true;
          } else if (cross > 0) {
            ++l;
          } else {
            ++r;
          }
        }
        if (l > 0) new_gs.push_back(l);
        if (r > 0) new_gs.push_back(r);
      }
      if (hits) continue;
      vector<int> temp_b(11, 0);
      for (int s : new_gs) {
        if (s <= 10) ++temp_b[s];
      }
      int ns = 0;
      for (int d = 1; d <= 10; ++d) ns += min(a[d], temp_b[d]);
      if (ns > best_score) {
        best_score = ns;
        best_line = {px, py, qx, qy};
      }
    }
    if (best_score == current_score) break;
    auto [px, py, qx, qy] = best_line;
    vector<vector<int>> new_groups;
    for (auto& g : current_groups) {
      vector<int> left, right;
      for (int idx : g) {
        ll cross = compute_cross(idx, px, py, qx, qy);
        if (cross > 0) {
          left.push_back(idx);
        } else if (cross < 0) {
          right.push_back(idx);
        }
      }
      if (!left.empty()) new_groups.push_back(move(left));
      if (!right.empty()) new_groups.push_back(move(right));
    }
    current_groups = move(new_groups);
    chosen_lines.emplace_back(px, py, qx, qy);
    current_score = best_score;
  }
  int k = chosen_lines.size();
  cout << k << '\n';
  for (auto [px, py, qx, qy] : chosen_lines) {
    cout << px << ' ' << py << ' ' << qx << ' ' << qy << '\n';
  }
}