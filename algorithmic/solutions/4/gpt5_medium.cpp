#include <bits/stdc++.h>
using namespace std;

using ll = long long;

static const int QUERY_LIMIT = 50000;

ll query_count = 0;

ll do_query(int x, int y) {
    cout << "QUERY " << x << " " << y << endl;
    cout.flush();
    ll v;
    if (!(cin >> v)) {
        // Interactor error; exit gracefully
        exit(0);
    }
    ++query_count;
    return v;
}

void done(ll ans) {
    cout << "DONE " << ans << endl;
    cout.flush();
}

struct Node {
    ll val;
    int x, y;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    long long k;
    if (!(cin >> n >> k)) {
        return 0;
    }

    long long total = 1LL * n * n;
    bool reversed = false;
    long long r = k;
    if (k > total / 2) {
        reversed = true;
        r = total - k + 1;
    }

    if (!reversed) {
        // Enumerate r smallest from (1,1)
        vector<vector<unsigned char>> vis(n + 2, vector<unsigned char>(n + 2, 0));
        auto cmp = [](const Node& a, const Node& b) {
            if (a.val != b.val) return a.val > b.val;
            if (a.x != b.x) return a.x > b.x;
            return a.y > b.y;
        };
        priority_queue<Node, vector<Node>, decltype(cmp)> pq(cmp);

        ll v00 = do_query(1, 1);
        vis[1][1] = 1;
        pq.push({v00, 1, 1});

        ll ans = v00;
        for (long long t = 1; t <= r; ++t) {
            if (pq.empty()) break;
            Node cur = pq.top(); pq.pop();
            ans = cur.val;
            int x = cur.x, y = cur.y;

            if (t == r) break;

            if (x + 1 <= n && !vis[x + 1][y]) {
                ll v = do_query(x + 1, y);
                vis[x + 1][y] = 1;
                pq.push({v, x + 1, y});
            }
            if (y + 1 <= n && !vis[x][y + 1]) {
                ll v = do_query(x, y + 1);
                vis[x][y + 1] = 1;
                pq.push({v, x, y + 1});
            }
        }
        done(ans);
    } else {
        // Enumerate r largest from (n,n)
        vector<vector<unsigned char>> vis(n + 2, vector<unsigned char>(n + 2, 0));
        auto cmp = [](const Node& a, const Node& b) {
            if (a.val != b.val) return a.val < b.val; // max-heap by value
            if (a.x != b.x) return a.x < b.x;
            return a.y < b.y;
        };
        priority_queue<Node, vector<Node>, decltype(cmp)> pq(cmp);

        ll vnn = do_query(n, n);
        vis[n][n] = 1;
        pq.push({vnn, n, n});

        ll ans = vnn;
        for (long long t = 1; t <= r; ++t) {
            if (pq.empty()) break;
            Node cur = pq.top(); pq.pop();
            ans = cur.val;
            int x = cur.x, y = cur.y;

            if (t == r) break;

            if (x - 1 >= 1 && !vis[x - 1][y]) {
                ll v = do_query(x - 1, y);
                vis[x - 1][y] = 1;
                pq.push({v, x - 1, y});
            }
            if (y - 1 >= 1 && !vis[x][y - 1]) {
                ll v = do_query(x, y - 1);
                vis[x][y - 1] = 1;
                pq.push({v, x, y - 1});
            }
        }
        done(ans);
    }

    return 0;
}