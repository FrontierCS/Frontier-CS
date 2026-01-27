#include <bits/stdc++.h>
using namespace std;

int main() {
  int n;
  cin >> n;
  vector<vector<int>> grid(n + 1, vector<int>(n + 1, -1));
  grid[1][1] = 1;
  grid[n][n] = 0;
  // Learn even s cells
  for (int sum = 4; sum <= 2 * n; sum += 2) {
    for (int i = max(1, sum - n); i <= min(n, sum - 1); i++) {
      int j = sum - i;
      if (grid[i][j] != -1) continue;
      bool found_pred = false;
      // Try (i-2, j)
      if (i - 2 >= 1 && grid[i - 2][j] != -1) {
        cout << "? " << (i - 2) << " " << j << " " << i << " " << j << endl;
        cout.flush();
        int ans;
        cin >> ans;
        grid[i][j] = (ans ? grid[i - 2][j] : 1 - grid[i - 2][j]);
        found_pred = true;
      }
      // Try (i, j-2)
      if (!found_pred && j - 2 >= 1 && grid[i][j - 2] != -1) {
        cout << "? " << i << " " << (j - 2) << " " << i << " " << j << endl;
        cout.flush();
        int ans;
        cin >> ans;
        grid[i][j] = (ans ? grid[i][j - 2] : 1 - grid[i][j - 2]);
        found_pred = true;
      }
      // Try (i-1, j-1)
      if (!found_pred && i - 1 >= 1 && j - 1 >= 1 && grid[i - 1][j - 1] != -1) {
        cout << "? " << (i - 1) << " " << (j -