#include <bits/stdc++.h>
using namespace std;

const int MAXN = 300000;

// ----------------- Segment Tree for LIS with max sum -----------------
struct SegNode {
    int len;
    long long sum;
    int idx; // index in the original array (1-based) where this best ends
};

SegNode tree[4 * MAXN + 5];
SegNode null_node = {0, 0, 0};

SegNode combine(SegNode a, SegNode b) {
    if (a.len != b.len) return a.len > b.len ? a : b;
    if (a.sum != b.sum) return a.sum > b.sum ? a : b;
    return a; // tie - keep a
}

void seg_update(int v, int tl, int tr, int pos, SegNode val) {
    if (tl == tr) {
        if (combine(val, tree[v]) == val) // val is better
            tree[v] = val;
    } else {
        int tm = (tl + tr) / 2;
        if (pos <= tm)
            seg_update(v*2, tl, tm, pos, val);
        else
            seg_update(v*2+1, tm+1, tr, pos, val);
        tree[v] = combine(tree[v*2], tree[v*2+1]);
    }
}

SegNode seg_query(int v, int tl, int tr, int l, int r) {
    if (l > r) return null_node;
    if (l == tl && r == tr) return tree[v];
    int tm = (tl + tr) / 2;
    return combine(seg_query(v*2, tl, tm, l, min(r, tm)),
                   seg_query(v*2+1, tm+1, tr, max(l, tm+1), r));
}
// --------------------------------------------------------------------

// ----------------- Treap for dynamic sequence -----------------
struct Node {
    int val;
    int prio;
    int sz;
    Node *l, *r, *p;
    Node(int v) : val(v), prio(rand()), sz(1), l(nullptr), r(nullptr), p(nullptr) {}
};

int size(Node *n) { return n ? n->sz : 0; }

void update(Node *n) {
    if (!n) return;
    n->sz = 1 + size(n->l) + size(n->r);
    if (n->l) n->l->p = n;
    if (n->r) n->r->p = n;
}

void split(Node *t, int k, Node* &L, Node* &R) {
    if (!t) { L = R = nullptr; return; }
    int left_size = size(t->l);
    if (k <= left_size) {
        split(t->l, k, L, t->l);
        R = t;
        if (L) L->p = nullptr;
        if (t->l) t->l->p = t;
    } else {
        split(t->r, k - left_size - 1, t->r, R);
        L = t;
        if (R) R->p = nullptr;
        if (t->r) t->r->p = t;
    }
    update(t);
}

Node* merge(Node *L, Node *R) {
    if (!L || !R) return L ? L : R;
    if (L->prio > R->prio) {
        L->r = merge(L->r, R);
        update(L);
        if (L->r) L->r->p = L;
        return L;
    } else {
        R->l = merge(L, R->l);
        update(R);
        if (R->l) R->l->p = R;
        return R;
    }
}

int get_rank(Node *node) {
    int rank = size(node->l) + 1;
    while (node->p) {
        if (node == node->p->r)
            rank += size(node->p->l) + 1;
        node = node->p;
    }
    return rank;
}
// -------------------------------------------------------------

int v[MAXN+1];
int prev_idx[MAXN+1]; // for LIS reconstruction
bool in_S[MAXN+1];
int cnt_smaller[MAXN+1];
Node* node_ptr[MAXN+1];

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    srand(time(0));

    int n;
    cin >> n;
    for (int i = 1; i <= n; i++)
        cin >> v[i];

    // -------- Compute LIS with maximum sum --------
    fill(tree, tree+4*MAXN+5, null_node);
    SegNode best_global = null_node;
    int best_global_idx = 0;

    for (int i = 1; i <= n; i++) {
        int x = v[i];
        SegNode best_prev;
        if (x == 1)
            best_prev = null_node;
        else
            best_prev = seg_query(1, 1, n, 1, x-1);
        SegNode cur = {best_prev.len + 1, best_prev.sum + x, i};
        prev_idx[i] = best_prev.idx;
        seg_update(1, 1, n, x, cur);

        // update global best
        if (combine(cur, best_global) == cur) {
            best_global = cur;
            best_global_idx