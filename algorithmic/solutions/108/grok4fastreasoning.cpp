#include <bits/stdc++.h>
using namespace std;

int main() {
  int n, m;
  cin >> n >> m;
  int S = n * m;
  vector<int> a(S);
  for (int t = 0; t < S; t++) {
    cout << "? 0 1" << endl;
    cout.flush();
    cin >> a[t];
  }
  cout << "? 0 1" << endl;
  cout.flush();
  int a_extra;
  cin >> a_extra;
  vector<int> delta(S);
  for (int t = 0; t < S - 1; t++) {
    delta[t] = a[t + 1] - a[t];
  }
  delta[S - 1] = a_extra - a[S - 1];
  vector<int> cov(S, 0);
  for (int r = 0; r < m; r++) {
    vector<int> chain(n);
    bool valid = true;
    chain[0] = 0;
    for (int kk = 0; kk < n - 1; kk++) {
      long long jm = (r + 1LL * kk * m) % S;
      int j = jm;
      int nextv = chain[kk] + delta[j];
      if (nextv < 0 || nextv > 1) {
        valid = false;
        break;
      }
      chain[kk + 1] = nextv;
    }
    long long jlast = (r + 1LL * (n - 1) * m) % S;
    int jl = jlast;
    int close = chain[n - 1] + delta[jl];
    if (close != chain[0]) valid = false;
    if (valid) {
      for (int kk = 0; kk < n; kk++) {
        long long jm = (r + 1LL * kk * m) % S;
        int j = jm;
        cov[j] = chain[kk];
      }
    } else {
      valid = true;
      chain[0] = 1;
      for (int kk = 0; kk < n - 1; kk++) {
        long long jm = (r + 1LL * kk * m) % S;
        int j = jm;
        int nextv = chain[kk] + delta[j];
        if (nextv < 0 || nextv > 1) {
          valid = false;
          break;
        }
        chain[kk + 1] = nextv;
      }
      long long jlast = (r + 1LL * (n -