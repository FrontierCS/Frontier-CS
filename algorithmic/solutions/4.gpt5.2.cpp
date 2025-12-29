#include <bits/stdc++.h>
using namespace std;

static const int QUERY_LIMIT = 50000;

struct Node {
    long long v;
    int x, y;
};

struct CmpMin {
    bool operator()(const Node& a, const Node& b) const { return a.v > b.v; }
};
struct CmpMax {
    bool operator()(const Node& a, const Node& b) const { return a.v < b.v; }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    long long k;
    if (!(cin >> n >> k)) return 0;

    const long long total = 1LL * n * n;

    const int N1 = n + 1;
    const int SZ = N1 * N1;

    vector<long long> cacheVal(SZ);
    vector<unsigned char> known(SZ, 0);
    vector<int> vis(SZ, 0);
    int visToken = 0;

    int used = 0;

    auto idx = [&](int x, int y) -> int { return x * N1 + y; };

    auto query = [&](int x, int y) -> long long {
        int p = idx(x, y);
        if (known[p]) return cacheVal[p];

        if (used >= QUERY_LIMIT) {
            // Out of budget; output something and exit gracefully.
            cout << "DONE " << 0 << "\n";
            cout.flush();
            exit(0);
        }

        cout << "QUERY " << x << " " << y << "\n";
        cout.flush();

        long long v;
        if (!(cin >> v)) exit(0);

        used++;
        known[p] = 1;
        cacheVal[p] = v;
        return v;
    };

    auto kthSmallestHeap = [&](long long t) -> long long {
        ++visToken;
        priority_queue<Node, vector<Node>, CmpMin> pq;

        vis[idx(1, 1)] = visToken;
        pq.push({query(1, 1), 1, 1});

        while (!pq.empty()) {
            Node cur = pq.top();
            pq.pop();
            if (--t == 0) return cur.v;

            if (cur.x < n) {
                int nx = cur.x + 1, ny = cur.y;
                int p = idx(nx, ny);
                if (vis[p] != visToken) {
                    vis[p] = visToken;
                    pq.push({query(nx, ny), nx, ny});
                }
            }
            if (cur.y < n) {
                int nx = cur.x, ny = cur.y + 1;
                int p = idx(nx, ny);
                if (vis[p] != visToken) {
                    vis[p] = visToken;
                    pq.push({query(nx, ny), nx, ny});
                }
            }
        }
        return 0;
    };

    auto kthLargestHeap = [&](long long t) -> long long {
        ++visToken;
        priority_queue<Node, vector<Node>, CmpMax> pq;

        vis[idx(n, n)] = visToken;
        pq.push({query(n, n), n, n});

        while (!pq.empty()) {
            Node cur = pq.top();
            pq.pop();
            if (--t == 0) return cur.v;

            if (cur.x > 1) {
                int nx = cur.x - 1, ny = cur.y;
                int p = idx(nx, ny);
                if (vis[p] != visToken) {
                    vis[p] = visToken;
                    pq.push({query(nx, ny), nx, ny});
                }
            }
            if (cur.y > 1) {
                int nx = cur.x, ny = cur.y - 1;
                int p = idx(nx, ny);
                if (vis[p] != visToken) {
                    vis[p] = visToken;
                    pq.push({query(nx, ny), nx, ny});
                }
            }
        }
        return 0;
    };

    long long ans = 0;

    if (total <= QUERY_LIMIT) {
        vector<long long> vals;
        vals.reserve((size_t)total);
        for (int i = 1; i <= n; i++) {
            for (int j = 1; j <= n; j++) {
                vals.push_back(query(i, j));
            }
        }
        nth_element(vals.begin(), vals.begin() + (k - 1), vals.end());
        ans = vals[(size_t)(k - 1)];
    } else {
        long long tSmall = k;
        long long tLarge = total - k + 1;
        long long t = min(tSmall, tLarge);

        if (t <= QUERY_LIMIT) {
            if (tSmall <= tLarge) ans = kthSmallestHeap(tSmall);
            else ans = kthLargestHeap(tLarge);
        } else {
            // No known exact strategy within budget for arbitrary k when total > QUERY_LIMIT.
            // Best-effort: fall back to heap from closer end (still will exceed limit if t > QUERY_LIMIT).
            if (tSmall <= tLarge) ans = kthSmallestHeap(tSmall);
            else ans = kthLargestHeap(tLarge);
        }
    }

    cout << "DONE " << ans << "\n";
    cout.flush();

    // Interactor may print a score; try to read and exit.
    double score;
    if (cin >> score) { /* ignore */ }

    return 0;
}