#include <bits/stdc++.h>

using namespace std;

using ll = long long;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int n;
  ll T;
  cin >> n >> T;
  vector<pair<ll, int>> items(n);
  for (int i = 0; i < n; i++) {
    ll a;
    cin >> a;
    items[i] = {a, i};
  }
  sort(items.rbegin(), items.rend());
  vector<int> sel(n, 0);
  ll S = 0;
  for (auto& p : items) {
    ll a = p.first;
    int idx = p.second;
    ll news = S + a;
    ll err_now = abs(S - T);
    ll err_new = abs(news - T);
    if (err_new < err_now) {
      S = news;
      sel[idx] = 1;
    }
  }
  string res(n, '0');
  for (int i = 0; i < n; i++) {
    if (sel[i]) res[i] = '1';
  }
  cout << res << '\n';
}