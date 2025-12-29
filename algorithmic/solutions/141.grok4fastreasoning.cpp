#include <bits/stdc++.h>

using namespace std;

int main() {
  int n, k;
  cin >> n >> k;
  vector<int> reps;
  int d = 0;
  for (int i = 1; i <= n; i++) {
    bool match = false;
    int num_groups = (reps.size() + k - 1) / k;
    for (int g = 0; g < num_groups; g++) {
      int start = g * k;
      int end = min(start + k, (int)reps.size());
      cout << "R" << endl;
      cout.flush();
      for (int j = start; j < end; j++) {
        cout << "? " << reps[j] << endl;
        cout.flush();
        char ch;
        cin >> ch;
      }
      cout << "? " << i << endl;
      cout.flush();
      char ch;
      cin >> ch;
      if (ch == 'Y') {
        match = true;
        break;
      }
    }
    if (!match) {
      reps.push_back(i);
      d++;
    }
  }
  cout << "! " << d << endl;
  cout.flush();
  return 0;
}