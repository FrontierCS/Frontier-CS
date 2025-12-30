#include <bits/stdc++.h>
using namespace std;

void search(long long la, long long ha, long long lb, long long hb) {
  if (la > ha || lb > hb) return;
  if (la == ha && lb == hb) {
    cout << la << " " << lb << endl;
    cout.flush();
    int r;
    cin >> r;
    if (r == 0) exit(0);
    return;
  }
  long long ma = la + (ha - la + 1LL) / 2;
  long long mb = lb + (hb - lb + 1LL) / 2;
  cout << ma << " " << mb << endl;
  cout.flush();
  int r;
  cin >> r;
  if (r == 0) exit(0);
  if (r == 1) {
    search(ma + 1, ha, lb, hb);
    return;
  }
  if (r == 2) {
    search(la, ha, mb + 1, hb);
    return;
  }
  // r == 3
  long long lefta = ma - la;
  if (lefta < 0) lefta = 0;
  long long leftb = mb - lb;
  if (leftb < 0) leftb = 0;
  __int128 sa = (__int128)lefta * (hb - lb + 1);
  __int128 sb = (__int128)(ha - la + 1) * leftb;
  bool a_first = (sa >= sb);
  long long new_ha = ma - 1;
  long long new_hb = mb - 1;
  if (a_first) {
    if (new_ha >= la) {
      search(la, new_ha, lb, hb);
    }
    if (new_hb >= lb) {
      search(la, ha, lb, new_hb);
    }
  } else {
    if (new_hb >= lb) {
      search(la, ha, lb, new_hb);
    }
    if (new_ha >= la) {
      search(la, new_ha, lb, hb);
    }
  }
}

int main() {
  long long n;
  cin >> n;
  search(1, n, 1, n);
  return 0;
}