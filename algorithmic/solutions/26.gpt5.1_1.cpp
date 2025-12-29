#include <bits/stdc++.h>
using namespace std;

struct Node {
    int val;
    int sz;
    uint32_t prio;
    Node *l, *r, *par;
    Node(int v, uint32_t p) : val(v), sz(1), prio(p), l(nullptr), r(nullptr), par(nullptr) {}
};

mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());

inline int getsz(Node* t) { return t ? t->sz : 0; }

inline void upd(Node* t) {
    if (!t) return;
    t->sz = 1 + getsz(t->l) + getsz(t->r);
    if (t->l) t->l->par = t;
    if (t->r) t->r->par = t;
}

Node* merge(Node* a, Node* b) {
    if (!a) { if (b) b->par = nullptr; return b; }
    if (!b) { if (a) a->par = nullptr; return a; }
    if (a->prio < b->prio) {
        a->r = merge(a->r, b);
        upd(a);
        a->par = nullptr;
        return a;
    } else {
        b->l = merge(a, b->l);
        upd(b);
        b->par = nullptr;
        return b;
    }
}

void split(Node* t, int k, Node*& a, Node*& b) { // first k nodes -> a
    if (!t) {
        a = b = nullptr;
        return;
    }
    int leftSize = getsz(t->l);
    if (k <= leftSize) {
        split(t->l, k, a, t->l);
        upd(t);
        t->par = nullptr;
        b = t;
    } else {
        split(t->r, k - leftSize - 1, t->r, b);
        upd(t);
        t->par = nullptr;
        a = t;
    }
}

int getPos(Node* x) {
    int res = getsz(x->l) + 1;
    while (x->par) {
        if (x == x->par->r) {
            res += getsz(x->par->l) + 1;
        }
        x = x->par;
    }
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;
    vector<int> v(n + 1);
    for (int i = 1; i <= n; ++i) cin >> v[i];

    vector<Node*> nodes(n + 1, nullptr);
    Node* root = nullptr;

    for (int i = 1; i <= n; ++i) {
        int val = v[i];
        Node* nd = new Node(val, rng());
        nodes[val] = nd;
        root = merge(root, nd);
    }

    vector<pair<int,int>> ops;
    ops.reserve(n);
    long long sumY = 0;

    for (int i = 1; i <= n; ++i) {
        Node* nd = nodes[i];
        int posI = getPos(nd);
        if (posI == i) continue;

        ops.emplace_back(posI, i);
        sumY += i;

        Node *left, *right1, *left2, *mid, *rootWithout, *A, *B;

        split(root, posI, left, right1);          // [1..posI] | [posI+1..]
        split(left, posI - 1, left2, mid);        // [1..posI-1] | [posI]
        rootWithout = merge(left2, right1);       // removed posI

        split(rootWithout, i - 1, A, B);          // [1..i-1] | [i..]
        root = merge(merge(A, mid), B);           // insert at i
    }

    long long moves = (long long)ops.size();
    long long finalCost = (sumY + 1) * (moves + 1);

    cout << finalCost << " " << moves << '\n';
    for (auto &op : ops) {
        cout << op.first << " " << op.second << '\n';
    }

    return 0;
}