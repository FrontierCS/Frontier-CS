#include <bits/stdc++.h>

using namespace std;

int main() {
  int n;
  while (cin >> n) {
    vector<vector<int>> c(n, vector<int>(n));
    for (int i = 0; i < n; i++) {
      for (int j = 0; j < n; j++) {
        cin >> c[i][j];
      }
    }
    for (int i = 1; i <= n; i++) {
      if (i > 1) cout << " ";
      cout << i;
    }
    cout << endl;
  }
  return 0;
}