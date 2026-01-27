#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    char buf[BUFSIZE];
    size_t idx = 0, size = 0;

    inline char readChar() {
        if (idx >= size) {
            size = fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

    template <class T>
    bool readInt(T &out) {
        char c;
        do {
            c = readChar();
            if (!c) return false;
        } while (c <= ' ');

        bool neg = false;
        if (c == '-') {
            neg = true;
            c = readChar();
        }

        T val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = readChar();
        }
        out = neg ? -val : val;
        return true;
    }
};

struct Cand {
    int idx;
    int start; // first i where this idx is optimal
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;

    int T;
    if (!fs.readInt(T)) return 0;

    string out;
    out.reserve((size_t)T * 16);

    while (T--) {
        int n, m;
        long long c;
        fs.readInt(n);
        fs.readInt(m);
        fs.readInt(c);

        vector<long long> prefA(n + 1, 0);
        for (int i = 1; i <= n; i++) {
            long long x;
            fs.readInt(x);
            prefA[i] = prefA[i - 1] + x;
        }

        // Build compressed (cost -> max level) arrays for requirements
        vector<long long> reqCost;
        vector<int> reqLvl;
        reqCost.reserve(m + 1);
        reqLvl.reserve(m + 1);

        reqCost.push_back(0);
        reqLvl.push_back(0);
        long long sumB = 0;
        for (int i = 1; i <= m; i++) {
            long long bi;
            fs.readInt(bi);
            sumB += bi;
            if (sumB == reqCost.back()) {
                reqLvl.back() = i;
            } else {
                reqCost.push_back(sumB);
                reqLvl.push_back(i);
            }
        }
        int K = (int)reqCost.size() - 1;

        auto level = [&](long long exp) -> int {
            // max level with reqCost[level] <= exp, returning corresponding reqLvl
            int lo = 0, hi = K;
            while (lo < hi) {
                int mid = (lo + hi + 1) >> 1;
                if (reqCost[mid] <= exp) lo = mid;
                else hi = mid - 1;
            }
            return reqLvl[lo];
        };

        vector<long long> dp(n + 1, 0);

        deque<Cand> hull;
        hull.push_back({0, 1});

        auto value = [&](int j, int i) -> long long {
            long long diff = prefA[i] - prefA[j];
            int lv = level(diff);
            return dp[j] + (long long)lv;
        };

        auto betterEq = [&](int jNew, int jOld, int i) -> bool {
            return value(jNew, i) >= value(jOld, i);
        };

        auto findStart = [&](int jOld, int jNew, int lo) -> int {
            if (lo > n) return n + 1;
            if (!betterEq(jNew, jOld, n)) return n + 1;
            int l = lo, r = n;
            while (l < r) {
                int mid = (l + r) >> 1;
                if (betterEq(jNew, jOld, mid)) r = mid;
                else l = mid + 1;
            }
            return l;
        };

        for (int i = 1; i <= n; i++) {
            while ((int)hull.size() >= 2 && hull[1].start <= i) hull.pop_front();
            int bestJ = hull.front().idx;
            dp[i] = value(bestJ, i) - c;

            if (i == n) continue;

            if (dp[i] == dp[i - 1]) continue; // dominated

            int newIdx = i;
            int newStart = newIdx + 1;
            bool discarded = false;

            while (!hull.empty()) {
                const auto &last = hull.back();
                int lo = max(last.start, newIdx + 1);
                int st = findStart(last.idx, newIdx, lo);
                if (st == n + 1) {
                    discarded = true;
                    break;
                }
                if (st <= last.start) {
                    hull.pop_back();
                } else {
                    newStart = st;
                    break;
                }
            }

            if (!discarded) {
                if (hull.empty()) newStart = newIdx + 1;
                if (newStart <= n) hull.push_back({newIdx, newStart});
            }
        }

        out.append(to_string(dp[n]));
        out.push_back('\n');
    }

    cout << out;
    return 0;
}