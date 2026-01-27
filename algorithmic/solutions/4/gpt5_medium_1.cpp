#include <bits/stdc++.h>
using namespace std;

static const int QUERY_LIMIT = 50000;

long long used_queries = 0;

long long do_query(int x, int y) {
    cout << "QUERY " << x << " " << y << endl;
    cout.flush();
    long long v;
    if (!(cin >> v)) {
        exit(0);
    }
    used_queries++;
    return v;
}

[[noreturn]] void done(long long ans) {
    cout << "DONE " << ans << endl;
    cout.flush();
    exit(0);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    long long k;
    if (!(cin >> n >> k)) {
        return 0;
    }

    long long total = 1LL * n * n;
    long long k_from_end = total - k + 1;

    struct Node {
        long long v;
        int i, j;
        bool operator<(const Node& other) const {
            return v > other.v; // min-heap
        }
    };
    struct NodeMax {
        long long v;
        int i, j;
        bool operator<(const NodeMax& other) const {
            return v < other.v; // max-heap
        }
    };

    if (k <= k_from_end) {
        priority_queue<Node> pq;
        vector<int> ptr(n + 1, 1);
        // Initialize heads of all rows (column 1)
        for (int i = 1; i <= n; ++i) {
            long long v = do_query(i, 1);
            pq.push({v, i, 1});
        }
        long long cnt = 0;
        long long ans = 0;
        while (!pq.empty()) {
            Node cur = pq.top(); pq.pop();
            cnt++;
            if (cnt == k) {
                ans = cur.v;
                done(ans);
            }
            int i = cur.i;
            int j = cur.j;
            if (j + 1 <= n) {
                long long v = do_query(i, j + 1);
                pq.push({v, i, j + 1});
            }
        }
    } else {
        priority_queue<NodeMax> pq;
        vector<int> ptr(n + 1, n);
        // Initialize tails of all rows (column n)
        for (int i = 1; i <= n; ++i) {
            long long v = do_query(i, n);
            pq.push({v, i, n});
        }
        long long target = k_from_end;
        long long cnt = 0;
        long long ans = 0;
        while (!pq.empty()) {
            NodeMax cur = pq.top(); pq.pop();
            cnt++;
            if (cnt == target) {
                ans = cur.v;
                done(ans);
            }
            int i = cur.i;
            int j = cur.j;
            if (j - 1 >= 1) {
                long long v = do_query(i, j - 1);
                pq.push({v, i, j - 1});
            }
        }
    }

    return 0;
}