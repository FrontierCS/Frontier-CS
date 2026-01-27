#include <bits/stdc++.h>
using namespace std;

static const int64_t MAXQ = 50000;

struct Node {
    long long val;
    int i, j;
    bool operator<(const Node& other) const {
        if (val != other.val) return val > other.val; // min-heap by default
        if (i != other.i) return i > other.i;
        return j > other.j;
    }
};
struct NodeMax {
    long long val;
    int i, j;
    bool operator<(const NodeMax& other) const {
        if (val != other.val) return val < other.val; // max-heap
        if (i != other.i) return i < other.i;
        return j < other.j;
    }
};

int n;
long long k;
long long queries_used = 0;

long long ask(int x, int y) {
    cout << "QUERY " << x << " " << y << "\n" << flush;
    long long v;
    if (!(cin >> v)) {
        // If interactor fails, return 0 to avoid UB
        exit(0);
    }
    queries_used++;
    return v;
}

long long solve_bfs_small_k(long long K) {
    vector<vector<char>> vis(n + 2, vector<char>(n + 2, 0));
    priority_queue<Node> pq; // min-heap via custom operator
    long long v = ask(1, 1);
    vis[1][1] = 1;
    pq.push({v, 1, 1});
    for (long long t = 1; t < K; ++t) {
        Node cur = pq.top(); pq.pop();
        int i = cur.i, j = cur.j;
        if (i + 1 <= n && !vis[i + 1][j]) {
            long long nv = ask(i + 1, j);
            vis[i + 1][j] = 1;
            pq.push({nv, i + 1, j});
        }
        if (j + 1 <= n && !vis[i][j + 1]) {
            long long nv = ask(i, j + 1);
            vis[i][j + 1] = 1;
            pq.push({nv, i, j + 1});
        }
    }
    return pq.top().val;
}

long long solve_bfs_small_m(long long M) {
    vector<vector<char>> vis(n + 2, vector<char>(n + 2, 0));
    priority_queue<NodeMax> pq; // max-heap
    long long v = ask(n, n);
    vis[n][n] = 1;
    pq.push({v, n, n});
    for (long long t = 1; t < M; ++t) {
        NodeMax cur = pq.top(); pq.pop();
        int i = cur.i, j = cur.j;
        if (i - 1 >= 1 && !vis[i - 1][j]) {
            long long nv = ask(i - 1, j);
            vis[i - 1][j] = 1;
            pq.push({nv, i - 1, j});
        }
        if (j - 1 >= 1 && !vis[i][j - 1]) {
            long long nv = ask(i, j - 1);
            vis[i][j - 1] = 1;
            pq.push({nv, i, j - 1});
        }
    }
    return pq.top().val;
}

long long solve_row_merge_k(long long K) {
    priority_queue<Node> pq; // min-heap
    for (int i = 1; i <= n; ++i) {
        long long v = ask(i, 1);
        pq.push({v, i, 1});
    }
    for (long long t = 1; t < K; ++t) {
        Node cur = pq.top(); pq.pop();
        int i = cur.i, j = cur.j;
        if (j + 1 <= n) {
            long long nv = ask(i, j + 1);
            pq.push({nv, i, j + 1});
        }
    }
    return pq.top().val;
}

long long solve_row_merge_m(long long M) {
    priority_queue<NodeMax> pq; // max-heap
    for (int i = 1; i <= n; ++i) {
        long long v = ask(i, n);
        pq.push({v, i, n});
    }
    for (long long t = 1; t < M; ++t) {
        NodeMax cur = pq.top(); pq.pop();
        int i = cur.i, j = cur.j;
        if (j - 1 >= 1) {
            long long nv = ask(i, j - 1);
            pq.push({nv, i, j - 1});
        }
    }
    return pq.top().val;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n >> k)) {
        return 0;
    }

    long long total = 1LL * n * n;
    long long m = total - k + 1;

    // Predict query counts for strategies
    auto safe_mul = [](long long a, long long b) -> long long {
        if (a == 0 || b == 0) return 0;
        if (a > (LLONG_MAX / b)) return LLONG_MAX / 2;
        return a * b;
    };

    long long pred_bfs_k = 1 + safe_mul(2, (k > 0 ? (k - 1) : 0));
    long long pred_bfs_m = 1 + safe_mul(2, (m > 0 ? (m - 1) : 0));
    long long pred_merge_k = n + (k > 0 ? (k - 1) : 0);
    long long pred_merge_m = n + (m > 0 ? (m - 1) : 0);

    // Choose the strategy with minimal predicted queries
    int strategy = 0;
    long long best_pred = LLONG_MAX;
    vector<pair<int, long long>> options = {
        {1, pred_bfs_k},   // BFS from min side
        {2, pred_bfs_m},   // BFS from max side
        {3, pred_merge_k}, // Row merge from min side
        {4, pred_merge_m}  // Row merge from max side
    };
    for (auto &op : options) {
        if (op.second < best_pred) {
            best_pred = op.second;
            strategy = op.first;
        }
    }

    long long ans = 0;
    if (strategy == 1) {
        ans = solve_bfs_small_k(k);
    } else if (strategy == 2) {
        ans = solve_bfs_small_m(m);
    } else if (strategy == 3) {
        ans = solve_row_merge_k(k);
    } else {
        ans = solve_row_merge_m(m);
    }

    cout << "DONE " << ans << "\n" << flush;
    return 0;
}