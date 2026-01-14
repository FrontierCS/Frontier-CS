#include <iostream>
#include <vector>
#include <algorithm>
#include <map>
#include <cmath>
#include <tuple>

using namespace std;

const int MAXN = 4097;
const int MAX_SETS = 2200005;
const int LOGN = 12;

int n, q;
int a[MAXN];
int pos[MAXN];

struct SetInfo {
    int f, g;
};
SetInfo sets[MAX_SETS];
vector<pair<int, int>> merges;
int cnt;

int merge_sets(int u, int v) {
    if (u == 0) return v;
    if (v == 0) return u;
    
    if (sets[u].g < sets[v].f) {
        merges.push_back({u, v});
        cnt++;
        sets[cnt] = {sets[u].f, sets[v].g};
        return cnt;
    } else {
        merges.push_back({v, u});
        cnt++;
        sets[cnt] = {sets[v].f, sets[u].g};
        return cnt;
    }
}

map<tuple<int, int, int, int>, int> get_set_memo;
int get_set(int k, int i, int v_min, int v_max) {
    if (v_min > v_max) return 0;
    
    auto key = make_tuple(k, i, v_min, v_max);
    if (get_set_memo.count(key)) {
        return get_set_memo[key];
    }
    
    if (v_min == v_max) {
        int p = pos[v_min];
        if (p >= i && p < i + (1 << k)) {
            return p;
        }
        return 0;
    }
    
    int v_mid = v_min + (v_max - v_min) / 2;
    int s1 = get_set(k, i, v_min, v_mid);
    int s2 = get_set(k, i, v_mid + 1, v_max);
    return get_set_memo[key] = merge_sets(s1, s2);
}

map<tuple<int, int, int, int, int, int>, int> general_merge_memo;
int general_merge(int k1, int i1, int k2, int i2, int v_min, int v_max) {
    if (v_min > v_max) return 0;
    
    auto key = make_tuple(k1, i1, k2, i2, v_min, v_max);
    if (general_merge_memo.count(key)) {
        return general_merge_memo[key];
    }
    
    if (v_min == v_max) {
        int p = pos[v_min];
        bool in_r1 = (p >= i1 && p < i1 + (1 << k1));
        bool in_r2 = (p >= i2 && p < i2 + (1 << k2));
        if (in_r1 || in_r2) {
            return p;
        }
        return 0;
    }
    
    int v_mid = v_min + (v_max - v_min) / 2;
    int res1 = general_merge(k1, i1, k2, i2, v_min, v_mid);
    int res2 = general_merge(k1, i1, k2, i2, v_mid + 1, v_max);
    return general_merge_memo[key] = merge_sets(res1, res2);
}

int st[LOGN + 1][MAXN];
int query_ans[1 << 16];

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n >> q;
    for (int i = 1; i <= n; ++i) {
        cin >> a[i];
        pos[a[i]] = i;
    }

    cnt = n;
    for (int i = 1; i <= n; ++i) {
        sets[i] = {a[i], a[i]};
        st[0][i] = i;
    }
    
    for (int k = 1; k <= LOGN; ++k) {
        if ((1 << k) > n) break;
        for (int i = 1; i + (1 << k) <= n + 1; ++i) {
            int s1 = st[k - 1][i];
            int s2 = st[k - 1][i + (1 << (k - 1))];

            if (sets[s1].g < sets[s2].f) {
                st[k][i] = merge_sets(s1, s2);
            } else if (sets[s2].g < sets[s1].f) {
                 st[k][i] = merge_sets(s2, s1);
            } else {
                st[k][i] = general_merge(k - 1, i, k - 1, i + (1 << (k - 1)), 1, n);
            }
        }
    }
    
    for (int i = 0; i < q; ++i) {
        int l, r;
        cin >> l >> r;
        if (l == r) {
            query_ans[i] = l;
            continue;
        }
        int k = log2(r - l + 1);
        int s1 = st[k][l];
        int s2 = st[k][r - (1 << k) + 1];
        
        if (sets[s1].g < sets[s2].f) {
            query_ans[i] = merge_sets(s1, s2);
        } else if (sets[s2].g < sets[s1].f) {
            query_ans[i] = merge_sets(s2, s1);
        } else {
            query_ans[i] = general_merge(k, l, k, r - (1 << k) + 1, 1, n);
        }
    }

    cout << cnt << "\n";
    for (const auto& p : merges) {
        cout << p.first << " " << p.second << "\n";
    }
    for (int i = 0; i < q; ++i) {
        cout << query_ans[i] << (i == q - 1 ? "" : " ");
    }
    cout << "\n";

    return 0;
}