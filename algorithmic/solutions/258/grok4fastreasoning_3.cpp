#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int t;
  cin >> t;
  for (int cas = 0; cas < t; cas++) {
    int n;
    cin >> n;
    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < n - 1; i++) {
      int u, v;
      cin >> u >> v;
      adj[u].push_back(v);
      adj[v].push_back(u);
    }
    cout << "? " << n;
    for (int i = 1; i <= n; i++) cout << " " << i;
    cout << "\n";
    cout.flush();
    int mm, DD;
    cin >> mm >> DD;
    if (mm == -1 && DD == -1) return 0;
    vector<int> neighh = adj[mm];
    cout << "? " << (int)neighh.size();
    for (int v : neighh) cout << " " << v;
    cout << "\n";
    cout.flush();
    int c11, dy1;
    cin >> c11 >> dy1;
    if (c11 == -1) return 0;
    int c_one = c11;
    bool two_arms = false;
    int c_twoo = -1;
    vector<int> set_twoo;
    for (int v : neighh) {
      if (v != c_one) set_twoo.push_back(v);
    }
    if (!set_twoo.empty()) {
      cout << "? " << (int)set_twoo.size();
      for (int v : set_twoo) cout << " " << v;
      cout << "\n";
      cout.flush();
      int z, ddz;
      cin >> z >> ddz;
      if (z == -1) return 0;
      if (ddz == DD) {
        two_arms = true;
        c_twoo = z;
      }
    }
    auto compute_end = [&](int r_arm, int p_par) -> int {
      vector<int> d_arm(n + 1, -1);
      vector<int> p_arm(n + 1, -1);
      vector<vector<int>> layerr;
      queue<int> qqq;
      d_arm[r_arm] = 0;
      p_arm[r_arm] = p_par;
      qqq.push(r_arm);
      while (!qqq.empty()) {
        int u = qqq.front();
        qqq.pop();
        int de = d_arm[u];
        while ((int)layerr.size() <= de) {
          layerr.emplace_back();
        }
        layerr[de].push_back(u);
        for (int v : adj[u]) {
          if (v == p_arm[u]) continue;
          if (d_arm[v] == -1) {
            d_arm[v] = de + 1;
            p_arm[v] = u;
            qqq.push(v);
          }
        }
      }
      int hhh = layerr.empty() ? 0 : layerr.size() - 1;
      int lo = 0;
      int hi = hhh;
      while (lo < hi) {
        int mi = (lo + hi + 1) / 2;
        const auto& la = layerr[mi];
        cout << "? " << (int)la.size();
        for (int vv : la) cout << " " << vv;
        cout << "\n";
        cout.flush();
        int xxi, ddi;
        cin >> xxi >> ddi;
        if (xxi == -1) return -1;
        if (ddi == DD) {
          lo = mi;
        } else {
          hi = mi - 1;
        }
      }
      int lll = lo;
      int en;
      if (lll == 0) {
        en = r_arm;
      } else {
        const auto& la = layerr[lll];
        cout << "? " << (int)la.size();
        for (int vv : la) cout << " " << vv;
        cout << "\n";
        cout.flush();
        int xxi, ddi;
        cin >> xxi >> ddi;
        if (xxi == -1) return -1;
        en = xxi;
      }
      return en;
    };
    int a, b;
    if (!two_arms) {
      a = mm;
      b = compute_end(c_one, mm);
    } else {
      a = compute_end(c_one, mm);
      b = compute_end(c_twoo, mm);
    }
    cout << "! " << a << " " << b << "\n";
    cout.flush();
    string ver;
    cin >> ver;
    if (ver == "Incorrect") return 0;
  }
  return 0;
}