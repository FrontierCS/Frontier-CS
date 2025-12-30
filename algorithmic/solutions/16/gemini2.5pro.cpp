#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <map>

using namespace std;

long long n;
map<pair<long long, long long>, long long> memo;

long long query(long long x, long long y) {
    if (x == y) return 0;
    if (x > y) swap(x, y);
    if (memo.count({x, y})) {
        return memo[{x, y}];
    }
    cout << "? " << x << " " << y << endl;
    long long dist;
    cin >> dist;
    if (dist == -1) exit(0);
    return memo[{x, y}] = dist;
}

void solve() {
    cin >> n;
    memo.clear();

    long long p = -1;
    long long base = 1;

    long long first_k = -1;
    long long l = 1, r = n / 2;
    while(l <= r) {
        long long k = l + (r - l) / 2;
        if (k == 0) { l = k + 1; continue; }
        long long v1 = (base + k - 1 + n) % n + 1;
        long long v2 = (base - k - 1 + n) % n + 1;
        if (query(base, v1) < k || query(base, v2) < k) {
            first_k = k;
            r = k - 1;
        } else {
            l = k + 1;
        }
    }
    
    if (first_k != -1) {
        long long v1 = (base + first_k - 1 + n) % n + 1;
        if (query(base, v1) < first_k) {
            p = v1;
        } else {
            p = (base - first_k - 1 + n) % n + 1;
        }
    }

    if (p == -1) {
        base = 2;
        first_k = -1;
        l = 1, r = n / 2;
        while(l <= r) {
            long long k = l + (r-l)/2;
            if (k == 0) { l = k + 1; continue; }
            long long v1 = (base + k - 1 + n) % n + 1;
            long long v2 = (base - k - 1 + n) % n + 1;
            if (query(base, v1) < k || query(base, v2) < k) {
                first_k = k;
                r = k - 1;
            } else {
                l = k + 1;
            }
        }
        long long v1 = (base + first_k - 1 + n) % n + 1;
        if (query(base, v1) < first_k) {
            p = v1;
        } else {
            p = (base - first_k - 1 + n) % n + 1;
        }
    }

    long long d = query(base, p);
    long long q_dist = d - 1;

    long long q1 = (base + q_dist - 1 + n) % n + 1;
    long long q2 = (base - q_dist - 1 + n) % n + 1;
    
    if (query(p, q1) == 1) {
        if (p > q1) swap(p, q1);
        cout << "! " << p << " " << q1 << endl;
    } else {
        if (p > q2) swap(p, q2);
        cout << "! " << p << " " << q2 << endl;
    }

    int result;
    cin >> result;
    if (result == -1) {
        exit(0);
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int t;
    cin >> t;
    while (t--) {
        solve();
    }

    return 0;
}