#include <bits/stdc++.h>
using namespace std;

static const long long UNKNOWN = LLONG_MIN;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    long long k;
    if (!(cin >> n >> k)) return 0;

    vector<vector<long long>> cache(n+1, vector<long long>(n+1, UNKNOWN));
    long long query_count = 0;
    const long long QUERY_LIMIT = 50000;

    auto flush = [](){ cout.flush(); };

    auto query = [&](int x, int y)->long long {
        if (cache[x][y] != UNKNOWN) return cache[x][y];
        if (query_count >= QUERY_LIMIT) {
            // Fallback: should not happen; but to avoid further queries, return known edge
            return cache[x][y] = 0;
        }
        cout << "QUERY " << x << " " << y << "\n";
        flush();
        long long v;
        if (!(cin >> v)) {
            // If read fails, set to 0
            v = 0;
        }
        cache[x][y] = v;
        ++query_count;
        return v;
    };

    auto count_leq = [&](long long mid)->long long {
        long long cnt = 0;
        int j = n;
        for (int i = 1; i <= n; ++i) {
            while (j >= 1) {
                long long v = query(i, j);
                if (v > mid) {
                    --j;
                } else {
                    cnt += j;
                    break;
                }
                if (j == 0) break;
            }
            if (j == 0) break;
        }
        return cnt;
    };

    // Establish bounds
    long long low = query(1,1);
    long long high = query(n,n);

    if (low > high) swap(low, high); // just in case

    // Binary search for minimal value v such that count_leq(v) >= k
    while (low < high) {
        long long mid = low + ( (__int128)(high - low) / 2 );
        long long cnt = count_leq(mid);
        if (cnt >= k) {
            high = mid;
        } else {
            low = mid + 1;
        }
        // Optional guard: if nearing query limit, break and use current high
        if (query_count + 2*n > QUERY_LIMIT) break;
    }

    cout << "DONE " << high << "\n";
    flush();

    return 0;
}