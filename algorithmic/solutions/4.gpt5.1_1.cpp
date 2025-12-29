#include <bits/stdc++.h>
using namespace std;

const int MAX_Q = 50000;

long long query_count = 0;
int n;
long long k;

long long do_query(int x, int y) {
    ++query_count;
    cout << "QUERY " << x << " " << y << '\n';
    cout.flush();
    long long v;
    if (!(cin >> v)) exit(0); // in interactive environment, this should not happen
    return v;
}

void done(long long ans) {
    cout << "DONE " << ans << '\n';
    cout.flush();
}

void solveBFS(long long kk) {
    struct Node {
        long long val;
        int x, y;
    };
    struct Cmp {
        bool operator()(const Node &a, const Node &b) const {
            return a.val > b.val;
        }
    };
    priority_queue<Node, vector<Node>, Cmp> pq;
    vector<vector<char>> vis(n + 2, vector<char>(n + 2, 0));

    long long v = do_query(1, 1);
    vis[1][1] = 1;
    pq.push({v, 1, 1});

    long long popped = 0;
    long long ans = -1;

    while (!pq.empty()) {
        Node cur = pq.top(); pq.pop();
        ++popped;
        if (popped == kk) {
            ans = cur.val;
            break;
        }
        int x = cur.x, y = cur.y;

        if (x + 1 <= n && !vis[x + 1][y]) {
            long long nv = do_query(x + 1, y);
            vis[x + 1][y] = 1;
            pq.push({nv, x + 1, y});
        }
        if (y + 1 <= n && !vis[x][y + 1]) {
            long long nv = do_query(x, y + 1);
            vis[x][y + 1] = 1;
            pq.push({nv, x, y + 1});
        }
    }

    if (ans == -1 && !pq.empty()) ans = pq.top().val; // fallback, should not happen
    done(ans);
}

void solveRowMerge(long long kk) {
    struct Node {
        long long val;
        int row, col;
    };
    struct Cmp {
        bool operator()(const Node &a, const Node &b) const {
            return a.val > b.val;
        }
    };
    priority_queue<Node, vector<Node>, Cmp> pq;

    for (int i = 1; i <= n; ++i) {
        long long v = do_query(i, 1);
        pq.push({v, i, 1});
    }

    long long popped = 0;
    long long ans = -1;

    while (!pq.empty()) {
        Node cur = pq.top(); pq.pop();
        ++popped;
        if (popped == kk) {
            ans = cur.val;
            break;
        }
        int i = cur.row, j = cur.col;
        if (j < n) {
            long long nv = do_query(i, j + 1);
            pq.push({nv, i, j + 1});
        }
    }

    if (ans == -1 && !pq.empty()) ans = pq.top().val; // fallback, should not happen
    done(ans);
}

void solveFallback(long long kk) {
    struct Node {
        long long val;
        int row, col;
    };
    struct Cmp {
        bool operator()(const Node &a, const Node &b) const {
            return a.val > b.val;
        }
    };
    priority_queue<Node, vector<Node>, Cmp> pq;

    for (int i = 1; i <= n; ++i) {
        long long v = do_query(i, 1);
        pq.push({v, i, 1});
    }

    long long popped = 0;
    long long ans = -1;

    while (!pq.empty()) {
        Node cur = pq.top(); pq.pop();
        ++popped;
        ans = cur.val;
        if (popped == kk) break;

        int i = cur.row, j = cur.col;
        if (j < n) {
            if (query_count + 1 > MAX_Q) {
                // cannot query more, so stop adding new elements
                continue;
            }
            long long nv = do_query(i, j + 1);
            pq.push({nv, i, j + 1});
        }
    }

    done(ans);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n >> k)) return 0;
    long long totcells = 1LL * n * n;
    if (totcells <= 0) {
        done(0);
        return 0;
    }
    if (k < 1) k = 1;
    if (k > totcells) k = totcells;

    if (k == 1) {
        long long val = do_query(1, 1); // smallest element
        done(val);
        return 0;
    }
    if (k == totcells) {
        long long val = do_query(n, n); // largest element
        done(val);
        return 0;
    }

    long long costBFS = 2 * k - 1;         // 1 + 2*(k-1)
    long long costMerge = n + k - 1;       // n initial + k-1 next
    bool canBFS = (costBFS <= MAX_Q);
    bool canMerge = (costMerge <= MAX_Q);

    if (canBFS && (!canMerge || costBFS <= costMerge)) {
        solveBFS(k);
    } else if (canMerge) {
        solveRowMerge(k);
    } else {
        // Both exceed limit in worst-case; use limited merge heuristic
        solveFallback(k);
    }

    return 0;
}