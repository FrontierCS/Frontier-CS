#include <bits/stdc++.h>
using namespace std;

struct Op {
    int l, r, dir; // dir: 0 left, 1 right
};

static const int X_BIG = 6;
static const int K_BIG = X_BIG + 1; // 7

static int fact_[K_BIG + 1];

static int encodePerm(const array<int, K_BIG>& p) {
    int code = 0;
    bool used[K_BIG] = {false};
    for (int i = 0; i < K_BIG; i++) {
        int smallerUnused = 0;
        for (int v = 0; v < p[i]; v++) if (!used[v]) smallerUnused++;
        used[p[i]] = true;
        code += smallerUnused * fact_[K_BIG - 1 - i];
    }
    return code;
}

static array<int, K_BIG> decodePerm(int code) {
    array<int, K_BIG> p{};
    vector<int> avail(K_BIG);
    iota(avail.begin(), avail.end(), 0);
    for (int i = 0; i < K_BIG; i++) {
        int f = fact_[K_BIG - 1 - i];
        int idx = code / f;
        code %= f;
        p[i] = avail[idx];
        avail.erase(avail.begin() + idx);
    }
    return p;
}

static vector<int> bfs_parent, bfs_op;

static void buildBFS() {
    fact_[0] = 1;
    for (int i = 1; i <= K_BIG; i++) fact_[i] = fact_[i - 1] * i;

    int SZ = fact_[K_BIG];
    bfs_parent.assign(SZ, -1);
    bfs_op.assign(SZ, -1);

    queue<int> q;
    int start = 0; // sorted perm encodes to 0
    bfs_parent[start] = -2;
    q.push(start);

    while (!q.empty()) {
        int cur = q.front(); q.pop();
        auto p = decodePerm(cur);

        for (int op = 0; op < 4; op++) {
            auto np = p;
            if (op == 0) { // seg1 left on [0..5]
                int tmp = np[0];
                for (int i = 0; i < 5; i++) np[i] = np[i + 1];
                np[5] = tmp;
            } else if (op == 1) { // seg1 right
                int tmp = np[5];
                for (int i = 5; i >= 1; i--) np[i] = np[i - 1];
                np[0] = tmp;
            } else if (op == 2) { // seg2 left on [1..6]
                int tmp = np[1];
                for (int i = 1; i < 6; i++) np[i] = np[i + 1];
                np[6] = tmp;
            } else { // op == 3 seg2 right
                int tmp = np[6];
                for (int i = 6; i >= 2; i--) np[i] = np[i - 1];
                np[1] = tmp;
            }
            int nxt = encodePerm(np);
            if (bfs_parent[nxt] == -1) {
                bfs_parent[nxt] = cur;
                bfs_op[nxt] = op;
                q.push(nxt);
            }
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<int> a(n + 1);
    for (int i = 1; i <= n; i++) cin >> a[i];

    if (n == 1) {
        cout << 1 << "\n" << 0 << "\n";
        return 0;
    }

    int x;
    vector<Op> ops;

    auto applyRotate = [&](int l, int dir, int xcur, vector<int>& pos) {
        int r = l + xcur - 1;
        if (dir == 0) { // left
            int tmp = a[l];
            for (int i = l; i < r; i++) a[i] = a[i + 1];
            a[r] = tmp;
        } else { // right
            int tmp = a[r];
            for (int i = r; i > l; i--) a[i] = a[i - 1];
            a[l] = tmp;
        }
        for (int i = l; i <= r; i++) pos[a[i]] = i;
        ops.push_back({l, r, dir});
    };

    if (n < K_BIG) {
        x = 2;
        vector<int> pos(n + 1);
        for (int i = 1; i <= n; i++) pos[a[i]] = i;

        for (int v = 1; v <= n; v++) {
            while (pos[v] > v) {
                int p = pos[v];
                applyRotate(p - 1, 0, x, pos); // swap left
            }
        }

        cout << x << "\n" << ops.size() << "\n";
        for (auto &op : ops) cout << op.l << " " << op.r << " " << op.dir << "\n";
        return 0;
    }

    buildBFS();

    x = X_BIG;
    int k = K_BIG; // 7
    vector<int> pos(n + 1);
    for (int i = 1; i <= n; i++) pos[a[i]] = i;

    int prefixLen = n - k; // fix [1..prefixLen]
    for (int i = 1; i <= prefixLen; i++) {
        if (a[i] == i) continue;
        int p = pos[i];
        while (p > i + (x - 1)) {
            int l = p - (x - 1);
            applyRotate(l, 1, x, pos);
            p = pos[i];
        }
        p = pos[i];
        int d = p - i;
        if (d != 0) {
            int leftCnt = d;
            int rightCnt = x - d;
            if (leftCnt <= rightCnt) {
                for (int t = 0; t < leftCnt; t++) applyRotate(i, 0, x, pos);
            } else {
                for (int t = 0; t < rightCnt; t++) applyRotate(i, 1, x, pos);
            }
        }
    }

    int s = n - k + 1; // start of tail
    int base = n - 6;  // tail values should be base..base+6
    array<int, K_BIG> tail{};
    for (int i = 0; i < k; i++) tail[i] = a[s + i] - base;

    int code = encodePerm(tail);
    while (code != 0) {
        int op = bfs_op[code];
        int inv = op ^ 1;

        if (inv == 0) { // seg1 left
            applyRotate(s, 0, x, pos);
        } else if (inv == 1) { // seg1 right
            applyRotate(s, 1, x, pos);
        } else if (inv == 2) { // seg2 left
            applyRotate(s + 1, 0, x, pos);
        } else { // inv == 3 seg2 right
            applyRotate(s + 1, 1, x, pos);
        }

        code = bfs_parent[code];
    }

    cout << x << "\n" << ops.size() << "\n";
    for (auto &op : ops) cout << op.l << " " << op.r << " " << op.dir << "\n";
    return 0;
}