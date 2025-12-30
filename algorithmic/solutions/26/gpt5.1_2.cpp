#include <bits/stdc++.h>
using namespace std;

struct Node {
    int val;
    int prio;
    int sz;
    Node *l, *r, *par;
};

inline int getsz(Node* t) { return t ? t->sz : 0; }

inline void upd(Node* t) {
    if (!t) return;
    t->sz = 1 + getsz(t->l) + getsz(t->r);
}

Node* merge(Node* a, Node* b) {
    if (!a) {
        if (b) b->par = nullptr;
        return b;
    }
    if (!b) {
        if (a) a->par = nullptr;
        return a;
    }
    if (a->prio > b->prio) {
        Node* r = merge(a->r, b);
        a->r = r;
        if (r) r->par = a;
        upd(a);
        a->par = nullptr;
        return a;
    } else {
        Node* l = merge(a, b->l);
        b->l = l;
        if (l) l->par = b;
        upd(b);
        b->par = nullptr;
        return b;
    }
}

void split(Node* t, int k, Node*& a, Node*& b) {
    if (!t) {
        a = b = nullptr;
        return;
    }
    if (getsz(t->l) >= k) {
        split(t->l, k, a, t->l);
        if (t->l) t->l->par = t;
        b = t;
        b->par = nullptr;
        upd(b);
    } else {
        split(t->r, k - getsz(t->l) - 1, t->r, b);
        if (t->r) t->r->par = t;
        a = t;
        a->par = nullptr;
        upd(a);
    }
}

int getIndex(Node* node) {
    int res = getsz(node->l) + 1;
    while (node->par) {
        if (node == node->par->r) {
            res += getsz(node->par->l) + 1;
        }
        node = node->par;
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

    vector<Node*> ptr(n + 1, nullptr);
    vector<Node> pool(n + 1);
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    Node* root = nullptr;
    for (int i = 1; i <= n; ++i) {
        Node* node = &pool[i];
        node->val = v[i];
        node->prio = rng();
        node->sz = 1;
        node->l = node->r = node->par = nullptr;
        ptr[v[i]] = node;
        root = merge(root, node);
    }

    vector<pair<int,int>> moves;
    moves.reserve(n);
    long long totalCost = 0;

    for (int i = 1; i <= n; ++i) {
        Node* node = ptr[i];
        int pos = getIndex(node);
        if (pos == i) continue; // already in place
        // pos > i always holds by invariant
        int x = pos, y = i;

        // Perform move x -> y (x > y)
        Node *left, *midplus, *middle, *rightplus, *nodeSeg, *right;
        split(root, y - 1, left, midplus);                  // [1..y-1], [y..n]
        split(midplus, x - y, middle, rightplus);           // [y..x-1], [x..n]
        split(rightplus, 1, nodeSeg, right);                // [x], [x+1..n]
        root = merge(left, merge(nodeSeg, merge(middle, right)));

        moves.emplace_back(x, y);
        totalCost += y;
    }

    long long m = (long long)moves.size();
    long long finalCost = (totalCost + 1) * (m + 1);

    cout << finalCost << " " << moves.size() << "\n";
    for (auto &op : moves) {
        cout << op.first << " " << op.second << "\n";
    }

    return 0;
}