#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(nullptr);
  int n;
  cin >> n;
  set<int> cand;
  for (int i = 1; i <= n; ++i) cand.insert(i);
  while (cand.size() > 1) {
    int r = -1;
    for (int i = 1; i <= n; ++i) {
      if (cand.find(i) == cand.end()) {
        r = i;
        break;
      }
    }
    bool outside = (r != -1);
    if (!outside) {
      r = *cand.begin();
      cand.erase(r);
    }
    long long pr_and = (1LL << 11) - 1;
    map<int, long long> this_or;
    for (int i : cand) {
      cout << "? " << r << " " << i << endl;
      cout.flush();
      long long res;
      cin >> res;
      if (res == -1) return 0;
      this_or[i] = res;
      pr_and &= res;
    }
    long long pr = pr_and;
    set<int> new_cand;
    for (auto& p : this_or) {
      int i = p.first;
      long long o = p.second;
      if (o == pr) new_cand.insert(i);
    }
    if (!outside) {
      new_cand.insert(r);
    }
    cand = move(new_cand);
  }
  int pos0 = *cand.begin();
  vector<long long> perm(n + 1);
  perm[pos0] = 0;
  for (int i = 1; i <= n; ++i) {
    if (i == pos0) continue;
    cout << "? " << pos0 << " " << i << endl;
    cout.flush();
    long long res;
    cin >> res;
    if (res == -1) return 0;
    perm[i] = res;
  }
  cout << "!";
  for (int i = 1; i <= n; ++i) {
    cout << " " << perm[i];
  }
  cout << endl;
  cout.flush();
  return 0;
}