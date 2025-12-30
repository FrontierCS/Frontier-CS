#include <bits/stdc++.h>
using namespace std;

struct InteractiveKthMatrix {
    int N;
    long long K;
    vector<long long> val;
    vector<unsigned char> vis;
    int used = 0;

    static constexpr int QLIMIT = 50000;
    static constexpr int BASE = 32;

    inline int idx(int x, int y) const { // 1-indexed
        return (x - 1) * N + (y - 1);
    }

    long long query(int x, int y) {
        int id = idx(x, y);
        if (vis[id]) return val[id];

        if (used >= QLIMIT) {
            cout << "DONE " << 0 << "\n" << flush;
            exit(0);
        }

        cout << "QUERY " << x << " " << y << "\n" << flush;

        long long v;
        if (!(cin >> v)) exit(0);

        vis[id] = 1;
        val[id] = v;
        used++;
        return v;
    }

    inline long long getVal(int r0, int c0, int step, int i, int j) {
        int x = r0 + step * (i - 1);
        int y = c0 + step * (j - 1);
        return query(x, y);
    }

    long long brute(int r0, int c0, int step, int n, long long k) {
        vector<long long> a;
        a.reserve(1LL * n * n);
        for (int i = 1; i <= n; i++) {
            for (int j = 1; j <= n; j++) {
                a.push_back(getVal(r0, c0, step, i, j));
            }
        }
        nth_element(a.begin(), a.begin() + (k - 1), a.end());
        return a[k - 1];
    }

    long long selectGreater(int r0, int c0, int step, int n, const vector<int>& lastLE, long long t) {
        struct Node {
            long long v;
            int r, c;
        };
        struct Cmp {
            bool operator()(const Node& a, const Node& b) const { return a.v > b.v; }
        };
        priority_queue<Node, vector<Node>, Cmp> pq;
        pq = {};

        for (int i = 1; i <= n; i++) {
            int c = lastLE[i] + 1;
            if (c <= n) {
                pq.push({getVal(r0, c0, step, i, c), i, c});
            }
        }

        Node cur{0, 0, 0};
        for (long long it = 1; it <= t; it++) {
            cur = pq.top();
            pq.pop();
            if (it == t) return cur.v;
            int nc = cur.c + 1;
            if (nc <= n) {
                pq.push({getVal(r0, c0, step, cur.r, nc), cur.r, nc});
            }
        }
        return cur.v;
    }

    long long selectLess(int r0, int c0, int step, int n, const vector<int>& lastLT, long long t) {
        struct Node {
            long long v;
            int r, c;
        };
        struct Cmp {
            bool operator()(const Node& a, const Node& b) const { return a.v < b.v; }
        };
        priority_queue<Node, vector<Node>, Cmp> pq;
        pq = {};

        for (int i = 1; i <= n; i++) {
            int c = lastLT[i];
            if (c >= 1) {
                pq.push({getVal(r0, c0, step, i, c), i, c});
            }
        }

        Node cur{0, 0, 0};
        for (long long it = 1; it <= t; it++) {
            cur = pq.top();
            pq.pop();
            if (it == t) return cur.v;
            int nc = cur.c - 1;
            if (nc >= 1) {
                pq.push({getVal(r0, c0, step, cur.r, nc), cur.r, nc});
            }
        }
        return cur.v;
    }

    long long solve(int r0, int c0, int step, int n, long long k) {
        if (n <= BASE) return brute(r0, c0, step, n, k);

        int m = n / 2;
        if (m == 0) return brute(r0, c0, step, n, k);

        long long k2 = (k + 3) / 4; // ceil(k/4)
        long long mm = 1LL * m * m;
        if (k2 < 1) k2 = 1;
        if (k2 > mm) k2 = mm;

        long long pivot = solve(r0 + step, c0 + step, step * 2, m, k2);

        vector<int> lastLE(n + 1), lastLT(n + 1);
        long long cntLE = 0, cntLT = 0;

        // lastLE: max j s.t. a[i][j] <= pivot
        int j = n;
        for (int i = 1; i <= n; i++) {
            while (j >= 1) {
                long long v = getVal(r0, c0, step, i, j);
                if (v <= pivot) break;
                --j;
            }
            lastLE[i] = j;
            cntLE += j;
        }

        // lastLT: max j s.t. a[i][j] < pivot
        j = n;
        for (int i = 1; i <= n; i++) {
            while (j >= 1) {
                long long v = getVal(r0, c0, step, i, j);
                if (v < pivot) break;
                --j;
            }
            lastLT[i] = j;
            cntLT += j;
        }

        if (k > cntLT && k <= cntLE) return pivot;

        if (k > cntLE) {
            long long t = k - cntLE;
            return selectGreater(r0, c0, step, n, lastLE, t);
        } else {
            long long t = cntLT - k + 1;
            return selectLess(r0, c0, step, n, lastLT, t);
        }
    }

    void run() {
        ios::sync_with_stdio(false);
        cin.tie(nullptr);

        if (!(cin >> N >> K)) return;
        val.assign(1LL * N * N, LLONG_MIN);
        vis.assign(1LL * N * N, 0);

        long long ans = solve(1, 1, 1, N, K);

        cout << "DONE " << ans << "\n" << flush;

        double score;
        cin >> score;
    }
};

int main() {
    InteractiveKthMatrix solver;
    solver.run();
    return 0;
}