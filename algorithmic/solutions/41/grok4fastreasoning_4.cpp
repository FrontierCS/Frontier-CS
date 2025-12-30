#include <bits/stdc++.h>
using namespace std;

int main() {
  long long n;
  cin >> n;
  if (n == 1) {
    cout << 1 << endl << 1 << endl;
    return 0;
  }
  // sieve
  const int MAXP = 1000100;
  vector<bool> is_prime(MAXP + 1, true);
  is_prime[0] = is_prime[1] = false;
  for (long long i = 2; i <= MAXP; i++) {
    if (is_prime[i]) {
      for (long long j = i * i; j <= MAXP; j += i) {
        if (j > MAXP) break;
        is_prime[j] = false;
      }
    }
  }
  vector<long long> p;
  for (int i = 2; i <= MAXP; i++) {
    if (is_prime[i]) p.push_back(i);
  }
  // build seq
  vector<long long> seq;
  seq.push_back(1);
  if (2 <= n) {
    seq.push_back(2);
  }
  int prime_idx = 1;
  while (prime_idx < p.size()) {
    long long prod = p[prime_idx - 1] * p[prime_idx];
    if (prod > n) break;
    seq.push_back(prod);
    prime_idx++;
  }
  // add extra
  if (seq.size() >= 2) {
    long long last = seq.back();
    long long pre = seq[seq.size() - 2];
    long long gg = __gcd(last, pre);
    long long modd = last / gg;
    long long max_kk = n / modd;
    if (max_kk > gg) {
      long long extra = max_kk * modd;
      seq.push_back(extra);
    }
  }
  // powers of 2
  vector<long long> pow2;
  long long cur = 1;
  while (cur <= n) {
    pow2.push_back(cur);
    if (cur > (n >> 1)) break;
    cur <<= 1;
  }
  // choose better
  auto compute_v = [](const vector<long long>& s) -> long double {
    int kk = s.size();
    long long su = 0;
    for (auto x : s) su += x;
    return (long double)kk * su;
  };
  long double v1 = compute_v(seq);
  long double v2 = compute_v(pow2);
  vector<long long> best = (v1 > v2 ? seq : pow2);
  // output
  cout << best.size() << endl;
  for (size_t i = 0; i < best.size(); i++) {
    if (i > 0) cout << " ";
    cout << best[i];
  }
  cout << endl;
  return 0;
}