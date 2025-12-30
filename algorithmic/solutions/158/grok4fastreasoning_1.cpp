#include <bits/stdc++.h>
using namespace std;
using ll = long long;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(nullptr);
  int N, K;
  cin >> N >> K;
  vector<int> a(11, 0);
  for (int d = 1; d <= 10; d++) cin >> a[d];
  vector<pair<ll, ll>> points(N);
  for (int i = 0; i < N; i++) {
    cin >> points[i].first >> points[i].second;
  }
  mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
  auto rand_coord = [&](ll l, ll r) -> ll {
    ll range = r - l + 1;
    return l + (rng() % range);
  };
  vector<tuple<ll, ll, ll, ll>> lines;
  const int target_k = 100;
  const ll scale = 100000000LL;
  const ll offset_range = 1000LL;
  for (int i = 0; i < target_k; i++) {
    double alpha = i * 2.0 * M_PI / target_k;
    double c = cos(alpha);
    double s = sin(alpha);
    ll dx = (ll)round(c * scale);
    ll dy = (ll)round(s * scale);
    bool found = false;
    for (int attempt = 0; attempt < 2001; attempt++) {
      ll bo = rand_coord(-offset_range, offset_range);
      ll px = 0;
      ll py = bo;
      ll qx = dx;
      ll qy = bo + dy;
      if (px == qx && py == qy) continue;
      bool hits = false;
      for (auto [x, y] : points) {
        ll det = (qx - px) * (y - py) - (qy - py) * (x - px);
        if (det == 0) {
          hits = true;
          break;
        }
      }
      if (!hits) {
        lines.emplace_back(px, py, qx, qy);
        found = true;
        break;
      }
    }
    if (!found) {
      // Fallback: use bo=0
      ll bo = 0;
      ll px = 0;
      ll py = bo;
      ll qx = dx;
      ll qy = bo + dy;
      lines.emplace_back(px, py, qx, qy);
    }
  }
  int k = min((int)lines.size(), K);
  cout << k << '\n';
  for (int i = 0; i < k; i++) {
    auto [px, py, qx, qy] = lines[i];
    cout << px << ' ' << py << ' ' << qx << ' ' << qy << '\n';
  }
}