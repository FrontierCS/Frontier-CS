#include <bits/stdc++.h>
using namespace std;

struct Op {
    int l, r, dir; // dir: 0 left, 1 right
};

static vector<int> factv;

static int encodePerm(const vector<int>& p) {
    int n = (int)p.size();
    vector<int> used(n + 1, 0);
    int id = 0;
    for (int i = 0; i < n; i++) {
        int smaller = 0;
        for (int v = 1; v < p[i]; v++) smaller += !used[v];
        id += smaller * factv[n - 1 - i];
        used[p[i]] = 1;
    }
    return id;
}

static vector<int> decodePerm(int id, int n) {
    vector<int> nums(n);
    iota(nums.begin(), nums.end(), 1);
    vector<int> p(n);
    for (int i = 0; i < n; i++) {
        int f = factv[n - 1 - i];
        int idx = (f == 0 ? 0 : id / f);
        if (f != 0) id %= f;
        p[i] = nums[idx];
        nums.erase(nums.begin() + idx);
    }
    return p;
}

static void rotateLocal(vector<int>& p, int s, int dir) {
    // rotate length 4 on indices [s..s+3]
    if (dir == 0) { // left
        int tmp = p[s];
        for (int i = s; i < s + 3; i++) p[i] = p[i + 1];
        p[s + 3] = tmp;
    } else { // right
        int tmp = p[s + 3];
        for (int i = s + 3; i > s; i--) p[i] = p[i - 1];
        p[s] = tmp;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<int> a(n + 1);
    for (int i = 1; i <= n; i++) cin >> a[i];

    vector<Op> ops;

    if (n <= 1) {
        cout << 1 << "\n" << 0 << "\n";
        return 0;
    }

    auto doRotate = [&](int x, vector<int>& pos, int l, int dir) {
        int r = l + x - 1;
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

    if (n <= 6) {
        int x = 2;
        vector<int> pos(n + 1);
        for (int i = 1; i <= n; i++) pos[a[i]] = i;

        for (int i = 1; i <= n; i++) {
            for (int j = 1; j + 1 <= n; j++) {
                if (a[j] > a[j + 1]) {
                    doRotate(x, pos, j, 0);
                }
            }
        }

        cout << x << "\n" << (int)ops.size() << "\n";
        for (auto &op : ops) {
            cout << op.l << " " << op.r << " " << op.dir << "\n";
        }
        return 0;
    }

    int x = 4;
    vector<int> pos(n + 1);
    for (int i = 1; i <= n; i++) pos[a[i]] = i;

    int T = 6; // suffix size to finish via BFS
    int prefixEnd = n - T; // fix [1..prefixEnd]

    for (int i = 1; i <= prefixEnd; i++) {
        int p = pos[i];
        while (p > i + 3) {
            doRotate(x, pos, p - 3, 1); // right shift [p-3..p], moves i left by 3
            p = pos[i];
        }
        p = pos[i];
        int k = p - i; // 0..3
        for (int t = 0; t < k; t++) {
            doRotate(x, pos, i, 0); // left rotate [i..i+3]
        }
    }

    // BFS precompute for T=6 with x=4 windows at s=0..2
    factv.assign(T + 1, 1);
    for (int i = 1; i <= T; i++) factv[i] = factv[i - 1] * i;
    int S = factv[T];

    vector<int> parent(S, -1), moveCode(S, -1);
    vector<int> idPerm(T);
    for (int i = 0; i < T; i++) idPerm[i] = i + 1;
    int id0 = encodePerm(idPerm);

    queue<int> q;
    parent[id0] = id0;
    q.push(id0);

    while (!q.empty()) {
        int cur = q.front(); q.pop();
        vector<int> p = decodePerm(cur, T);
        for (int s = 0; s <= T - 4; s++) {
            for (int dir = 0; dir <= 1; dir++) {
                vector<int> p2 = p;
                rotateLocal(p2, s, dir);
                int nxt = encodePerm(p2);
                if (parent[nxt] == -1) {
                    parent[nxt] = cur;
                    moveCode[nxt] = s * 2 + dir; // parent -> nxt
                    q.push(nxt);
                }
            }
        }
    }

    int sufStart = n - T + 1; // 1-indexed
    int base = n - T; // values in suffix should be base+1..base+T
    vector<int> curPerm(T);
    for (int i = 0; i < T; i++) curPerm[i] = a[sufStart + i] - base;
    int curId = encodePerm(curPerm);

    // Apply inverse moves from curId back to identity
    while (curId != id0) {
        int code = moveCode[curId];
        int s = code / 2;
        int dir = code % 2;
        int invDir = dir ^ 1;
        int l = sufStart + s;
        doRotate(x, pos, l, invDir);
        curId = parent[curId];
    }

    cout << x << "\n" << (int)ops.size() << "\n";
    for (auto &op : ops) {
        cout << op.l << " " << op.r << " " << op.dir << "\n";
    }
    return 0;
}