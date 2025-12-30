#include <bits/stdc++.h>
using namespace std;

struct Node {
    int val;
    uint32_t pr;
    int sz;
    Node *l, *r, *p;
    Node(int v, uint32_t _pr) : val(v), pr(_pr), sz(1), l(nullptr), r(nullptr), p(nullptr) {}
};

inline int getsz(Node* t) { return t ? t->sz : 0; }

inline void upd(Node* t) {
    if (!t) return;
    t->sz = 1 + getsz(t->l) + getsz(t->r);
    if (t->l) t->l->p = t;
    if (t->r) t->r->p = t;
}

Node* merge(Node* l, Node* r) {
    if (!l) {
        if (r) r->p = nullptr;
        return r;
    }
    if (!r) {
        if (l) l->p = nullptr;
        return l;
    }
    if (l->pr > r->pr) {
        l->r = merge(l->r, r);
        if (l->r) l->r->p = l;
        upd(l);
        l->p = nullptr;
        return l;
    } else {
        r->l = merge(l, r->l);
        if (r->l) r->l->p = r;
        upd(r);
        r->p = nullptr;
        return r;
    }
}

void split(Node* t, int k, Node* &l, Node* &r) {
    if (!t) {
        l = r = nullptr;
        return;
    }
    if (getsz(t->l) >= k) {
        split(t->l, k, l, t->l);
        if (t->l) t->l->p = t;
        t->p = nullptr;
        upd(t);
        r = t;
    } else {
        split(t->r, k - getsz(t->l) - 1, t->r, r);
        if (t->r) t->r->p = t;
        t->p = nullptr;
        upd(t);
        l = t;
    }
}

int getPos(Node* x) {
    int res = getsz(x->l) + 1;
    while (x->p) {
        if (x == x->p->r) {
            res += getsz(x->p->l) + 1;
        }
        x = x->p;
    }
    return res;
}

void move_element(Node* &root, int x, int y) {
    if (x == y) return;
    Node *A, *B, *C, *D, *E, *L, *R;
    split(root, x - 1, A, B);     // A: [1..x-1], B: [x..]
    split(B, 1, C, D);            // C: element at x, D: rest
    E = merge(A, D);              // array after removal
    split(E, y - 1, L, R);        // insert position y
    root = merge(merge(L, C), R);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;
    vector<int> v(n + 1);
    for (int i = 1; i <= n; ++i) cin >> v[i];

    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    vector<Node*> nodeOfVal(n + 1, nullptr);
    Node* root = nullptr;

    for (int i = 1; i <= n; ++i) {
        Node* cur = new Node(v[i], rng());
        nodeOfVal[v[i]] = cur;
        root = merge(root, cur);
    }

    vector<pair<int,int>> ops;
    ops.reserve(n);
    long long sumY = 0;
    int moves = 0;

    for (int val = 1; val <= n; ++val) {
        Node* u = nodeOfVal[val];
        int x = getPos(u);
        int y = val;
        if (x == y) continue;
        move_element(root, x, y);
        ops.push_back({x, y});
        sumY += y;
        ++moves;
    }

    long long finalCost = (sumY + 1) * ( (long long)moves + 1 );

    cout << finalCost << " " << moves << "\n";
    for (auto &op : ops) {
        cout << op.first << " " << op.second << "\n";
    }

    return 0;
}