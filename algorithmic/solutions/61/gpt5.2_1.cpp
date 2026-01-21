#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    size_t idx = 0, size = 0;
    unsigned char buf[BUFSIZE];

    inline unsigned char readChar() {
        if (idx >= size) {
            size = fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

    template <class T>
    bool readInt(T &out) {
        unsigned char c;
        do {
            c = readChar();
            if (!c) return false;
        } while (c <= ' ');

        bool neg = false;
        if (c == '-') {
            neg = true;
            c = readChar();
        }

        unsigned long long val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = readChar();
        }

        if constexpr (is_signed_v<T>) out = neg ? -(long long)val : (long long)val;
        else out = (T)val;
        return true;
    }
};

struct Solver {
    int n = 0;
    int m = 0;
    long long c = 0;

    vector<unsigned long long> s;   // prefix sums of a, size n+1
    vector<unsigned long long> P;   // prefix sums of b, size m+1 (possibly truncated)
    vector<long long> dp;           // dp over days, size n+1

    const unsigned long long* Pdata = nullptr;
    int Psz = 0;

    inline int level(unsigned long long x) const {
        // upper_bound(P, x) - 1 on [0..m]
        int l = 0, r = Psz;
        while (l < r) {
            int mid = (l + r) >> 1;
            if (Pdata[mid] <= x) l = mid + 1;
            else r = mid;
        }
        return l - 1;
    }

    inline long long value(int j, int i) const {
        unsigned long long diff = s[i] - s[j];
        int k = level(diff);
        return dp[j] + (long long)k - c;
    }

    inline int intersectFirst(int x, int y, int l) const {
        int low = l;
        if (low < x + 1) low = x + 1;
        if (low > n) return n + 1;

        if (value(x, low) >= value(y, low)) return low;
        if (value(x, n) < value(y, n)) return n + 1;

        int lo = low, hi = n;
        while (lo + 1 < hi) {
            int mid = (lo + hi) >> 1;
            if (value(x, mid) >= value(y, mid)) hi = mid;
            else lo = mid;
        }
        return hi;
    }

    long long solveOne() {
        dp.assign(n + 1, (long long)-4e18);
        dp[0] = 0;

        vector<int> q;
        vector<int> st;
        q.reserve(n + 1);
        st.reserve(n + 1);
        int head = 0;

        q.push_back(0);
        st.push_back(1);

        for (int i = 1; i <= n; i++) {
            while ((int)q.size() - head >= 2 && st[head + 1] <= i) head++;
            int best = q[head];
            dp[i] = value(best, i);

            int startPos = i + 1;
            while ((int)q.size() > head) {
                int last = q.back();
                int lastStart = st.back();
                int p = intersectFirst(i, last, lastStart);
                if (p <= lastStart) {
                    q.pop_back();
                    st.pop_back();
                } else {
                    startPos = p;
                    break;
                }
            }
            if ((int)q.size() == head) startPos = i + 1;
            if (startPos <= n) {
                q.push_back(i);
                st.push_back(startPos);
            }
        }

        return dp[n];
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int T;
    if (!fs.readInt(T)) return 0;

    Solver solver;
    while (T--) {
        fs.readInt(solver.n);
        fs.readInt(solver.m);
        fs.readInt(solver.c);

        solver.s.assign(solver.n + 1, 0);
        for (int i = 1; i <= solver.n; i++) {
            unsigned long long x;
            fs.readInt(x);
            solver.s[i] = solver.s[i - 1] + x;
        }
        unsigned long long totalA = solver.s[solver.n];

        solver.P.assign(solver.m + 1, 0);
        for (int i = 1; i <= solver.m; i++) {
            unsigned long long x;
            fs.readInt(x);
            solver.P[i] = solver.P[i - 1] + x;
        }

        // Truncate unreachable levels (diff <= totalA always)
        int mReach = (int)(upper_bound(solver.P.begin(), solver.P.end(), totalA) - solver.P.begin()) - 1;
        if (mReach < solver.m) {
            solver.m = mReach;
            solver.P.resize(solver.m + 1);
        }

        solver.Pdata = solver.P.data();
        solver.Psz = solver.m + 1;

        long long ans = solver.solveOne();
        cout << ans << '\n';
    }
    return 0;
}