#include <bits/stdc++.h>
using namespace std;

static const long long QUERY_LIMIT = 50000;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    long long k;
    if (!(cin >> n >> k)) {
        return 0;
    }

    auto query = [&](int x, int y) -> long long {
        cout << "QUERY " << x << " " << y << "\n" << flush;
        long long v;
        cin >> v;
        return v;
    };

    auto done = [&](long long ans) {
        cout << "DONE " << ans << "\n" << flush;
        // Do not read any further
        // Exit
    };

    long long total = 1LL * n * n;
    bool from_min = (k <= total - k + 1);
    long long t = from_min ? k : (total - k + 1);

    struct Node {
        long long val;
        int i, j;
    };

    if (from_min) {
        // K-way merge from the start of each row
        struct Cmp {
            bool operator()(const Node& a, const Node& b) const {
                return a.val > b.val;
            }
        };
        priority_queue<Node, vector<Node>, Cmp> pq;
        for (int i = 1; i <= n; ++i) {
            long long v = query(i, 1);
            pq.push({v, i, 1});
        }
        long long ans = 0;
        for (long long cnt = 1; cnt <= t; ++cnt) {
            Node cur = pq.top(); pq.pop();
            if (cnt == t) {
                ans = cur.val;
                break;
            }
            int ni = cur.i, nj = cur.j + 1;
            if (nj <= n) {
                long long v = query(ni, nj);
                pq.push({v, ni, nj});
            }
        }
        done(ans);
    } else {
        // K-way merge from the end of each row (descending order)
        struct Cmp {
            bool operator()(const Node& a, const Node& b) const {
                return a.val < b.val;
            }
        };
        priority_queue<Node, vector<Node>, Cmp> pq;
        for (int i = 1; i <= n; ++i) {
            long long v = query(i, n);
            pq.push({v, i, n});
        }
        long long ans = 0;
        for (long long cnt = 1; cnt <= t; ++cnt) {
            Node cur = pq.top(); pq.pop();
            if (cnt == t) {
                ans = cur.val;
                break;
            }
            int ni = cur.i, nj = cur.j - 1;
            if (nj >= 1) {
                long long v = query(ni, nj);
                pq.push({v, ni, nj});
            }
        }
        done(ans);
    }
    return 0;
}