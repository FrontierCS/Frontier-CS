#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int t;
  cin >> t;
  for (int test = 0; test < t; test++) {
    cout << "? 100000";
    for (int i = 0; i < 100000; i++) cout << " 1";
    cout << endl;
    int lines;
    cin >> lines;
    if (lines == -1) return 0;
    long long m = 100000;
    long long lef, rig;
    if (lines == 1) {
      lef = m;
      rig = m;
    } else {
      lef = (m + lines - 1LL) / lines;
      rig = (m - 1LL) / (lines - 1LL);
    }
    if (lef == rig) {
      cout << "! " << lef << endl;
      continue;
    }
    long long L = lef, R = rig, S = R - L + 1;
    vector<long long> art;
    art.push_back(1LL);
    art.push_back(L - 1LL);
    for (long long i = 1; i < S; i++) {
      art.push_back(i);
      art.push_back(L);
    }
    long long n2 = art.size();
    cout << "? " << n2;
    for (auto x : art) cout << " " << x;
    cout << endl;
    long long ll2;
    cin >> ll2;
    if (ll2 == -1) return 0;
    long long dd = 2 * S - 1 - ll2;
    long long W = L + dd;
    cout << "! " << W << endl;
  }
  return 0;
}