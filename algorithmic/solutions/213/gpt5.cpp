#include <bits/stdc++.h>
using namespace std;

struct Op {
    int l, r, d;
};

int n, x;
vector<int> a, pos;
vector<Op> ops;

void apply_shift(int l, int r, int d) {
    // d: 0 = left, 1 = right
    // assumes r - l + 1 == x
    if (l < 1 || r > n || r - l + 1 != x) return; // safety
    if (d == 0) {
        int first = a[l];
        for (int k = l; k < r; ++k) {
            a[k] = a[k + 1];
            pos[a[k]] = k;
        }
        a[r] = first;
        pos[first] = r;
    } else {
        int last = a[r];
        for (int k = r; k > l; --k) {
            a[k] = a[k - 1];
            pos[a[k]] = k;
        }
        a[l] = last;
        pos[last] = l;
    }
    ops.push_back({l, r, d});
}

vector<vector<int>> compute_swap_sequences(int x) {
    // Build BFS for region size S = x + 1 using two windows:
    // W1: positions [0..x-1]
    // W2: positions [1..x]
    int S = x + 1;
    // Precompute mapping of positions for 4 ops:
    // 0: left W1, 1: right W1, 2: left W2, 3: right W2
    vector<array<int,4>> mp(S);
    for (int p = 0; p < S; ++p) {
        // op 0: left W1
        if (0 <= p && p <= x - 1) mp[p][0] = (p == 0 ? x - 1 : p - 1);
        else mp[p][0] = p;
        // op 1: right W1
        if (0 <= p && p <= x - 1) mp[p][1] = (p == x - 1 ? 0 : p + 1);
        else mp[p][1] = p;
        // op 2: left W2
        if (1 <= p && p <= x) mp[p][2] = (p == 1 ? x : p - 1);
        else mp[p][2] = p;
        // op 3: right W2
        if (1 <= p && p <= x) mp[p][3] = (p == x ? 1 : p + 1);
        else mp[p][3] = p;
    }

    auto encode = [&](const vector<int>& vec)->uint64_t {
        uint64_t code = 0;
        for (int i = 0; i < S; ++i) {
            code |= (uint64_t)(vec[i] & 0xF) << (4*i);
        }
        return code;
    };
    auto decode = [&](uint64_t code)->vector<int> {
        vector<int> vec(S);
        for (int i = 0; i < S; ++i) {
            vec[i] = (code >> (4*i)) & 0xF;
        }
        return vec;
    };

    vector<int> id(S);
    for (int i = 0; i < S; ++i) id[i] = i;
    uint64_t start = encode(id);

    unordered_map<uint64_t, pair<uint64_t,int>> parent;
    parent.reserve(10000);
    queue<uint64_t> q;
    q.push(start);
    parent[start] = {start, -1};

    while (!q.empty()) {
        uint64_t cur = q.front(); q.pop();
        vector<int> mapp = decode(cur);
        for (int op = 0; op < 4; ++op) {
            vector<int> nxt(S);
            for (int j = 0; j < S; ++j) {
                int p = mapp[j];
                nxt[j] = mp[p][op];
            }
            uint64_t code = encode(nxt);
            if (!parent.count(code)) {
                parent[code] = {cur, op};
                q.push(code);
            }
        }
    }

    vector<vector<int>> seqs(x); // for t = 0..x-1 -> swap positions t and t+1
    for (int t = 0; t < x; ++t) {
        vector<int> target(S);
        for (int i = 0; i < S; ++i) target[i] = i;
        swap(target[t], target[t+1]);
        uint64_t goal = encode(target);
        // reconstruct path from start to goal
        vector<int> seq;
        if (!parent.count(goal)) {
            // Should not happen for even x
            // Fallback: empty (no-op)
            seqs[t] = seq;
            continue;
        }
        uint64_t cur = goal;
        while (cur != start) {
            auto pr = parent[cur];
            int op = pr.second;
            seq.push_back(op);
            cur = pr.first;
        }
        reverse(seq.begin(), seq.end());
        seqs[t] = seq;
    }
    return seqs;
}

int choose_x(int n) {
    if (n == 1) return 1;
    if (n == 2) return 2;
    int cand = 6;
    if (n - 1 < cand) cand = n - 1;
    if (cand % 2 == 1) cand--;
    if (cand < 2) cand = 2;
    return cand;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n)) return 0;
    a.assign(n + 1, 0);
    for (int i = 1; i <= n; ++i) cin >> a[i];

    x = choose_x(n);
    pos.assign(n + 1, 0);
    for (int i = 1; i <= n; ++i) pos[a[i]] = i;

    // Handle tiny cases directly
    if (n == 1) {
        cout << x << "\n";
        cout << 0 << "\n";
        return 0;
    }
    if (n == 2) {
        if (a[1] > a[2]) {
            apply_shift(1, 2, 0); // left shift swaps
        }
        cout << x << "\n";
        cout << (int)ops.size() << "\n";
        for (auto &op : ops) {
            cout << op.l << " " << op.r << " " << op.d << "\n";
        }
        return 0;
    }

    // Stage A: fix first n - x - 1 positions
    int limit_prefix = max(0, n - x - 1);
    for (int i = 1; i <= limit_prefix; ++i) {
        int p = pos[i];
        while (p - i >= x - 1) {
            int l = p - x + 1, r = p;
            apply_shift(l, r, 1); // right
            p = pos[i];
        }
        int delta = p - i;
        if (delta > 0) {
            int t = x - delta;
            for (int k = 0; k < t; ++k) {
                apply_shift(i, i + x - 1, 1); // right on [i, i+x-1]
            }
        }
    }

    // Stage B: sort tail region of size S = x + 1 using two windows
    int L = max(1, n - x);
    int R = n;
    int S = R - L + 1;

    // For safety, if S < 2, nothing to do
    if (S >= 2) {
        // If S == 2 and x == 2, we can swap if needed
        if (S == 2) {
            // Only one window [L, L+1]
            if (a[L] > a[L+1]) apply_shift(L, L+1, 0);
        } else {
            // Ensure we can use two windows inside [L..R], thus S == x+1 typically
            // If S > x+1 (shouldn't happen), we can still restrict to last x+1 by shifting L.
            if (S > x + 1) {
                L = R - (x + 1) + 1;
                S = x + 1;
            }
            // If S == x (rare), fallback to simple method: simulate needed swaps using larger region if possible
            if (S == x) {
                // Expand left by 1 if possible to get two windows
                if (L > 1) {
                    L = L - 1;
                    S = x + 1;
                } else if (R < n) {
                    // expand right (shouldn't happen as R==n in our plan)
                    R = R + 1;
                    S = x + 1;
                }
            }
            if (S == x + 1) {
                auto swapSeqs = compute_swap_sequences(x);
                // Bubble sort region [L..R]
                for (int pass = 0; pass < S - 1; ++pass) {
                    bool changed = false;
                    for (int j = L; j < R; ++j) {
                        if (a[j] > a[j + 1]) {
                            int t = j - L; // swap positions t and t+1 in region
                            const vector<int> &seq = swapSeqs[t];
                            for (int op : seq) {
                                if (op == 0) apply_shift(L, L + x - 1, 0); // left W1
                                else if (op == 1) apply_shift(L, L + x - 1, 1); // right W1
                                else if (op == 2) apply_shift(L + 1, L + x, 0); // left W2
                                else apply_shift(L + 1, L + x, 1); // right W2
                            }
                            changed = true;
                        }
                    }
                    if (!changed) break;
                }
            } else {
                // Fallback: if we still don't have S == x+1 (extremely rare), try simple adjacent swapping using windows touching region.
                // We'll try to use [L, L+x-1] and [L+1, L+x] if possible.
                if (L + x - 1 <= n && L + 1 + x - 1 <= n) {
                    auto swapSeqs = compute_swap_sequences(x);
                    for (int pass = 0; pass < S - 1; ++pass) {
                        bool changed = false;
                        for (int j = L; j < R; ++j) {
                            if (a[j] > a[j + 1]) {
                                int t = j - L;
                                const vector<int> &seq = swapSeqs[t];
                                for (int op : seq) {
                                    if (op == 0) apply_shift(L, L + x - 1, 0);
                                    else if (op == 1) apply_shift(L, L + x - 1, 1);
                                    else if (op == 2) apply_shift(L + 1, L + x, 0);
                                    else apply_shift(L + 1, L + x, 1);
                                }
                                changed = true;
                            }
                        }
                        if (!changed) break;
                    }
                } else {
                    // As an ultimate fallback (should not be needed), perform adjacent swaps using x=2 emulation if possible.
                    // Not implemented as it's unlikely to be hit with chosen x.
                }
            }
        }
    }

    cout << x << "\n";
    cout << (int)ops.size() << "\n";
    for (auto &op : ops) {
        cout << op.l << " " << op.r << " " << op.d << "\n";
    }

    return 0;
}