#include <bits/stdc++.h>
using namespace std;

int main() {
  map<int, long long> mp;
  cout << "walk 0" << endl;
  int start_label;
  cin >> start_label;
  mp[start_label] = 0;
  long long current_total = 0;
  const long long M = 40000;
  bool found = false;
  long long n = -1;
  for (long long i = 1; i <= M; ++i) {
    cout << "walk 1" << endl;
    int lab;
    cin >> lab;
    current_total += 1;
    if (mp.find(lab) != mp.end()) {
      n = current_total - mp[lab];
      found = true;
      break;
    }
    mp[lab] = current_total;
  }
  if (!found) {
    for (long long k = 1; k <= M; ++k) {
      cout << "walk " << M << endl;
      int lab;
      cin >> lab;
      current_total += M;
      if (mp.find(lab) != mp.end()) {
        n = current_total - mp[lab];
        found = true;
        break;
      }
    }
  }
  cout << "guess " << n << endl;
  return 0;
}