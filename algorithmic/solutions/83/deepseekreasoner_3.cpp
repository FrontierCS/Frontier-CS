#include <bits/stdc++.h>
using namespace std;

typedef long long ll;

struct SegmentTree {
    vector<ll> maxv, minv, lazy;
    int n;
    SegmentTree(int size) {
        n = size;
        int sz = 4 * n + 5;
        maxv.assign(sz, 0);
        minv.assign(sz, 0);
        lazy.assign(sz, 0);
    }
    void build(int idx, int l, int r) {
        if (l == r) {
            maxv[idx] = minv[idx] = l;   // S[l] = l
            return;
        }
        int mid = (l + r) / 2;
        build(idx * 2, l, mid);
        build(idx * 2 + 1, mid + 1, r);
        maxv[idx] = max(maxv[idx * 2], maxv[idx * 2 + 1]);
        minv[idx] = min(minv[idx * 2], minv[idx * 2 + 1]);
    }
    void push(int idx) {
        if (lazy[idx] != 0) {
            maxv[idx * 2] += lazy[idx];
            minv[idx * 2] += lazy[idx];
            lazy[idx * 2] += lazy[idx];
            maxv[idx * 2 + 1] += lazy[idx];
            minv[idx * 2 + 1] += lazy[idx];
            lazy[idx * 2 + 1] += lazy[idx];
            lazy[idx] = 0;
        }
    }
    void range_add(int idx, int l, int r, int ql, int qr, ll val) {
        if (ql <= l && r <= qr) {
            maxv[idx] += val;
            minv[idx] += val;
            lazy[idx] += val;
            return;
        }
        push(idx);
        int mid = (l + r) / 2;
        if (ql <= mid) range_add(idx * 2, l, mid, ql, qr, val);
        if (qr > mid) range_add(idx * 2 + 1, mid + 1, r, ql, qr, val);
        maxv[idx] = max(maxv[idx * 2], maxv[idx * 2 + 1]);
        minv[idx] = min(minv[idx * 2], minv[idx * 2 + 1]);
    }
    void range_add(int l, int r, ll val) {
        if (l > r) return;
        range_add(1, 1, n, l, r, val);
    }
    ll get_max() { return maxv[1]; }
    ll get_min() { return minv[1]; }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int n;
    cin >> n;

    // sieve primes up to n
    vector<bool> is_prime(n + 1, true);
    vector<int> primes;
    is_prime[0] = is_prime[1] = false;
    for (int i = 2; i <= n; ++i) {
        if (is_prime[i]) {
            primes.push_back(i);
            if (i * 1LL * i <= n) {
                for (int j = i * i; j <= n; j += i)
                    is_prime[j] = false;
            }
        }
    }

    // for each prime, list of indices i where v_p(i) is odd
    vector<vector<int>> lists(primes.size());
    for (size_t idx = 0; idx < primes.size(); ++idx) {
        int p = primes[idx];
        ll pe = p;
        for (int e = 1; pe <= n; ++e, pe *= p) {
            if (e % 2 == 1) {   // odd exponent
                ll base = pe;
                // j such that j * base <= n and p does not divide j
                for (ll j = 1; j * base <= n; ++j) {
                    if (j % p != 0) {
                        lists[idx].push_back((int)(j * base));
                    }
                }
            }
        }
    }

    // f[i] = 1 or -1, initially all 1
    vector<char> f(n + 1, 1);
    f[1] = 1;

    // segment tree for partial sums S (S[k] = sum_{i=1..k} f[i])
    SegmentTree seg(n);
    seg.build(1, 1, n);

    // process primes in decreasing order
    for (int idx = (int)primes.size() - 1; idx >= 0; --idx) {
        int p = primes[idx];
        vector<int>& lst = lists[idx];
        if (lst.empty()) continue;

        ll cur_max = seg.get_max();
        ll cur_min = seg.get_min();
        ll cur_absmax = max(cur_max, -cur_min);

        // try flipping this prime (i.e., set f(p) = -1)
        for (int i : lst) {
            int old = f[i];               // 1 or -1
            ll delta = -2LL * old;
            f[i] = -old;
            seg.range_add(i, n, delta);
        }

        ll new_max = seg.get_max();
        ll new_min = seg.get_min();
        ll new_absmax = max(new_max, -new_min);

        if (new_absmax < cur_absmax) {
            // keep the flip
            continue;
        } else {
            // revert the flip
            for (int i : lst) {
                int old = f[i];           // now it's -original
                ll delta = -2LL * old;    // = 2 * original
                f[i] = -old;
                seg.range_add(i, n, delta);
            }
        }
    }

    // output f[1..n]
    for (int i = 1; i <= n; ++i) {
        cout << (int)f[i] << " \n"[i == n];
    }

    return 0;
}