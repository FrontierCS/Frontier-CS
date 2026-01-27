#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(nullptr);
  int t;
  cin >> t;
  for (int test = 0; test < t; ++test) {
    int n;
    cin >> n;
    int rep = 1;
    int impostor = -1;
    bool found = false;
    for (int kk = 2; kk <= n; ++kk) {
      int k = kk;
      // ask ? rep k
      cout << "? " << rep << " " << k << endl;
      cout.flush();
      int a;
      cin >> a;
      if (a == -1) return 0;
      // ask ? k rep
      cout << "? " << k << " " << rep << endl;
      cout.flush();
      int b;
      cin >> b;
      if (b == -1) return 0;
      if (a != b) {
        // asymmetric, resolve with m
        int m = (n >= 3 && (rep != 3 && k != 3)) ? 3 : ((rep != 2 && k != 2) ? 2 : 4 % n + 1);
        if (m == rep || m == k) m = (rep + k + 1) % n + 1;
        if (m < 1 || m > n || m == rep || m == k) m = 3; // fallback
        // ask ? rep m
        cout << "? " << rep << " " << m << endl;
        cout.flush();
        int a2;
        cin >> a2;
        if (a2 == -1) return 0;
        // ask ? m rep
        cout << "? " << m << " " << rep << endl;
        cout.flush();
        int b2;
        cin >> b2;
        if (b2 == -1) return 0;
        if (a2 != b2) {
          // rep is impostor
          impostor = rep;
        } else {
          // k is impostor
          impostor = k;
        }
        found = true;
        break;
      }
    }
    if (!found) {
      // impossible, pick rep
      impostor = rep;
    }
    cout << "! " << impostor << endl;
    cout.flush();
  }
  return 0;
}