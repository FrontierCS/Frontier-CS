#include <bits/stdc++.h>
using namespace std;

struct Res {
    string expr;
    int type;
    int varid;
};

int compute_combine_cost(int t0, int c0, int v0, int t1, int c1, int v1, int v) {
    if (t0 == 1) return 0;
    if (t1 == 0) return c0;
    int and_c, and_t, and_v;
    if (t1 == 1) {
        and_c = 0;
        and_t = 2;
        and_v = v;
    } else if (t1 == 0) {
        and_c = 0;
        and_t = 0;
        and_v = -1;
    } else if (t1 == 2) {
        int w = v1;
        if (w == v) {
            and_c = 0;
            and_t = 2;
            and_v = v;
        } else {
            and_c = 1 + c1;
            and_t = 3;
            and_v = -1;
        }
    } else {
        and_c = 1 + c1;
        and_t = 3;
        and_v = -1;
    }
    if (and_t == 0) return c0;
    if (and_t == 1) return 0;
    if (t0 == 0) return and_c;
    if (t0 == 2 && and_t == 2) {
        int u = v0;
        int w = and_v;
        if (u == w) return 0;
        else return 1 + c0 + and_c;
    } else {
        return 1 + c0 + and_c;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    cin >> T;
    for (int t = 0; t < T; t++) {
        int n;
        cin >> n;
        string s;
        cin >> s;
        int N = 1 << n;
        assert((int)s.size() == N);
        bool is_monotone = true;
        for (int i = 0; i < n && is_monotone; i++) {
            int bit = 1 << i;
            for (int mask = 0; mask < N; mask++) {
                int low = mask & ~bit;
                int high = low | bit;
                if ((s[low] - '0') > (s[high] - '0')) {
                    is_monotone = false;
                    break;
                }
            }
        }
        if (!is_monotone) {
            cout << "No\n";
            continue;
        }
        vector<long long> pow3(n + 1, 1);
        for (int i = 1; i <= n; i++) {
            pow3[i] = pow3[i - 1] * 3;
        }
        int N3 = pow3[n];
        vector<int> mincost(N3, -1);
        vector<int> typ(N3, -1);
        vector<int> bestv(N3, -1);
        vector<int> bestvar(N3, -1);
        int root_id = 0;
        for (int i = 0; i < n; i++) {
            root_id += 2 * pow3[i];
        }
        function<void(int)> compute = [&](int state_id) {
            if (mincost[state_id] != -1) return;
            int minm = 0, maxm = 0;
            int temp = state_id;
            vector<int> status(n);
            for (int i = 0; i < n; i++) {
                int st = temp % 3;
                status[i] = st;
                temp /= 3;
                if (st == 1) {
                    minm |= (1 << i);
                    maxm |= (1 << i);
                } else if (st == 2) {
                    maxm |= (1 << i);
                }
            }
            char fminc = s[minm];
            char fmaxc = s[maxm];
            if (fminc == '1') {
                mincost[state_id] = 0;
                typ[state_id] = 1;
                return;
            }
            if (fmaxc == '0') {
                mincost[state_id] = 0;
                typ[state_id] = 0;
                return;
            }
            // mixed, check single
            int single_u = -1;
            for (int u = 0; u < n; u++) {
                if (status[u] != 2) continue;
                int min1 = minm | (1 << u);
                if (s[min1] != '1') continue;
                int max0 = maxm & ~(1 << u);
                if (s[max0] != '0') continue;
                single_u = u;
                break;
            }
            if (single_u != -1) {
                mincost[state_id] = 0;
                typ[state_id] = 2;
                bestvar[state_id] = single_u;
                return;
            }
            // split
            int min_cc = INT_MAX / 2;
            int best_vv = -1;
            for (int vv = 0; vv < n; vv++) {
                if (status[vv] != 2) continue;
                long long p3v = pow3[vv];
                int id_0 = state_id - 2LL * p3v;
                int id_1 = state_id - 1LL * p3v;
                compute(id_0);
                compute(id_1);
                int t0_ = typ[id_0];
                int c0_ = mincost[id_0];
                int v0_ = (t0_ == 2 ? bestvar[id_0] : -1);
                int t1_ = typ[id_1];
                int c1_ = mincost[id_1];
                int v1_ = (t1_ == 2 ? bestvar[id_1] : -1);
                int this_cc = compute_combine_cost(t0_, c0_, v0_, t1_, c1_, v1_, vv);
                if (this_cc < min_cc) {
                    min_cc = this_cc;
                    best_vv = vv;
                }
            }
            mincost[state_id] = min_cc;
            typ[state_id] = 3;
            bestv[state_id] = best_vv;
        };
        compute(root_id);
        // now build
        function<Res(int)> build_func = [&](int state_id) -> Res {
            int tt = typ[state_id];
            if (tt == 0) return {"F", 0, -1};
            if (tt == 1) return {"T", 1, -1};
            if (tt == 2) {
                int u = bestvar[state_id];
                char ch = 'a' + u;
                return {string(1, ch), 2, u};
            }
            // 3
            int v = bestv[state_id];
            long long p3v = pow3[v];
            int id0 = state_id - 2LL * p3v;
            int id1 = state_id - 1LL * p3v;
            Res left_r = build_func(id0);
            Res right_r = build_func(id1);
            // and_r
            Res and_r;
            char cv = 'a' + v;
            if (right_r.type == 1) {
                and_r.expr = string(1, cv);
                and_r.type = 2;
                and_r.varid = v;
            } else if (right_r.type == 0) {
                and_r.expr = "F";
                and_r.type = 0;
                and_r.varid = -1;
            } else if (right_r.type == 2) {
                int w = right_r.varid;
                if (w == v) {
                    and_r.expr = string(1, cv);
                    and_r.type = 2;
                    and_r.varid = v;
                } else {
                    char cw = 'a' + w;
                    and_r.expr = "(" + string(1, cv) + "&" + string(1, cw) + ")";
                    and_r.type = 3;
                    and_r.varid = -1;
                }
            } else {
                and_r.expr = "(" + string(1, cv) + "&" + right_r.expr + ")";
                and_r.type = 3;
                and_r.varid = -1;
            }
            // whole = left | and
            Res whole;
            if (left_r.type == 1) {
                whole.expr = "T";
                whole.type = 1;
                whole.varid = -1;
            } else if (and_r.type == 0) {
                whole = left_r;
            } else if (and_r.type == 1) {
                whole.expr = "T";
                whole.type = 1;
                whole.varid = -1;
            } else if (left_r.type == 0) {
                whole = and_r;
            } else if (left_r.type == 2 && and_r.type == 2) {
                int u = left_r.varid;
                int w = and_r.varid;
                if (u == w) {
                    char ch = 'a' + u;
                    whole.expr = string(1, ch);
                    whole.type = 2;
                    whole.varid = u;
                } else {
                    whole.expr = "(" + left_r.expr + "|" + and_r.expr + ")";
                    whole.type = 3;
                    whole.varid = -1;
                }
            } else {
                whole.expr = "(" + left_r.expr + "|" + and_r.expr + ")";
                whole.type = 3;
                whole.varid = -1;
            }
            return whole;
        };
        Res final_res = build_func(root_id);
        cout << "Yes\n" << final_res.expr << "\n";
    }
    return 0;
}