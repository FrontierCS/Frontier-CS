#include <bits/stdc++.h>
using namespace std;

int main() {
  int n;
  cin >> n;
  vector<int> spf(n+1);
  for(int i = 0; i <= n; i++) spf[i] = i;
  for(long long i = 2; i * i <= n; i++) {
    if(spf[i] == i) {
      for(long long j = i * i; j <= n; j += i) {
        if(spf[j] == j) spf[j] = i;
      }
    }
  }
  vector<int> primes;
  for(int i = 2; i <= n; i++) {
    if(spf[i] == i) primes.push_back(i);
  }
  vector<int> f_prime(n+1, 0);
  vector<int> f(n+1, 0);
  long long S = 0;
  f[1] = 1;
  S += 1;
  int prime_idx = 0;
  int pos = 2;
  while(pos <= n) {
    int p = primes[prime_idx];
    int q = (prime_idx + 1 < (int)primes.size() ? primes[prime_idx + 1] : n + 1);
    pair<int, int> best_cost = {INT_MAX, INT_MAX};
    int best_s = 0;
    for(int trial : {1, -1}) {
      f_prime[p] = trial;
      long long seg_S = 0;
      int this_max = 0;
      seg_S += trial;
      int absn = abs(S + seg_S);
      this_max = max(this_max, absn);
      int temp_j = p + 1;
      for(int j = p + 1; j < q && j <= n; j++) {
        int x = j;
        int total_exp = 0;
        while(x > 1) {
          int pp = spf[x];
          int v = 0;
          while(x % pp == 0) {
            x /= pp;
            v++;
          }
          if(f_prime[pp] == -1) {
            total_exp += v;
          }
        }
        int fj = (total_exp % 2 == 0 ? 1 : -1);
        seg_S += fj;
        absn = abs(S + seg_S);
        this_max = max(this_max, absn);
      }
      int final_abs = abs(S + seg_S);
      pair<int, int> cost = {this_max, final_abs};
      if(cost < best_cost) {
        best_cost = cost;
        best_s = trial;
      }
    }
    f_prime[p] = best_s;
    f[p] = best_s;
    S += best_s;
    for(int j = p + 1; j < q && j <= n; j++) {
      int x = j;
      int total_exp = 0;
      while(x > 1) {
        int pp = spf[x];
        int v = 0;
        while(x % pp == 0) {
          x /= pp;
          v++;
        }
        if(f_prime[pp] == -1) {
          total_exp += v;
        }
      }
      f[j] = (total_exp % 2 == 0 ? 1 : -1);
      S += f[j];
    }
    pos = q;
    prime_idx++;
  }
  for(int i = 1; i <= n; i++) {
    if(i > 1) cout << " ";
    cout << f[i];
  }
  cout << endl;
  return 0;
}