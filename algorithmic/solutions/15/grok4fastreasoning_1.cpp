#include <bits/stdc++.h>
using namespace std;

int main() {
  int n;
  cin >> n;
  vector<int> current(n + 1);
  for (int i = 1; i <= n; i++) cin >> current[i];
  vector<pair<int, int>> ops;
  int pos1 = 0;
  for (int i = 1; i <= n; i++) if (current[i] == 1) pos1 = i;
  bool special = false;
  if (n == 3 && pos1 == 2) {
    special = true;
    if (current[1] > current[3]) {
      vector<int> temp(n + 1);
      temp[1] = current[3];
      temp[2] = current[2];
      temp[3] = current[1];
      current = temp;
      ops.emplace_back(1, 1);
    }
  } else if (pos1 != 1) {
    if (pos1 == 2) {
      int x = 1, y = n - 2;
      vector<int> temp(n + 1);
      int id = 1;
      for (int k = n - y + 1; k <= n; k++) temp[id++] = current[k];
      for (int k = x + 1; k <= n - y; k++) temp[id++] = current[k];
      for (int k = 1; k <= x; k++) temp[id++] = current[k];
      current = temp;
      ops.emplace_back(x, y);
      x = 1, y = 2;
      temp = vector<int>(n + 1);
      id = 1;
      for (int k = n - y + 1; k <= n; k++) temp[id++] = current[k];
      for (int k = x + 1; k <= n - y; k++) temp[id++] = current[k];
      for (int k = 1; k <= x; k++) temp[id++] = current[k];
      current = temp;
      ops.emplace_back(x, y);
    } else {
      int y = n - pos1 + 1;
      int x = 1;
      vector<int> temp(n + 1);
      int id = 1;
      for (int k = n - y + 1; k <= n; k++) temp[id++] = current[k];
      for (int k = x + 1; k <= n - y; k++) temp[id++] = current[k];
      for (int k = 1; k <= x; k++) temp[id++] = current[k];
      current = temp;
      ops.emplace_back(x, y);
    }
  }
  cout << ops.size() << endl;
  for (auto [x, y] : ops) cout << x << " " << y << endl;
  return 0;
}