#include <bits/stdc++.h>
using namespace std;

typedef long long ll;

mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

struct Node {
    int val, prio, size;
    Node *l, *r, *p;
    Node(int v) : val(v), prio(rng()), size(1), l(nullptr), r(nullptr), p(nullptr) {}
};

int size(Node* t) { return t ? t->size : 0; }
void upd(Node* t) {
    if (!t) return;
    t->size = 1 + size(t->l) + size(t->r);
    if (t->l) t->l->p = t;
    if (t->r) t->r->p = t;
}

void split(Node* t, int k, Node*& left, Node*& right) {
    if (!t) { left = right = nullptr; return; }
    int left_size = size(t->l);
    if (k <= left_size) {
        split(t->l, k, left, t->l);
        right = t;
        if (left) left->p = nullptr;
        if (t->l) t->l->p = t;
        upd(t);
    } else {
        split(t->r, k - left_size - 1, t->r, right);
        left = t;
        if (right) right->p = nullptr;
        if (t->r) t->r->p = t;
        upd(t);
    }
}

Node* merge(Node* left, Node* right) {
    if (!left) return right;
    if (!right) return left;
    if (left->prio > right->prio) {
        left->r = merge(left->r, right);
        if (left->r) left->r->p = left;
        upd(left);
        return left;
    } else {
        right->l = merge(left, right->l);
        if (right->l) right->l->p = right;
        upd(right);
        return right;
    }
}

int get_pos(Node* node) {
    int pos = 1 + size(node->l);
    while (node->p) {
        if (node == node->p->r) {
            pos += 1 + size(node->p->l);
        }
        node = node->p;
    }
    return pos;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    int n;
    cin >> n;
    vector<int> v(n);
    for (int i = 0; i < n; ++i) {
        cin >> v[i];
    }
    
    vector<Node*> node_ptr(n+1, nullptr);
    Node* root = nullptr;
    for (int i = 0; i < n; ++i) {
        Node* nd = new Node(v[i]);
        node_ptr[v[i]] = nd;
        root = merge(root, nd);
    }
    
    ll total_cost = 0;
    vector<pair<int,int>> moves;
    
    for (int i = 1; i <= n; ++i) {
        Node* node = node_ptr[i];
        int x = get_pos(node);
        if (x == i) continue;
        total_cost += i;
        moves.emplace_back(x, i);
        
        Node *A, *B, *C;
        split(root, x-1, A, B);   // A = [1..x-1], B = [x..n]
        split(B, 1, B, C);        // B = node at x, C = [x+1..n]
        Node* T = merge(A, C);    // tree without B, size n-1
        Node *L, *R;
        split(T, i-1, L, R);      // L = [1..i-1], R = [i..n-1]
        root = merge(merge(L, B), R);
    }
    
    ll final_cost = (total_cost + 1) * (moves.size() + 1);
    cout << final_cost << " " << moves.size() << "\n";
    for (auto& [x, y] : moves) {
        cout << x << " " << y << "\n";
    }
    
    return 0;
}