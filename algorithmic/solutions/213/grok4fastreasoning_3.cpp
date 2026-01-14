#include <bits/stdc++.h>
using namespace std;

using u64 = uint64_t;

u64 pack(const vector<int>& pp, int kk) {
    u64 s = 0;
    for (int j = 0; j < kk; j++) {
        s |= (static_cast<u64>(pp[j]) << (4 * j));
    }
    return s;
}

vector<int> unpack(u64 s, int kk) {
    vector<int> pp(kk);
    for (int j = 0; j < kk; j++) {
        pp[j] = (s >> (4 * j)) & 15;
    }
    return pp;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<int> a(n + 1);
    for (int i = 1; i <= n; i++) {
        cin >> a[i];
    }

    int x = (n == 1 ? 1 : min(6, n));
    int max_i = n - x + 1;
    if (max_i < 1) max_i = n;

    vector<tuple<int, int, int>> operations;

    for (int i = 1; i <= max_i; i++) {
        int target = i;
        int pos = 0;
        for (int j = i; j <= n; j++) {
            if (a[j] == target) {
                pos = j;
                break;
            }
        }
        // jumping
        while (pos - i >= x - 1) {
            int start = pos - x + 1;
            // right shift dir=1
            operations.emplace_back(start, pos, 1);
            // apply
            int last = a[pos];
            for (int j = pos; j > start; j--) {
                a[j] = a[j - 1];
            }
            a[start] = last;
            pos = start;
        }
        // final left shifts
        int rr = pos - i;
        if (rr > 0) {
            int start_seg = i;
            int end_seg = i + x - 1;
            for (int t = 0; t < rr; t++) {
                operations.emplace_back(start_seg, end_seg, 0);
                // apply left
                int first = a[start_seg];
                for (int j = start_seg; j < end_seg; j++) {
                    a[j] = a[j + 1];
                }
                a[end_seg] = first;
            }
        }
    }

    // now suffix BFS
    int kk = min(9, n);
    int bbase = n - kk + 1;
    if (bbase < 1) bbase = 1;
    kk = n - bbase + 1;

    vector<int> init(kk);
    for (int j = 0; j < kk; j++) {
        int posi = bbase + j;
        init[j] = a[posi] - bbase;
    }
    u64 start_st = pack(init, kk);

    vector<int> targ(kk);
    for (int j = 0; j < kk; j++) targ[j] = j;
    u64 target_st = pack(targ, kk);

    if (start_st != target_st) {
        // BFS
        vector<int> seg_starts;
        for (int st = 0; st <= kk - x; st++) {
            seg_starts.push_back(st);
        }
        int m_segs = seg_starts.size();

        unordered_map<u64, pair<u64, int>> came_from;
        queue<u64> q;
        q.push(start_st);
        came_from[start_st] = {0, -1};

        bool found = false;
        while (!q.empty() && !found) {
            u64 cur = q.front();
            q.pop();
            if (cur == target_st) {
                found = true;
                continue;
            }
            vector<int> pp = unpack(cur, kk);
            for (int si = 0; si < m_segs; si++) {
                int l_local = seg_starts[si];
                int r_local = l_local + x - 1;
                for (int ddir = 0; ddir < 2; ddir++) {
                    vector<int> np = pp;
                    if (ddir == 0) { // left
                        int fi = np[l_local];
                        for (int jj = l_local; jj < r_local; jj++) {
                            np[jj] = np[jj + 1];
                        }
                        np[r_local] = fi;
                    } else { // right
                        int la = np[r_local];
                        for (int jj = r_local; jj > l_local; jj--) {
                            np[jj] = np[jj - 1];
                        }
                        np[l_local] = la;
                    }
                    u64 ns = pack(np, kk);
                    if (came_from.find(ns) == came_from.end()) {
                        came_from[ns] = {cur, si * 2 + ddir};
                        q.push(ns);
                        if (ns == target_st) {
                            found = true;
                        }
                    }
                }
            }
        }

        // backtrack
        if (found) {
            vector<tuple<int, int, int>> suffix_ops;
            u64 current = target_st;
            while (current != start_st) {
                auto [prevv, mid] = came_from[current];
                int si = mid / 2;
                int ddir = mid % 2;
                int l_local = seg_starts[si];
                int l_global = bbase + l_local;
                int r_global = l_global + x - 1;
                suffix_ops.emplace_back(l_global, r_global, ddir);
                current = prevv;
            }
            reverse(suffix_ops.begin(), suffix_ops.end());
            for (auto& op : suffix_ops) {
                operations.push_back(op);
            }
        }
        // if not found, do nothing, but assume always found
    }

    // output
    int m = operations.size();
    cout << x << " " << m << "\n";
    for (auto& op : operations) {
        int l, r, d;
        tie(l, r, d) = op;
        cout << l << " " << r << " " << d << "\n";
    }

    return 0;
}