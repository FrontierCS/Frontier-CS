#include <bits/stdc++.h>
using namespace std;

int main() {
  ios::sync_with_stdio(false);
  cin.tie(0);
  map<long long, long long> first_seen;
  long long cur_total = 0;
  cout << "walk 0" << endl;
  long long cur_label;
  cin >> cur_label;
  first_seen[cur_label] = 0;
  const long long M = 50000LL;
  // baby steps: walk 1, M times, to positions 1 to M
  for (long long i = 1; i <= M; ++i) {
    cout << "walk 1" << endl;
    long long nl;
    cin >> nl;
    cur_total += 1;
    if (first_seen.count(nl)) {
      long long nn = cur_total - first_seen[nl];
      cout << "guess " << nn << endl;
      return 0;
    }
    first_seen[nl] = cur_total;
  }
  // now cur_total = M, seen 0 to M
  long long step_size = M;
  // giant steps, up to sufficient to cover 2n
  for (long long i = 1; i <= 100000LL; ++i) {  // safe upper limit
    cout << "walk " << step_size << endl;
    long long nl;
    cin >> nl;
    cur_total += step_size;
    if (first_seen.count(nl)) {
      long long nn = cur_total - first_seen[nl];
      cout << "guess " << nn << endl;
      return 0;
    }
    first_seen[nl] = cur_total;
  }
  // should not reach here
  cout << "guess 1" << endl;
  return 0;
}