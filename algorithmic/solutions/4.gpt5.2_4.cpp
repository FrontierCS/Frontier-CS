#include <bits/stdc++.h>
using namespace std;

struct Node {
    long long v;
    int r, c;
};
struct Cmp {
    bool operator()(const Node& a, const Node& b) const {
        return a.v > b.v;
    }
};

static const int QUERY_LIMIT = 50000;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    long long k;
    if (!(cin >> n >> k)) return 0;

    long long used = 0;

    auto query = [&](int x, int y) -> long long {
        if (used >= QUERY_LIMIT) {
            // Cannot query further; return dummy.
            return (long long)4e18;
        }
        cout << "QUERY " << x << " " << y << "\n" << flush;
        long long v;
        if (!(cin >> v)) exit(0);
        ++used;
        return v;
    };

    auto done = [&](long long ans) {
        cout << "DONE " << ans << "\n" << flush;
        double score;
        cin >> score;
        exit(0);
    };

    if (n <= 0 || k <= 0) done(0);

    long long nn = 1LL * n * n;
    if (k > nn) k = nn;

    priority_queue<Node, vector<Node>, Cmp> pq;
    for (int c = 1; c <= n; ++c) {
        long long v = query(1, c);
        pq.push({v, 1, c});
    }

    long long ans = pq.top().v;
    for (long long t = 1; t <= k; ++t) {
        if (pq.empty()) break;
        Node cur = pq.top();
        pq.pop();

        ans = cur.v;
        if (t == k) break;

        if (cur.r < n) {
            if (used >= QUERY_LIMIT) {
                done(ans);
            }
            long long nv = query(cur.r + 1, cur.c);
            pq.push({nv, cur.r + 1, cur.c});
        }
    }

    done(ans);
    return 0;
}