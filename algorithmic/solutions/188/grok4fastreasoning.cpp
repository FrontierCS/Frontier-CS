#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(NULL);
  string s1, s2;
  cin >> s1 >> s2;
  int N = s1.size(), M = s2.size();
  vector<int> pos1[256], pos2[256];
  for (int i = 0; i < N; i++) {
    pos1[(unsigned char)s1[i]].push_back(i);
  }
  for (int i = 0; i < M; i++) {
    pos2[(unsigned char)s2[i]].push_back(i);
  }
  // Z1: iterate s1 using pos2
  string Z1 = "";
  int current = -1;
  for (char ch : s1) {
    int c = (unsigned char)ch;
    auto& p = pos2[c];
    auto it = lower_bound(p.begin(), p.end(), current + 1);
    if (it != p.end()) {
      Z1 += ch;
      current = *it;
    }
  }
  // Z2: iterate s2 using pos1
  string Z2 = "";
  current = -1;
  for (char ch : s2) {
    int c = (unsigned char)ch;
    auto& p = pos1[c];
    auto it = lower_bound(p.begin(), p.end(), current + 1);
    if (it != p.end()) {
      Z2 += ch;
      current = *it;
    }
  }
  // output longer one
  if (Z1.size() >= Z2.size()) {
    cout << Z1 << endl;
  } else {
    cout << Z2 << endl;
  }
  return 0;
}