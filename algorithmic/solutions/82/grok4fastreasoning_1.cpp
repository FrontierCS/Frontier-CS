#include <bits/stdc++.h>

using namespace std;

int main() {
  int n;
  cin >> n;
  vector<int> p(n + 1);
  vector<int> o(n + 1, 0);
  vector<int> op(n + 1, 0);
  // First star from 1
  for (int j = 2; j <= n; j++) {
    cout << "? 1 " << j << endl;
    cout.flush();
    int r;
    cin >> r;
    if (r == -1) return 0;
    o[j] = r;
  }
  // Find m1
  vector<int> freq(2048, 0);
  for (int j = 2; j <= n; j++) freq[o[j]]++;
  int m1 = -1;
  for (int mm = 0; mm < n; mm++) {
    vector<int> expected(2048, 0);
    for (int x = 0; x < n; x++) {
      if (x == mm) continue;
      int y = (mm | x);
      expected[y]++;
    }
    bool good = true;
    for (int y = 0; y < 2048; y++) {
      if (expected[y] != freq[y]) {
        good = false;
        break;
      }
    }
    if (good) {
      m1 = mm;
      break;
    }
  }
  p[1] = m1;
  // Second star from 2
  for (int j = 1; j <= n; j++) {
    if (j == 2) continue;
    cout << "? 2 " << j << endl;
    cout.flush();
    int r;
    cin >> r;
    if (r == -1) return 0;
    op[j] = r;
  }
  // Find m2
  vector<int> freq2(2048, 0);
  for (int j = 1; j <= n; j++) {
    if (j != 2) freq2[op[j]]++;
  }
  int m2 = -1;
  for (int mm = 0; mm < n; mm++) {
    vector<int> expected(2048, 0);
    for (int x = 0; x < n; x++) {
      if (