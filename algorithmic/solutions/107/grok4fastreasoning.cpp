#include <bits/stdc++.h>
using namespace std;

int main() {
  vector<long long> primes;
  const int MAXL = 1000;
  vector<bool> is_prime(MAXL + 1, true);
  is_prime[0] = is_prime[1] = false;
  for (long long i = 2; i <= MAXL; i++) {
    if (is_prime[i]) {
      primes.push_back(i);
      for (long long j = i * i; j <= MAXL; j += i) {
        if (j > MAXL) break;
        is_prime[j] = false;
      }
    }
  }
  // group primes
  vector<vector<long long>> groups;
  vector<long long> group;
  __int128 prod = 1;
  for (auto p : primes) {
    __int128 nextp = prod * (__int128)p;
    if (nextp > (__int128)1000000000000000000LL) {
      if (!group.empty()) {
        groups.push_back(group);
        group.clear();
        prod = 1;
      }
      nextp = (__int128)p;
    }
    prod = nextp;
    group.push_back(p);
  }
  if (!group.empty()) groups.push_back(group);
  int T;
  cin >> T;
  for (int t = 0; t < T; t++) {
    set<long long> div_primes;
    for (auto& grp : groups) {
      long long Q = 1LL;
      for (auto p : grp) {
        Q *= p;
      }
      cout << "0 " << Q << endl;
      cout.flush();
      long long g;
      cin >> g;
      long long temp = g;
      for (auto p : grp) {
        if (temp % p == 0) {
          div_primes.insert(p);
          temp /= p;
        }
      }
    }
    long long num_div = 1LL;
    for (auto p : div_primes) {
      __int128 powp = 1;
      while (true) {
        __int128 next = powp * (__int128)p;
        if (next > (__int128)1000000000000000000LL) break;
        powp = next;
      }
      long long Q = (long long)powp;
      cout << "0 " << Q << endl;
      cout.flush();
      long long d;
      cin >> d;
      long long tempd = d;
      int a = 0;
      while (tempd % p == 0) {
        tempd /= p;
        a++;
      }
      num_div *= (a + 1LL);
    }
    long long ans = 2LL * num_div;
    cout << "1 " << ans << endl;
    cout.flush();
  }
  return 0;
}