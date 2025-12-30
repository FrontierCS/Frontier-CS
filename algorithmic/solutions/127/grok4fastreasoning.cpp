#include <bits/stdc++.h>
using namespace std;

int n;

pair<int, int> ask(int i) {
  cout << "? " << i << endl;
  cout.flush();
  int x, y;
  cin >> x >> y;
  return {x, y};
}

int find_diamond(int L, int R) {
  if (L > R) return -1;
  if (L == R) {
    auto [a0, a1] = ask(L);
    if (a0 == 0 && a1 == 0) return L;
    return -1;
  }
  int mid = L + (R - L) / 2;
  auto [a0, a1] = ask(mid);
  if (a0 == 0 && a1 == 0) return mid;
  int leftL = L, leftR = mid - 1;
  int rightL = mid + 1, rightR = R;
  if (a0 == 0) {
    return find_diamond(rightL, rightR);
  }
  if (a1 == 0) {
    return find_diamond(leftL, leftR);
  }
  // branch
  bool left_first;
  int left_size = (leftR >= leftL ? leftR - leftL + 1 : 0);
  int right_size = (rightR >= rightL ? rightR - rightL + 1 : 0);
  if (a0 < a1 || (a0 == a1 && left_size <= right_size)) {
    left_first = true;
  } else {
    left_first = false;
  }
  if (left_first) {
    int pos = find_diamond(leftL, leftR);
    if (pos != -1) return pos;
    return find_diamond(rightL, rightR);
  } else {
    int pos = find_diamond(rightL, rightR);
    if (pos != -1) return pos;
    return find_diamond(leftL, leftR);
  }
}

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  cin >> n;
  int pos = find_diamond(0, n - 1);
  if (pos == -1) pos = 0;
  cout << "! " << pos << endl;
  cout.flush();
  return 0;
}