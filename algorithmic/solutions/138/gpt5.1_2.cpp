#include <bits/stdc++.h>
using namespace std;

struct Op {
    int op, x, y;
};

int id(char c) {
    if ('a' <= c && c <= 'z') return c - 'a';
    if ('A' <= c && c <= 'Z') return 26 + (c - 'A');
    if ('0' <= c && c <= '9') return 52 + (c - '0');
    return -1;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m, k;
    if (!(cin >> n >> m >> k)) return 0;

    vector<string> init(n), target(n);
    for (int i = 0; i < n; ++i) cin >> init[i];

    string blank;
    getline(cin, blank); // consume endline after init
    getline(cin, blank); // consume blank line before target (may be empty or first row)

    if ((int)blank.size() == m) {
        // blank actually is first row of target
        target[0] = blank;
        for (int i = 1; i < n; ++i) cin >> target[i];
    } else {
        // blank is empty, read n rows
        for (int i = 0; i < n; ++i) cin >> target[i];
    }

    // read presets but ignore them
    for (int pi = 0; pi < k; ++pi) {
        getline(cin, blank); // consume endline or blank
        if (blank.size() == 0) {
            // ok
        } else {
            // it was a line with numbers, push back into stream
            stringstream ss(blank);
            int np, mp;
            if (ss >> np >> mp) {
                // already read size; now read matrix lines
                string row;
                for (int i = 0; i < np; ++i) cin >> row;
                continue;
            }
        }
        int np, mp;
        cin >> np >> mp;
        string row;
        for (int i = 0; i < np; ++i) cin >> row;
    }

    const int ALPHA = 62;
    vector<int> cntInit(ALPHA, 0), cntTar(ALPHA, 0);
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < m; ++j) {
            ++cntInit[id(init[i][j])];
            ++cntTar[id(target[i][j])];
        }

    if (cntInit != cntTar) {
        cout << -1 << '\n';
        return 0;
    }

    // Build snake path
    int N = n * m;
    vector<pair<int,int>> path(N);
    int idx = 0;
    for (int i = 0; i < n; ++i) {
        if (i % 2 == 0) {
            for (int j = 0; j < m; ++j)
                path[idx++] = {i, j};
        } else {
            for (int j = m - 1; j >= 0; --j)
                path[idx++] = {i, j};
        }
    }

    // Flatten arrays along path
    vector<char> curArr(N), tarArr(N);
    for (int i = 0; i < N; ++i) {
        auto [x, y] = path[i];
        curArr[i] = init[x][y];
        tarArr[i] = target[x][y];
    }

    vector<string> board = init;
    vector<Op> ops;

    auto addSwap = [&](int ax, int ay, int bx, int by) {
        int op;
        if (ax == bx) {
            if (ay + 1 == by) op = -1;       // right
            else if (ay - 1 == by) op = -2;  // left
            else return;
        } else if (ay == by) {
            if (ax + 1 == bx) op = -4;       // down
            else if (ax - 1 == bx) op = -3;  // up
            else return;
        } else return;
        ops.push_back({op, ax + 1, ay + 1});
        swap(board[ax][ay], board[bx][by]);
    };

    // Bubble sort-like reordering along path
    for (int i = 0; i < N; ++i) {
        if (curArr[i] == tarArr[i]) continue;
        int j = i + 1;
        while (j < N && curArr[j] != tarArr[i]) ++j;
        // since multisets equal, such j must exist
        for (int p = j - 1; p >= i; --p) {
            swap(curArr[p], curArr[p + 1]);
            auto [x1, y1] = path[p];
            auto [x2, y2] = path[p + 1];
            addSwap(x1, y1, x2, y2);
        }
    }

    if ((int)ops.size() > 400000) {
        // Should not happen with N<=400 and this algorithm, but just in case
        cout << -1 << '\n';
        return 0;
    }

    cout << ops.size() << '\n';
    for (auto &op : ops) {
        cout << op.op << ' ' << op.x << ' ' << op.y << '\n';
    }

    return 0;
}