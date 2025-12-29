#include <bits/stdc++.h>
using namespace std;

static int ceilLog2_int(int x) {
    int k = 0;
    int p = 1;
    while (p < x) { p <<= 1; ++k; }
    return k;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<string> sval(n + 1);
    for (int i = 1; i <= n; ++i) sval[i] = to_string(i);

    long long sumNeeded = 0;
    for (int m = 2; m <= n; ++m) sumNeeded += ceilLog2_int(m);

    long long queryCount = 0;
    auto ask = [&](const vector<int>& a) -> int {
        static string out;
        out.clear();
        out.reserve((size_t)max(32, 3 + n * 6));
        out += '0';
        for (int i = 0; i < n; ++i) {
            out += ' ';
            out += sval[a[i]];
        }
        out += '\n';
        cout << out;
        cout.flush();

        int res;
        if (!(cin >> res)) exit(0);
        if (res < 0) exit(0);
        ++queryCount;
        return res;
    };

    auto answer = [&](const vector<int>& p) -> void {
        static string out;
        out.clear();
        out.reserve((size_t)max(32, 3 + n * 6));
        out += '1';
        for (int i = 0; i < n; ++i) {
            out += ' ';
            out += sval[p[i]];
        }
        out += '\n';
        cout << out;
        cout.flush();
        exit(0);
    };

    if (n == 1) {
        answer(vector<int>{1});
    }

    long long attemptsMax = max(1LL, 9999LL - sumNeeded);

    uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    seed ^= (uint64_t)(uintptr_t)&seed;
    mt19937 rng((uint32_t)seed);
    uniform_int_distribution<int> dist(1, n);

    vector<int> base(n);
    bool foundZero = false;
    for (long long att = 0; att < attemptsMax; ++att) {
        for (int i = 0; i < n; ++i) base[i] = dist(rng);
        int res = ask(base);
        if (res == 0) {
            foundZero = true;
            break;
        }
    }

    if (!foundZero) {
        // Extremely unlikely with the attempt budget; still try a bit more (may exceed scoring baseline, but aims for correctness).
        for (int extra = 0; extra < 5000; ++extra) {
            for (int i = 0; i < n; ++i) base[i] = dist(rng);
            int res = ask(base);
            if (res == 0) {
                foundZero = true;
                break;
            }
        }
        if (!foundZero) {
            // As a last resort, output something (likely wrong). This should never happen in practice.
            vector<int> p(n);
            iota(p.begin(), p.end(), 1);
            answer(p);
        }
    }

    vector<int> rem(n);
    iota(rem.begin(), rem.end(), 0);

    vector<int> perm(n, 0);
    vector<int> q(n);

    for (int v = 1; v <= n - 1; ++v) {
        int l = 0, r = (int)rem.size(); // [l, r)
        while (r - l > 1) {
            int mid = (l + r) >> 1;
            q = base;
            for (int i = l; i < mid; ++i) q[rem[i]] = v;
            int res = ask(q); // must be 0 or 1
            if (res == 1) r = mid;
            else l = mid;
        }
        int pos = rem[l];
        perm[pos] = v;
        rem.erase(rem.begin() + l);
    }

    perm[rem[0]] = n;
    answer(perm);
    return 0;
}