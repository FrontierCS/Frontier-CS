#include <bits/stdc++.h>

using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int n, m;
  cin >> n >> m;
  vector<int> mistakes(n, 0);
  for (int t = 0; t < m; t++) {
    string s;
    cin >> s;
    int min_mist = *min_element(mistakes.begin(), mistakes.end());
    int count0 = 0, count1 = 0;
    for (int i = 0; i < n; i++) {
      if (mistakes[i] == min_mist) {
        if (s[i] == '0') count0++;
        else count1++;
      }
    }
    int P = (count1 > count0) ? 1 : 0;
    cout << P << '\n';
    cout.flush();
    int A;
    cin >> A;
    for (int i = 0; i < n; i++) {
      int pred = s[i] - '0';
      if (pred != A) mistakes[i]++;
    }
  }
  return 0;
}