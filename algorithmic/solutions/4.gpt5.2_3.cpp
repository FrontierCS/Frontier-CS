#include <bits/stdc++.h>
using namespace std;

static const int QUERY_LIMIT = 50000;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    long long k;
    if (!(cin >> n >> k)) return 0;

    long long used = 0;

    unordered_map<unsigned long long, long long> cache;
    cache.reserve(100000);
    cache.max_load_factor(0.7f);

    auto keyOf = [](int x, int y) -> unsigned long long {
        return (unsigned long long)(unsigned int)x << 32 | (unsigned long long)(unsigned int)y;
    };

    auto query = [&](int x, int y) -> long long {
        unsigned long long key = keyOf(x, y);
        auto it = cache.find(key);
        if (it != cache.end()) return it->second;

        if (used >= QUERY_LIMIT) {
            exit(0);
        }

        cout << "QUERY " << x << " " << y << '\n' << flush;
        long long v;
        if (!(cin >> v)) exit(0);

        cache.emplace(key, v);
        ++used;
        return v;
    };

    auto countLE = [&](long long val) -> long long {
        int i = 1, j = n;
        long long cnt = 0;
        while (i <= n && j >= 1) {
            long long v = query(i, j);
            if (v <= val) {
                cnt += j;
                ++i;
            } else {
                --j;
            }
        }
        return cnt;
    };

    long long lo = query(1, 1);
    long long hi = query(n, n);

    while (lo < hi) {
        long long mid = lo + (long long)((__int128)(hi - lo) / 2);
        long long cnt = countLE(mid);
        if (cnt >= k) hi = mid;
        else lo = mid + 1;
    }

    cout << "DONE " << lo << '\n' << flush;

    double score;
    if (cin >> score) {
        // ignore
    }
    return 0;
}