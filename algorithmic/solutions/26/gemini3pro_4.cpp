#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <ctime>

using namespace std;

// Segment Tree for Max Sum LIS
struct Node {
    int len;
    long long sum;
    int val; // the value that ends this subsequence
};

Node merge(Node a, Node b) {
    if (a.len > b.len) return a;
    if (b.len > a.len) return b;
    if (a.sum > b.sum) return a;
    return b;
}

vector<Node> tree;
int n_tree;

void update(int p, Node value) {
    p += n_tree;
    tree[p] = merge(tree[p], value); // Merge in case of re-visit (though permutation implies unique)
    for (; p > 1; p >>= 1)
        tree[p >> 1] = merge(tree[p], tree[p ^ 1]);
}

Node query(int l, int r) {
    Node res = {0, 0, 0};
    for (l += n_tree, r += n_tree; l < r; l >>= 1, r >>= 1) {
        if (l & 1) res = merge(res, tree[l++]);
        if (r & 1) res = merge(res, tree[--r]);
    }
    return res;
}

// Treap Implementation
struct TreapNode {
    int priority;
    int val;
    int size;
    int stable_cnt;
    bool is_stable;
    TreapNode *l, *r, *p;
    
    TreapNode(int v, bool s) : val(v), is_stable(s), size(1), stable_cnt(s ? 1 : 0), l(nullptr), r(nullptr), p(nullptr) {
        priority = rand();
    }
};

int get_size(TreapNode* t) { return t ? t->size : 0; }
int get_stable(TreapNode* t) { return t ? t->stable_cnt : 0; }

void update_node(TreapNode* t) {
    if (t) {
        t->size = 1 + get_size(t->l) + get_size(t->r);
        t->stable_cnt = (t->is_stable ? 1 : 0) + get_stable(t->l) + get_stable(t->r);
        if (t->l) t->l->p = t;
        if (t->r) t->r->p = t;
    }
}

void split(TreapNode* t, int k, TreapNode*& l, TreapNode*& r) {
    if (!t) { l = r = nullptr; return; }
    if (t->p) t->p = nullptr; 
    
    int left_size = get_size(t->l);
    if (left_size < k) {
        split(t->r, k - left_size - 1, t->r, r);
        l = t;
    } else {
        split(t->l, k, l, t->l);
        r = t;
    }
    update_node(t);
}

void merge(TreapNode*& t, TreapNode* l, TreapNode* r) {
    if (!l || !r) t = l ? l : r;
    else if (l->priority > r->priority) {
        merge(l->r, l->r, r);
        t = l;
    } else {
        merge(r->l, l, r->l);
        t = r;
    }
    update_node(t);
}

int get_index(TreapNode* t) {
    int idx = get_size(t->l);
    while (t->p) {
        if (t == t->p->r) {
            idx += get_size(t->p->l) + 1;
        }
        t = t->p;
    }
    return idx + 1;
}

// Find the position of the k-th stable element (1-based k)
// Returns the index of that element in the implicit array
int find_kth_stable_pos(TreapNode* t, int k) {
    if (!t) return 0;
    int l_stable = get_stable(t->l);
    if (l_stable >= k) {
        return find_kth_stable_pos(t->l, k);
    }
    if (l_stable + (t->is_stable ? 1 : 0) == k && t->is_stable) {
        return get_size(t->l) + 1;
    }
    return get_size(t->l) + 1 + find_kth_stable_pos(t->r, k - l_stable - (t->is_stable ? 1 : 0));
}

TreapNode* remove_at(TreapNode*& root, int idx) {
    TreapNode *t1, *t2, *t3;
    split(root, idx, t2, t3);
    split(t2, idx - 1, t1, t2);
    merge(root, t1, t3);
    if (t2) t2->p = nullptr;
    return t2;
}

void insert_at(TreapNode*& root, int idx, TreapNode* node) {
    TreapNode *t1, *t2;
    split(root, idx - 1, t1, t2);
    merge(t1, t1, node);
    merge(root, t1, t2);
}

// Fenwick Tree
vector<int> bit;
int n_val;
void bit_add(int idx, int val) {
    for (; idx <= n_val; idx += idx & -idx) bit[idx] += val;
}
int bit_query(int idx) {
    int sum = 0;
    for (; idx > 0; idx -= idx & -idx) sum += bit[idx];
    return sum;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    srand(time(NULL));

    int n;
    if (!(cin >> n)) return 0;

    vector<int> v(n);
    for (int i = 0; i < n; i++) cin >> v[i];

    // 1. Max Sum LIS
    n_tree = n + 1;
    tree.resize(2 * n_tree, {0, 0, 0});
    vector<int> parent(n + 1, 0);

    for (int x : v) {
        Node best = query(0, x);
        parent[x] = best.val;
        Node current = {best.len + 1, best.sum + x, x};
        update(x, current);
    }

    Node res = query(0, n + 1);
    
    vector<bool> is_fixed(n + 1, false);
    int curr = res.val;
    while (curr != 0) {
        is_fixed[curr] = true;
        curr = parent[curr];
    }

    // 2. Setup Move Processing
    vector<int> move_vals;
    for (int x : v) {
        if (!is_fixed[x]) move_vals.push_back(x);
    }
    sort(move_vals.rbegin(), move_vals.rend());

    // 3. Initialize Treap and BIT
    TreapNode* root = nullptr;
    vector<TreapNode*> pointers(n + 1);
    for (int x : v) {
        TreapNode* node = new TreapNode(x, is_fixed[x]);
        pointers[x] = node;
        merge(root, root, node);
    }

    n_val = n;
    bit.assign(n + 1, 0);
    for (int i = 1; i <= n; i++) {
        if (is_fixed[i]) bit_add(i, 1);
    }

    // 4. Simulate
    long long total_move_cost = 0;
    vector<pair<int, int>> moves;

    for (int val : move_vals) {
        int current_pos = get_index(pointers[val]);
        int cnt_smaller = bit_query(val - 1);
        
        int target_pos = 1;
        if (cnt_smaller > 0) {
            target_pos = find_kth_stable_pos(root, cnt_smaller) + 1;
        }

        total_move_cost += target_pos;
        moves.push_back({current_pos, target_pos});

        TreapNode* node = remove_at(root, current_pos);
        node->is_stable = true;
        node->stable_cnt = 1;
        insert_at(root, target_pos, node);
        
        bit_add(val, 1);
    }

    long long final_cost = (total_move_cost + 1) * (moves.size() + 1);
    cout << final_cost << " " << moves.size() << "\n";
    for (auto p : moves) {
        cout << p.first << " " << p.second << "\n";
    }

    return 0;
}