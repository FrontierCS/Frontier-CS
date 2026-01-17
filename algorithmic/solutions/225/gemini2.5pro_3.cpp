#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>

using namespace std;

const int MAX_SETS = 2200005;

int n, q;
int a[4097];

int f[MAX_SETS], g[MAX_SETS];
vector<pair<int, int>> ops;
int cnt;

int new_set(int u, int v) {
    if (u == 0) return v;
    if (v == 0) return u;
    
    if (g[u] < f[v]) {
        ops.push_back({u, v});
    } else {
        ops.push_back({v, u});
    }
    
    cnt++;
    f[cnt] = min(f[u], f[v]);
    g[cnt] = max(g[u], g[v]);
    return cnt;
}

struct Node {
    Node *l = nullptr, *r = nullptr;
    int set_id = 0;
};

Node* val_trees[MAX_SETS];
map<pair<int, int>, int> union_memo;

Node* build_val_tree(int val, int set_id, int v_min, int v_max) {
    Node* node = new Node();
    if (v_min == v_max) {
        node->set_id = set_id;
        return node;
    }
    int v_mid = v_min + (v_max - v_min) / 2;
    if (val <= v_mid) {
        node->l = build_val_tree(val, set_id, v_min, v_mid);
    } else {
        node->r = build_val_tree(val, set_id, v_mid + 1, v_max);
    }
    node->set_id = new_set(node->l ? node->l->set_id : 0, node->r ? node->r->set_id : 0);
    return node;
}

Node* union_trees(Node* n1, Node* n2) {
    if (!n1) return n2;
    if (!n2) return n1;

    Node* new_node = new Node();
    
    new_node->l = union_trees(n1->l, n2->l);
    new_node->r = union_trees(n1->r, n2->r);
    
    if (!new_node->l && !new_node->r) { // Leaf
        new_node->set_id = new_set(n1->set_id, n2->set_id);
    } else {
        new_node->set_id = new_set(new_node->l ? new_node->l->set_id : 0, new_node->r ? new_node->r->set_id : 0);
    }
    return new_node;
}

int do_union(int id1, int id2) {
    if (id1 == 0) return id2;
    if (id2 == 0) return id1;
    if (id1 > id2) swap(id1, id2);
    if (union_memo.count({id1, id2})) {
        return union_memo[{id1, id2}];
    }
    
    Node* combined_tree = union_trees(val_trees[id1], val_trees[id2]);
    val_trees[combined_tree->set_id] = combined_tree;
    return union_memo[{id1, id2}] = combined_tree->set_id;
}


int st[13][4097];
int log_table[4097];

void precompute() {
    log_table[1] = 0;
    for (int i = 2; i <= n; i++) {
        log_table[i] = log_table[i / 2] + 1;
    }

    for (int i = 1; i <= n; i++) {
        st[0][i] = i;
        val_trees[i] = build_val_tree(a[i], i, 1, n);
    }

    for (int k = 1; (1 << k) <= n; k++) {
        for (int i = 1; i + (1 << k) - 1 <= n; i++) {
            st[k][i] = do_union(st[k - 1][i], st[k - 1][i + (1 << (k - 1))]);
        }
    }
}

int query(int l, int r) {
    int len = r - l + 1;
    int k = log_table[len];
    return do_union(st[k][l], st[k][r - (1 << k) + 1]);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n >> q;
    for (int i = 1; i <= n; i++) {
        cin >> a[i];
        f[i] = g[i] = a[i];
    }
    cnt = n;

    vector<pair<int, int>> queries(q);
    for (int i = 0; i < q; i++) {
        cin >> queries[i].first >> queries[i].second;
    }

    precompute();

    vector<int> ans(q);
    for (int i = 0; i < q; i++) {
        ans[i] = query(queries[i].first, queries[i].second);
    }

    cout << cnt << "\n";
    for (const auto& op : ops) {
        cout << op.first << " " << op.second << "\n";
    }
    for (int i = 0; i < q; i++) {
        cout << ans[i] << (i == q - 1 ? "" : " ");
    }
    cout << "\n";

    return 0;
}