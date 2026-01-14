#include <bits/stdc++.h>
using namespace std;

int main() {
  int t;
  cin >> t;
  for (int test = 0; test < t; test++) {
    int n;
    cin >> n;
    int K = 1;
    cout << K << endl;
    cout.flush();
    vector<int> P(n + 1, 0);
    int query_count = 0;
    for (int pos = 1; pos <= n; pos++) {
      vector<int> possible;
      for (int y = 1; y <= n; y++) if (y != pos) possible.push_back(y);
      sort(possible.begin(), possible.end());
      int mm = possible.size();
      vector<int> res(mm);
      for (int jj = 0; jj < mm; jj++) {
        int y = possible[jj];
        vector<int> q(n + 1);
        q[1] = y;
        q[2] = pos;
        vector<int> remain;
        for (int z = 1; z <= n; z++) if (z != pos && z != y) remain.push_back(z);
        sort(remain.begin(), remain.end());
        for (int ii = 0; ii < remain.size(); ii++) {
          q[3 + ii] = remain[ii];
        }
        cout << "?";
        for (int ii = 1; ii <= n; ii++) {
          cout << " " << q[ii];
        }
        cout << endl;
        cout.flush();
        int r;
        cin >> r;
        if (r == -1) return 0;
        res[jj] = r;
        query_count++;
        if (query_count > 10 * n) return 0;
      }
      int chosen = -1;
      for (int jj = 0; jj < mm; jj++) {
        vector<int> ss(mm);
        bool good = true;
        for (int m = 0; m < mm; m++) {
          if (m == jj) ss[m] = res[m];
          else ss[m] = res[m] - 1;
          if (ss[m] < 0) good = false;
        }
        if (!good) continue;
        for (int m = 1; m < mm && good; m++) {
          int step = ss[m] - ss[m - 1];
          if (step < 0 || step > 1) good = false;
        }
        if (good) {
          chosen = jj;
          break; // take the first
        }
      }
      assert(chosen != -1);
      P[pos] = possible[chosen];
    }
    cout << "!";
    for (int ii = 1; ii <= n; ii++) cout << " " << P[ii];
    cout << endl;
    cout.flush();
  }
  return 0;
}