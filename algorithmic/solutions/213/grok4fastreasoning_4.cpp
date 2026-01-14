#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<int> a(n + 1);
    for (int i = 1; i <= n; i++) {
        cin >> a[i];
    }
    vector<tuple<int, int, int>> ops;
    int xx;
    bool small_n = (n <= 11);
    xx = small_n ? 2 : 6;
    for (int k = 1; k <= n; k++) {
        bool do_place = small_n || (k <= n - xx + 1);
        if (do_place) {
            int j;
            for (j = k; j <= n; j++) {
                if (a[j] == k) {
                    break;
                }
            }
            while (j > k) {
                int dist = j - k;
                int l;
                bool can_jump = (dist >= xx - 1) && ((l = j - xx + 1) >= k);
                if (can_jump) {
                    int r = l + xx - 1;
                    ops.emplace_back(l, r, 0);
                    int temp = a[l];
                    for (int p = l; p < r; p++) {
                        a[p] = a[p + 1];
                    }
                    a[r] = temp;
                    j = l;
                } else {
                    l = max(k, j - xx + 1);
                    int r = l + xx - 1;
                    ops.emplace_back(l, r, 0);
                    int temp = a[l];
                    for (int p = l; p < r; p++) {
                        a[p] = a[p + 1];
                    }
                    a[r] = temp;
                    j--;
                }
            }
        }
    }
    if (!small_n) {
        int s = xx - 1;
        int affected_len = 2 * xx - 1;
        int ast = max(1, n - affected_len + 1);
        int mm = n - ast + 1;
        vector<int> curr_small(mm);
        for (int i = 0; i < mm; i++) {
            curr_small[i] = a[ast + i];
        }
        vector<int> nums = curr_small;
        sort(nums.begin(), nums.end());
        map<int, int> v2r;
        for (int i = 0; i < mm; i++) {
            v2r[nums[i]] = i;
        }
        vector<int> tperm(mm);
        for (int i = 0; i < mm; i++) {
            int val = ast + i;
            tperm[i] = v2r[val];
        }
        uint64_t target_st = 0;
        for (int i = 0; i < mm; i++) {
            target_st |= ((uint64_t)tperm[i] << (i * 4LL));
        }
        vector<int> iperm(mm);
        for (int i = 0; i < mm; i++) {
            iperm[i] = v2r[curr_small[i]];
        }
        uint64_t start_st = 0;
        for (int i = 0; i < mm; i++) {
            start_st |= ((uint64_t)iperm[i] << (i * 4LL));
        }
        if (start_st != target_st) {
            unordered_set<uint64_t> visited;
            unordered_map<uint64_t, uint64_t> parent;
            unordered_map<uint64_t, pair<int, int>> move_to;
            queue<uint64_t> q;
            q.push(start_st);
            visited.insert(start_st);
            parent[start_st] = 0;
            bool found = false;
            uint64_t found_st = 0;
            while (!q.empty() && !found) {
                uint64_t cur = q.front();
                q.pop();
                int num_ii = mm - xx + 1;
                for (int ii = 0; ii < num_ii; ii++) {
                    for (int dr = 0; dr < 2; dr++) {
                        uint64_t newst = cur;
                        vector<int> seg(xx);
                        for (int t = 0; t < xx; t++) {
                            int pos = ii + t;
                            seg[t] = (cur >> (pos * 4LL)) & 15;
                        }
                        if (dr == 0) {
                            int temp = seg[0];
                            for (int t = 0; t < xx - 1; t++) {
                                seg[t] = seg[t + 1];
                            }
                            seg[xx - 1] = temp;
                        } else {
                            int temp = seg[xx - 1];
                            for (int t = xx - 1; t > 0; t--) {
                                seg[t] = seg[t - 1];
                            }
                            seg[0] = temp;
                        }
                        for (int t = 0; t < xx; t++) {
                            int pos = ii + t;
                            uint64_t val = seg[t];
                            newst = (newst & ~(15ULL << (pos * 4LL))) | (val << (pos * 4LL));
                        }
                        if (visited.find(newst) == visited.end()) {
                            visited.insert(newst);
                            q.push(newst);
                            parent[newst] = cur;
                            move_to[newst] = {ii, dr};
                            if (newst == target_st) {
                                found = true;
                                found_st = newst;
                                goto found_label;
                            }
                        }
                    }
                }
            }
        found_label:
            (void)0;
            if (found) {
                vector<tuple<int, int, int>> small_ops;
                uint64_t cst = target_st;
                while (cst != start_st) {
                    auto [ii, dr] = move_to[cst];
                    int l_abs = ast + ii;
                    int r_abs = l_abs + xx - 1;
                    small_ops.emplace_back(l_abs, r_abs, dr);
                    cst = parent[cst];
                }
                reverse(small_ops.begin(), small_ops.end());
                for (auto& tp : small_ops) {
                    ops.push_back(tp);
                    auto [ll, rr, dd] = tp;
                    if (dd == 0) {
                        int temp = a[ll];
                        for (int p = ll; p < rr; p++) {
                            a[p] = a[p + 1];
                        }
                        a[rr] = temp;
                    } else {
                        int temp = a[rr];
                        for (int p = rr; p > ll; p--) {
                            a[p] = a[p - 1];
                        }
                        a[ll] = temp;
                    }
                }
            }
        }
    }
    cout << xx << " " << ops.size() << endl;
    for (auto [l, r, d] : ops) {
        cout << l << " " << r << " " << d << endl;
    }
    return 0;
}