#include <bits/stdc++.h>
using namespace std;

struct PairHash {
    size_t operator()(const pair<long long,long long>&p) const noexcept {
        return std::hash<long long>()((p.first<<32) ^ p.second);
    }
};

struct Solver {
    long long n;
    unordered_map<pair<long long,long long>, int, PairHash> cacheAsk;
    unordered_map<long long, long long> cacheF;

    long long addmod(long long a, long long k) {
        long long res = (a - 1 + k) % n;
        if (res < 0) res += n;
        return res + 1;
    }

    int ask(long long x, long long y) {
        if (x > y) swap(x, y);
        pair<long long,long long> key = {x, y};
        auto it = cacheAsk.find(key);
        if (it != cacheAsk.end()) return it->second;
        cout << "? " << x << " " << y << endl;
        cout.flush();
        int ans;
        if (!(cin >> ans)) exit(0);
        cacheAsk[key] = ans;
        return ans;
    }

    long long F(long long i) {
        auto it = cacheF.find(i);
        if (it != cacheF.end()) return it->second;
        long long val = 0;
        if (n % 2 == 0) {
            long long j = addmod(i, n/2);
            int d = ask(i, j);
            val = (long long)(n/2) - d;
        } else {
            long long m = n/2; // floor
            long long M = m + 1;
            long long j1 = addmod(i, m);
            long long j2 = addmod(i, M);
            int d1 = ask(i, j1);
            int d2 = ask(i, j2);
            val = (m - d1) + (M - d2);
        }
        cacheF[i] = val;
        return val;
    }

    long long find_peak() {
        long long l = 1, r = n;
        while (l < r) {
            long long mid = (l + r) >> 1;
            long long fmid = F(mid);
            long long fmid1 = F(mid + 1);
            if (fmid < fmid1) l = mid + 1;
            else r = mid;
        }
        return l;
    }

    void solve_one() {
        long long peak = find_peak();
        long long peakVal = F(peak);
        long long L;
        if (n % 2 == 0) L = peakVal + 1;
        else L = peakVal / 2 + 1;

        long long cand = addmod(peak, L);
        int d = ask(peak, cand);
        long long u = peak, v;
        if (d == 1) v = cand;
        else v = addmod(peak, -L);

        cout << "! " << u << " " << v << endl;
        cout.flush();
        int res;
        if (!(cin >> res)) exit(0);
        if (res == -1) exit(0);
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        Solver s;
        cin >> s.n;
        s.cacheAsk.reserve(4096);
        s.cacheF.reserve(1024);
        s.solve_one();
    }
    return 0;
}