#include <bits/stdc++.h>
using namespace std;

int main() {
  int n;
  cin >> n;
  vector<vector<int>> cnt(n+1, vector<int>(n+1, 0));
  for(int i=1; i<=n; i++) {
    for(int j=0; j<n; j++) {
      int x;
      cin >> x;
      cnt[i][x]++;
    }
  }
  bool issolid = true;
  for(int i=1; i<=n; i++) {
    if(cnt[i][i] != n) issolid = false;
  }
  if(issolid) {
    cout << 0 << endl;
    return 0;
  }
  vector<vector<int>> ops;
  int maxops = n * (n - 1);
  for(int opnum=0; opnum < maxops; opnum++) {
    vector<int> pass(n+1);
    for(int p=1; p<=n; p++) {
      int max_rem = -1;
      int ch_v = -1;
      for(int v=1; v<=n; v++) {
        if(cnt[p][v] > 0) {
          int rem = (v - p + n) % n;
          if(rem > 0 && rem > max_rem) {
            max_rem = rem;
            ch_v = v;
          }
        }
      }
      if(ch_v != -1) {
        pass[p] = ch_v;
      } else {
        pass[p] = p;
      }
    }
    for(int p=1; p<=n; p++) {
      int v = pass[p];
      cnt[p][v]--;
      int np = (p == n ? 1 : p+1);
      cnt[np][v]++;
    }
    vector<int> thisop;
    for(int p=1; p<=n; p++) thisop.push_back(pass[p]);
    ops.push_back(thisop);
    issolid = true;
    for(int i=1; i<=n; i++) {
      if(cnt[i][i] != n) {
        issolid = false;
        break;
      }
    }
    if(issolid) break;
  }
  cout << ops.size() << endl;
  for(auto& op : ops) {
    for(int j=0; j<n; j++) {
      cout << op[j];
      if(j < n-1) cout << " ";
      else cout << endl;
    }
  }
  return 0;
}