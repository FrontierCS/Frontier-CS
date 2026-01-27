#include <bits/stdc++.h>

using namespace std;

int main() {
  int n;
  cin >> n;
  int MASK = (1 << 11) - 1;
  auto query = [&](int i, int j) -> int {
    cout << "? " << i << " " << j << endl;
    cout.flush();
    int res;
    cin >> res;
    if (res == -1) {
      exit(0);
    }
    return res;
  };
  vector<int> p(n + 1);
  int ref1 = 1;
  vector<int> o1(n + 1, 0);
  for (int j = 1; j <= n; j++) if (j != ref1) o1[j] = query(ref1, j);
  int and1 = MASK;
  for (int j = 1; j <= n; j++) if (j != ref1) and1 &= o1[j];
  p[ref1] = and1;
  int ref2 = 2;
  vector<int> o2(n + 1, 0);
  o2[ref1] = o1[ref2];
  for (int j = 1; j <= n; j++) if (j != ref2 && j != ref1) o2[j] = query(ref2, j);
  int and2 = MASK;
  for (int j = 1; j <= n; j++) if (j != ref2) and2 &= o2[j];
  p[ref2] = and2;
  int common = p[ref1] & p[ref2];
  int not_common = MASK ^ common;
  set<int> remaining;
  for (int i = 0; i < n; i++) remaining.insert(i);
  remaining.erase(p[ref1]);
  remaining.erase(p[ref2]);
  for (int k = 1; k <= n; k++) if (k != ref1 && k != ref2) {
    int b = (o1[k] & (MASK ^ p[ref1])) | (o2[k] & (MASK ^ p[ref2]));
    auto it = remaining.begin();
    bool found = false;
    while (it != remaining.end()) {
      int v = *it;
      if ((v & not_common) == b) {
        p[k] = v;
        remaining.erase(it);
        found = true;
        break;
      }
      ++it;
    }
    assert(found);
  }
  cout << "!";
  for (int i = 1; i <= n; i++) cout << " " << p[i];
  cout << endl;
  cout.flush();
  return 0;
}