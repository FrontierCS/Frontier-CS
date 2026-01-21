#include <bits/stdc++.h>
using namespace std;

struct Op {
    int l, r, d;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if (!(cin >> n)) return 0;
    vector<int> a(n + 1);
    for (int i = 1; i <= n; ++i) cin >> a[i];

    int x;
    if (n >= 5) x = 4;
    else if (n >= 2) x = 2;
    else x = 1;

    vector<int> pos(n + 1);
    for (int i = 1; i <= n; ++i) pos[a[i]] = i;

    vector<Op> ops;

    auto apply = [&](int l, int dir) {
        int r = l + x - 1;
        if (l < 1 || r > n) return;
        ops.push_back({l, r, dir});
        if (x == 1) return;
        if (dir == 1) { // right shift
            int tmp = a[r];
            for (int j = r; j > l; --j) a[j] = a[j - 1];
            a[l] = tmp;
        } else { // left shift
            int tmp = a[l];
            for (int j = l; j < r; ++j) a[j] = a[j + 1];
            a[r] = tmp;
        }
        for (int j = l; j <= r; ++j) pos[a[j]] = j;
    };

    if (x >= 2) {
        int S;
        if (n >= 2 * x - 1) S = n - 2 * x + 2;
        else S = 1;

        // Stage A: place positions 1..S-1
        for (int i = 1; i <= S - 1; ++i) {
            int pv = pos[i];
            while (pv > i + x - 1) {
                apply(pv - x + 1, 1);
                pv -= (x - 1);
            }
            int r = i + x - 1;
            int t = r - pv;
            for (int k = 0; k < t; ++k) apply(i, 1);
            apply(i, 1);
        }

        // Stage B: BFS on zone S..n (length L)
        int L = n - S + 1;
        if (L >= x) {
            vector<int> start(L);
            for (int i = 0; i < L; ++i) start[i] = a[S + i] - S;
            vector<int> goal(L);
            iota(goal.begin(), goal.end(), 0);

            auto factorial = [&](int m) {
                vector<int> f(m + 1, 1);
                for (int i = 1; i <= m; ++i) f[i] = f[i - 1] * i;
                return f;
            };
            vector<int> fact = factorial(L);

            auto rankPerm = [&](const vector<int>& p) {
                int r = 0;
                for (int i = 0; i < (int)p.size(); ++i) {
                    int c = 0;
                    for (int j = i + 1; j < (int)p.size(); ++j) if (p[j] < p[i]) ++c;
                    r += c * fact[(int)p.size() - 1 - i];
                }
                return r;
            };
            auto unrankPerm = [&](int r) {
                vector<int> elems(L);
                iota(elems.begin(), elems.end(), 0);
                vector<int> p(L);
                for (int i = 0; i < L; ++i) {
                    int f = fact[L - 1 - i];
                    int idx = (f == 0 ? 0 : r / f);
                    r = (f == 0 ? 0 : r % f);
                    p[i] = elems[idx];
                    elems.erase(elems.begin() + idx);
                }
                return p;
            };

            int sRank = rankPerm(start);
            int gRank = rankPerm(goal);

            int totalStates = fact[L];
            vector<int> parent(totalStates, -1);
            vector<short> moveL(totalStates, -1);
            vector<short> moveD(totalStates, -1);

            queue<int> q;
            q.push(sRank);
            parent[sRank] = -2;

            while (!q.empty() && parent[gRank] == -1) {
                int cur = q.front(); q.pop();
                vector<int> curp = unrankPerm(cur);
                for (int lOff = 0; lOff <= L - x; ++lOff) {
                    // dir = 0 (left)
                    {
                        vector<int> np = curp;
                        int lz = lOff, rz = lOff + x - 1;
                        int tmp = np[lz];
                        for (int j = lz; j < rz; ++j) np[j] = np[j + 1];
                        np[rz] = tmp;
                        int nr = rankPerm(np);
                        if (parent[nr] == -1) {
                            parent[nr] = cur;
                            moveL[nr] = (short)lz;
                            moveD[nr] = 0;
                            q.push(nr);
                        }
                    }
                    // dir = 1 (right)
                    {
                        vector<int> np = curp;
                        int lz = lOff, rz = lOff + x - 1;
                        int tmp = np[rz];
                        for (int j = rz; j > lz; --j) np[j] = np[j - 1];
                        np[lz] = tmp;
                        int nr = rankPerm(np);
                        if (parent[nr] == -1) {
                            parent[nr] = cur;
                            moveL[nr] = (short)lz;
                            moveD[nr] = 1;
                            q.push(nr);
                        }
                    }
                }
            }

            if (sRank != gRank) {
                // reconstruct path
                vector<pair<int,int>> path;
                int cur = gRank;
                while (cur != sRank) {
                    int lz = moveL[cur];
                    int d = moveD[cur];
                    path.push_back({lz, d});
                    cur = parent[cur];
                }
                reverse(path.begin(), path.end());
                for (auto &e : path) {
                    int lglobal = S + e.first;
                    apply(lglobal, e.second);
                }
            }
        }
    }

    // Output
    cout << x << " " << (int)ops.size() << "\n";
    for (auto &op : ops) {
        cout << op.l << " " << op.r << " " << op.d << "\n";
    }
    return 0;
}