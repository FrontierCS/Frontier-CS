#include <bits/stdc++.h>
using namespace std;

using int64 = long long;

static const int64 QUERY_LIMIT = 50000;

int n;
long long k;

// Caching for binary search path (and generally safe to use everywhere)
vector<long long> cacheVal;
vector<unsigned char> cacheSeen;

inline size_t idx(int x, int y) {
    return (size_t)x * (n + 1) + (size_t)y;
}

long long ask(int x, int y) {
    cout << "QUERY " << x << " " << y << endl;
    cout.flush();
    long long v;
    if (!(cin >> v)) {
        // In case of I/O failure, exit immediately.
        exit(0);
    }
    // Cache the value
    if ((int)cacheVal.size() >= (n + 1) * (n + 1)) {
        size_t id = idx(x, y);
        cacheVal[id] = v;
        cacheSeen[id] = 1;
    }
    return v;
}

long long getCached(int x, int y) {
    size_t id = idx(x, y);
    if (!cacheSeen[id]) {
        long long v = ask(x, y);
        cacheVal[id] = v;
        cacheSeen[id] = 1;
        return v;
    }
    return cacheVal[id];
}

void done(long long ans) {
    cout << "DONE " << ans << endl;
    cout.flush();
}

long long kthByMerge() {
    struct Node {
        long long val;
        int i, j;
    };
    struct Cmp {
        bool operator()(const Node& a, const Node& b) const {
            if (a.val != b.val) return a.val > b.val;
            if (a.i != b.i) return a.i > b.i;
            return a.j > b.j;
        }
    };

    priority_queue<Node, vector<Node>, Cmp> pq;

    vector<long long> firstVal(n + 2, 0);
    vector<unsigned char> firstKnown(n + 2, 0);
    int nextRow = 1;

    auto maybePushRows = [&]() {
        if (pq.empty() && nextRow <= n) {
            if (!firstKnown[nextRow]) {
                firstVal[nextRow] = ask(nextRow, 1);
                firstKnown[nextRow] = 1;
            }
            pq.push({firstVal[nextRow], nextRow, 1});
            nextRow++;
        }
        while (nextRow <= n) {
            if (!firstKnown[nextRow]) {
                firstVal[nextRow] = ask(nextRow, 1);
                firstKnown[nextRow] = 1;
            }
            if (pq.empty()) {
                pq.push({firstVal[nextRow], nextRow, 1});
                nextRow++;
            } else {
                long long topv = pq.top().val;
                if (firstVal[nextRow] <= topv) {
                    pq.push({firstVal[nextRow], nextRow, 1});
                    nextRow++;
                } else break;
            }
        }
    };

    long long popped = 0;
    long long ans = 0;

    maybePushRows();

    while (true) {
        if (pq.empty()) {
            // If heap is empty, push next row (if any)
            if (nextRow <= n) {
                if (!firstKnown[nextRow]) {
                    firstVal[nextRow] = ask(nextRow, 1);
                    firstKnown[nextRow] = 1;
                }
                pq.push({firstVal[nextRow], nextRow, 1});
                nextRow++;
            } else {
                // No more elements; shouldn't happen if k <= n*n
                break;
            }
        }

        Node t = pq.top(); pq.pop();
        popped++;
        if (popped == k) {
            ans = t.val;
            break;
        }
        if (t.j + 1 <= n) {
            long long nv = ask(t.i, t.j + 1);
            pq.push({nv, t.i, t.j + 1});
        }
        // After pushing next, maybe include more rows whose first elements are now <= new top
        maybePushRows();
    }

    return ans;
}

long long countLE(long long X) {
    long long cnt = 0;
    int i = n;
    int j = 1;
    while (i >= 1 && j <= n) {
        long long v = getCached(i, j);
        if (v <= X) {
            cnt += i;
            j++;
        } else {
            i--;
        }
    }
    return cnt;
}

long long kthByBinary() {
    // Query min and max
    long long low = ask(1, 1);
    long long high = ask(n, n);
    // Binary search for smallest value with count >= k
    while (low < high) {
        long long mid = low + ((high - low) >> 1);
        long long c = countLE(mid);
        if (c >= k) high = mid;
        else low = mid + 1;
    }
    return low;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n >> k)) {
        return 0;
    }

    // Initialize cache for potential binary search
    cacheVal.assign((size_t)(n + 1) * (n + 1), 0);
    cacheSeen.assign((size_t)(n + 1) * (n + 1), 0);

    // Strategy selection
    const long long maxQueries = QUERY_LIMIT;

    // Prefer row-wise merge if feasible
    if (k + n <= maxQueries) {
        long long ans = kthByMerge();
        done(ans);
    } else {
        // Try binary search if feasible given value range <= 1e18 (60 iterations)
        // 2n per count + 2 initial endpoints
        if (2LL * n * 60 + 2 <= maxQueries) {
            long long ans = kthByBinary();
            done(ans);
        } else {
            // Fallback: attempt binary search with caching anyway (may exceed limit on worst cases)
            long long ans = kthByBinary();
            done(ans);
        }
    }

    return 0;
}