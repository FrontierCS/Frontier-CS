#include <bits/stdc++.h>

using namespace std;

int main() {
  int n;
  cin >> n;
  int m = n / 2;
  int half = (n + 1) / 2;
  int r = 1;
  while (true) {
    // compute dist from r
    vector<int> dstr(n + 1, 0);
    for (int v = 1; v <= n; v++) {
      if (v == r) continue;
      cout << "? " << r << " " << v << endl;
      cout.flush();
      int d;
      cin >> d;
      dstr[v] = d;
    }
    vector<int> children;
    for (int v = 1; v <= n; v++) {
      if (dstr[v] == 1) children.push_back(v);
    }
    sort(children.begin(), children.end());
    int dd = children.size();
    if (dd >= half) {
      cout << "! " << r << endl;
      cout.flush();
      return 0;
    }
    // now find heavy
    int total = n - 1;
    int sum_s = 0;
    int heavy = -1;
    for (int i = 0; i < dd; i++) {
      int c = children[i];
      // compute dist from c
      vector<int> distc(n + 1, 0);
      for (int v = 1; v <= n; v++) {
        if (v == c) continue;
        cout << "? " << c << " " << v << endl;
        cout.flush();
        int d;
        cin >> d;
        distc[v] = d;
      }
      int s = 0;
      for (int v = 1; v <= n; v++) {
        if (dstr[v] == 1 + distc[v]) s++;
      }
      if (s > m) {
        heavy = c;
        break;
      }
      sum_s += s;
      if (sum_s >= total - m) break;
    }
    if (heavy != -1) {
      r = heavy;
    } else {
      cout << "! " << r << endl;
      cout.flush();
      return 0;
    }
  }
  return 0;
}