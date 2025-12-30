#include <bits/stdc++.h>

using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  int N;
  cin >> N;
  vector<int> order(2 * N);
  for (int i = 0; i < 2 * N; i++) {
    order[i] = i + 1;
  }
  random_shuffle(order.begin(), order.end());
  vector<int> opens;
  for (int j = 0; j < 2 * N; j++) {
    int x = order[j];
    cout << "? " << x << endl;
    int r;
    cin >> r;
    if (r == (int) opens.size() + 1) {
      opens.push_back(x);
    } else {
      bool found = false;
      for (size_t i = 0; i < opens.size(); ++i) {
        int y = opens[i];
        cout << "? " << y << endl;
        int rt;
        cin >> rt;
        if (rt == (int) opens.size()) {
          cout << "? " << x << endl;
          int rtt;
          cin >> rtt;
          int a = min(x, y);
          int b = max(x, y);
          cout << "! " << a << " " << b << endl;
          opens.erase(opens.begin() + i);
          found = true;
          break;
        } else {
          cout << "? " << y << endl;
          int rb;
          cin >> rb;
        }
      }
      assert(found);
    }
  }
  assert(opens.empty());
  return 0;
}