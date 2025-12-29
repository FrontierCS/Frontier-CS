#include <bits/stdc++.h>
using namespace std;

const int MAXN = 100000;
using BS = bitset<MAXN + 1>;

int trans(int s, bool isH) {
  if (isH) {
    return (s == 1 ? 2 : 1);
  } else {
    return (s == 3 ? 4 : 3);
  }
}

int main() {
  ios::sync_with_stdio(false);
  cin.tie(nullptr);
  int t;
  cin >> t;
  for (int test = 0; test < t; test++) {
    int n;
    cin >> n;
    array<BS, 5> poss;
    for (auto& b : poss) b.reset();
    for (int i = 1; i <= n; i++) poss[0].set(i);
    while (true) {
      BS total;
      total.reset();
      for (int s = 0; s < 5; s++) total |= poss[s];
      size_t num_pos = total.count();
      if (num_pos <= 2) {
        vector<int> cands;
        for (int i = 1; i <= n; i++) {
          if (total.test(i)) cands.push_back(i);
        }
        for (int a : cands) {
          cout << "! " << a << endl;
          cout.flush();
          int y;
          cin >> y;
        }
        cout << "#" << endl;
        cout.flush();
        break;
      }
      size_t half = num_pos / 2;
      size_t cum = 0;
      int m = n;
      for (int i = 1; i <= n; i++) {
        if (total.test(i)) cum++;
        if (cum >= half) {
          m = i;
          break;
        }
      }
      int len = m;
      cout << "? 1 " << m << endl;
      cout.flush();
      int x;
      cin >> x;
      bool claim_in = (x == len - 1);
      BS lmask;
      lmask.reset();
      for (int i = 1; i <= m; i++) lmask.set(i);
      BS rmask;
      rmask.reset();
      for (int i = m + 1; i <= n; i++) rmask.set(i);
      array<BS, 5> newp;
      for (auto& b : newp) b.reset();
      for (int s = 0; s < 5; s++) {
        BS P = poss[s];
        BS Pl = P & lmask;
        BS Pr = P & rmask;
        bool canH = (s == 0 || s == 1 || s == 3 || s == 4);
        bool canD = (s == 0 || s == 1 || s == 2 || s == 3);
        if (canH) {
          BS contrib = claim_in ? Pl : Pr;
          int ns = trans(s, true);
          newp[ns] |= contrib;
        }
        if (canD) {
          BS contrib = claim_in ? Pr : Pl;
          int ns = trans(s, false);
          newp[ns] |= contrib;
        }
      }
      poss = move(newp);
    }
  }
  return 0;
}