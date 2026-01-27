#include <bits/stdc++.h>
using namespace std;

int main() {
  int n;
  cin >> n;
  auto query = [&](int u, long long kk, const vector<int>& SS) -> int {
    cout << "? " << u << " " << kk << " " << SS.size();
    for (int s : SS) cout << " " << s;
    cout << endl;
    cout.flush();
    int res;
    cin >> res;
    return res;
  };
  auto find_succ = [&](int u, long long kk) -> int {
    int lo = 1, hi = n;
    while (lo < hi) {
      int md = lo + (hi - lo) / 2;
      vector<int> SS(md);
      for (int i = 0; i < md; i++) SS[i] = i + 1;
      int res = query(u, kk, SS);
      if (res) hi = md;
      else lo = md + 1;
    }
    return lo;
  };
  long long BIG = n + 10LL;
  int cc = find_succ(1, BIG);
  vector<long long> pows;
  long long pp = 1;
  while (pp <= 2LL * n) {
    pows.push_back(pp);
    if (pp > (1LL << 60) / 2) break;
    pp *= 2;
  }
  set<int> reach;
  reach.insert(cc);
  for (auto thisk : pows) {
    vector<int> toq;
    for (int xx = 1; xx <= n; xx++) {
      if (reach.count(xx)) continue;
      toq.push_back(xx);
    }
    if (toq.empty()) break;
    vector<int> curr_list(reach.begin(), reach.end());
    vector<int> newa;
    for (int xx : toq) {
      int res = query(xx, thisk, curr_list);
      if (res) {
        newa.push_back(xx);
      }
    }
    for (int xx : newa) {
      reach.insert(xx);
    }
  }
  vector<int> ans(reach.begin(), reach.end());
  cout << "! " << ans.size();
  for (int x : ans) cout << " " << x;
  cout << endl;
  cout.flush();
  return 0;
}