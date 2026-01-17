#include <bits/stdc++.h>
using namespace std;

int main() {
  int D;
  cin >> D;
  int current = D;
  while (current > 0) {
    bool found = false;
    for (int c = 0; c < 3; c++) {
      cout << "move " << c << endl;
      int res;
      cin >> res;
      if (res == 1) {
        return 0;
      }
      int new_d;
      if (current == 1) {
        new_d = 2;
      } else {
        cout << "query" << endl;
        cin >> new_d;
      }
      if (new_d == current - 1) {
        current = new_d;
        found = true;
        break;
      } else {
        cout << "move " << c << endl;
        int res2;
        cin >> res2;
      }
    }
    assert(found);
  }
  return 0;
}