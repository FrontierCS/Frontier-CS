#include <bits/stdc++.h>
using namespace std;

struct Op {
    int l, r, dir;
};

static array<int, 8> fact7;

static int rankPerm7(const array<int,7>& p) {
    int rank = 0;
    bool used[7] = {false,false,false,false,false,false,false};
    for (int i = 0; i < 7; i++) {
        int smaller = 0;
        for (int v = 0; v < p[i]; v++) if (!used[v]) smaller++;
        rank += smaller * fact7[6 - i];
        used[p[i]] = true;
    }
    return rank;
}

static array<int,7> unrankPerm7(int rank) {
    array<int,7> p{};
    vector<int> elems = {0,1,2,3,4,5,6};
    for (int i = 0; i < 7; i++) {
        int f = fact7[6 - i];
        int idx = rank / f;
        rank %= f;
        p[i] = elems[idx];
        elems.erase(elems.begin() + idx);
    }
    return p;
}

static void applyOp7(array<int,7>& p, int type, int dir) {
    // type 0: rotate [0..5], type 1: rotate [1..6]
    if (type == 0) {
        if (dir == 0) { // left
            int tmp = p[0];
            for (int i = 0; i < 5; i++) p[i] = p[i+1];
            p[5] = tmp;
        } else { // right
            int tmp = p[5];
            for (int i = 5; i > 0; i--) p[i] = p[i-1];
            p[0] = tmp;
        }
    } else {
        if (dir == 0) { // left
            int tmp = p[1];
            for (int i = 1; i < 6; i++) p[i] = p[i+1];
            p[6] = tmp;
        } else { // right
            int tmp = p[6];
            for (int i = 6; i > 1; i--) p[i] = p[i-1];
            p[1] = tmp;
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

    vector<Op> ops;

    auto output = [&](int X) {
        cout << X << "\n" << ops.size() << "\n";
        for (auto &op : ops) cout << op.l << " " << op.r << " " << op.dir << "\n";
    };

    if (n == 1) {
        cout << 1 << "\n" << 0 << "\n";
        return 0;
    }

    int X;
    if (n <= 6) X = 2;
    else X = 6;

    vector<int> pos(n + 1);
    for (int i = 1; i <= n; i++) pos[a[i]] = i;

    auto applyRotation = [&](int l, int dir) {
        int r = l + X - 1;
        if (dir == 0) { // left
            int tmp = a[l];
            for (int i = l; i < r; i++) a[i] = a[i+1];
            a[r] = tmp;
        } else { // right
            int tmp = a[r];
            for (int i = r; i > l; i--) a[i] = a[i-1];
            a[l] = tmp;
        }
        for (int i = l; i <= r; i++) pos[a[i]] = i;
        ops.push_back({l, r, dir});
    };

    if (X == 2) {
        for (int i = 1; i <= n; i++) {
            while (pos[i] > i) {
                int p = pos[i];
                applyRotation(p - 1, 0);
            }
        }
        output(X);
        return 0;
    }

    // Precompute BFS on permutations of length 7 with x=6, windows starting at 0 or 1
    fact7[0] = 1;
    for (int i = 1; i <= 7; i++) fact7[i] = fact7[i-1] * i;

    const int S = 5040;
    vector<array<int,7>> idToPerm(S);
    for (int id = 0; id < S; id++) idToPerm[id] = unrankPerm7(id);

    vector<int> parent(S, -1);
    vector<uint8_t> opCode(S, 0);
    queue<int> q;
    parent[0] = 0;
    q.push(0);

    int visited = 1;
    while (!q.empty()) {
        int id = q.front(); q.pop();
        const auto &perm = idToPerm[id];
        for (int code = 0; code < 4; code++) {
            int type = code >> 1;
            int dir = code & 1;
            array<int,7> p2 = perm;
            applyOp7(p2, type, dir);
            int id2 = rankPerm7(p2);
            if (parent[id2] == -1) {
                parent[id2] = id;
                opCode[id2] = (uint8_t)code;
                q.push(id2);
                visited++;
            }
        }
    }

    // Main sorting for n >= 7, X=6: fix positions 1..n-7
    int lastFixed = n - 7;
    for (int i = 1; i <= lastFixed; i++) {
        int p = pos[i];
        while (p - 5 >= i) {
            applyRotation(p - 5, 1); // right rotate [p-5..p]
            p -= 5;
        }
        while (p > i) {
            applyRotation(i, 0); // left rotate [i..i+5]
            p--;
        }
    }

    // Sort tail of length 7: positions tStart..n where tStart = n-6
    int tStart = n - 6;
    array<int,7> tail{};
    for (int k = 0; k < 7; k++) tail[k] = a[tStart + k] - tStart; // 0..6
    int curId = rankPerm7(tail);

    while (curId != 0) {
        uint8_t code = opCode[curId];
        int type = code >> 1;
        int dir = code & 1;
        int invDir = dir ^ 1;
        int realStart = tStart + type; // type 0->tStart, type1->tStart+1
        applyRotation(realStart, invDir);
        curId = parent[curId];
    }

    output(X);
    return 0;
}