#include <bits/stdc++.h>
using namespace std;

struct BIT {
    int n = 0;
    vector<int> bit;
    BIT() = default;
    explicit BIT(int n_) { init(n_); }

    void init(int n_) {
        n = n_;
        bit.assign(n + 1, 0);
        for (int i = 1; i <= n; i++) bit[i] = 1;
        for (int i = 1; i <= n; i++) {
            int j = i + (i & -i);
            if (j <= n) bit[j] += bit[i];
        }
    }

    void add(int idx, int delta) {
        for (; idx <= n; idx += idx & -idx) bit[idx] += delta;
    }

    int sumPrefix(int idx) const {
        int res = 0;
        for (; idx > 0; idx -= idx & -idx) res += bit[idx];
        return res;
    }
};

static string toString128(__int128 x) {
    if (x == 0) return "0";
    bool neg = false;
    if (x < 0) { neg = true; x = -x; }
    string s;
    while (x > 0) {
        int d = (int)(x % 10);
        s.push_back(char('0' + d));
        x /= 10;
    }
    if (neg) s.push_back('-');
    reverse(s.begin(), s.end());
    return s;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<int> v(n + 1), pos(n + 1);
    for (int i = 1; i <= n; i++) {
        cin >> v[i];
        pos[v[i]] = i;
    }

    // Strategy A: keep longest suffix of values t..n already in increasing order in the permutation,
    // move values (t-1..1) to front in descending order.
    int t = n;
    while (t > 1 && pos[t - 1] < pos[t]) --t;

    long long movesA = t - 1;
    if (t > 1 && pos[t - 1] == 1) movesA--; // first move would be a no-op (x=1,y=1)

    __int128 costA = (__int128)(movesA + 1) * (movesA + 1);

    // Strategy B: fix from the end (selection to end), possibly fewer moves, but higher y costs.
    BIT bitB(n);
    long long sumB = 0, cntB = 0;
    int tot = n;
    for (int k = n; k >= 1; --k) {
        int x = bitB.sumPrefix(pos[k]);
        int y = tot;
        if (x != y) {
            cntB++;
            sumB += y;
        }
        bitB.add(pos[k], -1);
        tot--;
    }
    __int128 costB = (__int128)(sumB + 1) * (cntB + 1);

    vector<pair<int,int>> moves;
    long long sumY = 0;

    if (costB < costA) {
        // Generate strategy B moves
        BIT bit(n);
        moves.reserve((size_t)cntB);
        int tot2 = n;
        for (int k = n; k >= 1; --k) {
            int x = bit.sumPrefix(pos[k]);
            int y = tot2;
            if (x != y) {
                moves.push_back({x, y});
                sumY += y;
            }
            bit.add(pos[k], -1);
            tot2--;
        }
    } else {
        // Generate strategy A moves
        BIT bit(n);
        moves.reserve((size_t)max(0LL, movesA));
        int cntMoved = 0;
        for (int k = t - 1; k >= 1; --k) {
            int rank = bit.sumPrefix(pos[k]);
            int x = cntMoved + rank;
            if (x != 1) {
                moves.push_back({x, 1});
                sumY += 1;
            }
            bit.add(pos[k], -1);
            cntMoved++;
        }
    }

    __int128 finalCost = (__int128)(sumY + 1) * ((long long)moves.size() + 1);

    string out;
    out.reserve(64 + moves.size() * 20);
    out += toString128(finalCost);
    out += ' ';
    out += to_string(moves.size());
    out += '\n';
    for (auto [x, y] : moves) {
        out += to_string(x);
        out += ' ';
        out += to_string(y);
        out += '\n';
    }
    cout << out;
    return 0;
}