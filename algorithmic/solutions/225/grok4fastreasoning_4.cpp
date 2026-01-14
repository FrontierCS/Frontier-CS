#include <bits/stdc++.h>
using namespace std;

int n, q;
vector<int> a;
map<pair<int, int>, int> built;
vector<pair<int, int>> merges;
int current_cnt;

int get_id(int l, int r) {
  pair<int, int> key = {l, r};
  if (built.count(key)) return built[key];
  vector<int> pos;
  for (int i = l; i <= r; i++) pos.push_back(i);
  if (pos.empty()) return -1;
  sort(pos.begin(), pos.end(), [&](int x, int y) {
    return a[x] < a[y];
  });
  int curr = pos[0];
  for (size_t j = 1; j < pos.size(); ++j) {
    int nxt = pos[j];
    current_cnt++;
    merges.emplace_back(curr, nxt);
    curr = current_cnt;
  }
  built[key] = curr;
  return curr;
}

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  cin >> n >> q;
  a.resize(n + 1);
  for (int i = 1; i <= n; i++) cin >> a[i];
  vector<int> answers(q);
  current_cnt = n;
  for (int i = 0; i < q; i++) {
    int l, r;
    cin >> l >> r;
    answers[i] = get_id(l, r);
  }
  int cnt_E = current_cnt;
  cout << cnt_E << '\n';
  for (auto [u, v] : merges) {
    cout << u << " " << v << '\n';
  }
  for (int i = 0; i < q; i++) {
    cout << answers[i];
    if (i < q - 1) cout << " ";
    else cout << "\n";
  }
  return 0;
}