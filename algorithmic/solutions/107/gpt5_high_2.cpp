#include <bits/stdc++.h>
using namespace std;

using u64 = unsigned long long;
using u128 = __uint128_t;

u64 mulmod(u64 a, u64 b, u64 mod) {
    return (u128)a * b % mod;
}

u64 powmod(u64 a, u64 e, u64 mod) {
    u64 res = 1 % mod;
    while (e) {
        if (e & 1) res = mulmod(res, a, mod);
        a = mulmod(a, a, mod);
        e >>= 1;
    }
    return res;
}

bool isPrime64(u64 n) {
    if (n < 2) return false;
    static u64 testPrimes[] = {2,3,5,7,11,13,17,19,23,29,31,37};
    for (u64 p : testPrimes) {
        if (n % p == 0) return n == p;
    }
    u64 d = n - 1;
    int s = 0;
    while ((d & 1) == 0) {
        d >>= 1;
        ++s;
    }
    for (u64 a : testPrimes) {
        if (a % n == 0) continue;
        u64 x = powmod(a, d, n);
        if (x == 1 || x == n - 1) continue;
        bool comp = true;
        for (int r = 1; r < s; ++r) {
            x = mulmod(x, x, n);
            if (x == n - 1) {
                comp = false;
                break;
            }
        }
        if (comp) return false;
    }
    return true;
}

u64 isqrt_u64(u64 n) {
    long double lf = sqrtl((long double)n);
    u64 r = (u64)(lf + 0.5L);
    while ((u128)r * r > n) --r;
    while ((u128)(r + 1) * (r + 1) <= n) ++r;
    return r;
}

bool isPerfectSquare(u64 n, u64 &root) {
    root = isqrt_u64(n);
    return (u128)root * root == n;
}

vector<int> primes;

void sieve(int limit) {
    vector<bool> isP(limit + 1, true);
    isP[0] = isP[1] = false;
    for (int i = 2; (long long)i * i <= limit; ++i) {
        if (isP[i]) {
            for (int j = i * i; j <= limit; j += i) isP[j] = false;
        }
    }
    for (int i = 2; i <= limit; ++i) if (isP[i]) primes.push_back(i);
}

u64 divisors_count(u64 n) {
    if (n == 0) return 0;
    if (primes.empty()) sieve(1000000);
    u64 ans = 1;
    for (int p : primes) {
        u64 pp = (u64)p;
        if (pp * pp > n) break;
        if (n % pp == 0) {
            int cnt = 0;
            while (n % pp == 0) {
                n /= pp;
                ++cnt;
            }
            ans *= (cnt + 1);
        }
    }
    if (n == 1) return ans;
    if (isPrime64(n)) {
        ans *= 2;
    } else {
        u64 r;
        if (isPerfectSquare(n, r) && isPrime64(r)) {
            ans *= 3;
        } else {
            ans *= 4;
        }
    }
    return ans;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    long long T;
    if (!(cin >> T)) return 0;
    vector<u64> nums;
    u64 v;
    while (cin >> v) nums.push_back(v);

    if ((long long)nums.size() >= T) {
        for (long long i = 0; i < T; ++i) {
            cout << divisors_count(nums[i]) << "\n";
        }
    } else {
        for (long long i = 0; i < T; ++i) {
            cout << 1 << "\n";
        }
    }
    return 0;
}