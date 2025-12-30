#include <bits/stdc++.h>
using namespace std;

struct Node {
    int val;
    uint32_t prio;
    int sz;
    Node *l, *r, *p;
    Node(int v, uint32_t pr): val(v), prio(pr), sz(1), l(nullptr), r(nullptr), p(nullptr) {}
};

inline int sz(Node* t){ return t ? t->sz : 0; }
inline void upd(Node* t){
    if(!t) return;
    t->sz = 1 + sz(t->l) + sz(t->r);
    if(t->l) t->l->p = t;
    if(t->r) t->r->p = t;
}

pair<Node*, Node*> split(Node* t, int k){
    if(!t) return {nullptr, nullptr};
    if(sz(t->l) >= k){
        auto pr = split(t->l, k);
        t->l = pr.second;
        upd(t);
        if(pr.first) pr.first->p = nullptr;
        if(t) t->p = nullptr;
        return {pr.first, t};
    }else{
        auto pr = split(t->r, k - sz(t->l) - 1);
        t->r = pr.first;
        upd(t);
        if(t) t->p = nullptr;
        if(pr.second) pr.second->p = nullptr;
        return {t, pr.second};
    }
}

Node* merge(Node* a, Node* b){
    if(!a) { if(b) b->p = nullptr; return b; }
    if(!b) { if(a) a->p = nullptr; return a; }
    if(a->prio > b->prio){
        a->r = merge(a->r, b);
        upd(a);
        a->p = nullptr;
        return a;
    }else{
        b->l = merge(a, b->l);
        upd(b);
        b->p = nullptr;
        return b;
    }
}

int getIndex(Node* u){
    int idx = sz(u->l) + 1;
    while(u->p){
        if(u == u->p->r) idx += sz(u->p->l) + 1;
        u = u->p;
    }
    return idx;
}

// Move element at index x to position y (1-indexed). Assumes x != y.
Node* moveIndex(Node* root, int x, int y){
    // remove at x
    Node *A, *BC;
    tie(A, BC) = split(root, x - 1);
    Node *X, *C;
    tie(X, C) = split(BC, 1);
    Node* without = merge(A, C);
    // insert at y
    Node *L, *R;
    tie(L, R) = split(without, y - 1);
    root = merge(merge(L, X), R);
    return root;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if(!(cin >> n)) return 0;
    vector<int> v(n+1);
    for(int i=1;i<=n;i++) cin >> v[i];

    // Build treap
    std::mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());
    vector<Node*> nodeOf(n+1, nullptr);
    Node* root = nullptr;
    for(int i=1;i<=n;i++){
        Node* nd = new Node(v[i], rng());
        nodeOf[v[i]] = nd;
        root = merge(root, nd);
    }

    long long sum_cost = 0;
    vector<pair<int,int>> moves;

    int last_pos = getIndex(nodeOf[n]); // position of value n
    for(int j = n-1; j >= 1; --j){
        Node* nd = nodeOf[j];
        int x = getIndex(nd);
        if(x > last_pos){
            root = moveIndex(root, x, last_pos);
            moves.push_back({x, last_pos});
            sum_cost += last_pos;
            // last_pos remains the same (new start is j at last_pos)
        }else{
            last_pos = x;
        }
    }

    long long m = (long long)moves.size();
    long long final_cost = (sum_cost + 1) * (m + 1);

    cout << final_cost << " " << moves.size() << "\n";
    for(auto &op : moves){
        cout << op.first << " " << op.second << "\n";
    }
    return 0;
}