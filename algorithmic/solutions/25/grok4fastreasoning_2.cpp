#include <bits/stdc++.h>
using namespace std;

int main() {
  int T;
  cin >> T;
  for (int t = 0; t < T; t++) {
    int n;
    cin >> n;
    vector<bool> inS(n + 1, false);
    vector<int> unreached;
    if (n >= 1) {
      inS[1] = true;
      int cur_size = 1;
      for (int i = 2; i <= n; i++) unreached.push_back(i);
      bool done = false;
      while (!done) {
        string ss(n, '0');
        for (int i = 1; i <= n; i++) if (inS[i]) ss[i - 1] = '1';
        cout << "? " << ss << endl;
        cout.flush();
        int k;
        cin >> k;
        if (k == 0) {
          if (cur_size == n) {
            cout << "! 1" << endl;
          } else {
            cout << "! 0" << endl;
          }
          cout.flush();
          done = true;
          continue;
        }
        int m = unreached.size();
        int lft = 0, rgt = m - 1;
        while (lft < rgt) {
          int md = (lft + rgt) / 2;
          vector<int> Lnd, Rnd;
          for (int p = lft; p <= md; p++) Lnd.push_back(unreached[p]);
          for (int p = md + 1; p <= rgt; p++) Rnd.push_back(unreached[p]);
          string sl(n, '0');
          for (int nd : Lnd) sl[nd - 1] = '1';
          cout << "? " << sl << endl;
          cout.flush();
          int q1;
          cin >> q1;
          string sr(n, '0');
          for (int nd : Rnd) sr[nd - 1] = '1';
          cout << "? " << sr << endl;
          cout.flush();
          int q3;
          cin >> q3;
          int sumdiff = k + q1 - q3;
          int a = sumdiff / 2;
          if (a > 0) {
            rgt = md;
          } else {
            lft = md + 1;
          }
        }
        int idx = lft;
        int x = unreached[idx];
        inS[x] = true;
        cur_size++;
        unreached.erase(unreached.begin() + idx);
      }
    } else {
      // n=0 impossible
    }
  }
  return 0;
}