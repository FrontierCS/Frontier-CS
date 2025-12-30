#include <bits/stdc++.h>
using namespace std;

int main() {
  int t;
  cin >> t;
  for(int test = 0; test < t; test++) {
    int n;
    cin >> n;
    int x = n - 3;
    vector<int> remaining;
    for(int i = 0; i < n; i++) remaining.push_back(i);
    int high_pen = -1;
    while(true) {
      int pen = remaining.back();
      remaining.pop_back();
      bool survived = true;
      for(int q = 0; q < x; q++) {
        cout << 0 << " " << pen << endl;
        int res;
        cin >> res;
        if(res == 0) {
          survived = false;
          break;
        }
      }
      if(survived) {
        high_pen = pen;
        break;
      }
    }
    int p1 = remaining[0];
    int p2 = remaining[1];
    cout << 1 << " " << p1 << " " << p2 << endl;
  }
  return 0;
}