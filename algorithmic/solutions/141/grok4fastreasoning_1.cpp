#include <bits/stdc++.h>

using namespace std;

int main() {
  int n, k;
  cin >> n >> k;
  int count = 0;
  vector<char> res(n + 1);
  for (int i = 1; i <= n; i++) {
    cout << "? " << i << endl;
    cout.flush();
    char ch;
    cin >> ch;
    res[i] = ch;
    if (ch == 'N') count++;
  }
  vector<int> potential;
  for (int i = k + 1; i <= n; i++) {
    if (res[i] == 'N') potential.push_back(i);
  }
  int decrement = 0;
  for (int p : potential) {
    int l = p - k;
    int num_batches = (l + k - 1) / k;
    bool covered = false;
    for (int b = 0; b < num_batches && !covered; b++) {
      cout << "R" << endl;
      cout.flush();
      cout << "? " << p << endl;
      cout.flush();
      char dummy;
      cin >> dummy;  // N
      int start = b * k + 1;
      int end = min(start + k - 1, l);
      for (int j = start; j <= end; j++) {
        cout << "? " << j << endl;
        cout.flush();
        char ch;
        cin >> ch;
        if (ch == 'Y') {
          covered = true;
          break;
        }
      }
    }
    if (covered) decrement++;
  }
  int d = count - decrement;
  cout << "! " << d << endl;
  cout.flush();
  return 0;
}