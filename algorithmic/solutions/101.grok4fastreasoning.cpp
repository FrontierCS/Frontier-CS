#include <bits/stdc++.h>
using namespace std;

int main() {
  int N, R;
  cin >> N >> R;
  vector<pair<int, int>> conn(N);
  for (int i = 0; i < N; i++) {
    cin >> conn[i].first >> conn[i].second;
  }
  int total = 2 * N + 1;
  vector<int> par(total, -1);
  for (int i = 0; i < N; i++) {
    int u = conn[i].first, v = conn[i].second;
    par[u] = i;
    par[v] = i;
  }
  vector<char> typ(N, 0);
  auto set_sub = [&](auto&& self, int node, int val, string& ss) -> void {
    if (node >= N) {
      ss[node] = '0' + val;
      return;
    }
    ss[node] = '0';
    int u = conn[node].first, v = conn[node].second;
    self(self, u, val, ss);
    self(self, v, val, ss);
  };
  auto determine = [&](auto&& self, int k) -> void {
    if (k >= N) return;
    string ss(total, '0');
    int uu = conn[k].first, vv = conn[k].second;
    if (k == 0) {
      set_sub(set_sub, uu, 0, ss);
      set_sub(set_sub, vv, 1, ss);
      cout << "? " << ss << endl;
      cout.flush();
      int resp;
      cin >> resp;
      typ[0] = (resp == 0 ? '&' : '|');
    } else {
      vector<int> ancestors;
      int curp = par[k];
      while (curp != -1) {
        ancestors.push_back(curp);
        curp = par[curp];
      }
      int dd = ancestors.size();
      int cval0 = 0, cval1 = 1;
      vector<int> ch_w(dd);
      for (int l = 0; l < dd; l++) {
        int g = ancestors[l];
        bool isand = (typ[g] == '&');
        int n0 = isand ? min(cval0, 0) : max(cval0, 0);
        int n1 = isand ? min(cval1, 0) : max(cval1, 0);
        if (n0 != n1) {
          ch_w[l] = 0;
          cval0 = n0;
          cval1 = n1;
          continue;
        }
        n0 = isand ? min(cval0, 1) : max(cval0, 1);
        n1 = isand ? min(cval1, 1) : max(cval1, 1);
        ch_w[l] = 1;
        cval0 = n0;
        cval1 = n1;
      }
      int exp0 = cval0, exp1 = cval1;
      set_sub(set_sub, uu, 0, ss);
      set_sub(set_sub, vv, 1, ss);
      ss[k] = '0';
      vector<int> pchild(dd);
      pchild[0] = k;
      for (int l = 1; l < dd; l++) {
        pchild[l] = ancestors[l - 1];
      }
      for (int l = 0; l < dd; l++) {
        int g = ancestors[l];
        int ch1 = conn[g].first, ch2 = conn[g].second;
        int sib = (ch1 == pchild[l] ? ch2 : ch2 == pchild[l] ? ch1 : -1);
        set_sub(set_sub, sib, ch_w[l], ss);
      }
      cout << "? " << ss << endl;
      cout.flush();
      int resp;
      cin >> resp;
      typ[k] = (resp == exp0 ? '&' : '|');
    }
    int u = conn[k].first, v = conn[k].second;
    self(self, u);
    self(self, v);
  };
  determine(determine, 0);
  cout << "!";
  for (char c : typ) cout << c;
  cout << endl;
  cout.flush();
  return 0;
}