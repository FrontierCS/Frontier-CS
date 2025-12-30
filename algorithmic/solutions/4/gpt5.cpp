#include <bits/stdc++.h>
using namespace std;

static const long long QUERY_LIMIT = 50000;

struct Node {
    long long key;
    int x, y;
    bool operator<(const Node& other) const {
        return key > other.key; // for min-heap
    }
};

int n;
long long k;
long long queries_used = 0;

long long do_query(int x, int y) {
    cout << "QUERY " << x << " " << y << endl;
    cout.flush();
    long long v;
    if (!(cin >> v)) {
        // If interactor terminates or input fails, exit.
        exit(0);
    }
    queries_used++;
    return v;
}

void done(long long ans) {
    cout << "DONE " << ans << endl;
    cout.flush();
    exit(0);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n >> k)) {
        return 0;
    }

    long long total = 1LL * n * n;
    if (k < 1) k = 1;
    if (k > total) k = total;

    bool reversed = false;
    long long kk = k;

    // If k is closer to the end, search from bottom-right for (n*n - k + 1)-th largest
    if (kk > total - kk + 1) {
        reversed = true;
        kk = total - kk + 1;
    }

    vector<vector<char>> pushed(n + 2, vector<char>(n + 2, 0));
    priority_queue<Node> pq;

    auto push_cell = [&](int x, int y) {
        if (x < 1 || x > n || y < 1 || y > n) return;
        if (pushed[x][y]) return;
        pushed[x][y] = 1;
        long long v = do_query(x, y);
        long long key = reversed ? -v : v;
        pq.push(Node{key, x, y});
    };

    if (!reversed) {
        push_cell(1, 1);
    } else {
        push_cell(n, n);
    }

    for (long long t = 1; t < kk; ++t) {
        if (pq.empty()) break; // safety
        Node cur = pq.top(); pq.pop();
        int x = cur.x, y = cur.y;
        if (!reversed) {
            push_cell(x + 1, y);
            push_cell(x, y + 1);
        } else {
            push_cell(x - 1, y);
            push_cell(x, y - 1);
        }
        if (queries_used >= QUERY_LIMIT) {
            // Fallback: terminate with current best guess (not guaranteed correct)
            long long ans_guess = reversed ? -cur.key : cur.key;
            done(ans_guess);
        }
    }

    if (pq.empty()) {
        done(0);
    } else {
        long long ans = pq.top().key;
        if (reversed) ans = -ans;
        done(ans);
    }

    return 0;
}