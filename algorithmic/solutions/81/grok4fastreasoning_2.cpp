#include <bits/stdc++.h>
using namespace std;

int main() {
  int N;
  cin >> N;
  string ss(N, '?');
  for (int k = 0; k < N; k++) {
    int m = k + 3;
    vector<int> a(m, 0), b(m, 0);
    for (int i = 0; i < k; i++) {
      int bit = ss[i] - '0';
      if (bit == 0) {
        a[i] = i + 1;
        b[i] = 0;
      } else {
        b[i] = i + 1;
        a[i] = 0;
      }
    }
    int branch = k;
    int s0 = k + 1, s1 = k + 2;
    a[branch] = s0;
    b[branch] = s1;
    a[s0] = s0; b[s0] = s0;
    a[s1] = s1; b[s1] = s1;
    cout << 1 << endl;
    cout << m << endl;
    for (int i = 0; i < m; i++) {
      cout << a[i];
      if (i < m - 1) cout << " ";
      else cout << endl;
    }
    for (int i = 0; i < m; i++) {
      cout << b[i];
      if (i < m - 1) cout << " ";
      else cout << endl;
    }
    cout.flush();
    int res;
    cin >> res;
    if (res == s0) ss[k] = '0';
    else ss[k] = '1';
  }
  cout << 0 << endl;
  cout << ss << endl;
  return 0;
}