#include <bits/stdc++.h>

using namespace std;

int main() {
  int n, l1, l2;
  cin >> n >> l1 >> l2;
  vector<int> is_connected(n - 1, 0);
  for (int i = 1; i < n; i++) {
    cout << "1 " << i << " " << i + 1 << endl;
    cout.flush();
    int x;
    cin >> x;
    is_connected[i - 1] = (x == 1);
  }
  vector<int> p(n + 1);
  int cur = 1;
  int i = 1;
  while (i <= n) {
    int start = i;
    i++;
    while (i <= n && is_connected[i - 2]) i++;
    int len = i - start;
    int high = cur + len - 1;
    for (int j = 0; j < len; j++) {
      p[start + j] = high - j;
    }
    cur += len;
  }
  cout << "3";
  for (int j = 1; j <= n; j++) {
    cout << " " << p[j];
  }
  cout << endl;
  cout.flush();
  return 0;
}