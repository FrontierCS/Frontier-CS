#include <bits/stdc++.h>
using namespace std;

struct Node {
    int val;
    uint32_t prior;
    int sz;
    Node *l, *r, *p;
    Node(int v, uint32_t pr) : val(v), prior(pr), sz(1), l(nullptr), r(nullptr), p(nullptr) {}
};

inline int getsz(Node* x) { return x ? x->sz : 0; }

inline void upd(Node* x) {
    if (x) {
        x->sz = 1 + getsz(x->l) + getsz(x->r);
    }
}

void split(Node* root, int k, Node* &left, Node* &right) {
    if (!root) { left = right = nullptr; return; }
    if (k <= getsz(root->l)) {
        split(root->l, k, left, root->l);
        if (root->l) root->l->p = root;
        upd(root);
        right = root;
        right->p = nullptr;
    } else {
        split(root->r, k - getsz(root->l) - 1, root->r, right);
        if (root->r) root->r->p = root;
        upd(root);
        left = root;
        left->p = nullptr;
    }
}

Node* merge(Node* left, Node* right) {
    if (!left || !right) {
        Node* res = left ? left : right;
        if (res) res->p = nullptr;
        return res;
    }
    if (left->prior < right->prior) {
        left->r = merge(left->r, right);
        if (left->r) left->r->p = left;
        upd(left);
        left->p = nullptr;
        return left;
    } else {
        right->l = merge(left, right->l);
        if (right->l) right->l->p = right;
        upd(right);
        right->p = nullptr;
        return right;
    }
}

int getIndex(Node* x) {
    int idx = getsz(x->l) + 1;
    while (x->p) {
        if (x == x->p->r) {
            idx += getsz(x->p->l) + 1;
        }
        x = x->p;
    }
    return idx;
}

// Move element from position x to position y (x > y)
void moveLeft(Node* &root, int x, int y) {
    if (x == y) return;
    Node *left, *temp;
    split(root, x - 1, left, temp);       // left: 1..x-1, temp: x..n
    Node *mid, *right;
    split(temp, 1, mid, right);           // mid: x, right: x+1..n
    Node *l1, *l2;
    split(left, y - 1, l1, l2);           // l1:1..y-1, l2:y..x-1
    root = merge(l1, mid);
    root = merge(root, l2);
    root = merge(root, right);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;
    vector<int> v(n + 1);
    for (int i = 1; i <= n; ++i) cin >> v[i];

    static mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());

    Node* root = nullptr;
    vector<Node*> byVal(n + 1);

    for (int i = 1; i <= n; ++i) {
        Node* node = new Node(v[i], rng());
        byVal[v[i]] = node;
        root = merge(root, node);
    }

    long long totalCost = 0;
    vector<pair<int,int>> moves;
    moves.reserve(n);

    for (int val = 1; val <= n; ++val) {
        Node* node = byVal[val];
        int pos = getIndex(node);
        if (pos > val) {
            moves.emplace_back(pos, val);
            totalCost += val;
            moveLeft(root, pos, val);
        }
    }

    long long m = (long long)moves.size();
    long long finalCost = (totalCost + 1) * (m + 1);

    cout << finalCost << " " << m << "\n";
    for (auto &op : moves) {
        cout << op.first << " " << op.second << "\n";
    }

    return 0;
}