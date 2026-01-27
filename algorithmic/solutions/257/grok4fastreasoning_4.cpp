#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int n;
  cin >> n;
  vector<long long> arr(n + 1);
  int pos = 1;
  while (pos <= n) {
    long long v;
    int ff;
    cout << "? " << pos << " " << pos << '\n';
    cout.flush();
    cin >> v >> ff;
    int low = pos, high = n;
    int endd = pos - 1;
    while (low <= high) {
      int mid = low + (high - low) / 2;
      cout << "? " << pos << " " << mid << '\n';
      cout.flush();
      long long mx;
      int mf;
      cin >> mx >> mf;
      if (mx == v && mf == mid - pos + 1) {
        endd = mid;
        low = mid + 1;
      } else {
        high = mid - 1;
      }
    }
    for (int i = pos; i <= endd; i++) {
      arr[i] = v;
    }
    pos = endd + 1;
  }
  cout << "!";
  for (int i = 1; i <= n; i++) {
    cout << " " << arr[i];
  }
  cout << '\n';
  cout.flush();
  return 0;
}