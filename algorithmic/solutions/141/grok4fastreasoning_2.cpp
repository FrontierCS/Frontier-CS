#include <bits/stdc++.h>

using namespace std;

int main() {
  int n, k;
  cin >> n >> k;
  vector<vector<int>> groups;
  int distinct = 0;
  for(int c = 1; c <= n; c++) {
    bool is_new = true;
    for(const auto& group : groups) {
      // load group
      for(int r : group) {
        cout << "? " << r << endl;
        cout.flush();
        char dummy;
        cin >> dummy;
      }
      // now query c
      cout << "? " << c << endl;
      cout.flush();
      char res;
      cin >> res;
      if(res == 'Y') {
        is_new = false;
        break;
      }
    }
    if(is_new) {
      distinct++;
      if(groups.empty() || groups.back().size() == k) {
        groups.emplace_back();
      }
      groups.back().push_back(c);
    }
  }
  cout << "! " << distinct << endl;
  cout.flush();
  return 0;
}