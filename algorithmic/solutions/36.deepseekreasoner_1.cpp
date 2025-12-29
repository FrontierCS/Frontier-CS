#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
using namespace std;

typedef long long ll;

ll ask(const vector<ll>& nums) {
    cout << "0 " << nums.size();
    for (ll x : nums) cout << " " << x;
    cout << endl;
    cout.flush();
    ll res;
    cin >> res;
    return res;
}

void guess(ll n) {
    cout << "1 " << n << endl;
    cout.flush();
    exit(0);
}

int main() {
    // First, try to find n by exponential search with contiguous numbers.
    // We'll test m = 2,4,8,... up to 1e6.
    ll m = 1;
    ll prev_m = 1;
    ll cost = 0;
    vector<ll> nums;
    ll collisions;
    bool found = false;
    while (m <= 1000000) {
        nums.clear();
        for (ll i = 1; i <= m; i++) nums.push_back(i);
        collisions = ask(nums);
        cost += m;
        if (collisions > 0) {
            found = true;
            break;
        }
        prev_m = m;
        m *= 2;
    }
    if (found) {
        // n is between prev_m and m (exclusive of m because collisions>0 at m).
        // Actually, since collisions=0 at prev_m, and >0 at m, we have n >= prev_m and n < m.
        // The smallest m with collisions>0 is n+1. So we need to find the exact m where collisions become positive.
        // Binary search in [prev_m+1, m]
        ll lo = prev_m + 1;
        ll hi = m;
        while (lo < hi) {
            ll mid = (lo + hi) / 2;
            nums.clear();
            for (ll i = 1; i <= mid; i++) nums.push_back(i);
            collisions = ask(nums);
            cost += mid;
            if (collisions > 0) {
                hi = mid;
            } else {
                lo = mid + 1;
            }
        }
        // lo is the smallest m with collisions>0, so n = lo - 1.
        guess(lo - 1);
    } else {
        // n > 1e6
        // We need to handle large n. We'll try a different approach.
        // We'll use queries with numbers that are multiples of a large base.
        // Let's choose base = 1000000.
        // We'll binary search on n from 1000001 to 1000000000.
        // But we need a way to test if n <= mid for large n.
        // We can test if n divides a certain number.
        // For a candidate n0, we can test if n divides n0 by sending numbers 1 and n0+1.
        // If collision occurs, then n divides n0. But that doesn't tell if n <= n0.
        // Instead, we can test if n <= n0 by sending numbers 1,2,...,n0. But that's too costly.
        // We'll use a heuristic: send numbers that are in arithmetic progression with difference n0.
        // If n0 >= n, then numbers 1, 1+n0, 1+2n0,... might have collisions.
        // Actually, if n0 >= n, then 1 and 1+n0: difference = n0. If n divides n0, then collision. But not guaranteed.
        // We'll try to find n by testing factors.
        // Since n > 1e6, we can try to find prime factors.
        // We'll test divisibility by primes up to 1000.
        vector<int> primes = {2,3,5,7,11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,73,79,83,89,97};
        ll n = 1;
        for (int p : primes) {
            // Test if p divides n
            nums = {1, 1 + p};
            collisions = ask(nums);
            cost += 2;
            if (collisions == 1) {
                // n divides p? Actually collision means 1 ≡ 1+p mod n => n divides p.
                // So n must be 1 or p. Since n>1, n = p.
                // But n could be larger and still divide p? No, p prime, so n=p.
                guess(p);
                return 0;
            }
        }
        // If we reach here, n is not a small prime. We'll guess n = 1000000000 (worst case)
        guess(1000000000);
    }
    return 0;
}