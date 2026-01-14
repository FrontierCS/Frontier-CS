#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

// Using 1-based indexing for problem entities, 0 for special values (e.g., empty set ID)

const int MAXN_VAL = 1 << 12; // n <= 2^12 = 4096
const int MAX_NODES_PST = MAXN_VAL * 15; // A safe upper bound for PST nodes

struct Node {
    int l_child, r_child;
    int set_id;
};

int n, q;
int a[MAXN_VAL + 1];
int pos[MAXN_VAL + 1];

Node pst_nodes[MAX_NODES_PST];
int pst_node_count = 0;

int roots[MAXN_VAL + 1];

std::vector<std::pair<int, int>> merges;
int current_set_id;

int new_pst_node() {
    return ++pst_node_count;
}

int merge_sets(int u, int v) {
    if (u == 0) return v;
    if (v == 0) return u;
    current_set_id++;
    merges.push_back({u, v});
    return current_set_id;
}

int build_pst(int tl, int tr) {
    int curr_idx = new_pst_node();
    pst_nodes[curr_idx] = {0, 0, 0};
    if (tl == tr) {
        return curr_idx;
    }
    int tm = tl + (tr - tl) / 2;
    pst_nodes[curr_idx].l_child = build_pst(tl, tm);
    pst_nodes[curr_idx].r_child = build_pst(tm + 1, tr);
    return curr_idx;
}

int update_pst(int prev_node_idx, int tl, int tr, int val_to_add) {
    int curr_idx = new_pst_node();
    pst_nodes[curr_idx] = pst_nodes[prev_node_idx];

    if (tl == tr) {
        pst_nodes[curr_idx].set_id = pos[val_to_add];
        return curr_idx;
    }

    int tm = tl + (tr - tl) / 2;
    if (val_to_add <= tm) {
        pst_nodes[curr_idx].l_child = update_pst(pst_nodes[prev_node_idx].l_child, tl, tm, val_to_add);
    } else {
        pst_nodes[curr_idx].r_child = update_pst(pst_nodes[prev_node_idx].r_child, tm + 1, tr, val_to_add);
    }
    
    int left_set_id = pst_nodes[pst_nodes[curr_idx].l_child].set_id;
    int right_set_id = pst_nodes[pst_nodes[curr_idx].r_child].set_id;
    pst_nodes[curr_idx].set_id = merge_sets(left_set_id, right_set_id);
    return curr_idx;
}

int query_pst(int u_node_idx, int v_node_idx, int tl, int tr) {
    if (pst_nodes[u_node_idx].set_id == pst_nodes[v_node_idx].set_id) {
        return 0; // No new elements in this value range
    }
    if (tl == tr) {
        return pst_nodes[u_node_idx].set_id;
    }

    int tm = tl + (tr - tl) / 2;
    int left_set = query_pst(pst_nodes[u_node_idx].l_child, pst_nodes[v_node_idx].l_child, tl, tm);
    int right_set = query_pst(pst_nodes[u_node_idx].r_child, pst_nodes[v_node_idx].r_child, tm + 1, tr);

    return merge_sets(left_set, right_set);
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> n >> q;
    for (int i = 1; i <= n; ++i) {
        std::cin >> a[i];
        pos[a[i]] = i;
    }

    current_set_id = n;
    
    roots[0] = build_pst(1, n);
    for (int i = 1; i <= n; ++i) {
        roots[i] = update_pst(roots[i-1], 1, n, a[i]);
    }

    std::vector<int> query_results(q);
    for (int i = 0; i < q; ++i) {
        int l, r;
        std::cin >> l >> r;
        query_results[i] = query_pst(roots[r], roots[l-1], 1, n);
    }

    std::cout << current_set_id << "\n";
    for (const auto& p : merges) {
        std::cout << p.first << " " << p.second << "\n";
    }
    for (int i = 0; i < q; ++i) {
        std::cout << query_results[i] << (i == q - 1 ? "" : " ");
    }
    std::cout << "\n";

    return 0;
}