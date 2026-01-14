#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <functional>

#if defined(__GNUC__) || defined(__clang__)
#define BUILTIN_CLZ __builtin_clz
#else
#include <intrin.h>
#define BUILTIN_CLZ __lzcnt
#endif

const int MAXN = 4096 + 5;
const int LOGN = 13;

int n, q;
int a[MAXN];
int pos[MAXN];

int cnt;
std::vector<std::pair<int, int>> ops;

int st_min[LOGN][MAXN];
int seg_tree_node_set_id[4 * MAXN];

void build_rmq() {
    for (int i = 1; i <= n; ++i) {
        st_min[0][i] = a[i];
    }
    for (int k = 1; k < LOGN; ++k) {
        for (int i = 1; i + (1 << k) - 1 <= n; ++i) {
            st_min[k][i] = std::min(st_min[k - 1][i], st_min[k - 1][i + (1 << (k - 1))]);
        }
    }
}

int query_rmq(int l, int r) {
    if (l > r) return n + 1;
    int len = r - l + 1;
    int k = 31 - BUILTIN_CLZ(len);
    return std::min(st_min[k][l], st_min[k][r - (1 << k) + 1]);
}

int build_from_sorted_vals(const std::vector<int>& vals, int start, int end) {
    if (start == end - 1) {
        return pos[vals[start]];
    }
    int mid = start + (end - start) / 2;
    
    int left_id = build_from_sorted_vals(vals, start, mid);
    int right_id = build_from_sorted_vals(vals, mid, end);
    
    cnt++;
    ops.push_back({left_id, right_id});
    return cnt;
}

void build_seg_tree(int v, int tl, int tr) {
    if (tl == tr) {
        seg_tree_node_set_id[v] = tl;
        return;
    }
    int tm = tl + (tr - tl) / 2;
    build_seg_tree(v * 2, tl, tm);
    build_seg_tree(v * 2 + 1, tm + 1, tr);
    
    std::vector<int> vals;
    vals.reserve(tr - tl + 1);
    for (int i = tl; i <= tr; ++i) {
        vals.push_back(a[i]);
    }
    std::sort(vals.begin(), vals.end());
    
    seg_tree_node_set_id[v] = build_from_sorted_vals(vals, 0, vals.size());
}

struct NodeInfo {
    int id;
    int l, r;
};

void get_query_nodes_info(int v, int tl, int tr, int l, int r, std::vector<NodeInfo>& result) {
    if (l > r) {
        return;
    }
    if (l == tl && r == tr) {
        result.push_back({seg_tree_node_set_id[v], tl, tr});
        return;
    }
    int tm = tl + (tr - tl) / 2;
    get_query_nodes_info(v * 2, tl, tm, l, std::min(r, tm), result);
    get_query_nodes_info(v * 2 + 1, tm + 1, tr, std::max(l, tm + 1), r, result);
}

struct SetInfo {
    int id;
    int min_val;
};

bool compareSetInfo(const SetInfo& a, const SetInfo& b) {
    return a.min_val < b.min_val;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    
    std::cin >> n >> q;
    for (int i = 1; i <= n; ++i) {
        std::cin >> a[i];
        pos[a[i]] = i;
    }
    
    cnt = n;
    
    build_rmq();
    build_seg_tree(1, 1, n);
    
    std::vector<int> query_ans(q);
    
    for (int i = 0; i < q; ++i) {
        int l, r;
        std::cin >> l >> r;
        
        std::vector<NodeInfo> nodes_info;
        get_query_nodes_info(1, 1, n, l, r, nodes_info);
        
        std::vector<SetInfo> sets_info;
        sets_info.reserve(nodes_info.size());
        for(const auto& node : nodes_info) {
            sets_info.push_back({node.id, query_rmq(node.l, node.r)});
        }
        
        std::sort(sets_info.begin(), sets_info.end(), compareSetInfo);
        
        if (sets_info.size() == 1) {
            query_ans[i] = sets_info[0].id;
        } else {
            int current_set_id = sets_info[0].id;
            for (size_t j = 1; j < sets_info.size(); ++j) {
                cnt++;
                ops.push_back({current_set_id, sets_info[j].id});
                current_set_id = cnt;
            }
            query_ans[i] = current_set_id;
        }
    }
    
    std::cout << cnt << "\n";
    for (const auto& op : ops) {
        std::cout << op.first << " " << op.second << "\n";
    }
    for (int i = 0; i < q; ++i) {
        std::cout << query_ans[i] << (i == q - 1 ? "" : " ");
    }
    std::cout << "\n";
    
    return 0;
}