#include <bits/stdc++.h>

using namespace std;

int main() {
  int n;
  cin >> n;
  vector<int> p(n+1);
  for(int i=1 ;i<=n ;i++) cin >> p[i];
  vector<pair<int, int>> ops;
  if(n ==3 ) {
    if(p[1] > p[3]) {
      ops.emplace_back(1,1);
    }
  } else {
    int j =0;
    for(int i=1 ;i<=n ;i++) if(p[i] ==1 ) j =i;
    if(j !=1 ) {
      if(j ==2 ) {
        ops.emplace_back(2,1);
        vector<int> newp(n+1);
        int idx=1;
        for(int i =n-1 +1 ;i<=n ;i++) newp[idx++] = p[i];
        for(int i