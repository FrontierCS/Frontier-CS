#include <bits/stdc++.h>
using namespace std;

int n;

void find_diamond(int L, int R) {
  if (L > R) return;
  if (L == R) {
    cout << "? " << L << endl;
    int a0, a1;
    cin >> a0 >> a1;
    if (a0 == 0 && a1 == 0) {
      cout << "! " << L << endl;
      exit(0);
    }
    return;
  }
  int mid = L + (R - L) / 2;
  cout << "? " << mid << endl;
  int a0, a1;
  cin >> a0 >> a1;
  if (a0 == 0 && a1 == 0) {
    cout << "! " << mid << endl;
    exit(0);
  }
  if (a0 == 0) {
    find_diamond(mid + 1, R);
  } else if (a1 == 0) {
    find_diamond(L, mid - 1);
  } else {
    if (a0 <= a1) {
      find_diamond(L, mid - 1);
      find_diamond(mid + 1, R);
    } else {
      find_diamond(mid + 1, R);
      find_diamond(L, mid - 1);
    }
  }
}

int main() {
  ios::sync_with_stdio(false);
  cin.tie(NULL);
  cin >> n;
  find_diamond(0, n - 1);
  cout << "! 0" << endl;
  return 0;
}