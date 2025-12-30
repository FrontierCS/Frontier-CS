#include <bits/stdc++.h>
using namespace std;

int main() {
  ios_base::sync_with_stdio(false);
  cin.tie(NULL);
  int n;
  long long k;
  cin >> n >> k;
  vector<vector<long long>> mat(n+1, vector<long long>(n+1, -1LL));
  auto get_val = [&](int r, int c) -> long long {
    if (mat[r][c] != -1) return mat[r][c];
    cout << "QUERY " << r << " " << c << endl;
    cout.flush();
    long long v;
    cin >> v;
    mat[r][c] = v;
    return v;
  };
  auto count_leq = [&](long long x) -> long long {
    long long cnt = 0;
    int row = 1;
    int colu = n;
    while (row <= n && colu >= 1) {
      long long val = get_val(row, colu);
      if (val <= x) {
        cnt += colu;
        row++;
      } else {
        colu--;
      }
    }
    return cnt;
  };
  long long lo = 0;
  long long hi = 1000000000000000001LL;
  while (lo < hi) {
    long long mid = lo + (hi - lo) / 2;
    if (count_leq(mid) >= k) {
      hi = mid;
    } else {
      lo = mid + 1;
    }
  }
  cout << "DONE " << lo << endl;
  cout.flush();
  return 0;
}