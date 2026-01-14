#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int n;
  cin >> n;
  for(int graph = 0; graph < n; graph++) {
    cout << "? 1 1" << endl;
    cout.flush();
    int cc;
    cin >> cc;
    int c = cc;
    const int m = 1000;
    vector<int> pos(m + 1);
    pos[0] = c;
    int current = c;
    bool found = false;
    ll s = -1;
    for(int i = 1; i <= m; i++) {
      cout << "? " << current << " 1" << endl;
      cout.flush();
      int nxt;
      cin >> nxt;
      pos[i] = nxt;
      current = nxt;
      if(i >= 3 && nxt == c) {
        found = true;
        s = i;
        break;
      }
    }
    if(found) {
      cout << "! " << s << endl;
      cout.flush();
      int ver;
      cin >> ver;
      if(ver == -1) return 0;
      continue;
    }
    map<int, int> bab;
    for(int i = 0; i <= m; i++) {
      bab[pos[i]] = i;
    }
    vector<ll> diffs;
    for(int k = 1; k <= m; k++) {
      ll steps = (ll)k * m;
      cout << "? " << c << " " << steps << endl;
      cout.flush();
      int g;
      cin >> g;
      auto it = bab.find(g);
      if(it != bab.end()) {
        int i = it->second;
        ll diff = steps - i;
        if(diff >= 3) {
          diffs.push_back(diff);
        }
      }
    }
    ll G = diffs[0];
    for(size_t j = 1; j < diffs.size(); j++) {
      G = __gcd(G, diffs[j]);
    }
    cout << "! " << G << endl;
    cout.flush();
    int ver;
    cin >> ver;
    if(ver == -1) return 0;
  }
  return 0;
}