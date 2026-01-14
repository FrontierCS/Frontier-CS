#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(NULL);
  int n;
  cin >> n;
  vector<vector<char>> parity(n + 1, vector<char>(n + 1, 0));
  vector<vector<char>> comp(n + 1, vector<char>(n + 1, 0));
  vector<vector<char>> pre(n + 1, vector<char>(n + 2, 0));
  for (int len = 2; len <= n; len++) {
    int d = len - 1;
    for (int i = 1; i <= n - d; i++) {
      int l = i;
      int r = i + d;
      cout << "0 " << l << " " << r << '\n';
      cout.flush();
      int resp;
      cin >> resp;
      parity[l][r] = resp;
      int temp = parity[l][r] ^ parity[l][r - 1];
      int iplus = l + 1;
      int px = pre[r][iplus];
      int xval = temp ^ px;
      comp[l][r] = xval;
      pre[r][l] = xval ^ px;
    }
  }
  vector<int> p(n + 1);
  for (int k = 1; k <= n; k++) {
    int smaller = 0;
    for (int m = 1; m < k; m++) {
      if (comp[m][k] == 0) smaller++;
    }
    for (int m = k + 1; m <= n; m++) {
      if (comp[k][m] == 1) smaller++;
    }
    p[k] = smaller + 1;
  }
  cout << "1";
  for (int i = 1; i <= n; i++) {
    cout << " " << p[i];
  }
  cout << '\n';
  cout.flush();
  return 0;
}